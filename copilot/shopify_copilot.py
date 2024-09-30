'''
Created on 12 Jun 2024

@author: dileep sharma
'''
# these three lines swap the stdlib sqlite3 lib with the pysqlite3 package
from langsmith.run_helpers import traceable
from langchain_openai.chat_models.base import ChatOpenAI
from langchain_core.exceptions import OutputParserException
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
import json

# JWT_SECRET=st.secrets["shopify_credentials"]["jwt_secret"]
def fetch_result(token: str, token_secret: str, question:str, openai_api_key: str, messages: list, checkout_data: list ,chroma_host:str, chroma_port: int, get_orders_api_url: str): 
    decoded_token = jwt.decode(token, token_secret, algorithms=["HS256"])
    request_data = {"question": question, "shop_id": decoded_token["shopId"], "user_id": decoded_token["customerId"],
                  "collection_name": decoded_token["collection_name"], "messages": messages, "checkout_data": checkout_data, "openai_api_key": openai_api_key,
                  "chroma_host": chroma_host, "chroma_port": chroma_port, "get_orders_api_url": get_orders_api_url}
    answer = shopify_result(request_data=request_data)
    return answer


def get_shopify_chroma_instance(database: str, host: str, port: int):
    CHROMA_API_IMPL = "chromadb.api.fastapi.FastAPI"
    HOST = host
    PORT = port
    TENANT = DEFAULT_TENANT
    DATABASE = database
    
    return ChromaClient.get_instance(chroma_api_impl=CHROMA_API_IMPL, host=HOST, port=PORT, tenant=TENANT, database=DATABASE)

def get_shopify_orders(api_url: str, shop_id: str, user_id: str, order_numbers: list):
    order_numbers_str = ",".join(order_numbers)
    url = f"{api_url}?shopId={shop_id}&userId={user_id}&orderNumbers={order_numbers_str}"
    return requests.get(url=url)

def clean_and_parse_json(response: str):
    # Remove any non-JSON content
    try:
        json_str = response.strip().replace("```json", "").replace("```", "").strip()
        return json.loads(json_str)
    except json.JSONDecodeError as e:
        raise OutputParserException(f"Failed to parse JSON response: {e}")

def get_user_query_pydantic(chat_history: list, query: str, model: ChatOpenAI) -> UserQuery:   
        # Set up a parser + inject instructions into the prompt template.
        parser = PydanticOutputParser(pydantic_object=UserQuery)
        
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
            
            Your response **must** be a valid JSON object **without any extra characters**, comments, explanations, or backticks. Ensure the output is a plain JSON string with no formatting errors. The JSON format should be:

            {{
                "is_order_inquiry": <True or False>,
                "is_checkout_inquiry": <True or False>,
                "is_product_inquiry": <True or False>,
                "extracted_order_numbers": [<List of strings representing order numbers>]
            }}
    
            Only output the JSON string with no additional text or formatting.
            """,
            input_variables=["chat_history", "query"],
            #partial_variables={"format_instructions": parser.get_format_instructions()},
        )
        
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
    
    user_query_pydantic = get_user_query_pydantic(chat_history=request_data["messages"][-6:], query=question, model=llm)
    print(f"user_query_pydantic : {user_query_pydantic}")
    is_order_inquiry = user_query_pydantic.is_order_inquiry
    is_checkout_inquiry = user_query_pydantic.is_checkout_inquiry
    is_product_inquiry = user_query_pydantic.is_product_inquiry
    extracted_order_numbers = user_query_pydantic.extracted_order_numbers
    
    context_list = []
    
    # Step 2: Handle checkout data
    if is_checkout_inquiry:
        if checkout_data:
            context_list.append(f"Checkout Data: \n\n{checkout_data}")
        else:
            return "Could you kindly provide the checkout details related to your query so I can assist you better?"
    if is_product_inquiry:
        if is_checkout_inquiry and checkout_data:
            input = f"User Query : \n\n{question}\n\nCheckout Data: \n\n{checkout_data}"
        else:
            input=question
        product_docs = retriever.invoke(input=input)
        product_docs_str = "\n".join(doc.page_content for doc in product_docs)
        context_list.append(f"Products Data : \n\n{product_docs_str}")
    if is_order_inquiry:
        if extracted_order_numbers:  # If order numbers are present
            # Call the order API using extracted order numbers
            api_url = request_data["get_orders_api_url"]
            order_api_response = get_shopify_orders(api_url=api_url, shop_id=shop_id, user_id=request_data["user_id"], order_numbers=extracted_order_numbers).json()
            # Use the order API response as context for RAG query
            context_list.append(f"Orders Data: \n\n{order_api_response}")
        else: # If order numbers are not present
            # Step 3b: Ask user for order numbers
            return "Could you kindly provide the order number(s) related to your query so I can assist you better?"
    
    context = "\n\n".join(context_list)
    print(f"Context : {context}")
    # Step 4: Create the system prompt for the assistant
    system_prompt = """
        You are an AI assistant specialized in eCommerce support. You will be provided with context regarding eCommerce products, user orders, and abandoned checkouts. Based on this context, you need to respond to user queries with precise and accurate information.
        This chat is focused on eCommerce customer support.
        
        If a user begins with a greeting (e.g., 'hello', 'hi', 'how are you'), respond politely with a greeting in return, such as:
        - "Hello, how can I help you?"
        - "Hi there, how can I assist you today?"
        
        If a question falls outside the eCommerce support domain (and is not a greeting), please respond with: 'I can only assist with questions related to eCommerce customer support.'
        
        ### Instructions:
        
        1. **Checkout Data**:
            - Always prioritize the "Checkout Data" when answering queries related to items in the user's checkout.
            - When a user asks about the product in their checkout, **you MUST match the product in the "Checkout Data" with the corresponding product in the "Products Data" using the `item_variant_id` field**. 
            - Use the `item_variant_id` to precisely identify the product variant in both sections.
            - Once you find the matching product in "Products Data" using `item_variant_id`, use that information to provide detailed product descriptions, features, specifications, and pricing.
            - **If a user asks about discounts** (e.g., "Is there any discount available for this checkout?"), check for discounts in the "Checkout Data" and respond accordingly.
        
        2. **Product Queries**:
            - If a query is about products in general, answer based on the "Products Data" without relying on the checkout context. 
            - For queries about specific products in the checkout (e.g., "Which product is in my checkout?"), first find the product in the "Checkout Data" using its `item_variant_id` and then match it with the same `item_variant_id` in the "Products Data". 
            - Only after successfully matching, provide information about that product.
        
        3. **Order Queries**:
            - Retrieve and summarize order details from the "Orders Data" such as order status, tracking information, estimated delivery times, and order history.
            - Handle queries about order modifications, cancellations, returns, and refunds based solely on the "Orders Data."
        
        4. **General eCommerce Support**:
            - Assist with account-related inquiries, including account settings, password resets, and payment methods.            
            - **Answer queries about discounts** for both products and checkouts, when relevant. If discounts are available in the "Checkout Data" or "Products Data," provide this information in your response.
            - Address any issues or concerns raised by the user in a clear and empathetic manner.
        
        ### Important Guidelines for Context Handling:
        
        - **Structured Context Use**: You will receive context in the following format:
          - **Checkout Data**: Information about items currently in the user's checkout.
          - **Products Data**: General information about available products.
          - **Orders Data**: Information about the user’s order history and status.
        
        - **Exact Matching Process**: 
            - When asked about items in the checkout (e.g., "Which product is in my checkout?"), first extract the `item_variant_id` from the "Checkout Data".
            - Then, locate the same `item_variant_id` in the "Products Data" to retrieve full product details.
            - Do not assume the first product in the list is correct — the answer must be based on matching `item_variant_id` exactly.
            - **Only after confirming this match** should you provide the user with details from "Products Data".
            
        - **Discount Queries**: If a user asks about discounts, check for discount information in the "Checkout Data" (e.g., `checkout_total_discounts`) or "Products Data" (e.g., product promotions or discounts). Ensure that your response reflects this information accurately.
        
        - **Avoid Assumptions**: Do not make assumptions based on the order or presence of products in "Products Data". Always match products based on the provided `item_variant_id`.
        
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
        - "What items are in my abandoned checkout?"
        - "Can you help me complete my abandoned purchase?"
        - "Which product is in my checkout?"
        - "Is there any discount available for this checkout?"
        - "Is there any discount available?"
        
        Context: {context}
        
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
            #*request_data["messages"][-6:],
            ("human", "{input}")
        ])
    
    # Use your custom context and pass it to the LLM
    question_answer_chain = prompt | llm
    
    response = question_answer_chain.invoke({"input": question, "context": context})
    print(f"context : {context}")
    #print(f"response : {response}")
    return response["text"]

    
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
    
