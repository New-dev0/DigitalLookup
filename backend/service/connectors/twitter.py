import os
import json, asyncio
from .abstract import Connector, generator, AsyncNewContext
from random import choice, randint
from service.config import (
    TWITTER_ACCOUNTS_PATH,
    TWITTER_USERNAME,
    TWITTER_PASSWORD,
    CHROME_PATH,
)
from logging import getLogger
from service.analysis.llm_spam_detection import analyze_in_bulk, summarise_output
from playwright.async_api import (
    async_playwright,
    Cookie,
    TimeoutError,
    Route,
    Page,
    Browser,
)
from fastapi import WebSocket


class Twitter(Connector):
    service = "twitter"
    logger = getLogger(__name__)

    def __init__(self, username: str, websocket: WebSocket) -> None:
        super().__init__(username, websocket)

        self._client = None
        self._cookies = None
        self.captured_json = {}
        self.result_path = None
        self.tweets_path = None

    def get_cookies(self):
        if self._cookies:
            return self._cookies

        if os.listdir(TWITTER_ACCOUNTS_PATH):
            cookiePath = os.path.join(
                TWITTER_ACCOUNTS_PATH, choice(os.listdir(TWITTER_ACCOUNTS_PATH))
            )
            with open(cookiePath, "r") as f:
                cookies = json.load(f)
            if isinstance(cookies, dict) and cookies.get("cookies"):
                cookies = cookies["cookies"]

            if isinstance(cookies, list):
                cookies = {cookie["name"]: cookie["value"] for cookie in cookies}
            self._cookies = cookies
            return cookies

        return None

    async def get_client(self):
        from twikit import Client

        if not self._client:
            self._client = Client()

            if not os.listdir(TWITTER_ACCOUNTS_PATH):
                await self._client.login(
                    auth_info_1=TWITTER_USERNAME, password=TWITTER_PASSWORD
                )
                cookies_path = os.path.join(
                    TWITTER_ACCOUNTS_PATH, f"{self.username}.json"
                )
                self._client.save_cookies(cookies_path)

                with open(cookie_path, "r") as f:
                    self._cookies = json.load(f)

            else:
                path = choice(os.listdir(TWITTER_ACCOUNTS_PATH))
                cookie_path = os.path.join(TWITTER_ACCOUNTS_PATH, path)
                self._cookies = self.get_cookies()
                self._client.set_cookies(self._cookies)

        return self._client

    async def get_api_data(self):
        client = await self.get_client()
        user = await client.get_user_by_screen_name(self.username)
        return user

    async def capture_followers(self, path: str, page: Page):
        followers_path = os.path.join(path, "followers")
        os.makedirs(followers_path, exist_ok=True)
        try:
            await page.goto(
                f"https://x.com/{self.username}/followers",
                wait_until="networkidle",
                timeout=10000,
            )
        except TimeoutError:
            pass

    async def handle_browser_session(self, cookies: dict, path: str, browser: Browser):
        context = await AsyncNewContext(
            browser, fingerprint=generator.generate(device=("mobile",))
        )
        await context.add_cookies(
            [
                Cookie(name=name, value=value, domain=".x.com", path="/")
                for name, value in cookies.items()
            ]
        )
        page = await context.new_page()
        await page.route("**/*", self.get_on_route(path))

        try:
            await page.goto(
                f"https://x.com/{self.username}",
                wait_until="networkidle",
                timeout=20000,
            )
        except TimeoutError:
            pass

        while not self.captured_json.get("user_profile"):
            await page.wait_for_timeout(1000)

        profileImage = os.path.join(path, "profile.png")
        await page.screenshot(path=profileImage, full_page=self.full_page)
        imageOutput = [os.path.abspath(profileImage)]
        await self.send_data({"key": "images", "data": imageOutput})

        while not self.captured_json.get("tweets"):
            await page.wait_for_timeout(1000)
#        return await browser.close()

        images = await self.capture_bulk_page(
            page,
            max_screenshots=10,
            message="Capturing tweets",
            path=os.path.join(path, "tweets"),
        )
        imageOutput.extend(images)
        await self.send_data({"key": "images", "data": imageOutput})

        imageOutput.extend(await self.capture_followers_page(page, path))
        await self.send_data({"key": "images", "data": imageOutput})

        imageOutput.extend(await self.capture_following_page(page, path))
        await self.send_data({"key": "images", "data": imageOutput})

        random_wait = randint(1000, 5000)
        # random wait to avoid getting flagged
        await page.wait_for_timeout(random_wait)

        await browser.close()

    def get_on_route(self, path: str):

        async def on_route(route: Route):
            await route.continue_()

            request = route.request
            url = request.url
            if "https://x.com/i/api/graphql" not in url:
                return

            if "Followers" in url:
                self.logger.info(f"Capturing followers for {self.username}")
                self.followers_path = os.path.join(path, "followers.json")
                try:
                    response = await request.response()
                    jsonData = await response.json()
                    followersMap = {}
                    for user in jsonData["data"]["user"]["result"]["timeline"][
                        "timeline"
                    ]["instructions"]:
                        if user["type"] == "TimelineAddEntries":
                            for entry in user["entries"]:
                                if "user" in entry["entryId"]:
                                    user = entry["content"]["itemContent"][
                                        "user_results"
                                    ]["result"]["legacy"]
                                    followersMap[user["screen_name"]] = user

                    if os.path.exists(self.followers_path):
                        with open(self.followers_path, "r", encoding="utf-8") as f:
                            existing_data = json.load(f)
                        followersMap.update(existing_data)

                    with open(self.followers_path, "w", encoding="utf-8") as f:
                        json.dump(followersMap, f, ensure_ascii=False)
                except Exception as e:
                    self.logger.error(f"Error capturing followers: {e}")

                self.captured_json["followers"] = True

            if "Following" in url:
                self.logger.info(f"Capturing following for {self.username}")
                self.following_path = os.path.join(path, "following.json")
                try:
                    response = await request.response()
                    jsonData = await response.json()
                    followersMap = {}
                    for user in jsonData["data"]["user"]["result"]["timeline"][
                        "timeline"
                    ]["instructions"]:
                        if user["type"] == "TimelineAddEntries":
                            for entry in user["entries"]:
                                if "user" in entry["entryId"]:
                                    user = entry["content"]["itemContent"][
                                        "user_results"
                                    ]["result"]["legacy"]
                                    followersMap[user["screen_name"]] = user

                    if os.path.exists(self.following_path):
                        with open(self.following_path, "r", encoding="utf-8") as f:
                            existing_data = json.load(f)
                        followersMap.update(existing_data)

                    with open(self.following_path, "w", encoding="utf-8") as f:
                        json.dump(followersMap, f, ensure_ascii=False)
                except Exception as e:
                    self.logger.error(f"Error capturing following: {e}")

                self.captured_json["following"] = True

            if "UserTweets" in url:
                self.tweets_path = os.path.join(path, "tweets.json")
                self.logger.info(f"Capturing tweets for {self.username}")

                try:
                    response = await request.response()
                    jsonData = await response.json()
                    tweetElements = {}
                    for tweet in jsonData["data"]["user"]["result"]["timeline_v2"][
                        "timeline"
                    ]["instructions"]:
                        if tweet["type"] == "TimelineAddEntries":
                            for entry in tweet["entries"]:
                                if "tweet" in entry["entryId"]:
                                    tweet = entry["content"]["itemContent"][
                                        "tweet_results"
                                    ]["result"]["legacy"]
                                    tweetElements[tweet["id_str"]] = tweet

                    if os.path.exists(self.tweets_path):
                        with open(self.tweets_path, "r", encoding="utf-8") as f:
                            existing_data = json.load(f)
                        tweetElements.update(existing_data)

                    with open(self.tweets_path, "w", encoding="utf-8") as f:
                        json.dump(tweetElements, f, ensure_ascii=False)

                except Exception as e:
                    self.logger.error(f"Error capturing tweets: {e}")

                self.captured_json["tweets"] = True

            if "UserByScreenName" in url:
                self.logger.info(f"Fetching {url}")

                response = await request.response()
                jsonData = await response.json()
                legacy = jsonData["data"]["user"]["result"]["legacy"]
                filteredData = {
                    "name": legacy["name"],
                    "created_at": legacy["created_at"],
                    "description": legacy["description"],
                    "followers_count": legacy["followers_count"],
                    "following_count": legacy["friends_count"],
                    "location": legacy["location"],
                    "image_url": legacy["profile_image_url_https"].replace(
                        "_normal", ""
                    ),
                }
                await self.send_data({"key": "api_data", "data": filteredData})

                dataPath = os.path.join(path, "api_data.json")
                with open(dataPath, "w", encoding="utf-8") as f:
                    json.dump(jsonData, f, ensure_ascii=False)

                self.captured_json["user_profile"] = True

        return on_route

    async def process_data(
        self,
        output_path: str,
        store_api_responses: bool = True,
        in_depth: bool = False,
        browser: Browser = None,
    ):
        path = os.path.join(output_path, f"{self.service}/{self.username}")
        self.result_path = path
        os.makedirs(path, exist_ok=True)
        cookies = self.get_cookies()
        if cookies:
            await self.handle_browser_session(cookies, path, browser)
        else:
            self.logger.info(f"No cookies found for {self.username}")

    async def capture_followers_page(self, page: Page, path: str):
        try:
            await page.goto(
                f"https://x.com/{self.username}/followers",
                wait_until="networkidle",
                timeout=10000,
            )
        except TimeoutError:
            pass

        while not self.captured_json.get("followers"):
            await page.wait_for_timeout(1000)

        return await self.capture_bulk_page(
            page,
            max_screenshots=10,
            message="Capturing followers",
            path=os.path.join(path, "followers"),
        )

    async def capture_following_page(self, page: Page, path: str):
        try:
            await page.goto(
                f"https://x.com/{self.username}/following",
                wait_until="networkidle",
                timeout=10000,
            )
        except TimeoutError:
            pass

        while not self.captured_json.get("following"):
            await page.wait_for_timeout(1000)

        return await self.capture_bulk_page(
            page,
            max_screenshots=10,
            message="Capturing following",
            path=os.path.join(path, "following"),
        )

    async def post_task(self):
        print(self.tweets_path)
        if self.tweets_path and os.path.exists(self.tweets_path):

            self.logger.info(f"Starting Twitter Report for {self.username}")

            await self.websocket.send_json(
                {"type": "global_message", "data": "Starting Twitter Report"}
            )
            with open(self.tweets_path, "r", encoding="utf-8") as f:
                tweets = json.load(f)

            tweetstoAnalyze = [
                {"rest_id": d, "text": tweets[d]["full_text"]} for d in tweets
            ]

            output = summarise_output(tweetstoAnalyze)
            await self.websocket.send_json({"type": "twitter_report", "data": output})

            await self.websocket.send_json({"type": "global_message", "data": ""})
