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
from langchain_core.output_parsers.base import BaseOutputParser
import json
from langchain_core.exceptions import OutputParserException

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
    
class CustomJSONOutputParser(BaseOutputParser):
    def parse(self, text: str) -> dict:
        try:
            # Clean the response text by removing unnecessary ```json or other extraneous characters
            clean_text = self.clean_and_parse_json(text)
            
            # Parse the cleaned JSON string
            return json.loads(clean_text)
        except json.JSONDecodeError as e:
            raise OutputParserException(f"Failed to parse output as valid JSON: {str(e)}")
    
    def clean_and_parse_json(self, text: str) -> str:
        # Check if the response starts with ```json or similar patterns
        if text.startswith("```json."):
            # Strip the backticks and "json" identifier
            text = text.strip("```json.").strip("```")
        elif text.startswith("```json"):
            # Strip the backticks and "json" identifier
            text = text.strip("```json").strip("```")
        elif text.startswith("```"):
            # If it starts with just backticks, strip them too
            text = text.strip("```")
        
        # Remove any trailing or leading whitespace
        return text.strip()


def test_pydantic(query: str, chat_history: list):  
    try: 
        # Set up a parser + inject instructions into the prompt template.
        #parser = PydanticOutputParser(pydantic_object=UserQuery)
        parser = CustomJSONOutputParser()
        
        # Define the prompt with clear instructions
        prompt = PromptTemplate(
            template="""
            You are an AI assistant specialized in eCommerce support. Analyze the following chat history and the current user query to determine the following:
    
            1. `is_order_inquiry`: Set this to True **only if** the query is asking for information specific to the status, modification, or details of a particular order (e.g., order status, delivery status, or product-related issues in a specific order). 
            
                If the query is about general processes or policies (e.g., "How can I cancel my order?" or "What is your return policy?") even if an order number is mentioned, set this to False. Focus on the intent of the query—if the user is asking about a process that can be answered through general policy or FAQ documentation, set this to False.
                
                If the query is related to an order, set `is_checkout_inquiry` to False.  
            
            2. `is_checkout_inquiry`: Set this to True if the query is asking about items present in the user's abandoned checkout (e.g., "What items are in my checkout?" or "Can you apply a discount to my checkout items?"). 
                
                If the query is related to an abandoned checkout, set `is_order_inquiry` to False.
                
            3. Ensure that **only one of** `is_order_inquiry` or `is_checkout_inquiry` can be True at a time. If one is True, the other must be False.
            
            4. `is_product_inquiry`: Set this to True if the query asks about product details, features, availability, or recommendations (e.g., "What are the features of this product?" or "Tell me about the products in my checkout."). Both `is_product_inquiry` and `is_checkout_inquiry` can be True if the user is asking for product information related to their abandoned checkout.
    
            5. `extracted_order_numbers`: Extract specific order number(s) only if `is_order_inquiry` is True. If `is_order_inquiry` is False, return an empty list even if order numbers are mentioned in the query.
    
            Chat history: {chat_history}
    
            User query: {query}
            
            Your response **must** be a valid JSON object in the following format:

            ```json
            {{
                "is_order_inquiry": <True or False>,
                "is_checkout_inquiry": <True or False>,
                "is_product_inquiry": <True or False>,
                "extracted_order_numbers": [<List of strings representing order numbers>]
            }}
            ```

            Ensure your response is strictly formatted as a JSON object with no additional comments, text, or explanation.
            """,
            input_variables=["chat_history", "query"],
            #partial_variables={"format_instructions": parser.get_format_instructions()},
        )
        
        # Combine history and current query for complete context
        chat_history_str = "\n".join([f"{speaker}: {content}" for speaker, content in chat_history])
        
        model = llm_utils.get_chat_model(model_name="gpt-4o-mini", temperature=0, openai_api_key=os.environ['OPENAI_API_KEY'])
        chain = prompt | model | parser
        return chain.invoke({"chat_history" : chat_history_str, "query": query})
    except Exception as e:
        print(f"Error : {e}")



if __name__ == '__main__':
    # Sample chat history
    chat_history = [
        ("user", "what is the status of my order?"),
        ("assistant", "Could you kindly provide the order number(s) related to your query so I can assist you better?")
    ]
    
    #response = test_pydantic(chat_history=chat_history, query="Tell me more about items present in my abandon checkout?")
    #print(f"response : {response}")
    text ="""```json
        {
            "is_order_inquiry": True,
            "is_checkout_inquiry": False,
            "is_product_inquiry": False,
            "extracted_order_numbers": []
        }
        ```"""
    text = text.strip("```json").strip("```")
    print(text)
    
    