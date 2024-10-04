'''
Created on 25 Sept 2024

@author: ubuntu
'''
import webbrowser

import requests


class FacebookProxy():
    name = "facebook_proxy"
    description = "Get the Authorization Code and exchange the authorization code for an access token"
    
    BASE_URL = "https://graph.facebook.com/v20.0"
    FB_BASE_URL = "https://www.facebook.com/v20.0"
    
    def get_authorization_code(self,app_id,scope, callback_url,state):
        # Construct the OAuth URL
        oauth_url = (
            f"{self.FB_BASE_URL}/dialog/oauth?client_id={app_id}&redirect_uri={callback_url}&scope={scope}&response_type=code&state={state}"
        )
        webbrowser.open(oauth_url)
        
    def get_access_token(self,app_id,app_secret, callbacl_url, code):
        url = f"{self.BASE_URL}/oauth/access_token?client_id={app_id}&redirect_uri={callbacl_url}&client_secret={app_secret}&code={code}"
        response = requests.get(url)
        return response.json()
    
    def upload_image(self, files, act_account_id, access_token):
        url = f"{self.BASE_URL}/{act_account_id}/adimages"
        payload = {
            'access_token': access_token,
            'bytes': files
        }
        
        headers = {
          'Content-Type': 'application/json'
        }
        response = requests.post(url, headers=headers, data=payload)
        # Check the response
        if response.status_code == 200:
            return response.json()
        else:
            return response.text 
