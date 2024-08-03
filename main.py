from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import tweepy
from typing import List, Optional

# Initialize FastAPI app
app = FastAPI()


# Pydantic models for request bodies
class AuthInfo(BaseModel):
    bearer_token: str


class ProxyConfig(BaseModel):
    proxies: Optional[List[str]]


class UserSearchRequest(BaseModel):
    usernames: List[str]


class KeywordSearchRequest(BaseModel):
    keywords: List[str]


# Global variables to store auth and proxy config
bearer_token = None
proxies = None


def create_twitter_client():
    if bearer_token is None:
        raise HTTPException(status_code=400, detail="Twitter authentication not configured.")

    # Set up the API client for Twitter API v2
    client = tweepy.Client(bearer_token=bearer_token)

    return client


# Endpoint for account management
@app.post("/account_manage")
async def account_manage(auth_info: AuthInfo):
    global bearer_token
    bearer_token = auth_info.bearer_token
    return {"message": "Authentication information updated successfully."}


# Endpoint for proxy configuration
@app.post("/proxy_config")
async def proxy_config(proxy_config: ProxyConfig):
    global proxies
    proxies = proxy_config.proxies
    return {"message": "Proxy configuration updated successfully.", "proxies": proxies}


# Endpoint for user search
@app.post("/users_search")
async def users_search(user_search_request: UserSearchRequest):
    client = create_twitter_client()

    results = []
    for username in user_search_request.usernames:
        try:
            user = client.get_user(username=username)
            user_id = user.data.id
            tweets = client.get_users_tweets(id=user_id, max_results=10)

            for tweet in tweets.data:
                tweet_details = client.get_tweet(tweet.id, expansions=["author_id", "entities"])
                tweet_info = tweet_details.data
                entities = tweet_info.get('entities', {})

                results.append({
                    "tweet_text": tweet_info.text,
                    "time_of_tweet": tweet_info.created_at,
                    "likes": tweet_info.public_metrics["like_count"],
                    "retweets": tweet_info.public_metrics["retweet_count"],
                    "tweet_type": determine_tweet_type(tweet_info),
                    "hashtags": [hashtag["tag"] for hashtag in entities.get("hashtags", [])],
                    "mentions": [mention["username"] for mention in entities.get("mentions", [])],
                    "links": [url["expanded_url"] for url in entities.get("urls", [])],
                    "username": username,
                    "user_id": user_id,
                    "geo": tweet_info.geo,
                    "tweet_link": f"https://twitter.com/{username}/status/{tweet.id}"
                })
        except tweepy.errors.Forbidden as e:
            raise HTTPException(status_code=403, detail=f"Access forbidden: {str(e)}")
        except tweepy.errors.TweepyException as e:
            raise HTTPException(status_code=400, detail=f"Error fetching tweets for {username}: {str(e)}")

    return results


# Endpoint for keyword search
@app.post("/keywords_search")
async def keywords_search(keyword_search_request: KeywordSearchRequest):
    client = create_twitter_client()

    results = []
    for keyword in keyword_search_request.keywords:
        try:
            tweets = client.search_recent_tweets(query=keyword, max_results=10)

            for tweet in tweets.data:
                tweet_details = client.get_tweet(tweet.id, expansions=["author_id", "entities"])
                tweet_info = tweet_details.data
                entities = tweet_info.get('entities', {})

                results.append({
                    "tweet_text": tweet_info.text,
                    "time_of_tweet": tweet_info.created_at,
                    "likes": tweet_info.public_metrics["like_count"],
                    "retweets": tweet_info.public_metrics["retweet_count"],
                    "tweet_type": determine_tweet_type(tweet_info),
                    "hashtags": [hashtag["tag"] for hashtag in entities.get("hashtags", [])],
                    "mentions": [mention["username"] for mention in entities.get("mentions", [])],
                    "links": [url["expanded_url"] for url in entities.get("urls", [])],
                    "username": tweet_info.author_id,
                    "user_id": tweet_info.author_id,
                    "geo": tweet_info.geo,
                    "tweet_link": f"https://twitter.com/i/web/status/{tweet.id}"
                })
        except tweepy.errors.Forbidden as e:
            raise HTTPException(status_code=403, detail=f"Access forbidden: {str(e)}")
        except tweepy.errors.TweepyException as e:
            raise HTTPException(status_code=400, detail=f"Error fetching tweets for keyword '{keyword}': {str(e)}")

    return results


# Utility function to determine tweet type
def determine_tweet_type(tweet):
    if 'referenced_tweets' in tweet:
        referenced_type = tweet['referenced_tweets'][0]['type']
        if referenced_type == 'retweeted':
            return "retweet"
        elif referenced_type == 'quoted':
            return "quote"
        elif tweet.in_reply_to_user_id is not None:
            return "reply"
    return "tweet"


# Example usage
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8000)