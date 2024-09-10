'''
Created on 09-Sep-2024

@author: ongraph
'''

import os
import sys
from dotenv import load_dotenv, find_dotenv
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

from copilot import shopify_copilot
   
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
    
# Display chat messages from history on app rerun  
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])        

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
