'''
Created on 09-Sep-2024

@author: ongraph
'''

import os
import sys
import uuid

from dotenv import load_dotenv, find_dotenv
import requests
from streamlit_javascript import st_javascript

from copilot import shopify_copilot
import streamlit as st


_ = load_dotenv(find_dotenv())  # read local .env file

_ = """
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

#domain, email, name, human_message, ai_message, ai_error_messag
def website_lead_save(api_url: str,x_api_key: str,session_id:str, name: str, email: str, human_message: str,ai_message:str,ai_error_message:str):
    # Send the user message to your API and get the bot response
    headers = {
    "x-api-key": x_api_key,
    "Content-Type": "application/json"
    }
    payload = {
        "session_id": session_id,
        "name":name,
        "email":email,
        "human_message":human_message,
        "ai_message":ai_message,
        "ai_error_message":ai_error_message
    }
    return requests.post(url=api_url,headers=headers, json=payload)

    
page_title = f"OnGraph AI Assistant"
st.set_page_config(page_title=page_title, page_icon=":flag-in:")

hide_streamlit_style = """
<style>
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
</style>

"""
st.markdown(hide_streamlit_style, unsafe_allow_html=True)

st.title("🔗 OnGraph AI Assistant")

# Initialize chat history
if "messages" not in st.session_state:
    st.session_state.messages = []
if 'session_id' not in st.session_state:
    st.session_state['session_id'] = str(uuid.uuid4())
    
# Display chat messages from history on app rerun  
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])        
domain = st_javascript("await fetch('').then(r => window.location.host)")
if is_cloud: 
    with st.sidebar:
        st.title("fill your information")
        openai_api_key = st.text_input("OpenAI API Key", type="password", key="openai_api_key")
        user_name = st.text_input(label="Name", key="name", placeholder="Enter Your Name")
        user_email = st.text_input(label="Email", key="email", placeholder="Enter Your Email")
        if not openai_api_key.startswith("sk-"):
            st.warning("Please enter your OpenAI API key!", icon="⚠")
else:
    with st.sidebar:
        st.title("fill your information")
        openai_api_key = st.secrets["openai"]["api_key"]
        user_name = st.text_input(label="Name", key="name", placeholder="Enter Your Name")
        user_email = st.text_input(label="Email", key="email", placeholder="Enter Your Email")
    
if user_input := st.chat_input("What's your query?"):
    if openai_api_key.startswith("sk-") and (user_name and user_name.strip()) and (user_email and user_email.strip()):
        # Display user message in chat message container
        with st.chat_message("user"):
            st.markdown(user_input)
        # Add user message to chat history
        st.session_state.messages.append({"role": "user", "content": user_input})
        
        # Display assistant response in chat message container
        with st.chat_message("assistant"):
            ai_message = shopify_copilot.fetch_website_result(website_domain="ongraph.com", collection_name="collection",
                                                              question=user_input, openai_api_key=openai_api_key,
                                                              messages=create_placeholder_messages(st.session_state.messages),
                                                              chroma_host=st.secrets["chroma_credentials"]["host"],
                                                              chroma_port=st.secrets["chroma_credentials"]["port"])
            st.markdown(ai_message)
        
        # Add assistant response to chat history
        st.session_state.messages.append({"role": "assistant", "content": ai_message})
        if ai_message:
            try:
                session_id=st.session_state['session_id']
                website_lead_save(api_url=st.secrets["copilot"]["website_lead_save_api_url"],x_api_key=st.secrets["copilot"]["website_x_api_key"] ,session_id=session_id, name=user_name, email=user_email, human_message=user_input, ai_message=ai_message, ai_error_message=None)
            except Exception as e:
                pass
    else:
        st.write("Enter Name , Email, OpenAI Api Key")      
