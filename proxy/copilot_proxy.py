'''
Created on 26 Sept 2024

@author: ubuntu
'''
import requests


class CopilotProxy(object):
    name = "Copilot Proxy"
    description = "CopilotProxy call api from copilot"
    
    BASE_URL = "https://copilot.heymira.ai"
    #BASE_URL = "http://127.0.0.1:8001"
    
    """
        *** api call for fb ads copilot ***
    """
    
    def validate_token_and_account(self, access_token, app_id, app_secret, act_account_id):
        url = f"{self.BASE_URL}/fb-ads/validate/account/token"
        payload = {
            'access_token': access_token,
            'app_id': app_id,
            'app_secret':app_secret,
            'act_account_id':act_account_id
        }
        
        response = requests.post(url, json=payload)
        # Check the response
        if response.status_code == 200:
            return response.status_code
        else:
            return response.json()
        
    def validate_token(self, access_token, app_id, app_secret):
        url = f"{self.BASE_URL}/fb-ads/validate/token"
        payload = {
            'access_token': access_token,
            'app_id': app_id,
            'app_secret':app_secret
        }
        response = requests.post(url, json=payload)
        return response.json()
        
    def create_fb_ads(self, access_token, app_id, app_secret, act_account_id, api_key,
                      campaign_id, campaign_name, adset_id, adset_name, adset_bid_amount, adset_daily_budget, creative_id, adcreative_name,
                      adcreative_image_hash, adcreative_message, ad_name):
        url = f"{self.BASE_URL}/fb-ads/create"
        payload = {
            'access_token': access_token,
            'app_id': app_id,
            'app_secret':app_secret,
            'api_key':api_key,
            'act_account_id':act_account_id,
            'campaign_id':campaign_id,
            'campaign_name':campaign_name,
            'adset_id':adset_id,
            'adset_name':adset_name,
            'adset_bid_amount':adset_bid_amount,
            'adset_daily_budget':adset_daily_budget,
            'creative_id':creative_id,
            'adcreative_name':adcreative_name,
            'adcreative_image_hash':adcreative_image_hash,
            'adcreative_message':adcreative_message,
            'ad_name':ad_name
        }
        
        response = requests.post(url, json=payload)
        return response.json()
        
    def get_fb_ads(self, access_token, app_id, app_secret, act_account_id, limit):
        url = f"{self.BASE_URL}/fb-ads/get"
        payload = {
            'access_token': access_token,
            'app_id': app_id,
            'app_secret':app_secret,
            'act_account_id':act_account_id,
            'limit':limit
        }
        
        response = requests.post(url, json=payload)
        return response.json()
        
    def create_ad_message(self, title, description, api_key):
        url = f"{self.BASE_URL}/fb-ads/create/message"
        payload = {
            'title': title,
            'description': description,
            'api_key':api_key
        }
        
        response = requests.post(url, json=payload)
        return response.json()
    
    def get_account_metrics(self, access_token, app_id, app_secret, act_account_id):
        url = f"{self.BASE_URL}/fb-ads/account/metrics"
        payload = {
            'access_token': access_token,
            'app_id': app_id,
            'app_secret':app_secret,
            'act_account_id':act_account_id
        }
        
        response = requests.post(url, json=payload)
        return response.json()
        
    def get_campain_metrics(self, access_token, app_id, app_secret, campain_id):
        url = f"{self.BASE_URL}/fb-ads/campain/metrics"
        payload = {
            'access_token': access_token,
            'app_id': app_id,
            'app_secret':app_secret,
            'campain_id':campain_id
        }
        
        response = requests.post(url, json=payload)
        return response.json()
        
    def get_adset_metrics(self, access_token, app_id, app_secret, adset_id):
        url = f"{self.BASE_URL}/fb-ads/adset/metrics"
        payload = {
            'access_token': access_token,
            'app_id': app_id,
            'app_secret':app_secret,
            'adset_id':adset_id
        }
        
        response = requests.post(url, json=payload)
        return response.json()
        
    def get_ads_metrics(self, access_token, app_id, app_secret, ads_id):
        url = f"{self.BASE_URL}/fb-ads/metrics"
        payload = {
            'access_token': access_token,
            'app_id': app_id,
            'app_secret':app_secret,
            'ads_id':ads_id
        }
        
        response = requests.post(url, json=payload)
        return response.json()
        
    def get_ads_details(self, access_token, app_id, app_secret, ads_id):
        url = f"{self.BASE_URL}/fb-ads/details"
        payload = {
            'access_token': access_token,
            'app_id': app_id,
            'app_secret':app_secret,
            'ads_id':ads_id
        }
        
        response = requests.post(url, json=payload)
        return response.json()

    """
        *** api call for shopify copilot ***
    """
    
    def get_shopify_documents_by_type(self, shop_id, collection_name, type_data):
        url = f"{self.BASE_URL}/shopify/documents/list"
        payload = {
            'shop_id': shop_id,
            'collection_name': collection_name,
            'type':type_data
        }
        
        response = requests.post(url, json=payload)
        return response.json()
    
    def chat_shopify_data(self,shop_id,collection_name,question,chat_history,checkout_data,user_id):
        url = f"{self.BASE_URL}/shopify/chat"
        payload = {
            'shop_id': shop_id,
            'collection_name': collection_name,
            'question':question,
            'chat_history':chat_history,
            'checkout_data':checkout_data,
            'user_id':user_id
        }
        response = requests.post(url, json=payload)
        print(f"result:{response.text}")
        return response.text
    
    
    """

        *** api call for website copilot ***

    """
    
    def website_lead_chat(self,x_api_key,session_id, collection_name,question):
        api_url = f"{self.BASE_URL}/sites-service/websites/chat"
        headers = {
        "x-api-key": x_api_key,
        "Content-Type": "application/json"
        }
        payload = {
            "session_id": session_id,            
            "collection_name":collection_name,
            "question":question
        }
        response=requests.post(url=api_url,headers=headers, json=payload)
        data=response.json()
        if response.status_code == 200:
            return data['answer']
        else:
            return data['error']
        