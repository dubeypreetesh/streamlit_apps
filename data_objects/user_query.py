'''
Created on 24-Sep-2024

@author: ongraph
'''
from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.prompts import PromptTemplate
from pydantic import BaseModel, Field, root_validator
from utils import llm_utils
from dotenv import load_dotenv, find_dotenv
import os

_ = load_dotenv(find_dotenv())  # read local .env file

class UserQuery(BaseModel):
    """UserQuery for eCommerce support system about products, orders, or abandon checkout."""

    is_order_inquiry: bool = Field(
        description="True if the query is about a specific order inquiry (e.g., order status, delivery, or product-related issues in an order), otherwise False."
    )
    is_checkout_inquiry: bool = Field(
        description="True if the query is about an abandon checkout inquiry (e.g., items in an abandon cart or related offers to complete the checkout), otherwise False."
    )
    is_product_inquiry: bool = Field(
        description="True if the query is about product details, features, or availability, otherwise False."
    )
    extracted_order_numbers: list[str] = Field(
        description="List of strings containing the order number(s) extracted from the user query only if 'is_order_inquiry' is True, otherwise an empty list."
    )
    
    """
    @root_validator
    def check_inquiry_flags(cls, values):
        is_order_inquiry = values.get('is_order_inquiry')
        is_checkout_inquiry = values.get('is_checkout_inquiry')
        is_product_inquiry = values.get('is_product_inquiry')
        extracted_order_numbers = values.get('extracted_order_numbers')

        # Only one of is_order_inquiry or is_checkout_inquiry can be True at a time
        if is_order_inquiry and is_checkout_inquiry:
            raise ValueError("Both 'is_order_inquiry' and 'is_checkout_inquiry' cannot be True at the same time.")

        # Ensure extracted_order_numbers is empty if is_order_inquiry is False
        if not is_order_inquiry:
            values['extracted_order_numbers'] = []

        # Both is_checkout_inquiry and is_product_inquiry can be True together
        return values
    """
    
def test_pydantic(query: str, chat_history: list):  
    try: 
        # Set up a parser + inject instructions into the prompt template.
        parser = PydanticOutputParser(pydantic_object=UserQuery)
        
        # Define the prompt with clear instructions
        prompt = PromptTemplate(
            template="""
            You are an AI assistant specialized in eCommerce support. Analyze the following chat history and the current user query to determine the following:
    
            1. `is_order_inquiry`: Set this to `true` **only if** the query is asking for information specific to the status, modification, or details of a particular order (e.g., order status, delivery status, or product-related issues in a specific order). 
            
                If the query is about general processes or policies (e.g., "How can I cancel my order?" or "What is your return policy?") even if an order number is mentioned, set this to `false`. Focus on the intent of the query—if the user is asking about a process that can be answered through general policy or FAQ documentation, set this to `false`.
                
                If the query is related to an order, set `is_checkout_inquiry` to `false`. 
            
            2. `is_checkout_inquiry`: Set this to `true` **if the query refers to any items, discounts, coupon codes or other details about the user's checkout**, including abandoned checkouts. 
            
                If the user mentions products in their checkout, discounts, or asks about any actions specific to their checkout (e.g., applying discounts, checking items in their checkout), set this to `true`. 
    
                For example, if the user asks "What items are in my checkout?" or "Are there any discounts on my checkout items?" both `is_checkout_inquiry` and `is_product_inquiry` should be set to `true`.
        
                If `is_checkout_inquiry` is `true`, `is_order_inquiry` must be set to `false`.                            
            
            3. `is_product_inquiry`: Set this to `true` if the query asks about product details, features, availability, or recommendations (e.g., "What are the features of this product?" or "Tell me about the products in my checkout.").
            
                **Both `is_product_inquiry` and `is_checkout_inquiry` should be `true` if the query asks about products or discounts related to the user's abandoned checkout.**
                
            4. Ensure that **only one of** `is_order_inquiry` or `is_checkout_inquiry` can be `true` at a time. If one is `true`, the other must be `false`.
    
            5. `extracted_order_numbers`: Extract specific order number(s) only if `is_order_inquiry` is `true`. If `is_order_inquiry` is `false`, return an empty list even if order numbers are mentioned in the query.
    
            Chat history: {chat_history}
    
            User query: {query}
            
            Your response **must** be a valid JSON object **without any extra characters**, comments, explanations, or backticks. Ensure the output is a plain JSON string with no formatting errors. The JSON format should be:

            {{
                "is_order_inquiry": <true or false>,
                "is_checkout_inquiry": <true or false>,
                "is_product_inquiry": <true or false>,
                "extracted_order_numbers": [<List of strings representing order numbers>]
            }}
    
            Only output the JSON string with no additional text or formatting.
            """,
            input_variables=["chat_history", "query"],
            #partial_variables={"format_instructions": parser.get_format_instructions()},
        )
        
        model = llm_utils.get_chat_model(model_name="gpt-4o-mini", temperature=0, openai_api_key=os.environ['OPENAI_API_KEY'])
        
        # Combine history and current query for complete context
        chat_history_str = "\n".join([f"{speaker}: {content}" for speaker, content in chat_history])
        
        chain = prompt | model
        response = chain.invoke({"chat_history" : chat_history_str, "query": query})
        #Extract json and remove any extra chars if any
        output_str = response.content
        start = output_str.find('{')
        end = output_str.find('}')+1
        output_str_final = output_str[start:end]
        return parser.parse(output_str_final)
    except Exception as e:
        print(f"Error : {e}")


import re
if __name__ == '__main__':
    # Sample chat history
    chat_history = [
        ("user", "hi"),
        ("assistant", "Hi there, how can I assist you today?"),
        ("user", "I need details of the item of my checkout."),
        ("assistant", "The item in your checkout is the **Apple iPad Pro 11″ (4th Generation)**. Here are the details:\n\n- **Model**: Apple iPad Pro 11″ (4th Generation)\n- **Chip**: M2 chip\n- **Display**: Liquid Retina Display\n- **Storage**: 128GB\n- **Connectivity**: Wi-Fi 6E\n- **Cameras**: 12MP front camera, 12MP and 10MP back cameras\n- **Face ID**: Yes\n- **Battery Life**: All-Day Battery Life\n- **Price**: ₹79,900.00\n\nFor more information, you can view the product [here](https://development-ongraph.myshopify.com/products/apple-ipad-pro-11-4th-generation-with-m2-chip-liquid-retina-display-128gb-wi-fi-6e-12mp-front-12mp-and-10mp-back-cameras-face-id-all-day-battery-life-space-grey).\n\nIf you have any other questions or need further assistance, feel free to ask!"),
        ("user", "was there any discount applied?"),
        ("assistant", "Yes, there was a discount applied to your checkout. The total discount amount is ₹15,980.00. \n\nIf you have any more questions or need further assistance, feel free to ask!"),
        ("user", "are there any discount coupons available?"),
        ("assistant", "I can only assist with questions related to eCommerce customer support.")        
    ]
    
    response = test_pydantic(chat_history=chat_history, query="Tell me more about items present in my abandon checkout?")
    print(f"response : {response}")
    
    
    text ="""```json
        {
            "is_order_inquiry": True,
            "is_checkout_inquiry": False,
            "is_product_inquiry": False,
            "extracted_order_numbers": []
        }
        ```"""
    start = text.find('{')
    end = text.find('}')+1
    #print(text[start:end])
    
    