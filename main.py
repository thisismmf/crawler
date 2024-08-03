from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional
import httpx
import os

# Initialize FastAPI
app = FastAPI()

# Twitter API keys from environment variables
API_KEY = os.getenv("TWITTER_API_KEY", "YOUR_API_KEY")
API_SECRET_KEY = os.getenv("TWITTER_API_SECRET_KEY", "YOUR_API_SECRET_KEY")
ACCESS_TOKEN = os.getenv("TWITTER_ACCESS_TOKEN", "YOUR_ACCESS_TOKEN")
ACCESS_TOKEN_SECRET = os.getenv("TWITTER_ACCESS_TOKEN_SECRET", "YOUR_ACCESS_TOKEN_SECRET")

# Proxies configuration
proxies = []

# Models for requests
class UserAuth(BaseModel):
    api_key: str
    api_secret_key: str
    access_token: str
    access_token_secret: str

class ProxyConfig(BaseModel):
    proxy_list: List[str]

class UserSearchRequest(BaseModel):
    usernames: List[str]

class KeywordSearchRequest(BaseModel):
    keywords: List[str]

# Endpoint: account_manage
@app.post("/account_manage")
async def account_manage(user_auth: UserAuth):
    global API_KEY, API_SECRET_KEY, ACCESS_TOKEN, ACCESS_TOKEN_SECRET
    API_KEY = user_auth.api_key
    API_SECRET_KEY = user_auth.api_secret_key
    ACCESS_TOKEN = user_auth.access_token
    ACCESS_TOKEN_SECRET = user_auth.access_token_secret
    return {"message": "Twitter authentication updated"}

# Endpoint: proxy_config
@app.post("/proxy_config")
async def proxy_config(proxy_config: ProxyConfig):
    global proxies
    proxies = proxy_config.proxy_list
    return {"message": "Proxy configuration updated", "proxies": proxies}

# Helper function to fetch tweets using HTTPX
async def fetch_tweets_with_httpx(query_type: str, query_value: str):
    tweets_data = []
    url = "https://api.twitter.com/2/tweets/search/recent"
    headers = {
        "Authorization": f"Bearer {ACCESS_TOKEN}"
    }

    # Choose the query type and URL based on the query type
    if query_type == "user":
        url = f"https://api.twitter.com/2/tweets?usernames={query_value}&tweet.fields=created_at,public_metrics,entities,geo"
    elif query_type == "keyword":
        url = f"https://api.twitter.com/2/tweets/search/recent?query={query_value}&tweet.fields=created_at,public_metrics,entities,geo"

    # Prepare proxy dictionary if proxies are set
    proxy_dict = None
    if proxies:
        proxy_dict = {
            "http": proxies[0],  # use the first proxy as an example
            "https": proxies[0]
        }

    try:
        async with httpx.AsyncClient(proxies=proxy_dict) as client:
            response = await client.get(url, headers=headers)
            response.raise_for_status()
            tweets = response.json().get("data", [])

            for tweet in tweets:
                tweet_info = {
                    "tweet_text": tweet.get("text"),
                    "tweet_time": tweet.get("created_at"),
                    "likes": tweet.get("public_metrics", {}).get("like_count", 0),
                    "retweets": tweet.get("public_metrics", {}).get("retweet_count", 0),
                    "tweet_type": "tweet",  # Adjusted for demonstration
                    "hashtags": [hashtag["tag"] for hashtag in tweet.get("entities", {}).get("hashtags", [])],
                    "mentions": [mention["username"] for mention in tweet.get("entities", {}).get("mentions", [])],
                    "links": [url["expanded_url"] for url in tweet.get("entities", {}).get("urls", [])],
                    "username": query_value,
                    "user_id": tweet.get("id"),
                    "geo": tweet.get("geo"),
                    "tweet_link": f"https://twitter.com/{query_value}/status/{tweet.get('id')}"
                }
                tweets_data.append(tweet_info)

    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail=f"HTTP Error: {e}")
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    return tweets_data

# Endpoint: users_search
@app.post("/users_search")
async def users_search(request: UserSearchRequest):
    results = {}
    for username in request.usernames:
        tweets = await fetch_tweets_with_httpx(query_type="user", query_value=username)
        results[username] = tweets
    return results

# Endpoint: keywords_search
@app.post("/keywords_search")
async def keywords_search(request: KeywordSearchRequest):
    results = {}
    for keyword in request.keywords:
        tweets = await fetch_tweets_with_httpx(query_type="keyword", query_value=keyword)
        results[keyword] = tweets
    return results
