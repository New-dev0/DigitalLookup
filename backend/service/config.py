import os
import json
from decouple import config

CHROME_PATH = config(
    "CHROME_PATH", default="C:\Program Files\Google\Chrome\Application\chrome.exe"
)
TWITTER_USERNAME = config("TWITTER_USERNAME", default="")
TWITTER_PASSWORD = config("TWITTER_PASSWORD", default="")

TWITTER_ACCOUNTS_PATH = config("TWITTER_ACCOUNTS_PATH", default="")

INSTAGRAM_SESSIONS_PATH = config(
    "INSTAGRAM_SESSIONS_PATH", default=""
)
INSTAGRAM_USERNAME = config("INSTAGRAM_USERNAME", default="")
INSTAGRAM_PASSWORD = config("INSTAGRAM_PASSWORD", default="")
INSTAGRAM_COOKIES_PATH = config(
    "INSTAGRAM_COOKIES_PATH", default=""
)

GROQ_TOKEN = config("GROQ_TOKEN", default="GROQ_TOKEN")
GROQ_MODEL = config("GROQ_MODEL", default="llama-3.1-8b-instant")
PORT = config("PORT", default=8000)
RESULT_DATA_DIR = config("RESULT_DATA_DIR", default="results")


def read_config():
    if os.path.exists("config.json"):
        with open("config.json", "r") as f:
            return json.load(f)
    else:
        return {}


def get_config(key: str, default: str = None):
    config = read_config()
    return config.get(key, default)