import json

import requests
from requests_oauthlib import OAuth1Session

from utils import utils

class TwitterPoster:

    def __init__(self, api_key, api_secret, access_token, access_token_secret):
        self.api_key = api_key
        self.api_secret = api_secret
        self.access_token = access_token
        self.access_token_secret = access_token_secret

        self.twitter = OAuth1Session(
            client_key=self.api_key,
            client_secret=self.api_secret,
            resource_owner_key=self.access_token,
            resource_owner_secret=self.access_token_secret
        )

    def post_tweet_with_image(self, tweet_text, image_url=None, reply_to=None):
        if image_url:
            media_id = self.upload_image(image_url)
            print(f"media_id : {media_id}")
        
        # Set up the endpoint URL
        url = "https://api.twitter.com/2/tweets"

        # Set up the tweet payload
        payload = {
                "text": tweet_text
            }
        if image_url and media_id:
            payload["media"] = {"media_ids": [str(media_id)]}
        if reply_to:
            payload["reply"] = {"in_reply_to_tweet_id": reply_to}

        # Send a POST request to create a tweet
        print(f"payload : {payload}")
        
        response = self.twitter.post(url, json=payload)
        print(response.status_code)
        response_dict = json.loads(response.text)
        print(str(response_dict))
        
        if response.status_code == 201:
            # return f"Tweet posted successfully : '{tweet_text}'", 200
            return response.json()["data"]["id"]
        else:
            raise Exception(f"Failed to post tweet: {response.text}")
        
    def post_thread(self, tweet_text, image_url):
        chunks = utils.split_text(tweet_text, 280, "utf-16-le")
    
        # Post the first tweet
        tweet_id = self.post_tweet_with_image(tweet_text=chunks[0], image_url=image_url)
        
        # Post the remaining tweets as replies
        for chunk in chunks[1:]:
            tweet_id = self.post_tweet_with_image(tweet_text=chunk, reply_to=tweet_id)
        
        return "Tweet posted successfully", 200

    def upload_image(self, image_url):
        response = requests.get(image_url)
        if response.status_code == 200:
            files = {'media': response.content}
            media_upload_response = self.twitter.post("https://upload.twitter.com/1.1/media/upload.json", files=files)
            if media_upload_response.status_code == 200:
                return media_upload_response.json().get("media_id")
        return None