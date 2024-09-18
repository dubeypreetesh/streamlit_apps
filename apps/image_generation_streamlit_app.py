'''
Created on 18-Sep-2024

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
    
page_title = f"HF FLUX.1-schnell Image Generator"
st.set_page_config(page_title=page_title, page_icon=":flag-in:")

import io
import requests
from PIL import UnidentifiedImageError

def generate_image_using_flux_hugging_face(prompt: str, hf_access_token: str) -> bytes:
    api_url = "https://api-inference.huggingface.co/models/black-forest-labs/FLUX.1-schnell"
    headers = {"Authorization": f"Bearer {hf_access_token}"}
    
    payload = {
        "inputs": prompt
    }

    response = requests.post(api_url, headers=headers, json=payload)
    response.raise_for_status() # This will raise an HTTPError for bad responses
    image_bytes = response.content
    return image_bytes

@st.dialog("Image Generation Status")
def display_response_dialog(message, status_code):
    st.write(message)
    st.write(f"Status : {status_code}")

#App Code Starts here
hide_streamlit_style = """
<style>
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
</style>

"""
st.markdown(hide_streamlit_style, unsafe_allow_html=True)

st.title("🔗 HF FLUX.1-schnell Image Generator")

# Initialize chat history
if "messages" not in st.session_state:
    st.session_state.messages = []
    
# Display chat messages from history on app rerun  
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        if message["image_url"]:
            st.image(message["image_url"])
            
with st.sidebar:
    hf_access_token = st.text_input("HF Access Token", type="password", key="hf_access_token")
    if not hf_access_token:
        st.warning("Please enter HF Access Token!", icon="⚠")
        
# Accept user input        
if user_input := st.chat_input("Imagine your idea..."):
    if hf_access_token:
        # Display user message in chat message container
        with st.chat_message("user"):
            st.markdown(user_input)
        # Add user message to chat history
        st.session_state.messages.append({"role": "user", "content": user_input, "image_url" : None})
        
        # Display assistant response in chat message container
        with st.chat_message("assistant"):
            try:
                generated_image = generate_image_using_flux_hugging_face(prompt=user_input, hf_access_token=hf_access_token)
            except requests.exceptions.HTTPError as http_err:
                error_message = http_err.message
            except UnidentifiedImageError as uie:
                error_message = uie.message
            except FileNotFoundError as fnfe:
                error_message = fnfe.message
            except Exception as e:
                error_message = e.message
            
            if generated_image:
                # Add assistant response to chat history
                st.session_state.messages.append({"role": "assistant", "content": None, "image_url" : generated_image})
                image_bytes_io = io.BytesIO(generated_image)
                image_bytes_io.seek(0)
                st.image(image=image_bytes_io)
            else:
                display_response_dialog(message=f"Error while generating the image : {error_message}", status_code=400)