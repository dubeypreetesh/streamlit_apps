'''
Created on 12 Jun 2024

@author: dileep sharma
'''
# these three lines swap the stdlib sqlite3 lib with the pysqlite3 package
from langsmith.run_helpers import traceable
from langchain_openai.chat_models.base import ChatOpenAI
__import__('pysqlite3')
import sys
sys.modules['sqlite3'] = sys.modules.pop('pysqlite3')

from langchain.chains.combine_documents.stuff import create_stuff_documents_chain
from langchain.chains.retrieval import create_retrieval_chain
from langchain_core.prompts.chat import ChatPromptTemplate
from langchain_openai import OpenAIEmbeddings

from utils import llm_utils
from langchain_chroma import Chroma
from chromadb import DEFAULT_TENANT
from utils.chroma_client import ChromaClient
import jwt
import requests
from data_objects.user_query import UserQuery
from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.prompts import PromptTemplate

# JWT_SECRET=st.secrets["shopify_credentials"]["jwt_secret"]
def fetch_result(token: str, token_secret: str, question:str, openai_api_key: str, messages: list, checkout_data: list ,chroma_host:str, chroma_port: int): 
    decoded_token = jwt.decode(token, token_secret, algorithms=["HS256"])
    request_data = {"question": question, "shop_id": decoded_token["shopId"], "user_id": decoded_token["customerId"],
                  "collection_name": decoded_token["collection_name"], "messages": messages, "checkout_data": checkout_data, "openai_api_key": openai_api_key,
                  "chroma_host": chroma_host, "chroma_port": chroma_port}
    answer = shopify_result(request_data=request_data)
    return answer


def get_shopify_chroma_instance(database: str, host: str, port: int):
    CHROMA_API_IMPL = "chromadb.api.fastapi.FastAPI"
    HOST = host
    PORT = port
    TENANT = DEFAULT_TENANT
    DATABASE = database
    
    return ChromaClient.get_instance(chroma_api_impl=CHROMA_API_IMPL, host=HOST, port=PORT, tenant=TENANT, database=DATABASE)

def get_shopify_orders(shop_id: str, user_id: str, order_numbers: list):
    order_numbers_str = ",".join(order_numbers)
    url = f"https://app.heymira.ai/api/order/status?shopId={shop_id}&userId={user_id}&orderNumbers={order_numbers_str}"
    return requests.get(url=url)

def get_user_query_pydantic(query: str, model: ChatOpenAI) -> UserQuery:   
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
    
    chain = prompt | model | parser
    return chain.invoke({"query": query})

@traceable  # Auto-trace this function
def shopify_result(request_data):
    question = request_data["question"]
    shop_id = request_data["shop_id"]
    collection_name = request_data["collection_name"]
    openai_api_key = request_data["openai_api_key"]
    checkout_data = request_data["checkout_data"]
    
    chroma_host = request_data["chroma_host"]
    chroma_port = request_data["chroma_port"]
    
    # Step 1: Get LLM model and Chroma vector store client
    llm = llm_utils.get_chat_model(False, False, openai_api_key=openai_api_key)
    
    client = get_shopify_chroma_instance(database=shop_id, host=chroma_host, port=chroma_port)
    embedding_function = OpenAIEmbeddings(openai_api_key=openai_api_key,model="text-embedding-3-large")
    vectorstore = Chroma(client=client, collection_name=collection_name, embedding_function=embedding_function)
    
    retriever = vectorstore.as_retriever()
    
    if checkout_data:
        context = checkout_data
    # Step 3: Handle order-related queries
    else:
        user_query_pydantic = get_user_query_pydantic(query=question, model=llm)
        is_order_inquiry = user_query_pydantic.is_order_inquiry
        extracted_order_numbers = user_query_pydantic.extracted_order_numbers
        
        if is_order_inquiry:
            if extracted_order_numbers:  # If order numbers are present
                # Call the order API using extracted order numbers
                order_api_response = get_shopify_orders(shop_id=shop_id, user_id=request_data["user_id"], order_numbers=extracted_order_numbers).json()
                # Use the order API response as context for RAG query
                context = f"Order details: {order_api_response}"
            else: # If order numbers are not present
                # Step 3b: Ask user for order numbers
                return "Could you kindly provide the order number(s) related to your query so I can assist you better?"
        else:
            # If the query is not about orders, perform a regular RAG query
            context = retriever.invoke(input=question)
    
    # Step 4: Create the system prompt for the assistant
    system_prompt = """
    You are an AI assistant specialized in eCommerce support. You will be provided with context regarding eCommerce products and user orders. Based on this context, you need to respond to user queries with precise and accurate information.
    This chat is focused on eCommerce customer support. Please answer questions only related to this domain.
    If a question falls outside the eCommerce support domain, please respond with: 'I can only assist with questions related to eCommerce customer support. 

    ### Instructions:
    
    1. **Product Queries**:
        - Provide detailed information about products, including specifications, features, pricing, availability, and user reviews.
        - Answer any questions related to product comparisons, recommendations, and suitability based on user needs.
    
    2. **Order Queries**:
        - Retrieve and summarize order details such as order status, tracking information, estimated delivery times, and order history.
        - Handle queries about order modifications, cancellations, returns, and refunds.
    
    3. **General eCommerce Support**:
        - Assist with account-related inquiries, including account settings, password resets, and payment methods.
        - Address any issues or concerns raised by the user in a clear and empathetic manner.
    
    ### Response Guidelines:
    
    - **Accuracy**: Ensure all responses are factually correct based on the provided context.
    - **Clarity**: Provide clear and concise answers.
    - **Relevance**: Stay focused on the user's query, providing the most relevant information.
    - **Tone**: Maintain a professional, friendly, and helpful tone.
    
    **Sample User Queries**:
    - "What is the battery life of the Wireless Bluetooth Headphones?"
    - "Can I change the shipping address for my order 67890?"
    - "How do I return a product I purchased?"
    - "What are the reviews like for the Portable Charger?"
    
    Context:{context}
    
    Use the above Context and Instructions and Response Guidelines to provide accurate and helpful responses to user queries.
    Please answer the user queries based solely on the provided context. Do not include any information outside of this context.
    """
    
    """
    chat_history = [('human', 'User Query'), ('ai', 'AI response'), ('human', 'Tell me the different iphone available to you and features provided.'), ('human', 'None')]
    
    conversation=[]
    conversation.append(("system", system_prompt))
    conversation.extend(chat_history)
    conversation.append(("human", "{input}"))
    """
    
    # Step 5: Build the conversation prompt using ChatPromptTemplate
    prompt = ChatPromptTemplate([
            ("system", system_prompt),
            *request_data["messages"],
            ("human", "{input}")
        ])
    
    # Step 6: Create the question-answer chain and retrieve the response
    
    # We assume 'context' is calculated above based on the order query or product retrieval
    question_answer_chain = create_stuff_documents_chain(llm, prompt)
    
    # Modify system prompt to include the calculated context explicitly
    chain = create_retrieval_chain(retriever, question_answer_chain)
    
    # Pass 'context' explicitly in the chain.invoke method
    response = chain.invoke({"input": question, "context" : context})
    
    answer = response['answer']
    return answer

    # response = chain.stream({"input": question})
    # return response
    
@traceable  # Auto-trace this function
def shopify_result_old(request_data):
    question = request_data["question"]
    shop_id = request_data["shop_id"]
    collection_name = request_data["collection_name"]
    openai_api_key = request_data["openai_api_key"]
    
    chroma_host = request_data["chroma_host"]
    chroma_port = request_data["chroma_port"]
    
    # Step 1: Get LLM model and Chroma vector store client
    llm = llm_utils.get_chat_model(False, False, openai_api_key=openai_api_key)
    
    client = get_shopify_chroma_instance(database=shop_id, host=chroma_host, port=chroma_port)
    embedding_function = OpenAIEmbeddings(openai_api_key=openai_api_key,model="text-embedding-3-large")
    vectorstore = Chroma(client=client, collection_name=collection_name, embedding_function=embedding_function)
    
    retriever = vectorstore.as_retriever()
    
    # Step 2: Determine if the query is order-related
    order_inquiry_prompt = f"""
        Given the "user_query" below, determine if the query is about an order inquiry. If it is, reply with "Y". If it is not, reply with "N" and nothing else.
        "user_query": "{question}"
        """
    is_order_inquiry = llm_utils.get_completion(prompt=order_inquiry_prompt, temperature=0.0, openai_api_key=openai_api_key)
    
    # Step 3: Handle order-related queries
    if is_order_inquiry == "Y":
        #retriever.search_kwargs = {"filter": {"user_id": request_data["user_id"]}, "k": 10}
        # Check if the query contains order number(s)
        order_number_extraction_prompt = f"""
            Identify the order number(s) in the user query as a list of **strings**.
            If there are no order numbers present, reply with an empty list.
            Ensure that each order number is returned as a string, even if it consists of digits.
        
            "user_query": "{question}"
        """

        extracted_order_numbers = llm_utils.get_completion(prompt=order_number_extraction_prompt, temperature=0.0, openai_api_key=openai_api_key)
        
        if extracted_order_numbers:  # If order numbers are present
            # Call the order API using extracted order numbers
            order_api_response = get_shopify_orders(shop_id=shop_id, user_id=request_data["user_id"], order_numbers=extracted_order_numbers).json()
            # Use the order API response as context for RAG query
            context = f"Order details: {order_api_response}"
        else: # If order numbers are not present
            # Step 3b: Ask user for order numbers
            return "Could you kindly provide the order number(s) related to your query so I can assist you better?"
    else:
        # If the query is not about orders, perform a regular RAG query
        context = retriever.invoke(input=question)
    
    # Step 4: Create the system prompt for the assistant
    system_prompt = """
    You are an AI assistant specialized in eCommerce support. You will be provided with context regarding eCommerce products and user orders. Based on this context, you need to respond to user queries with precise and accurate information.
    This chat is focused on eCommerce customer support. Please answer questions only related to this domain.
    If a question falls outside the eCommerce support domain, please respond with: 'I can only assist with questions related to eCommerce customer support. 

    ### Instructions:
    
    1. **Product Queries**:
        - Provide detailed information about products, including specifications, features, pricing, availability, and user reviews.
        - Answer any questions related to product comparisons, recommendations, and suitability based on user needs.
    
    2. **Order Queries**:
        - Retrieve and summarize order details such as order status, tracking information, estimated delivery times, and order history.
        - Handle queries about order modifications, cancellations, returns, and refunds.
    
    3. **General eCommerce Support**:
        - Assist with account-related inquiries, including account settings, password resets, and payment methods.
        - Address any issues or concerns raised by the user in a clear and empathetic manner.
    
    ### Response Guidelines:
    
    - **Accuracy**: Ensure all responses are factually correct based on the provided context.
    - **Clarity**: Provide clear and concise answers.
    - **Relevance**: Stay focused on the user's query, providing the most relevant information.
    - **Tone**: Maintain a professional, friendly, and helpful tone.
    
    **Sample User Queries**:
    - "What is the battery life of the Wireless Bluetooth Headphones?"
    - "Can I change the shipping address for my order 67890?"
    - "How do I return a product I purchased?"
    - "What are the reviews like for the Portable Charger?"
    
    Context:{context}
    
    Use the above Context and Instructions and Response Guidelines to provide accurate and helpful responses to user queries.
    Please answer the user queries based solely on the provided context. Do not include any information outside of this context.
    """
    
    """
    chat_history = [('human', 'User Query'), ('ai', 'AI response'), ('human', 'Tell me the different iphone available to you and features provided.'), ('human', 'None')]
    
    conversation=[]
    conversation.append(("system", system_prompt))
    conversation.extend(chat_history)
    conversation.append(("human", "{input}"))
    """
    
    # Step 5: Build the conversation prompt using ChatPromptTemplate
    prompt = ChatPromptTemplate([
            ("system", system_prompt),
            *request_data["messages"],
            ("human", "{input}")
        ])
    
    # Step 6: Create the question-answer chain and retrieve the response
    
    # We assume 'context' is calculated above based on the order query or product retrieval
    question_answer_chain = create_stuff_documents_chain(llm, prompt)
    
    # Modify system prompt to include the calculated context explicitly
    chain = create_retrieval_chain(retriever, question_answer_chain)
    
    # Pass 'context' explicitly in the chain.invoke method
    response = chain.invoke({"input": question, "context" : context})
    
    answer = response['answer']
    return answer

    # response = chain.stream({"input": question})
    # return response
    
def fetch_website_result(website_domain: str, collection_name: str, question:str, openai_api_key: str, messages: list, chroma_host:str, chroma_port: int): 
    request_data = {"website_domain": website_domain, "collection_name": collection_name, "question": question,
                  "openai_api_key": openai_api_key, "messages": messages,
                  "chroma_host": chroma_host, "chroma_port": chroma_port}
    answer = website_result(request_data=request_data)
    return answer


@traceable  # Auto-trace this function
def website_result(request_data):
    website_domain = request_data["website_domain"]
    collection_name = request_data["collection_name"]
    question = request_data["question"]
    openai_api_key = request_data["openai_api_key"]
    
    chroma_host = request_data["chroma_host"]
    chroma_port = request_data["chroma_port"]
    
    llm = llm_utils.get_chat_model(False, False, openai_api_key=openai_api_key)
    
    client = get_shopify_chroma_instance(database=website_domain, host=chroma_host, port=chroma_port)
    embedding_function = OpenAIEmbeddings(openai_api_key=openai_api_key)
    vectorstore = Chroma(client=client, collection_name=collection_name, embedding_function=embedding_function)
    
    retriever = vectorstore.as_retriever()
       
    system_prompt = """
    You are a chat assistant for a website. Your role is to assist users by answering their queries based on the content and information 
    indexed from the website. The website may belong to any domain, such as eCommerce, gaming, services, or others, and covers various 
    aspects of the business like products/services offered, case studies, blogs, team expertise, and client testimonials.

    Key instructions:
    1. When a user asks a question, retrieve the most relevant information from the indexed website content.
    2. Provide concise, clear, and accurate answers based on the available data.
    3. If the information isn't directly available, explain that, and offer general guidance based on the website's context.
    4. Always maintain a helpful and professional tone.
    5. Keep answers relevant to the specific business domain of the website (e.g., commerce, services, gaming).
    6. Use any technical terms or jargon appropriately, ensuring clarity for both technical and non-technical users.
    7. Be mindful of the website's purpose: to offer expertise, products, or services related to its specific domain.
    8. Include links to relevant website pages in your responses whenever appropriate, based on the user query. Present the links in your response only if clear `url` found in context.
    9. If needed, suggest related pages or sections of the website for further reading or detailed information.
    
    Context:{context}
    
    Use the above Context and Key instructions to provide accurate and helpful responses to user queries.
    """
    
    """
    chat_history = [('human', 'User Query'), ('ai', 'AI response'), ('human', 'Tell me the different iphone available to you and features provided.'), ('human', 'None')]
    
    conversation=[]
    conversation.append(("system", system_prompt))
    conversation.extend(chat_history)
    conversation.append(("human", "{input}"))
    """
    
    prompt = ChatPromptTemplate([
            ("system", system_prompt),
            *request_data["messages"][-6:],
            ("human", "{input}")
        ])
    
    question_answer_chain = create_stuff_documents_chain(llm, prompt)
    chain = create_retrieval_chain(retriever, question_answer_chain)
    response = chain.invoke({"input": question})
    answer = response['answer']
    return answer
    
