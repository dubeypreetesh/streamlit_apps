'''
Created on 24-Sep-2024

@author: ongraph
'''
from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.prompts import PromptTemplate
from pydantic import BaseModel, Field
from utils import llm_utils
from dotenv import load_dotenv, find_dotenv
import os

_ = load_dotenv(find_dotenv())  # read local .env file

class UserQuery(BaseModel):
    """UserQuery to determine whether a user query is about an order and extract relevant order numbers."""

    is_order_inquiry: bool = Field(
        description="True if the query is about an order inquiry (related to specific orders or order status), otherwise False."
    )
    extracted_order_numbers: list[str] = Field(
        description="List of strings containing the order number(s) extracted from the user query. If no order numbers are present, return an empty list."
    )


def test_pydantic(query: str):   
    try: 
        # Set up a parser + inject instructions into the prompt template.
        parser = PydanticOutputParser(pydantic_object=UserQuery)
        
        # Define the prompt with clear instructions
        prompt = PromptTemplate(
            template="""
            You are an AI assistant specialized in eCommerce support. Analyze the following user query and extract two pieces of information:

            1. Determine if the query is related to an order. If the user is asking about order status, cancellation, refund, or any order-related issue, set `is_order_inquiry` to True. Otherwise, set it to False.

            2. If the query mentions specific order number(s), extract the order numbers as a list of strings. If no order numbers are found, return an empty list.

            {format_instructions}

            User query: {query}
            """,
            input_variables=["query"],
            partial_variables={"format_instructions": parser.get_format_instructions()},
        )
        
        openai_api_key=os.environ['OPENAI_API_KEY']
        model = llm_utils.get_chat_model(model_name="gpt-4o-mini", temperature=0, openai_api_key=os.environ['OPENAI_API_KEY'])
        chain = prompt | model | parser
        response = chain.invoke({"query": query})
        return response
    except Exception as e:
        print(f"Error : {e}")



if __name__ == '__main__':
    response = test_pydantic(question="How do you process refund of an order?")
    print(f"response : {response}")
    
    