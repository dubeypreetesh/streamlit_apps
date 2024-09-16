'''
Created on 31-Jul-2024

@author: ongraph
'''
import sys
import os
import sqlite3
from pathlib import Path
from streamlit.runtime.scriptrunner import add_script_run_ctx
import requests
from dotenv import load_dotenv, find_dotenv
import streamlit as st

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

from utils import llm_utils
from proxy import twitter_proxy
from utils.meta_ai_client import MetaAIClient
from datetime import datetime, timedelta, time
import time
import threading
from utils import aws_client
import uuid

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
    messages_copy.append({"role": "system", "content": prompt})
    
    tweet_stream = llm_utils.get_completion_stream(prompt=prompt, temperature=0.0, messages=messages_copy, openai_api_key=openai_api_key)
    return tweet_stream    
    #return tweet_idea

def generate_tweet_image_using_meta(tweet):
    meta_ai = MetaAIClient.get_instance(fb_email=st.secrets["meta_ai_credentials"]["fb_username"], fb_password=st.secrets["meta_ai_credentials"]["fb_password"])
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
    
def generate_tweet_image(tweet):
    api_url = st.secrets["image_generation"]["api_url"]
    api_key = st.secrets["image_generation"]["api_key"]
    headers = {"Authorization": "Bearer {api_key}"}
    
    payload = {
        "inputs": f"Create a vibrant, engaging image for the following tweet: [{tweet}]. Use eye-catching colors, creative typography, and a clean layout. Format the image for Twitter (1200x675 pixels, JPEG or PNG)."
    }

    response = requests.post(api_url, headers=headers, json=payload)
    image_bytes = response.content
    return image_bytes

def save_tweet_streamlit_connection(tweet, tweet_image_url, twitter_api_key, twitter_api_key_secret, twitter_access_token, twitter_access_token_secret, schedule_date_time):
    # Create the SQL connection to pets_db as specified in your secrets file.
    conn = st.connection('twitter_app_db', type='sql')
    
    with conn.session as s:
        # Create a table
        s.execute("""CREATE TABLE IF NOT EXISTS tweets (id INTEGER PRIMARY KEY, tweet TEXT, tweet_image_url TEXT, twitter_api_key TEXT, twitter_api_key_secret TEXT, twitter_access_token TEXT, twitter_access_token_secret TEXT, schedule_date_time TEXT, status TEXT);""")
        s.execute(
            """INSERT INTO tweets (tweet, tweet_image_url, twitter_api_key, twitter_api_key_secret, twitter_access_token, twitter_access_token_secret, schedule_date_time, status) 
            VALUES (:tweet, :tweet_image_url, :twitter_api_key, :twitter_api_key_secret, :twitter_access_token, :twitter_access_token_secret, :schedule_date_time, :status);""",
            params=dict(tweet=tweet, tweet_image_url=tweet_image_url, twitter_api_key=twitter_api_key, twitter_api_key_secret=twitter_api_key_secret, twitter_access_token=twitter_access_token, twitter_access_token_secret=twitter_access_token_secret, schedule_date_time=schedule_date_time, status='PENDING')
        )
        s.commit()
        
    # Query and display the data you inserted
    tweets = conn.query('select * from tweets')
    st.dataframe(tweets)


def save_tweet_old(tweet, tweet_image_url, twitter_api_key, twitter_api_key_secret, twitter_access_token, twitter_access_token_secret, schedule_date_time):
    ROOT_DIR=Path(__file__).parent.parent
    db_path = os.path.join(ROOT_DIR, "databases", "twitter_app.db")
    # Connect to a database (or create one if it doesn't exist)
    connection = sqlite3.connect(db_path)
    
    # Create a cursor object to interact with the database
    cursor = connection.cursor()
    
    # Create a table
    cursor.execute('''CREATE TABLE IF NOT EXISTS tweets (id INTEGER PRIMARY KEY, tweet TEXT, tweet_image_url TEXT, twitter_api_key TEXT, twitter_api_key_secret TEXT, twitter_access_token TEXT, twitter_access_token_secret TEXT, schedule_date_time TEXT, status TEXT)''')
    
    #Insert Data
    cursor.execute("""
    INSERT INTO tweets (tweet, tweet_image_url, twitter_api_key, twitter_api_key_secret, twitter_access_token, twitter_access_token_secret, schedule_date_time, status) 
    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (tweet, tweet_image_url, twitter_api_key, twitter_api_key_secret, twitter_access_token, twitter_access_token_secret, schedule_date_time, 'PENDING'))
    
    # Commit the changes
    connection.commit()
    
    # Close the connection
    connection.close()
    
def save_tweet(tweet, image_url, api_key, api_key_secret, access_token, access_token_secret, schedule_date_time, status):
    url = st.secrets["save_tweet_url"]
    payload = {
                "tweet": tweet,
                "image_url": image_url,
                "api_key": api_key,
                "api_key_secret": api_key_secret,
                "access_token": access_token,
                "access_token_secret": access_token_secret,
                "schedule_date_time":schedule_date_time,
                "status": status
            }        
    return requests.post(url=url, json=payload)

def upload_image(file_bytes):
    access_key = st.secrets["aws_crendentials"]["access_key"]
    secret_key = st.secrets["aws_crendentials"]["secret_key"]
    region = st.secrets["aws_crendentials"]["region"]
    bucket = st.secrets["aws_crendentials"]["bucket"]
    
    _aws_client = aws_client.AwsClient(aws_access_key=access_key, aws_secret_key=secret_key, aws_region=region)
    file_url = _aws_client.upload_file_bytes_to_s3(file_bytes=file_bytes, bucket=bucket, s3_file_name=f"{str(uuid.uuid1())}.png")
    print(f"file_url : {file_url}")
    return file_url
    
# Function to run the scheduler
def scheduler():
    while True:
        print("===scheduler is running")
        current_time = datetime.now()
        loop_end_time = current_time + timedelta(seconds = 1*60)
        
        ROOT_DIR=Path(__file__).parent.parent
        db_path = os.path.join(ROOT_DIR, "databases", "twitter_app.db")
        # Connect to a database (or create one if it doesn't exist)
        connection = sqlite3.connect(db_path)
        connection.row_factory = sqlite3.Row  # This allows row access by column name
        
        # Create a cursor object to interact with the database
        cursor = connection.cursor()
        
        #Delete tweets which has been posted successfully 7 days back
        date_before_seven_days=current_time.date() - timedelta(days=7)
        cursor.execute("""
        DELETE * FROM tweets WHERE status = "SUCCESS" AND schedule_date_time <= ?
        """, (date_before_seven_days,))
        
        current_time_str = current_time.strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute("""
        SELECT * FROM tweets WHERE status = "PENDING" AND schedule_date_time <= ?
        """, (current_time_str,))
        rows = cursor.fetchall()
                
        for row in rows:
            status = row["status"]
            try:
                twitter_poster = twitter_proxy.TwitterPoster(row["twitter_api_key"], row["twitter_api_key_secret"], row["twitter_access_token"], row["twitter_access_token_secret"])
                message, status_code = twitter_poster.post_thread(tweet_text=row["tweet"], image_url=row["tweet_image_url"])
                if status_code == 200:
                    status = "SUCCESS"
                else:
                    status = "FAILED"
            except Exception as e:
                status = "FAILED"
            
            if status!="PENDING":
                # Update the status to SUCCESS
                cursor.execute("""
                UPDATE tweets SET status = ? WHERE id = ?
                """, (status, row["id"],))
            if datetime.now() > loop_end_time:
                break
        
        connection.commit()
        connection.close()
        
        # Wait for 60 seconds before running the scheduler again
        time.sleep(1*60)
        
# Start the scheduler in a separate thread
#scheduler_thread = threading.Thread(target=scheduler, daemon=True)
#add_script_run_ctx(scheduler_thread)
#scheduler_thread.start()

#App Code Starts here
hide_streamlit_style = """
<style>
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
</style>

"""
st.markdown(hide_streamlit_style, unsafe_allow_html=True)

st.title("🦜🔗 Twitter App")
col1, col2 = st.columns(2)
with col1:
    generate_image = True
    if generate_image:
        generate_image = st.checkbox("Generate Image", key="generate_image")
    else:
        st.caption(":blue[_[Generate Image]_] :blue[Coming Soon] :sunglasses:")
    #
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
        generated_image=None
        if generate_image:
            try:
                generated_image = generate_tweet_image(generated_tweet)
                if generated_image:
                    st.image(generated_image)
            finally:
                pass
    # Add assistant response to chat history
    st.session_state.messages.append({"role": "assistant", "content": generated_tweet, "image_url" : generated_image})    
    # Update assistant response to tweet
    st.session_state.tweet = generated_tweet
    if generated_image:
        st.session_state.tweet_image_url = generated_image
    else:
        st.session_state.tweet_image_url = None    
        
with st.sidebar:
    openai_api_key = st.text_input("OpenAI API Key", type="password", key="openai_api_key")
    if not openai_api_key.startswith("sk-"):
        st.warning("Please enter your OpenAI API key!", icon="⚠")
    with st.form("twitter_form"):
        st.write("Post this on X")
        tweet_image_url = None
        tweet = st.text_area(label="Tweet", key="tweet", placeholder="Your tweet to be posted")
        
        #tweet_image_url = st.text_input(label="Tweet Image Url", key="tweet_image_url", placeholder="Image Url to be posted")
        if generated_image:
            st.image(generated_image)
        
        twitter_api_key = st.text_input(label="Api Key", key="twitter_api_key", placeholder="X Developer Account Api Key")
        twitter_api_key_secret = st.text_input(label="Api Key Secret", key="twitter_api_key_secret", placeholder="X Developer Account Api Key Secret")
        twitter_access_token = st.text_input(label="Access Token", key="twitter_access_token", placeholder="X Developer Account Access Token")
        twitter_access_token_secret = st.text_input(label="Access Token Secret", key="twitter_access_token_secret", placeholder="X Developer Account Access Token Secret")
        
        today_date = datetime.now().date()
        date_after_seven_days=today_date + timedelta(days=7)
        
        schedule_date = st.date_input(label="Tweet Schedule Date", value=today_date, min_value=today_date, max_value=date_after_seven_days, 
                                      key="schedule_date", format = "YYYY-MM-DD")
        schedule_time = st.time_input(label="Tweet Schedule Time", value=None, key="schedule_time")
        # Every form must have a submit button.
        post_tweet_submitted = st.form_submit_button("Schedule Tweet")
        if post_tweet_submitted and openai_api_key.startswith("sk-"):
            _="""
            twitter_poster = twitter_proxy.TwitterPoster(twitter_api_key, twitter_api_key_secret, twitter_access_token, twitter_access_token_secret)
            message, status_code = twitter_poster.post_thread(tweet_text=tweet, image_url=tweet_image_url)
            """
            schedule_date_time=datetime.combine(schedule_date, schedule_time)
            schedule_date_time_str = schedule_date_time.strftime('%Y-%m-%d %H:%M:%S')
            
            if generated_image:
                try:
                    tweet_image_url= upload_image(generated_image)
                except Exception as e:
                    print(f"Error :: {e.message}")
            
            if generated_image and tweet_image_url:
                save_tweet(tweet, tweet_image_url, twitter_api_key, twitter_api_key_secret, twitter_access_token, twitter_access_token_secret, schedule_date_time_str, "PENDING")
                display_response_dialog(message="Tweet Scheduled Successfully", status_code=200)
            else:
                display_response_dialog(message="Error while uploading the Image File", status_code=400)
            
                         