import json, re, requests
from service.config import GROQ_TOKEN, GROQ_MODEL
from groq import Groq

llm = Groq(
    api_key=GROQ_TOKEN,
)

SPAM_DETECT_PROMPT = """Your task is to rate social media tweets. Provide a valid JSON response, without any additional information.
Example:
<note>
Value is a factor between 0-1, depending on 'text' present in tweet.
Don't include single or double quote in any way.

Provide a JSON response such as 
{"results": [
{
  "spam_likelihood": 0,
  "profanity_detection": 0,
  "fraudulent_content_likelihood": 0,
  "false_information_probability": 0,
  "cyber_fraud_risk": 0,
  "illegal_activity_detection": 0,
  "personal_data_exposure": 0,
  "tweetId": "restTweetId",
  "reason": "reason for considering"
}],
"summarized_message": "<summarized message here>"}

Note: Social promotion of one's own account is acceptable. Users can ask others to follow them, as this is common on social media. Motivational tweets are also allowed and should not be considered spam.
"""


class FailedToParseJSON(Exception): ...


def analyze_tweet_chunks(tweets):
    for tweet in tweets:
        t_urls = re.findall(r'https?://t\.co/\w+', tweet['text'])
        text = tweet['text']
        for url in t_urls:
            try:
                text = text.replace(url, requests.get(url).url)
            except Exception:
                pass

        tweet['text'] = text

    message = llm.chat.completions.create(
        messages=[
            {"role": "system", "content": SPAM_DETECT_PROMPT},
            {"role": "user", "content": json.dumps([json.dumps(t) for t in tweets])},
        ],
        model=GROQ_MODEL,
    )
    try:
        messages = message.choices[0].message.content
        if not messages.strip().endswith("}"):
            messages += "}"

        with open("message.json", "w") as f:
            f.write(messages)

        messages = json.loads(messages)
        return messages
    except json.JSONDecodeError:
        raise FailedToParseJSON("Failed to parse")


def analyze_in_bulk(tweets, chunk_size: int = 10):
    messages = []
    while tweets:
        chunks = tweets[:chunk_size]
        tweets = tweets[chunk_size:]
        response = None
        for _ in range(3):
            try:
                response = analyze_tweet_chunks(chunks)
                break
            except FailedToParseJSON:
                continue
        if response and "results" in response:
            messages.extend(response["results"])
    return messages

def generalize_reasons(reasons):
    message = llm.chat.completions.create(
        messages=[
            {"role": "system", "content": "Summarize the main reason for flagging these tweets in a single, concise sentence."},
            {"role": "user", "content": f"Based on these reasons, provide a one-line summary of why these tweets were flagged: {json.dumps(reasons)}"},
        ],
        model=GROQ_MODEL,
    )
    return message.choices[0].message.content.strip()
def summarise_output(tweets, chunk_size: int = 10):
    output = {}
    results = analyze_in_bulk(tweets, chunk_size)
    reasons = []
    for result in results:
        for key, value in result.items():
            if key == "reason":
                reasons.append(value)
                continue
            if not isinstance(value, (int, float)):
                continue
            if key not in output:
                output[key] = value
            else:
                output[key] += value

    for key, value in output.items():
        output[key] = value / len(results)

    general_message = generalize_reasons(reasons)
    output["general_message"] = general_message

    return output
