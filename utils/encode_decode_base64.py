'''
Created on 1 Oct 2024

@author: dileep sharma
'''
import base64
import json


def encode_base64(my_string):
    encoded_data = base64.b64encode(my_string.encode('utf-8'))
    # Converting bytes to string
    return encoded_data.decode('utf-8')


def decode_base64(encoded_string):
    decoded_data = base64.b64decode(encoded_string)
    # Converting bytes to string
    return decoded_data.decode('utf-8')


if __name__ == '__main__':
    sho_dict = {}
    sho_dict['shop_id'] = "offline_development-ongraph.myshopify.com"
    sho_dict['collection_name'] = "collection"
    sho_dict['id'] = "43489535230141"
    my_string = json.dumps(sho_dict)
    print(f"json_object:{my_string}")
    encode_string=encode_base64(my_string)
    print(f"encode:{encode_string}")
    
    dencode_string=decode_base64("eyJzaG9wX2lkIjogIm9mZmxpbmVfZGV2ZWxvcG1lbnQtb25ncmFwaC5teXNob3BpZnkuY29tIiwgImNvbGxlY3Rpb25fbmFtZSI6ICJjb2xsZWN0aW9uIiwgImlkIjogIjQzNDg5NTM1MjMwMTQxIn0=")
    
    print(f"dencode:{dencode_string}")

