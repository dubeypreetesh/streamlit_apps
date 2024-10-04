'''
Created on 6 Sept 2024

@author: ubuntu
'''

import base64
import json
import os

from dotenv import load_dotenv, find_dotenv
import requests

import pandas as pd
import streamlit as st
import sys
from time import time
import io
from streamlit_javascript import st_javascript

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
# Sample JSON data
from utils import encode_decode_base64
from proxy.copilot_proxy import CopilotProxy
from proxy.facebook_proxy import FacebookProxy
def getDocuments():
    with st.spinner('In progress...'):
        shop_id=None
        collection_name=None
        query_params = st._get_query_params()
        if not query_params:
            if 'shop_collection' not in st.session_state:
                st.session_state.shop_collection={}
                sho_dict = {}
                sho_dict['shop_id'] = "offline_development-ongraph.myshopify.com"
                sho_dict['collection_name'] = "collection"
                st.session_state.shop_collection = sho_dict
                dic_object=st.session_state.shop_collection
                shop_id = dic_object["shop_id"]
                collection_name = dic_object["collection_name"] 
            else:
                dic_object=st.session_state.shop_collection
                shop_id = dic_object["shop_id"]
                collection_name = dic_object["collection_name"]
        else:
            access_token=query_params['access_token'][0]
            expires_at=query_params['expires_at'][0]
            st.session_state.token_collection={}
            token_dict = {}
            token_dict['access_token'] = access_token
            token_dict['expires_at'] = expires_at
            st.session_state.token_collection = token_dict
            dencode_string=encode_decode_base64.decode_base64(query_params['state'][0])
            res = json.loads(dencode_string)
            st.session_state.shop_collection={}
            sho_dict = {}
            sho_dict['shop_id'] = res["shop_id"]
            sho_dict['collection_name'] = res["collection_name"]
            st.session_state.shop_collection = sho_dict
            dic_object=st.session_state.shop_collection
            shop_id = dic_object["shop_id"]
            collection_name = dic_object["collection_name"] 
            
        type_data = "product"
        copilot_proxy = CopilotProxy()
        documents = copilot_proxy.get_shopify_documents_by_type(shop_id=shop_id, collection_name=collection_name, type_data=type_data)
        return documents


# Load JSON data
def get_json_data():
    product_list = []
    response = getDocuments()
    if response:
        for doc in response:
            data = json.loads(doc)
            product_dic = {}
            product_dic["id"] = data["id"]
            product_dic["vendor"] = data["item_vendor"]
            product_dic["product_id"] = data["item_product_id"]
            product_dic["status"] = data["item_status"]
            product_dic["title"] = data["item_title"]
            product_dic["name"] = data["item_display_name"]
            product_dic["price"] = data["item_price"]
            if "item_image_url" in data:
                product_dic["image"] = data["item_image_url"]
            else:
                product_dic["image"] = None
            product_dic["store_url"] = data["item_online_store_preview_url"]
            product_list.append(product_dic)
    
    return product_list

        
data_list = get_json_data()           
    # Convert the JSON data to a DataFrame
df = pd.DataFrame(data_list)
if not df.empty:
    # Add a column with a "Details" button for each record
    df['Details'] = [f"View Details {i}" for i in df['id']]


# JavaScript for redirecting to an external URL
def js_redirect(url):
    js = f'window.open("{url}", "_blank").then(r => window.parent.location.href);'
    st_javascript(js)
    
# Function to display the detailed record
def show_details(record_id):
    if is_cloud: 
        with st.sidebar:
            st.title("fill your information")
            openai_api_key = st.text_input("OpenAI API Key", type="password", key="openai_api_key")
            if not openai_api_key.startswith("sk-"):
                st.warning("Please enter your OpenAI API key!", icon="⚠")
    else:
        with st.sidebar:
            openai_api_key = st.secrets["openai"]["api_key"]
    
    st.write(f"### Detailed View of Record ID {record_id}")
    selected_record = df[df['id'] == record_id].drop(columns=['Details'])
    image_url = selected_record.iloc[0]['image']
    name = selected_record.iloc[0]['name']
    title = selected_record.iloc[0]['title']
    price = selected_record.iloc[0]['price']
    store_url = selected_record.iloc[0]['store_url']
    
    col1, col2 = st.columns(2)
    with col1:
        st.header("Product Image")
        if isNotBlank(image_url):
            st.image(image_url, use_column_width=True)
        else:
            col1.write("image not available")
    with col2:
        st.header("Product Detail")
        col_a, col_b, col_c, col_d = st.columns([40,20,20,20])
        col_a.write(f"Name : {name}")
        col_b.write(f"Title :{title}")
        col_c.write(f"Price :{price}")
        col_d.write(f"check out this shop :[shop store]({store_url})")
    
    cola, colb, colc = st.columns(3)
    get_token=False
    access_token=None
    expires_at=None
    if 'token_collection' in st.session_state:
        dic_object=st.session_state.token_collection
        access_token = dic_object["access_token"]
        expires_at = int(dic_object["expires_at"])
        current_time = int(time() * 1000)
        if current_time > expires_at:
            get_token=True
            
    elif 'token_collection' not in st.session_state:
        get_token=True
    
    
    if get_token:
        with st.form("my_form4"): 
            submit_authentication = st.form_submit_button("User Authentication")
            if submit_authentication:
                fb_proxy = FacebookProxy()
                dic_object=st.session_state.shop_collection
                state_dict = {}
                state_dict['shop_id'] = dic_object["shop_id"]
                state_dict['collection_name'] = dic_object["collection_name"]
                state_dict['id'] = record_id
                state_dict['type'] = "product"
                encoded_string=encode_decode_base64.encode_base64(json.dumps(state_dict))
                state=encoded_string
                try:
                    BASE_URL = "https://graph.facebook.com/v20.0"
                    FB_BASE_URL = "https://www.facebook.com/v20.0"
                    fb_redirect_url = f'{FB_BASE_URL}/dialog/oauth?client_id={st.secrets["fb_credentials"]["client_id"]}&redirect_uri={st.secrets["fb_credentials"]["callback_url"]}&scope={st.secrets["fb_credentials"]["scope"]}&response_type=code&state={state}'
                    js_redirect(fb_redirect_url)
                    #fb_proxy.get_authorization_code(app_id=st.secrets["fb_credentials"]["client_id"],scope=st.secrets["fb_credentials"]["scope"], callback_url=st.secrets["fb_credentials"]["callback_url"],state=state)
                except Exception as e:
                    print(f"Error while authorization facebook: {e}")
    else:
        dic_object=st.session_state.token_collection
        access_token = dic_object["access_token"]
        expires_at = int(dic_object["expires_at"])
        current_time = int(time() * 1000)
        if expires_at > current_time:
            with cola:
                # st.write(selected_record)
                if st.button("Ads Generation"):
                    if openai_api_key.startswith("sk-"):
                        ads(openai_api_key,access_token,expires_at,record_id, title, name, image_url)
                    else:
                        st.write("Enter OpenAI Api Key")
                if 'ads' in st.session_state:
                    ads_dic=st.session_state.ads
                    if ads_dic["item"]==record_id:
                        f"ads submitted successfully! item record id: {ads_dic['item']} and {ads_dic['message']}"    
            with colb:
                if st.button("Ads listing"):
                    if openai_api_key.startswith("sk-"):
                        adsList(record_id,access_token)
                    else:
                        st.write("Enter OpenAI Api Key")
    
    with colc:
            # Back button to return to the main page
        if st.button("Back"):
            st.session_state.page = 'main'
            query_params = st._get_query_params()
            if query_params:
                del query_params["id"]
                st._set_query_params()
            st.rerun()
    

@st.dialog("Ads listing", width="large")
def adsList(record_id,access_token):
    with st.form("my_form3"): 
        st.write(f"### ads Listing for Record ID {record_id}")
        app_id = st.secrets["fb_credentials"]["client_id"] 
        app_secret=st.secrets["fb_credentials"]["client_secret"] 
        act_account_id = st.text_input("Enter account Id ")
        adset_limit = st.number_input("Enter limit", 1, 100)
        submit_ads_listing = st.form_submit_button("Get Ads Listing")
        if submit_ads_listing:
            if not access_token:
                st.error("access_token cannot be empty")
                st.stop()
                
            if not act_account_id:
                st.error("act_account_id cannot be empty.")
                st.stop()
                
            if not adset_limit:
                st.error("adset_limit cannot be 0.")
                st.stop()
            copilot_proxy = CopilotProxy()
            adsListingResponse = copilot_proxy.get_fb_ads(access_token=access_token, app_id=app_id, app_secret=app_secret, act_account_id=act_account_id, limit=adset_limit)
            if 'data' in adsListingResponse:
                ads_list = []
                for adsResponse in adsListingResponse['data']:
                    ads_dic = {}
                    ads_dic["ads_id"] = adsResponse["id"]
                    ads_dic["ads_name"] = adsResponse["name"]
                    ads_dic["campaign_id"] = adsResponse["campaign_id"]
                    ads_dic["adset_id"] = adsResponse["adset_id"]
                    ads_dic["creative_id"] = adsResponse["creative"]["id"]
                    ads_dic["status"] = adsResponse["status"]
                    ads_dic["bid_amount"] = adsResponse["bid_amount"]
                    ads_dic["created_time"] = adsResponse["created_time"]
                    ads_list.append(ads_dic)
                ads_df = pd.DataFrame(ads_list)
                st.dataframe(ads_df, use_container_width=True)
            else:
                st.error(f"Failed to geting adslisting: {adsListingResponse}")


@st.dialog("Ads Generation", width="large")
def ads(openai_api_key,access_token,expires_at,record_id, title, description, image_url):
    st.write(f"### Generate Ads for Record ID {record_id}")
    current_time = int(time() * 1000)
    if current_time > expires_at or not expires_at:
        st.write(f"### access token has expired .close popup and do user authentication for Record ID {record_id}")
    else:
        if 'image_data' not in st.session_state:
            st.session_state.image_data = {}
        if 'message_data' not in st.session_state:
            st.session_state.message_data = {}
            
        campaign_option = st.radio("Campaign Option?",
                ("new campaign", "existing campaign"),
                index=None,
        )
        adset_option = st.radio("Adset Option?",
                ("new adset", "existing adset"),
                index=None,
            )
        creative_option = st.radio("creative Option?",
                ("new creative", "existing creative"),
                index=None,
            )
        image_option = st.radio("Product Image Option?",
                ("use product image", "use AI image"),
                index=None,
        )
        app_id = st.secrets["fb_credentials"]["client_id"] 
        app_secret=st.secrets["fb_credentials"]["client_secret"] 
        act_account_id = st.text_input("Enter account Id ")
        if creative_option == None or creative_option == 'new creative':
            with st.form("my_form1"):
                image_bytes=None
                if image_option == None or image_option == 'use product image':
                    print("product image use")
                    if isNotBlank(image_url):
                        image_response = requests.get(image_url)
                        if image_response.status_code == 200:
                            image_bytes = image_response.content
                    else:
                        uploaded_file = st.file_uploader("Choose a file", type=["jpg", "png", "jpeg"])
                elif image_option == 'use AI image':
                    print("product AI use")
                    try:
                        image_bytes = generate_tweet_image(title)
                    except Exception as e:
                        print(f"Error while generating the image :: {e}")
                    
                ads_message_submitted = st.form_submit_button("Generate Message For FB Ads")  
                ads_submitted = st.form_submit_button("Generate Image Hash For FB Ads")
                image_hash = None  # "1baa6f1a23d1ca88f74a67a65f48c0f0"#
                
                # Show the uploaded image
                if ads_submitted:
                    with st.spinner('Wait for it...'):
                        st.write("Image is being uploaded...")
                        if image_option == None or image_option == 'use product image':
                            print("ads_submitted use product image")
                            if isNotBlank(image_url):
                                st.image(image_url, caption="Uploaded Image.", use_column_width=True)
                            elif uploaded_file is not None:
                                image_bytes = uploaded_file.read()
                                st.image(uploaded_file, caption="Uploaded Image.", use_column_width=True)
                        elif image_option == 'use AI image':
                            print("ads_submitted use ai image")
                            if image_bytes:
                                image_bytes_io = io.BytesIO(image_bytes)
                                image_bytes_io.seek(0)
                                st.image(image=image_bytes_io)
                        if image_bytes:
                            print("upload image_bytes")
                            encoded_image = base64.b64encode(image_bytes).decode('utf-8')
                            if not app_id:
                                st.error("app_id cannot be empty")
                                st.stop()
                            
                            if not app_secret:
                                st.error("app_secret cannot be empty.")
                                st.stop()
                                
                            if not access_token:
                                st.error("access_token cannot be empty")
                                st.stop()
                                
                            if not act_account_id:
                                st.error("act_account_id cannot be empty.")
                                st.stop()
                                
                            # Show the uploaded image
                            #app_id=st.secrets["fb_credentials"]["client_id"], app_secret=st.secrets["fb_credentials"]["client_secret"]
                            facebook_proxy=FacebookProxy()
                            act_account_id=f"act_{act_account_id}"
                            result = facebook_proxy.upload_image(files=encoded_image, act_account_id=act_account_id, access_token=access_token)
                            # Step 2: Upload image to Facebook API
                            if 'images' in result:
                                image_hash = result['images']['bytes']['hash']
                                image_dict = {}
                                image_dict['image_hash'] = image_hash
                                st.session_state.image_data = image_dict
                                st.success(f"Image uploaded successfully! Hash: {image_hash}")
                            else:
                                st.error(f"Failed to upload image: {result}")
                        
                if ads_message_submitted:
                    with st.spinner('Wait for it...'):
                        copilot_proxy = CopilotProxy()
                        response=copilot_proxy.create_ad_message(title=title, description=description, api_key=openai_api_key)
                        if response and response["message"]:
                            message_dict = {}
                            message_dict['ads_message'] = response["message"]
                            st.session_state.message_data = message_dict
                            st.success("ads message generate successfully!")
                
        with st.form("my_form2"):
            campaign_name = None
            campaign_id = None
    
            if campaign_option == None or campaign_option == 'new campaign':
                campaign_name = st.text_input("Enter campaign_name ")
            elif campaign_option == 'existing campaign':
                campaign_id = st.text_input("Enter campaign_id ")
            
            adset_name = None
            adset_bid_amount = None
            adset_daily_budget = None
            adset_id = None
            if adset_option == None or adset_option == 'new adset':
                adset_name = st.text_input("Enter adset_name")
                adset_bid_amount = st.number_input("Enter adset_bid_amount", 0, 100)
                adset_daily_budget = st.number_input("Enter adset_daily_budget", 0, 10000)
            else:
                adset_id = st.text_input("Enter adset_id")
                 
            adcreative_name = None
            adcreative_message = None
            adcreative_image_hash = None
            creative_id = None
            if creative_option == None or creative_option == 'new creative':
                adcreative_name = st.text_input("Enter adcreative_name")
                adcreative_image_hash = st.text_input("Image Hash ", value=st.session_state.image_data.get("image_hash"))
                adcreative_message = st.text_area("Enter adcreative_message", value=st.session_state.message_data.get("ads_message"))
            else:
                creative_id = st.text_input("Enter creative_id")
            
            ad_name = st.text_input("Enter ad_name")
            submitted = st.form_submit_button("Submit")
            if submitted:
                if not app_id:
                    st.error("app_id cannot be empty.")
                    st.stop()
                    
                if not app_secret:
                    st.error("app_secret cannot be empty")
                    st.stop()
                    
                if not access_token:
                    st.error("access_token cannot be empty")
                    st.stop()
                    
                if not act_account_id:
                    st.error("act_account_id cannot be empty")
                    st.stop()
                    
                if campaign_option == None:
                    st.error("select campaign_option")
                    st.stop()
                    
                if adset_option == None:
                    st.error("select adset_option")
                    st.stop()
                    
                if creative_option == None:
                    st.error("select creative_option")
                    st.stop()
                    
                if campaign_option == 'new campaign':
                    if not campaign_name:
                        st.error("campaign_name cannot be empty")
                        st.stop()
                
                if campaign_option == 'existing campaign':
                    if not campaign_id:
                        st.error("campaign_id cannot be empty")
                        st.stop()
                    
                if adset_option == 'new adset':
                    if not adset_name:
                        st.error("adset_name cannot be empty")
                        st.stop()
                        
                    if not adset_bid_amount:
                        st.error("adset_bid_amount cannot be 0")
                        st.stop()
                        
                    if not adset_daily_budget:
                        st.error("adset_daily_budget cannot be 0")
                        st.stop()
                
                if adset_option == 'existing adset':
                    if not adset_id:
                        st.error("adset_id cannot be empty")
                        st.stop()
                            
                if creative_option == 'new creative':
                    if not adcreative_name:
                        st.error("adcreative_name cannot be empty")
                        st.stop()
                        
                    if not adcreative_image_hash:
                        st.error("adcreative_image_hash cannot be empty")
                        st.stop()
                        
                    if not adcreative_message:
                        st.error("adcreative_message cannot be empty")
                        st.stop()
                
                if creative_option == 'existing creative':
                    if not creative_id:
                        st.error("creative_id cannot be empty")
                        st.stop()
                            
                if not ad_name:
                    st.error("ad_name cannot be empty")
                    st.stop()
                copilot_proxy = CopilotProxy()
                response = copilot_proxy.create_fb_ads(access_token=access_token, app_id=app_id, app_secret=app_secret,
                            act_account_id=act_account_id, api_key=openai_api_key,
                            campaign_id=campaign_id, campaign_name=campaign_name, adset_id=adset_id,
                            adset_name=adset_name, adset_bid_amount=adset_bid_amount, adset_daily_budget=adset_daily_budget,
                            creative_id=creative_id, adcreative_name=adcreative_name, adcreative_image_hash=adcreative_image_hash,
                            adcreative_message=adcreative_message, ad_name=ad_name)
                st.session_state.ads = {"item": record_id, "message": f"ads Name is {ad_name} and {response['output']}"}
                st.rerun()


def isBlank (myString):
    return not (myString and myString.strip())


def isNotBlank (myString):
    return bool(myString and myString.strip())

def generate_tweet_image(tweet: str):
    api_url = st.secrets["image_generation"]["api_url"]
    api_key = st.secrets["image_generation"]["api_key"]
    headers = {"Authorization": f"Bearer {api_key}"}
    
    payload = {
        "inputs": f"Design a vibrant, engaging image for the following facebook ads : [{tweet}]. Ensure the image is eye-catching with bold, contrasting colors and dynamic, creative typography that matches the facebook ads tone. Keep the layout clean and balanced, with enough negative space to avoid clutter. Incorporate visual elements or icons relevant to the facebook ads content. Format the image for FACEBOOK (1200x675 pixels, JPEG or PNG) with optimized clarity for both mobile and desktop viewing."
    }
    
    response = requests.post(api_url, headers=headers, json=payload)
    image_bytes = response.content
    return image_bytes

def main_page():
    st.write("### Product Listing")
    cola, colb, colc, cold, cole = st.columns([15, 35, 10, 10, 10], vertical_alignment="top")
    cola.write("Id")
    colb.write("Name")
    colc.write("Price")
    cold.write("Status")
    cole.write("Action")
    
    if not df.empty:
        # Create a button in each row inside the table
        for index, row in df.iterrows():
            col1, col2, col3, col4, col5 = st.columns([15, 35, 10, 10, 10], vertical_alignment="top")
            # Display row data
            col1.write(row['id'])
            col2.write(row['name'])
            col3.write(row['price'])
            col4.write(row['status'])
            
            # Create an inline button in the table
            if col5.button("Details", key=row['id']):
                st.session_state.page = 'details'
                st.session_state.record_id = row['id']
                st.rerun() 


# Initialize session state for page navigation
if 'page' not in st.session_state:
    st.session_state.page = 'main'

# Page navigation logic
if st.session_state.page == 'main':
    query_params = st._get_query_params()
    if not query_params:
        main_page()
    else:
        value=query_params['id'][0]
        del query_params["id"]
        st._set_query_params()
        show_details(value)
    
elif st.session_state.page == 'details':
    show_details(st.session_state.record_id)
