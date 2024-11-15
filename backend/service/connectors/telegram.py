import os
import json
from aiohttp import ClientSession
from .abstract import Connector
from bs4 import BeautifulSoup
from logging import getLogger
from fastapi import WebSocket
from playwright.async_api import async_playwright, Playwright, Browser, TimeoutError
from service.parsers import extract_usernames
from service.config import get_config


class Telegram(Connector):
    service = "telegram"
    logger = getLogger(service)

    def __init__(self, username: str, websocket: WebSocket) -> None:
        super().__init__(username, websocket)

    def parse_data(self, data: str):
        self.logger.info(f"Parsing data for {self.username}")

        responseData = {}
        soup = BeautifulSoup(data, "html.parser")
        name = soup.find("div", "tgme_page_title")
        if name:
            responseData["name"] = name.text
        description = soup.find("div", "tgme_page_description")
        if description:
            responseData["description"] = description.text
        image_url = soup.find("img", "tgme_page_photo_image")
        if image_url:
            responseData["image_url"] = image_url.get("src")
        extra = soup.find("div", "tgme_page_extra")
        extraText = extra.text if extra else ""

        responseData["meta"] = extraText
        if "members" in extraText:
            responseData["type"] = "group"
        elif "subscribers" in extraText:
            responseData["type"] = "channel"
        else:
            responseData["type"] = "user"
        return responseData

    async def get_api_data(self, username: str):
        self.logger.info(f"Getting API data for {username}")
        async with ClientSession() as session:
            data = await session.get(f"https://t.me/{username}")
            responseData = self.parse_data(await data.read())
        return responseData

    async def process_data(
        self,
        output_path: str,
        store_api_responses: bool = True,
        browser: Browser = None,
        in_depth: bool = False,
    ):
        self.logger.info(f"Processing data for {self.username}")
        path = os.path.join(output_path, f"{self.service}/{self.username}")
        os.makedirs(path, exist_ok=True)

        if store_api_responses:
            json_path = os.path.join(path, "api_data.json")
            api_data = await self.get_api_data(self.username)
            await self.send_data({"key": "api_data", "data": api_data})

            store_profile_image = get_config("store_profile_images", True)

            if store_profile_image and api_data.get("image_url"):
                self.logger.info(f"Storing profile image for {self.username}")
                image_path = os.path.join(path, "profile.png")
                await self.download_image(api_data.get("image_url"), image_path)
                await self.send_data({"key": "profile_image", "data": image_path})

            try:
                with open(json_path, "w") as f:
                    json.dump(api_data, f)
            except Exception as e:
                self.logger.error(f"Error storing API response: {e}")

        captureData = {
            f"https://t.me/{self.username}": os.path.join(path, "capture.png"),
        }
        if in_depth:
            usernames = extract_usernames(api_data.get("description", ""))
            # TODO: REMOVE
            print(usernames)
            for username in usernames:
                if username.lower() == self.username.lower():
                    continue

                get_data = await self.get_api_data(username)
                if get_data.get("type") == "channel":
                    url = f"https://t.me/s/{username}"
                else:
                    url = f"https://t.me/{username}"

                captureData[url] = os.path.join(path, f"{username}/capture.png")

        images = await self.capture_page(browser=browser, page_url=captureData)
        await self.send_data({"key": "images", "data": images})

        self.logger.info(f"Data processed for {self.username}")
        return

    async def get_name_history(self):
        # TODO: Get name history from sangmata bot
        pass
