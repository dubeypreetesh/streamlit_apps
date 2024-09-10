from langchain.agents import initialize_agent
from langchain_community.agent_toolkits.load_tools import load_tools
from langchain.schema import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
import openai

from langsmith.wrappers import wrap_openai

def get_llm_model():
    llm_model = "gpt-3.5-turbo"
    return llm_model


def generate_image(prompt, temperature , llm_tools, model=get_llm_model(), openai_api_key=None):    
    llm = ChatOpenAI(model=model, temperature=temperature, api_key=openai_api_key)
    tools = load_tools(llm_tools, llm=llm, api_key=openai_api_key)
    agent = initialize_agent(tools, llm, handle_parsing_errors=True, verbose=True)
    output = agent(prompt)
    print(f"output : {output}")
    return output['output']


def get_completion(prompt, temperature, model=get_llm_model(), messages=[], openai_api_key=None):
    if not messages:
        messages = [{"role": "user", "content": prompt}]
    openai_client = openai.OpenAI(api_key=openai_api_key)    
    response = openai_client.chat.completions.create(model=model, messages=messages, temperature=temperature)    
    return response.choices[0].message.content


def get_completion_stream(prompt, temperature, model=get_llm_model(), messages=[], openai_api_key=None):
    if not messages:
        messages = [{"role": "user", "content": prompt}]
    openai_client = openai.OpenAI(api_key=openai_api_key)
    stream = openai_client.chat.completions.create(model=model, messages=messages, temperature=temperature, stream=True)    
    return stream


def content_generator(instruction_system, user_data, temperature, model=get_llm_model(), openai_api_key=None):
    messages = [
    SystemMessage(
        content=instruction_system
    ),
    HumanMessage(
        content=user_data
    )]
    chat = ChatOpenAI(streaming=True, model=model, temperature=temperature, api_key=openai_api_key)
    response = chat.stream(messages)
    return response


def get_chat_model(model_name, temperature, openai_api_key):
    if not model_name:
        model_name = get_llm_model()
    if not temperature:
        temperature = 0    
    chat_open_ai_client = ChatOpenAI(model=model_name, temperature=temperature, api_key=openai_api_key)
    return chat_open_ai_client
    #langsmith_chat_open_ai_client = wrap_openai(chat_open_ai_client)
    #return langsmith_chat_open_ai_client