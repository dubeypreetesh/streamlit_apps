'''
Created on 09-Sep-2024

@author: ongraph
'''

import os
import sys
import uuid
import streamlit as st

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

from proxy.copilot_proxy import CopilotProxy
   
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

with st.sidebar:
    st.title("fill your information")
    if is_cloud: 
        openai_api_key = st.text_input("OpenAI API Key", type="password", key="openai_api_key")
        if not openai_api_key.startswith("sk-"):
            st.warning("Please enter your OpenAI API key!", icon="⚠")
    else:
        openai_api_key = st.secrets["openai"]["api_key"]
        
    #user_name = st.text_input(label="Name", key="name", placeholder="Enter Your Name")
    #user_email = st.text_input(label="Email", key="email", placeholder="Enter Your Email")

    
if user_input := st.chat_input("What's your query?"):
    if openai_api_key.startswith("sk-"): #and (user_name and user_name.strip()) and (user_email and user_email.strip()):
        # Display user message in chat message container
        with st.chat_message("user"):
            st.markdown(user_input)
        # Add user message to chat history
        st.session_state.messages.append({"role": "user", "content": user_input})
        
        # Display assistant response in chat message container
        with st.chat_message("assistant"):
            copilot_proxy=CopilotProxy()
            session_id=st.session_state['session_id']
            ai_message=copilot_proxy.website_lead_chat(x_api_key=st.secrets["copilot"]["website_x_api_key"], session_id=session_id, collection_name="collection", question=user_input)
            
            st.markdown(ai_message)
        
        # Add assistant response to chat history
        st.session_state.messages.append({"role": "assistant", "content": ai_message})
    else:
        st.write("Enter Name , Email, OpenAI Api Key")      
