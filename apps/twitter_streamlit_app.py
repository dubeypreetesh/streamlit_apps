'''
Created on 31-Jul-2024

@author: ongraph
'''
import sys
import os
from pathlib import Path
ROOT_DIR=Path(__file__).parent.parent
os.chdir(ROOT_DIR)
sys.path.append(ROOT_DIR)

import streamlit as st
from utils import llm_utils
from proxy import twitter_proxy

@st.dialog("Tweet Post Status")
def display_response_dialog(message, status_code):
    st.write(message)
    st.write(f"Status : {status_code}")

def generate_llm_response(tweet_idea, messages, openai_api_key):
    # Generate Tweet Text
    prompt = f"Craft a concise tweet to share [{tweet_idea}]. Be creative and engaging, ensuring that the tweet captivates the audience's attention and leaves a lasting impression. Please be strict to keep the generated text length within the 280 characters limit."
    messages_copy = []
    messages_copy.extend(messages)
    messages_copy.append({"role": "system", "content": prompt})
    
    tweet_stream = llm_utils.get_completion_stream(prompt=prompt, temperature=0.0, messages=messages_copy, openai_api_key=openai_api_key)
    return tweet_stream    
    #return tweet_idea

st.title("🦜🔗 Twitter App")

# Initialize chat history
if "messages" not in st.session_state:
    st.session_state.messages = []

# Display chat messages from history on app rerun  
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Accept user input        
if user_input := st.chat_input("What's your tweet idea?"):
    # Display user message in chat message container
    with st.chat_message("user"):
        st.markdown(user_input)
    # Add user message to chat history
    st.session_state.messages.append({"role": "user", "content": user_input})
    
    # Display assistant response in chat message container
    with st.chat_message("assistant"):        
        stream = generate_llm_response(user_input, st.session_state.messages, st.session_state.openai_api_key)
        llm_response=st.write_stream(stream)
    # Add assistant response to chat history
    st.session_state.messages.append({"role": "assistant", "content": llm_response})
    # Update assistant response to tweet
    st.session_state.tweet = llm_response
    #st.write(st.session_state)
        
with st.sidebar:
    openai_api_key = st.text_input("OpenAI API Key", type="password", key="openai_api_key")
    if not openai_api_key.startswith("sk-"):
        st.warning("Please enter your OpenAI API key!", icon="⚠")
    with st.form("twitter_form"):
        st.write("Post this on X")
        tweet = st.text_area(label="Tweet", max_chars=560, key="tweet", placeholder="Your tweet to be posted")
        twitter_api_key = st.text_input(label="Api Key", key="twitter_api_key", placeholder="X Developer Account Api Key")
        twitter_api_key_secret = st.text_input(label="Api Key Secret", key="twitter_api_key_secret", placeholder="X Developer Account Api Key Secret")
        twitter_access_token = st.text_input(label="Access Token", key="twitter_access_token", placeholder="X Developer Account Access Token")
        twitter_access_token_secret = st.text_input(label="Access Token Secret", key="twitter_access_token_secret", placeholder="X Developer Account Access Token Secret")
        # Every form must have a submit button.
        post_tweet_submitted = st.form_submit_button("Post Tweet")
        if post_tweet_submitted and openai_api_key.startswith("sk-"):
            twitter_poster = twitter_proxy.TwitterPoster(twitter_api_key, twitter_api_key_secret, twitter_access_token, twitter_access_token_secret)
            message, status_code = twitter_poster.post_thread(tweet_text=tweet, image_url=None)
            display_response_dialog(message=message, status_code=status_code)            
