from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel
from typing import List, Optional
import tweepy

app = FastAPI()

# Declare client as a global variable
client = None


# Models for request and response
class AuthInfo(BaseModel):
    api_key: str
    api_key_secret: str
    access_token: str
    access_token_secret: str


class ProxyConfig(BaseModel):
    proxies: List[str]


class UserSearchResponse(BaseModel):
    tweet_text: str
    time_of_tweet: str
    number_of_likes: int
    number_of_retweets: int
    type_of_tweet: str
    hashtags: List[str]
    mentions: List[str]
    links: List[str]
    username: str
    user_id: int
    geo: Optional[str]
    tweet_link: str


class KeywordSearchResponse(UserSearchResponse):
    keyword: str


# Helper function to determine tweet type
def get_tweet_type(tweet):
    if hasattr(tweet, "retweeted_status"):
        return "retweet"
    elif hasattr(tweet, "quoted_status"):
        return "quote"
    elif tweet.in_reply_to_status_id is not None:
        return "reply"
    return "tweet"


@app.post("/account_manage")
def account_manage(auth_info: AuthInfo):
    try:
        global client
        client = tweepy.Client(
            consumer_key=auth_info.api_key,
            consumer_secret=auth_info.api_key_secret,
            access_token=auth_info.access_token,
            access_token_secret=auth_info.access_token_secret,
            bearer_token="AAAAAAAAAAAAAAAAAAAAAGusvAEAAAAA2ETup9C7Eptf%2FFqevHl3pkCGc%2B4%3DwAdtRaN9eQcBkvJcmpcGGC0Ryy12mUmgmmZP2vPySjktEmbRr1"
        )
        return {"message": "Authentication successful"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Authentication failed: {str(e)}")


@app.post("/proxy_config")
def proxy_config(proxy_config: ProxyConfig):
    global proxies
    proxies = proxy_config.proxies
    return {"message": "Proxy configuration updated successfully"}


@app.get("/users_search", response_model=List[UserSearchResponse])
def users_search(usernames: List[str] = Query(...)):
    if client is None:
        raise HTTPException(status_code=401,
                            detail="Authentication required. Please authenticate using /account_manage first.")

    results = []
    try:
        for username in usernames:
            # Use Twitter API v2 client method to get user by username
            response = client.get_user(username=username, user_fields=['id', 'name', 'username'])
            if response.data is None:
                raise HTTPException(status_code=404, detail=f"User '{username}' not found.")

            user_id = response.data.id
            # Get tweets from user
            tweets_response = client.get_users_tweets(id=user_id, max_results=10,
                                                      tweet_fields=['created_at', 'public_metrics', 'geo', 'entities'])

            if not tweets_response.data:
                continue

            for tweet in tweets_response.data:
                public_metrics = tweet.public_metrics
                tweet_type = get_tweet_type(tweet)
                hashtags = [hashtag['tag'] for hashtag in tweet.entities.get('hashtags', [])]
                mentions = [mention['username'] for mention in tweet.entities.get('mentions', [])]
                links = [url['expanded_url'] for url in tweet.entities.get('urls', [])]
                geo = tweet.geo.get('place_id') if tweet.geo else None

                results.append(UserSearchResponse(
                    tweet_text=tweet.text,
                    time_of_tweet=str(tweet.created_at),
                    number_of_likes=public_metrics.get('like_count', 0),
                    number_of_retweets=public_metrics.get('retweet_count', 0),
                    type_of_tweet=tweet_type,
                    hashtags=hashtags,
                    mentions=mentions,
                    links=links,
                    username=username,
                    user_id=user_id,
                    geo=geo,
                    tweet_link=f"https://twitter.com/{username}/status/{tweet.id}"
                ))
    except tweepy.TweepyException as e:
        raise HTTPException(status_code=400, detail=f"Error retrieving tweets: {str(e)}")
    return results


@app.get("/keywords_search", response_model=List[KeywordSearchResponse])
def keywords_search(keywords: List[str] = Query(...)):
    if client is None:
        raise HTTPException(status_code=401,
                            detail="Authentication required. Please authenticate using /account_manage first.")

    results = []
    try:
        for keyword in keywords:
            # Use Twitter API v2 client method to search recent tweets
            search_response = client.search_recent_tweets(query=keyword, max_results=10,
                                                          tweet_fields=['created_at', 'public_metrics', 'geo',
                                                                        'entities'])

            if not search_response.data:
                continue

            for tweet in search_response.data:
                public_metrics = tweet.public_metrics
                tweet_type = get_tweet_type(tweet)
                hashtags = [hashtag['tag'] for hashtag in tweet.entities.get('hashtags', [])]
                mentions = [mention['username'] for mention in tweet.entities.get('mentions', [])]
                links = [url['expanded_url'] for url in tweet.entities.get('urls', [])]
                geo = tweet.geo.get('place_id') if tweet.geo else None

                results.append(KeywordSearchResponse(
                    tweet_text=tweet.text,
                    time_of_tweet=str(tweet.created_at),
                    number_of_likes=public_metrics.get('like_count', 0),
                    number_of_retweets=public_metrics.get('retweet_count', 0),
                    type_of_tweet=tweet_type,
                    hashtags=hashtags,
                    mentions=mentions,
                    links=links,
                    username=tweet.author.username,
                    user_id=tweet.author.id,
                    geo=geo,
                    tweet_link=f"https://twitter.com/{tweet.author.username}/status/{tweet.id}",
                    keyword=keyword
                ))
    except tweepy.TweepyException as e:
        raise HTTPException(status_code=400, detail=f"Error retrieving tweets: {str(e)}")
    return results
