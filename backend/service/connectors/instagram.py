import os, json
from typing import Callable
from instagrapi import Client
from instagrapi.types import User
from pydantic.networks import HttpUrl
from os.path import splitext
from service.connectors.abstract import Connector, generator
from browserforge.injectors.playwright import AsyncNewContext
from service.config import (
    INSTAGRAM_SESSIONS_PATH,
    INSTAGRAM_USERNAME,
    INSTAGRAM_PASSWORD,
    INSTAGRAM_COOKIES_PATH,
    CHROME_PATH,
)
from playwright.async_api import (
    async_playwright,
    Cookie,
    Browser,
    TimeoutError,
    Route,
    Page,
)

from logging import getLogger
from fastapi import WebSocket


class Instagram(Connector):
    service = "instagram"
    logger = getLogger(service)

    def __init__(self, username: str, websocket: WebSocket) -> None:
        super().__init__(username, websocket)
        self._client = None
        self._path = None
        self.processed_api = False

    @property
    def client(self):
        if self._client is None:
            self._client = Client()
            path = os.path.join(INSTAGRAM_SESSIONS_PATH, f"{INSTAGRAM_USERNAME}.json")
            if os.path.exists(path):
                self._client.load_settings(path)
            else:
                self._client.login(INSTAGRAM_USERNAME, INSTAGRAM_PASSWORD)
                os.makedirs(os.path.dirname(path), exist_ok=True)

                self._client.dump_settings(path)

        return self._client

    async def get_followers(self, user_id: str, path: str, browser: Browser):
        self.logger.info(f"Getting followers for {self.username}")

        path = os.path.join(path, "followers")
        os.makedirs(path, exist_ok=True)

        followers = self.client.user_followers(user_id)
        data = [
            json.loads(follower.model_dump_json()) for follower in followers.values()
        ]

        with open(os.path.join(path, "followers.json"), "w") as f:
            json.dump(data, f)

        images = await self.capture_page(
            browser=browser,
            fn=self.capture_page_view,
            screenshot_path=os.path.join(path, "capture.png"),
            page_url=f"https://www.instagram.com/{self.username}/followers/",
        )
        await self.send_data({"key": "followers_capture", "data": images})

    async def get_following(self, user_id: str, path: str, browser: Browser):
        self.logger.info(f"Getting following for {self.username}")
        path = os.path.join(path, "following")
        os.makedirs(path, exist_ok=True)

        following = self.client.user_following(user_id)
        data = [
            json.loads(following.model_dump_json()) for following in following.values()
        ]

        with open(os.path.join(path, "following.json"), "w") as f:
            json.dump(data, f)

        pageUrl = f"https://www.instagram.com/{self.username}/following/"
        self.logger.info(f"Capturing page view for {pageUrl}")

        images = await self.capture_page(
            browser=browser,
            page_url=pageUrl,
            fn=self.capture_page_view,
            screenshot_path=os.path.join(path, "capture.png"),
        )
        await self.send_data({"key": "following_capture", "data": images})

    async def get_api_data(self, username: str):
        info = self.client.user_info_by_username(username)
        return info.model_dump_json()

    async def process_data(
        self,
        output_path: str,
        store_api_responses: bool = True,
        browser: Browser = None,
        in_depth: bool = False,
    ):
        path = os.path.join(output_path, f"{self.service}/{self.username}")
        os.makedirs(path, exist_ok=True)
        self._path = path

        #        if store_api_responses:
        #            self.logger.info(f"Getting API data for {self.username}")
        #            info = await self.get_api_data(self.username)
        #            with open(os.path.join(path, "api_data.json"), "w") as f:
        #                f.write(info)

        #        user_id = self.client.user_id_from_username(self.username)

        #        await self.get_followers(user_id, path, browser)
        #        await self.get_following(user_id, path, browser)
        await self.send_data({"key": "message", "data": "Capturing screenshots."})
        images = await self.capture_page(
            browser=browser,
            fn=self.capture_page_view,
            screenshot_path=os.path.join(path, "capture.png"),
        )
        await self.send_data({"key": "images", "data": images})
        await self.send_data({"key": "message", "data": ""})

    def on_routes(self, path: str):

        async def on_route_handler(route: Route):
            await route.continue_()
            request = route.request
            if "https://www.instagram.com/graphql/query" in request.url:
                response = await request.response()
                responseData = await response.json()
                try:
                    user = responseData["data"]["user"]
                    if path:
                        with open(os.path.join(path, "api_data.json"), "w") as f:
                            json.dump(user, f)

                    parsedUser = {
                        "name": user["full_name"],
                        "description": user["biography"],
                        "image_url": user["profile_pic_url"],
                        "followers_count": user["follower_count"],
                        "following_count": user["following_count"],
                        "is_private": user["is_private"],
                    }
                    if parsedUser.get("image_url"):
                        imagePath = os.path.join(path, "profile_image.png")
                        await self.download_image(parsedUser["image_url"], imagePath)
                        parsedUser["image_path"] = os.path.abspath(imagePath)

                    await self.send_data({"key": "api_data", "data": parsedUser})

                    await self.send_data(
                        {
                            "key": "message",
                            "data": "Capturing screenshots",
                            "type": "info",
                        }
                    )
                except KeyError:
                    return

        return on_route_handler

    #        print(request.url)

    async def make_profile_meta(self, page: Page):
        responseData = {}
        nameTag = await page.query_selector(
            '//*[@id="mount_0_0_4x"]/div/div/div/div[2]/div/div/div[1]/div[2]/div/div[1]/section/main/div/header/section[4]/div/div[1]/span'
        )
        if nameTag:
            responseData["name"] = await nameTag.inner_text()
        descriptionTag = await page.query_selector(
            '//*[@id="mount_0_0_4x"]/div/div/div/div[2]/div/div/div[1]/div[2]/div/div[1]/section/main/div/header/section[4]/div/span/div'
        )
        if descriptionTag:
            responseData["description"] = await descriptionTag.inner_text()
        imageUrl = await page.query_selector(
            '//*[@id="mount_0_0_4x"]/div/div/div/div[2]/div/div/div[1]/div[2]/div/div[1]/section/main/div/header/section[1]/div/div/a/img'
        )
        if imageUrl:
            responseData["image_url"] = await imageUrl.get_attribute("src")

        return responseData

    async def capture_page_view(
        self,
        browser: Browser,
        page_url: str = None,
        screenshot_path: str = None,
        mobile: bool = False,
        handler: Callable = None,
    ):

        with open(INSTAGRAM_COOKIES_PATH, "r") as f:
            cookies = json.load(f)

        if mobile:
            context = await AsyncNewContext(
                browser, fingerprint=generator.generate(device=("mobile",))
            )
        else:
            context = await browser.new_context()
        page = await context.new_page()
        for cookie in cookies:
            await context.add_cookies(
                [
                    Cookie(
                        name=cookie["name"],
                        value=cookie["value"],
                        domain=cookie["domain"],
                        path=cookie["path"],
                        expires=-1,
                        httpOnly=cookie["httpOnly"],
                        secure=cookie["secure"],
                    )
                ]
            )
        if not self.processed_api:
            await page.route("**/*", self.on_routes(self._path))
            self.processed_api = True

        try:
            await page.goto(
                f"https://www.instagram.com/{self.username}",
                wait_until="networkidle",
                timeout=10000,
            )
        except TimeoutError as e:
            print(e)

        #        await self.make_profile_meta(page)

        if handler:
            await handler(page)

        screen, extension = splitext(screenshot_path)
        screenshot_path = screen + ("_mobile" if mobile else "_desktop") + extension
        await page.screenshot(path=screenshot_path, full_page=self.full_page)
        await page.close()

        return [os.path.abspath(screenshot_path)]
