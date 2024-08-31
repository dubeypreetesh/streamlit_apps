'''
Created on 29-Aug-2024

@author: ongraph
'''
import os
import sys
from dotenv import load_dotenv, find_dotenv

_ = load_dotenv(find_dotenv())  # read local .env file

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

import requests
import streamlit as st
from copilot import shopify_copilot
# URL for your API endpoints
CHAT_HISTORY_API = "https://app.heymira.ai/api/conversation" #GET
SEND_MESSAGE_API = "https://app.heymira.ai/api/conversation" #POST

def fetch_chat_history(token: str):
    # Fetch the chat history from your API
    url = CHAT_HISTORY_API
    headers = {
            "Authorization": f"Bearer {token}"
        }        
    return requests.get(url=url, headers=headers)

def send_chat_messages(token: str, user_input: str, ai_message: str):
    # Send the user message to your API and get the bot response
    #response = requests.post(SEND_MESSAGE_API, json={"user_id": user_id, "message": message})
    #return response.json() if response.status_code == 200 else {"response": "Error: Unable to get response."}
    url = SEND_MESSAGE_API
    headers = {
            "Authorization": f"Bearer {token}"
        }
    
    payload = {
        "conversation": [
            {
                "body": user_input,
                "type": "incoming"
            },
            {
                "body": ai_message,
                "type": "outgoing"
            }
        ]
    }      
    return requests.post(url=url, headers=headers, json=payload)

def create_chat_messages(response: dict):
    messages = response["data"]
    messages_copy = []
    for message in messages:
        role = None
        type = message["type"]
        if type == "incoming":
            role = "user"
        elif type == "outgoing":
            role = "assistant"
        messages_copy.append({"role": role, "content": message["body"]})
    return messages_copy

def create_placeholder_messages(messages: list):
    messages_copy = []
    for message in messages:
        role = message["role"]
        if role == "user":
            role = "human"
        elif role == "assistant":
            role = "ai"
        if message["content"]:
            messages_copy.append((role, message["content"]))
    return messages_copy

#App Code Starts here
st.title("🔗 Shopify App")
# Fetch the query parameters
query_params = st.query_params

# Access a specific query parameter
token = query_params.get('token')

# Initialize chat history
if "messages" not in st.session_state:
    st.session_state.messages = create_chat_messages(fetch_chat_history(token=token).json())
    
# Display chat messages from history on app rerun  
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        
with st.sidebar:
    openai_api_key = st.text_input("OpenAI API Key", type="password", key="openai_api_key")
    if not openai_api_key.startswith("sk-"):
        st.warning("Please enter your OpenAI API key!", icon="⚠")        

if user_input := st.chat_input("What's your query?"):
    if openai_api_key.startswith("sk-"):
        # Display user message in chat message container
        with st.chat_message("user"):
            st.markdown(user_input)
        # Add user message to chat history
        st.session_state.messages.append({"role": "user", "content": user_input})
        
        # Display assistant response in chat message container
        with st.chat_message("assistant"):
            ai_message = shopify_copilot.fetch_result(token=token, token_secret=st.secrets["shopify_credentials"]["jwt_secret"] ,question=user_input, openai_api_key=openai_api_key, messages=create_placeholder_messages(st.session_state.messages))
            st.markdown(ai_message)
        
        # Add assistant response to chat history
        st.session_state.messages.append({"role": "assistant", "content": ai_message})    
        try:
            send_chat_messages(token=token, user_input=user_input, ai_message=ai_message)
        except Exception as e:
            pass
        
        