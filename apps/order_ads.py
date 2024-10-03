'''
Created on 18 Sept 2024

@author: ubuntu
'''
import base64
import json
import os
import sys

from dotenv.main import load_dotenv, find_dotenv
import requests

import pandas as pd
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

from proxy.copilot_proxy import CopilotProxy
from proxy.facebook_proxy import FacebookProxy
# Sample JSON data
def getDocument():
    # with st.sidebar:
    with st.spinner('In progress...'):
        shop_id=None
        collection_name=None
        if 'shop_collection' not in st.session_state:
            shop_id = "offline_development-ongraph.myshopify.com"
            collection_name = "collection"
        else:
            dic_object=st.session_state.shop_collection
            shop_id = dic_object["shop_id"]
            collection_name = dic_object["collection_name"]
        type_data = "order"
        copilot_proxy = CopilotProxy()
        documents = copilot_proxy.get_shopify_doucuments_by_type(shop_id=shop_id, collection_name=collection_name, type_data=type_data)
        return documents

# Load JSON data
def get_json_data():
    order_list = []
    response = getDocument()
    if response:
        for doc in response:
            data = json.loads(doc)
            order_dic = {}
            order_dic["id"] = data["id"]
            order_dic["order_date"] = data["order_created_at"]
            order_dic["order_status"] = data["order_display_financial_status"]
            order_dic["order_no"] = data["order_confirmation_number"]
            order_dic["order_return_status"] = data["order_return_status"]
            order_dic["currency"] = data["order_currency"]
            order_dic["total_price"] = data["order_total_price"]
            order_dic["user_name"] = data["user_name"]
            order_dic["email"] = data["user_email"]
            order_dic["title"] = data["item_title"]
            order_dic["item_id"] = data["item_variant_id"]
            order_dic["price"] = data["item_price"]
            order_dic["quantity"] = data["item_quantity"]
            if "item_image" in data:
                order_dic["image"] = data["item_image"]
            else:
                order_dic["image"] = None
            order_list.append(order_dic)
    
    return order_list

        
data_list = get_json_data()           
# data_list = json.loads(json_data)
# Convert the JSON data to a DataFrame
df = pd.DataFrame(data_list)

if not df.empty:
    df['Detail'] = [f"View Detail {i}" for i in df['id']]


# Add a column with a "Details" button for each record


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
    selected_record = df[df['id'] == record_id].drop(columns=['Detail'])
    image_url = selected_record.iloc[0]['image']
    order_no = selected_record.iloc[0]['order_no']
    title = selected_record.iloc[0]['title']
    price = selected_record.iloc[0]['price']
    total_price = selected_record.iloc[0]['total_price']
    
    col1, col2 = st.columns(2)
    with col1:
        st.header("Order Image")
        if isNotBlank(image_url):
            st.image(image_url, use_column_width=True)
        else:
            col1.write("image not available")
    with col2:
        st.header("Order Detail")
        col_a, col_b, col_c, col_d = st.columns(4)
        col_a.write(f"Order Number  {order_no}")
        col_b.write(f"Title {title}")
        col_c.write(f"Price {price}")
        col_d.write(f"Total price {total_price}")
    
    cola, colb, colc = st.columns(3)
    with cola:
        # st.write(selected_record)
        if 'ads' not in st.session_state:
            if st.button("Ads Generation"):
                ads(openai_api_key,record_id, title, order_no, image_url)
        else:
            f"ads submitted successfully! item record id: {st.session_state.ads['item']} and {st.session_state.ads['message']}"    
    with colb:
        if st.button("Ads listing"):
            adsList(record_id)
    with colc:
            # Back button to return to the main page
        if st.button("Back"):
            st.session_state.page = 'main'
            st.rerun()
    

@st.dialog("Ads listing", width="large")
def adsList(record_id):
    with st.form("my_form3"): 
        st.write(f"### ads Listing for Record ID {record_id}")
        app_id = st.text_input("Enter app_id ")
        app_secret = st.text_input("Enter app_secret ")
        access_token = st.text_input("Enter access_token ")
        act_account_id = st.text_input("Enter account Id ")
        adset_limit = st.number_input("Enter limit", 1, 100)
        submit_ads_listing = st.form_submit_button("Get Ads Listing")
        if submit_ads_listing:
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
def ads(openai_api_key,record_id, title, description, image_url):
    st.write(f"### Generate Ads for Record ID {record_id}")
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
    
    app_id = st.text_input("Enter app_id ")
    app_secret = st.text_input("Enter app_secret ")
    access_token = st.text_input("Enter access_token ")
    act_account_id = st.text_input("Enter account Id ")
    if creative_option == None or creative_option == 'new creative':
        with st.form("my_form1"):
            if isNotBlank(image_url):
                image_response = requests.get(image_url)
                if image_response.status_code == 200:
                    image_bytes = image_response.content
            else:
                uploaded_file = st.file_uploader("Choose a file", type=["jpg", "png", "jpeg"])
                
            ads_message_submitted = st.form_submit_button("Generate Message For FB Ads")  
            ads_submitted = st.form_submit_button("Generate Image Hash For FB Ads")
            image_hash = None  # "1baa6f1a23d1ca88f74a67a65f48c0f0"#
            
            # Show the uploaded image
            if ads_submitted:
                with st.spinner('Wait for it...'):
                    st.write("Image is being uploaded...")
                    if isNotBlank(image_url):
                        st.image(image_url, caption="Uploaded Image.", use_column_width=True)
                    elif uploaded_file is not None:
                        image_bytes = uploaded_file.read()
                        st.image(uploaded_file, caption="Uploaded Image.", use_column_width=True)
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
                    facebook_proxy=FacebookProxy()
                    result = facebook_proxy.upload_image(files=encoded_image, act_account_id=act_account_id, access_token=access_token)
                    # Step 2: Upload image to Facebook API
                    if 'images' in result:
                        image_hash = result['images']['bytes']['hash']
                        dict = {}
                        dict['image_hash'] = image_hash
                        st.session_state.image_data = dict
                        st.success(f"Image uploaded successfully! Hash: {image_hash}")
                    else:
                        st.error(f"Failed to upload image: {result}")
                    
            if ads_message_submitted:
                with st.spinner('Wait for it...'):
                    copilot_proxy = CopilotProxy()
                    response=copilot_proxy.create_ad_message(title=title, description=description, api_key=openai_api_key)
                    if response and response["message"]:
                        dict = {}
                        dict['ads_message'] = response["message"]
                        st.session_state.message_data = dict
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

def main_page():
    st.write("### Order Listing")
    cola, cold, cole,colf,colg = st.columns([10, 2, 5,5,5], vertical_alignment="top")
    cola.write("Id")
    cold.write("Qty")
    cole.write("Price")
    colf.write("Status")
    colg.write("Action")
    if not df.empty:
    # Create a button in each row inside the table
        for index, row in df.iterrows():
            col1, col4, col5,col6,col7 = st.columns([10, 1, 5,5,5], vertical_alignment="top")
            # Display row data
            col1.write(row['id'])
            col4.write(row['quantity'])
            col5.write(row['price'])
            col6.write(row['order_status'])
            
            # Create an inline button in the table
            if col7.button("Detail", key=row['id']):
                st.session_state.page = 'detail'
                st.session_state.record_id = row['id']
                st.rerun()


# Initialize session state for page navigation
if 'page' not in st.session_state:
    st.session_state.page = 'main'

# Page navigation logic
if st.session_state.page == 'main':
    main_page()
elif st.session_state.page == 'detail':
    show_details(st.session_state.record_id)
