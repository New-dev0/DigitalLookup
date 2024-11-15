import os, asyncio
from abc import ABC, abstractmethod
from typing import Union, Dict, List
from logging import Logger
from os.path import splitext
from playwright.async_api import (
    async_playwright,
    Playwright,
    Browser,
    TimeoutError,
    Page,
)
from browserforge.injectors.playwright import AsyncNewContext
from service.config import get_config
from browserforge.fingerprints.generator import FingerprintGenerator
from fastapi import WebSocket
from aiohttp import ClientSession

generator = FingerprintGenerator()


class Connector(ABC):
    service: str
    logger: Logger

    def __init__(self, username: str, websocket: WebSocket) -> None:
        super().__init__()

        self.last_active_timestamp = None
        self.websocket = websocket
        self.username = username

    @abstractmethod
    async def get_api_data(self):
        raise NotImplementedError("Method not implemented")

    @abstractmethod
    async def process_data(
        self, output_path: str, store_api_responses: bool = True, in_depth: bool = False
    ):
        raise NotImplementedError("Method not implemented")

    async def send_data(self, data: dict):
        if self.websocket:
            await self.websocket.send_json({"service": self.service, "data": data})
        return

    async def capture_page(
        self,
        browser: Browser,
        page_url: Union[str, Dict[str, str]] = None,
        screenshot_path: str = None,
        device_targets: List[str] = None,
        fn=None,
        handler=None,
    ):
        if not device_targets:
            device_targets = get_config("device_targets", ["desktop", "android"])

        images = []

        cl = fn or self.__capture_page
        if "desktop" in device_targets:
            images.extend(await cl(browser, page_url, screenshot_path, handler=handler))

        if "android" in device_targets:
            images.extend(
                await cl(
                    browser, page_url, screenshot_path, mobile=True, handler=handler
                )
            )

        return images

    @property
    def full_page(self):
        return get_config("capture_full_page", False)

    async def __capture_page(
        self,
        browser: Browser,
        page_url: str,
        screenshot_path: str = None,
        mobile: bool = False,
        handler=None,
    ):
        """
        Capture a screenshot of the page and return the path to the screenshot.
        """
        full_page = self.full_page

        if mobile:
            context = await AsyncNewContext(
                browser, fingerprint=generator.generate(device=("mobile",))
            )
            page = await context.new_page()
        else:
            page = await browser.new_page()

        outputs = []
        if isinstance(page_url, str):
            page_url = {page_url: screenshot_path}

        for url, path in page_url.items():
            os.makedirs(os.path.dirname(path), exist_ok=True)

            screen_path, extension = splitext(path)
            actual_path = (
                screen_path + "_" + ("mobile" if mobile else "desktop") + extension
            )
            if handler:
                await handler(page)

            try:
                await page.goto(url, wait_until="networkidle", timeout=10000)
            except TimeoutError:
                pass
            await page.screenshot(path=actual_path, full_page=full_page)
            outputs.append(os.path.abspath(actual_path))

        await page.close()
        return outputs

    async def download_image(self, image_url: str, output_path: str):
        """
        Download an image from the given URL and return the path to the image.
        """
        async with ClientSession() as session:
            async with session.get(image_url) as response:
                with open(output_path, "wb") as f:
                    f.write(await response.read())

        return output_path

    async def get_page_height(self, page: Page) -> int:
        """
        Get the height of the page.
        """
        return await page.evaluate("document.body.scrollHeight")

    async def get_client_height(self, page: Page) -> int:
        """
        Get the height of the client.
        """
        return await page.evaluate("window.innerHeight")

    async def scroll_to(self, page: Page, y: int):
        """
        Scroll to the given y coordinate.
        """
        await page.evaluate(f"window.scrollTo(0, {y})")

    async def post_task(self):
        pass

    async def capture_bulk_page(
        self, page: Page, max_screenshots: int, path: str, message: str
    ):
        """
        Capture a screenshot of the page at the given y coordinate.
        """
        os.makedirs(path, exist_ok=True)

        await self.send_data({"key": "message", "data": message})

        maxHeight = await self.get_page_height(page)
        clientHeight = await self.get_client_height(page)
        screenshots = []

        for i in range(0, maxHeight, clientHeight):
            if len(screenshots) >= max_screenshots:
                break

            self.logger.info(f"Capturing screenshot at {i}")

            await self.scroll_to(page, i)
            maxHeight = await self.get_page_height(page)
            ssPath = os.path.join(path, f"screen-{i}.png")

            await page.wait_for_load_state("domcontentloaded")
            await page.screenshot(path=ssPath)

            screenshots.append(os.path.abspath(ssPath))
            await asyncio.sleep(0.5)

        await self.send_data({"key": "message", "data": ""})

        return screenshots
