from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional
import tweepy

app = FastAPI()

# Define models for input data
class AccountCredentials(BaseModel):
    consumer_key: str
    consumer_secret: str
    access_token: str
    access_token_secret: str

class ProxyConfig(BaseModel):
    proxies: List[str]

class UserSearch(BaseModel):
    usernames: List[str]

class KeywordSearch(BaseModel):
    keywords: List[str]

# Global variables to store configuration
auth = None
proxies = []

# Endpoint to manage Twitter account authentication
@app.post("/account_manage")
def account_manage(credentials: AccountCredentials):
    global auth
    try:
        auth = tweepy.OAuthHandler(credentials.consumer_key, credentials.consumer_secret)
        auth.set_access_token(credentials.access_token, credentials.access_token_secret)
        return {"message": "Authentication successful"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Authentication failed: {str(e)}")

# Endpoint to configure proxies
@app.post("/proxy_config")
def proxy_config(proxy_config: ProxyConfig):
    global proxies
    proxies = proxy_config.proxies
    return {"message": "Proxies configured successfully", "proxies": proxies}

# Helper function to create a Twitter API client
def create_api():
    if not auth:
        raise HTTPException(status_code=401, detail="Authentication credentials not provided")
    api = tweepy.API(auth, proxy=proxies[0] if proxies else None)
    return api

# Endpoint to search for users and retrieve the last 10 tweets
@app.post("/users_search")
def users_search(user_search: UserSearch):
    api = create_api()
    results = []
    for username in user_search.usernames:
        try:
            tweets = api.user_timeline(screen_name=username, count=10, tweet_mode="extended")
            user_results = []
            for tweet in tweets:
                tweet_data = {
                    "text": tweet.full_text,
                    "created_at": tweet.created_at,
                    "likes": tweet.favorite_count,
                    "retweets": tweet.retweet_count,
                    "tweet_type": "retweet" if hasattr(tweet, "retweeted_status") else "tweet",
                    "hashtags": [hashtag["text"] for hashtag in tweet.entities.get("hashtags", [])],
                    "mentions": [mention["screen_name"] for mention in tweet.entities.get("user_mentions", [])],
                    "links": [url["expanded_url"] for url in tweet.entities.get("urls", [])],
                    "username": tweet.user.screen_name,
                    "user_id": tweet.user.id_str,
                    "geo": tweet.geo,
                    "tweet_link": f"https://twitter.com/{tweet.user.screen_name}/status/{tweet.id_str}"
                }
                user_results.append(tweet_data)
            results.append({"username": username, "tweets": user_results})
        except Exception as e:
            results.append({"username": username, "error": str(e)})
    return results

# Endpoint to search for tweets by keywords
@app.post("/keywords_search")
def keywords_search(keyword_search: KeywordSearch):
    api = create_api()
    results = []
    for keyword in keyword_search.keywords:
        try:
            tweets = api.search(q=keyword, count=10, tweet_mode="extended")
            keyword_results = []
            for tweet in tweets:
                tweet_data = {
                    "text": tweet.full_text,
                    "created_at": tweet.created_at,
                    "likes": tweet.favorite_count,
                    "retweets": tweet.retweet_count,
                    "tweet_type": "retweet" if hasattr(tweet, "retweeted_status") else "tweet",
                    "hashtags": [hashtag["text"] for hashtag in tweet.entities.get("hashtags", [])],
                    "mentions": [mention["screen_name"] for mention in tweet.entities.get("user_mentions", [])],
                    "links": [url["expanded_url"] for url in tweet.entities.get("urls", [])],
                    "username": tweet.user.screen_name,
                    "user_id": tweet.user.id_str,
                    "geo": tweet.geo,
                    "tweet_link": f"https://twitter.com/{tweet.user.screen_name}/status/{tweet.id_str}"
                }
                keyword_results.append(tweet_data)
            results.append({"keyword": keyword, "tweets": keyword_results})
        except Exception as e:
            results.append({"keyword": keyword, "error": str(e)})
    return results

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)