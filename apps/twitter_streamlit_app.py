'''
Created on 31-Jul-2024

@author: ongraph
'''
import sys
import os

_="""
ROOT_DIR=Path(__file__).parent.parent
os.chdir(ROOT_DIR)
sys.path.append(ROOT_DIR)

Note ::
Setting PYTHONPATH dynamically like above using ROOT_DIR is not working in streamlit cloud, so path is hardcoded as 
below in two lines of code `os.chdir` and `sys.path.append`.
Comment these two lines in local development mode.
"""
os.chdir("/mount/src/streamlit_apps")
sys.path.append("/mount/src/streamlit_apps")

import streamlit as st
from utils import llm_utils
from proxy import twitter_proxy
from utils.meta_ai_client import MetaAIClient

@st.dialog("Tweet Post Status")
def display_response_dialog(message, status_code):
    st.write(message)
    st.write(f"Status : {status_code}")

def generate_tweet(tweet_idea, messages, openai_api_key, tweet_form):
    # Generate Tweet Text
    #Please be strict to keep the generated text length within the 280 characters limit.
    if tweet_form=="140 chars limit":
        prompt = f"Craft a concise tweet to share [{tweet_idea}]. Be creative and engaging, ensuring that the tweet captivates the audience's attention and leaves a lasting impression. Please be strict to keep the generated text length within the 140 characters limit."
    else:
        prompt = f"Craft a detailed tweet to share [{tweet_idea}]. Be creative and engaging, providing more context and explanation ensuring that the tweet captivates the audience's attention and leaves a lasting impression. Feel free to go beyond single tweet limit."
        
    #Removing "image_url" key from each message to reduce number of tokens send to AI.
    messages_copy = [{k: v for k, v in d.items() if k != "image_url"} for d in messages]
    messages_copy.extend(messages)
    messages_copy.append({"role": "system", "content": prompt})
    
    tweet_stream = llm_utils.get_completion_stream(prompt=prompt, temperature=0.0, messages=messages_copy, openai_api_key=openai_api_key)
    return tweet_stream    
    #return tweet_idea
    
def generate_tweet_image(tweet):
    meta_ai = MetaAIClient.get_instance(fb_email="preetesh@mall91.com", fb_password="h@b1t_netw0rk")
    prompt=f"Create a vibrant, engaging image for the following tweet: [{tweet}]. Use eye-catching colors, creative typography, and a clean layout. Format the image for Twitter (1200x675 pixels, JPEG or PNG)."
    resp = meta_ai.prompt(message=prompt)
    print(resp)

    image_url = None    
    if len(resp["media"]):
        for media in resp["media"]:
            if media["type"] == "IMAGE":
                image_url = media["url"]
                break
    return image_url            

st.title("🦜🔗 Twitter App")

col1, col2 = st.columns(2)
with col1:
    generate_image = st.checkbox("Generate Image", key="generate_image")
with col2:
    tweet_form = st.radio("Select Tweet Form", ["140 chars limit", "no limit"], key="tweet_form")

# Initialize chat history
if "messages" not in st.session_state:
    st.session_state.messages = []

# Display chat messages from history on app rerun  
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        if message["image_url"]:
            st.image(message["image_url"])

# Accept user input        
if user_input := st.chat_input("What's your tweet idea?"):
    # Display user message in chat message container
    with st.chat_message("user"):
        st.markdown(user_input)
    # Add user message to chat history
    st.session_state.messages.append({"role": "user", "content": user_input, "image_url" : None})
    
    # Display assistant response in chat message container
    with st.chat_message("assistant"):        
        stream = generate_tweet(user_input, st.session_state.messages, st.session_state.openai_api_key, tweet_form)
        generated_tweet=st.write_stream(stream)
        generated_image_url=None
        if generate_image:
            try:
                generated_image_url = generate_tweet_image(generated_tweet)
                if generated_image_url:
                    st.image(generated_image_url)
            finally:
                pass
    # Add assistant response to chat history
    st.session_state.messages.append({"role": "assistant", "content": generated_tweet, "image_url" : generated_image_url})    
    # Update assistant response to tweet
    st.session_state.tweet = generated_tweet
    if generated_image_url:
        st.session_state.tweet_image_url = generated_image_url
    else:
        st.session_state.tweet_image_url = None
    #if generated_image_url:
    #    st.session_state.image_url = generated_image_url
    #    st.image(generated_image_url)
    #st.write(st.session_state)
        
with st.sidebar:
    openai_api_key = st.text_input("OpenAI API Key", type="password", key="openai_api_key")
    if not openai_api_key.startswith("sk-"):
        st.warning("Please enter your OpenAI API key!", icon="⚠")
    with st.form("twitter_form"):
        st.write("Post this on X")
        tweet = st.text_area(label="Tweet", max_chars=560, key="tweet", placeholder="Your tweet to be posted")
        tweet_image_url = st.text_input(label="Tweet Image Url", key="tweet_image_url", placeholder="Image Url to be posted")
        twitter_api_key = st.text_input(label="Api Key", key="twitter_api_key", placeholder="X Developer Account Api Key")
        twitter_api_key_secret = st.text_input(label="Api Key Secret", key="twitter_api_key_secret", placeholder="X Developer Account Api Key Secret")
        twitter_access_token = st.text_input(label="Access Token", key="twitter_access_token", placeholder="X Developer Account Access Token")
        twitter_access_token_secret = st.text_input(label="Access Token Secret", key="twitter_access_token_secret", placeholder="X Developer Account Access Token Secret")
        # Every form must have a submit button.
        post_tweet_submitted = st.form_submit_button("Post Tweet")
        if post_tweet_submitted and openai_api_key.startswith("sk-"):
            twitter_poster = twitter_proxy.TwitterPoster(twitter_api_key, twitter_api_key_secret, twitter_access_token, twitter_access_token_secret)
            message, status_code = twitter_poster.post_thread(tweet_text=tweet, image_url=tweet_image_url)
            display_response_dialog(message=message, status_code=status_code)            
