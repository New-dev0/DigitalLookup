import asyncio, logging

logging.basicConfig(level=logging.INFO)
import sys, asyncio, os

from fastapi import WebSocket
from playwright.async_api import async_playwright, Browser
from secrets import token_hex
from service.connectors.abstract import Connector
from service.connectors.whatsapp import Whatsapp
from service.connectors.telegram import Telegram
from service.connectors.instagram import Instagram
from service.connectors.twitter import Twitter
from service.connectors.facebook import Facebook

from playwright.async_api import async_playwright
from service.config import CHROME_PATH, RESULT_DATA_DIR

if not os.path.exists(RESULT_DATA_DIR):
    os.mkdir(RESULT_DATA_DIR)

LOG = logging.getLogger(__name__)


async def test_telegram():
    async with async_playwright() as p:
        telegram = Telegram("karboncopy")
        await telegram.process_data(
            "data",
            browser=await p.chromium.launch(
                headless=False, executable_path=CHROME_PATH
            ),
            in_depth=True,
        )


async def test_instagram():
    async with async_playwright() as p:
        ig = Instagram("newdev00")
        #    await ig.process_data("data", in_depth=True)
        await ig.process_data(
            "data",
            browser=await p.chromium.launch(
                headless=False, executable_path=CHROME_PATH
            ),
        )


async def test_twitter():
    t = Twitter("elonmusk", None)
    async with async_playwright() as p:
        await t.process_data(
            "data",
            browser=await p.chromium.launch(
                headless=False, executable_path=CHROME_PATH
            ),
            in_depth=True,
        )


connectors = {
    "telegram": Telegram,
    "instagram": Instagram,
    "twitter": Twitter,
    "facebook": Facebook,
    "whatsapp": Whatsapp,
}


def get_connector(id):
    return connectors[id]


async def processUserRequest(data, socket: WebSocket):
    inputs = data["socialInputs"]
    devices = data["devices"]
    device_targets = []
    if devices.get("android"):
        device_targets.append("android")
    if devices.get("desktop"):
        device_targets.append("desktop")
    taskId = token_hex(16)
    connectors = []

    async with async_playwright() as playwright:
        chrome = await playwright.chromium.launch(
            headless=True, executable_path=CHROME_PATH
        )
        for key, value in inputs.items():
            if not value:
                continue

            LOG.info(f"Processing {key} with {value}")

            connector: Connector = get_connector(key)(value, socket)
            connectors.append(connector)
            await connector.process_data(
                os.path.join(RESULT_DATA_DIR, taskId),
                browser=chrome,
            )

    LOG.info("Running post tasks")
    for connector in connectors:
        await connector.post_task()

    await socket.send_json(
        {"type": "system", "status": "COMPLETED", "resultId": taskId}
    )


def test_tweets_detection(path):
    from service.analysis.llm_spam_detection import analyze_tweet_chunks
    import json

    with open(path, "r", encoding="utf8") as f:
        data = json.load(f)

    print(
        analyze_tweet_chunks(
            [{"rest_id": d, "text": data[d]["full_text"]} for d in data]
        )
    )

    from service.analysis.llm_spam_detection import summarise_output

    import json

    with open(
        r"D:\DigiLookup\python\results\6edc279a52fd137bd5eef2b9e140b375\twitter\newdev0\tweets.json",
        "r",
        encoding="utf-8",
    ) as f:
        data = json.load(f)

    print(
        summarise_output([{"rest_id": d, "text": data[d]["full_text"]} for d in data])
    )
    # test_tweets_detection(r'D:\DigiLookup\python\data\twitter\elonmusk\tweets.json')
    # exit()
