'''
Created on 29-Aug-2024

@author: ongraph
'''
import os
import sys
from dotenv import load_dotenv, find_dotenv
import jwt
import streamlit as st
import requests

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
is_cloud = os.getenv('HOME') == "/home/appuser"
if is_cloud:
    os.chdir("/mount/src/streamlit_apps")
    sys.path.append("/mount/src/streamlit_apps")
    # Setting environment variables from Streamlit secrets
    os.environ["LANGCHAIN_TRACING_V2"] = st.secrets["langsmith"]["LANGCHAIN_TRACING_V2"]
    os.environ["LANGCHAIN_API_KEY"] = st.secrets["langsmith"]["LANGCHAIN_API_KEY"]

from proxy.copilot_proxy import CopilotProxy

def fetch_chat_history(api_url: str, token: str):
    # Fetch the chat history from your API
    headers = {
            "Authorization": f"Bearer {token}"
        }        
    return requests.get(url=api_url, headers=headers)

def send_chat_messages(api_url: str, token: str, user_input: str, ai_message: str):
    # Send the user message to your API and get the bot response
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
    return requests.post(url=api_url, headers=headers, json=payload)
"""
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
"""
#App Code Starts here
STANDARD_ERROR_MESSAGE = "We're sorry, but something didn’t go as planned. Please try again in a little while."
# Fetch the query parameters
query_params = st.query_params

# Access a specific query parameter
token = query_params.get('token')

token_secret = st.secrets["shopify_credentials"]["jwt_secret"]
decoded_token = jwt.decode(token, token_secret, algorithms=["HS256"])
page_title = f"I am Mira - your personal 24/7 Shopping Assistant for {decoded_token['shopName']}"
st.set_page_config(page_title=page_title, page_icon=":flag-in:")
title="🔗 Mira - your personal 24/7 Shopping Assistant"
hide_streamlit_style = """
<style>
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
.custom-title {
        font-size: 28px;
        font-weight: bold;
        text-align: left;
        margin-top: 20px;
        font-family: 'Arial', sans-serif;
    }
</style>
<h3 class="custom-title">"""f"{title}""""</h3>
"""
st.markdown(hide_streamlit_style, unsafe_allow_html=True)

#st.title(title)
# Initialize chat history
if "messages" not in st.session_state:
    response = fetch_chat_history(api_url=st.secrets["shopify_credentials"]["chat_history_api"], token=token).json()
    if response["data"]:
        st.session_state.messages = response["data"]#create_chat_messages(response)
    else:
        st.session_state.messages=[]
        
    if response["checkout_data"]:
        st.session_state.checkout_data = response["checkout_data"]
    else:
        st.session_state.checkout_data = []    

# Display chat messages from history on app rerun  
for message in st.session_state.messages:
    with st.chat_message("user" if message["type"]=="incoming" else "assistant" ):
        st.markdown(message["body"])

if is_cloud:        
    with st.sidebar:
        openai_api_key = st.text_input("OpenAI API Key", type="password", key="openai_api_key")
        if not openai_api_key.startswith("sk-"):
            st.warning("Please enter your OpenAI API key!", icon="⚠")
else:
    openai_api_key = st.secrets["openai"]["api_key"]

if user_input := st.chat_input("What's your query?"):
    if openai_api_key.startswith("sk-"):
        # Display user message in chat message container
        with st.chat_message("user"):
            st.markdown(user_input)
        # Add user message to chat history
        st.session_state.messages.append({"type": "incoming", "body": user_input})
        
        # Display assistant response in chat message container
        with st.chat_message("assistant"):
            ai_message = None
            #create_placeholder_messages(st.session_state.messages)
            try:
                copilot_proxy=CopilotProxy()
                decoded_token = jwt.decode(token, st.secrets["shopify_credentials"]["jwt_secret"], algorithms=["HS256"])
                ai_message = copilot_proxy.chat_shopify_data(shop_id=decoded_token["shopId"], collection_name=decoded_token["collection_name"],
                                                             question=user_input, chat_history=st.session_state.messages,checkout_data=st.session_state.checkout_data,user_id= decoded_token["customerId"])
            except Exception as e:
                print(f"Error : {e}")
                ai_message = STANDARD_ERROR_MESSAGE
                
            st.markdown(ai_message)
        # Add assistant response to chat history
        st.session_state.messages.append({"type": "outgoing", "body": ai_message})    
        try:
            send_chat_messages(api_url=st.secrets["shopify_credentials"]["send_message_api"], token=token, user_input=user_input, ai_message=ai_message)
        except Exception as e:
            print(f"Error : {e}")
        
        