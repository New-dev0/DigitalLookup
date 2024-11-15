import re


def extract_usernames(data: str):
    return re.findall(r"@(\w+)", data)
