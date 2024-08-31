'''
Created on 12 Jun 2024

@author: dileep sharma
'''
from langchain.chains.combine_documents.stuff import create_stuff_documents_chain
from langchain.chains.retrieval import create_retrieval_chain
from langchain_core.prompts.chat import ChatPromptTemplate
from langchain_openai import OpenAIEmbeddings

from utils import llm_utils
from langchain_chroma import Chroma
from chromadb import DEFAULT_TENANT
from utils.chroma_client import ChromaClient
import jwt

JWT_SECRET="SDfew97etG8Y324t"
def fetch_result(token: str, question:str, openai_api_key: str, messages: list):
    decoded_token = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
    request_data={"question": question, "shop_id": decoded_token["shopId"], "user_id": decoded_token["customerId"], 
                  "collection_name": decoded_token["collection_name"], "messages": messages, "openai_api_key": openai_api_key}
    print(f"request_data : {request_data}")
    answer = shopify_result(request_data=request_data)
    return answer

def get_shopify_chroma_instance(database: str):
    CHROMA_API_IMPL="chromadb.api.fastapi.FastAPI"
    HOST="copilot.heymira.ai"
    PORT=8000
    TENANT=DEFAULT_TENANT
    DATABASE=database
    
    return ChromaClient.get_instance(chroma_api_impl=CHROMA_API_IMPL, host=HOST, port=PORT, tenant=TENANT, database=DATABASE)

def shopify_result(request_data):
    question = request_data["question"]
    shop_id = request_data["shop_id"]
    collection_name = request_data["collection_name"]
    openai_api_key= request_data["openai_api_key"]
    
    llm = llm_utils.get_chat_model(False, False, openai_api_key=openai_api_key)
    
    client = get_shopify_chroma_instance(database=shop_id)
    embedding_function = OpenAIEmbeddings(openai_api_key=openai_api_key)
    vectorstore = Chroma(client=client, collection_name=collection_name, embedding_function=embedding_function)
    
    retriever = vectorstore.as_retriever()
    
    # Determine whether user query is an order inquiry or something else.
    order_inquiry_prompt = f"""
        Given the "user_query" below, determine if the query is about an order inquiry. If it is, reply with "Y". If it is not, reply with "N" and nothing else.
        "user_query": "{question}"
        """
    is_order_inquiry = llm_utils.get_completion(prompt=order_inquiry_prompt, temperature=0.0, openai_api_key=openai_api_key)
    
    # if collection_name == CollectionType.item_order.value:
    if is_order_inquiry == "Y":
        retriever.search_kwargs = {"filter": {"user_id": request_data["user_id"]}, "k": 10}
    
    system_prompt = """
    You are an AI assistant specialized in eCommerce support. You will be provided with context regarding eCommerce products and user orders. Based on this context, you need to respond to user queries with precise and accurate information. 

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
            *request_data["messages"],
            ("human", "{input}")
        ])
    
    question_answer_chain = create_stuff_documents_chain(llm, prompt)
    chain = create_retrieval_chain(retriever, question_answer_chain)
    response = chain.invoke({"input": question})
    answer = response['answer']
    return answer

    #response = chain.stream({"input": question})
    #return response
    