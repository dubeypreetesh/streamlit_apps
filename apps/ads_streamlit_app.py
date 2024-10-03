'''
Created on 18 Sept 2024

@author: dileep sharma
'''
import streamlit as st

product_page = st.Page("product_ads.py", title="Product List", icon=":material/dashboard:")
order_page = st.Page("order_ads.py", title="Order List", icon=":material/dashboard:")

pg = st.navigation([product_page, order_page])
#st.set_page_config(page_title="Ads manager", page_icon=":material/dashboard:")


page_title = f"Ads manager AI Assistant"
st.set_page_config(page_title=page_title, page_icon=":flag-in:")

hide_streamlit_style = """
<style>
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
</style>

"""
st.markdown(hide_streamlit_style, unsafe_allow_html=True)

st.title("🔗 Ads manager AI Assistant")
pg.run()

with st.sidebar:
    with st.form("my_form0"):
        st.write(f"### Fill shop and collection info ")
        shop_id = st.text_input(label="Enter Shop Id ",placeholder="Enter Shop Id")
        collection_name = st.text_input(label="Enter Collection Name ",placeholder="Enter collection name")
        submit_ads_listing = st.form_submit_button("Submit")
        if submit_ads_listing:
            st.session_state.shop_collection={}
            sho_dict = {}
            sho_dict['shop_id'] = shop_id
            sho_dict['collection_name'] = collection_name
            st.session_state.shop_collection = sho_dict
            st.rerun()
    