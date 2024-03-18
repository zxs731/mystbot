import requests
import streamlit as st

search_service_name='search4ai0830'
index_name='index0314'
admin_api_key='ViBtVTWO7h3GCw2Gexg7VI5GlMWkyk6kZUXLT67TYDAzSeC9DzQZ'

url = f'https://{search_service_name}.search.windows.net/indexes/{index_name}/docs/search?api-version=2023-11-01'
headers = {
"Content-Type": "application/json",
"api-key": f'{admin_api_key}'
}

def fetch_related_content(txt):
    """
    专门用于查询私有知识库。
    :param txt: 字符串形式的文本
    :return：语义查询的结果集
    """    
    
    data = {
        "count": True,
        "select": "content,filepath",
        "top": 4,
        "vectorQueries": [
            {
                "kind": "text",
                "text": txt,
                "fields":"contentVector",
                "k": 4
            }
        ]
    }
    
    url=f'https://{search_service_name}.search.windows.net/indexes/{index_name}/docs/search?api-version=2023-10-01-Preview'
    response = requests.post(url, headers=headers, json=data)
    res=response.json()
    #print(res)
    if "value" not in res:
        return ["",[]]
    content = '\n\n\n'.join([item['content'] for item in res["value"]])  
    #print(res)
    return [content,res["value"]]

fetch_related_content_desc = {
    'name': 'fetch_related_content',
    'description': 'query information and return all related content',
    'parameters': {
        'type': 'object',
        'properties': {
            'txt': {
                'type': 'string',
                'description': 'The keyword for query'
            }
        },
        'required': ['txt']
    }
}

import json, ast
import openai
from dotenv import load_dotenv  
import os

# 加载.env文件  
load_dotenv("./en0314.env")  

os.environ["OPENAI_API_TYPE"] = os.environ["Azure_OPENAI_API_TYPE1"]
os.environ["OPENAI_API_BASE"] = os.environ["Azure_OPENAI_API_BASE1"]
os.environ["OPENAI_API_KEY"] =  os.environ["Azure_OPENAI_API_KEY1"]
os.environ["OPENAI_API_VERSION"] = os.environ["Azure_OPENAI_API_VERSION1"]
BASE_URL=os.environ["OPENAI_API_BASE"]
API_KEY=os.environ["OPENAI_API_KEY"]

CHAT_DEPLOYMENT_NAME=os.environ.get('AZURE_OPENAI_API_CHAT_DEPLOYMENT_NAME')
EMBEDDING_DEPLOYMENT_NAME=os.environ.get('AZURE_OPENAI_API_EMBEDDING_DEPLOYMENT_NAME')

openai.api_type = os.environ["OPENAI_API_TYPE"]
openai.api_base = os.environ["OPENAI_API_BASE"]
openai.api_version = "2023-08-01-preview"
openai.api_key = os.getenv("OPENAI_API_KEY")
print([openai.api_type, openai.api_base,openai.api_version,openai.api_key,CHAT_DEPLOYMENT_NAME])
def run_conversation(question,feedback):
    
    system_message = {"role":"system","content":'''You always query information from the function of fetch_related_content. 
    And alway find answer from its result. Please use the language of the question to give answer!
    (Note if you cannot find any answer please said you don't know)"
        '''}
    messages = []
    
    for msg in st.session_state.messages[-20:]:
        print(msg)
        if msg["role"]=="user":
            messages.append({ "role": "user","content": msg["content"]})
        elif msg is not None and msg["content"] is not None:
            messages.append({ "role": "assistant", "content":msg["content"]})
       
    response = openai.ChatCompletion.create(
        engine=CHAT_DEPLOYMENT_NAME,
        messages = [system_message]+messages,
        functions=[fetch_related_content_desc], 
        function_call='auto',
        stream=False
    ) 
    
    #print(response)
    #response["choices"][0]["message"]
    
    response_message=response["choices"][0]["message"]
    if "function_call" not in response_message:
        result1=response_message["content"]
        feedback(result1)
        for chunk in [result1]:
            yield chunk
            
        st.session_state.messages+= [{'role':'assistant','content':result1}]
        return result1
    
    feedback(f'⏳Query internal knowledge...')
    # 获取函数名
    function_name = response_message["function_call"]["name"]
    # 获取函数对象
    
    fuction_to_call = globals()[function_name]
    # 获取函数参数
    function_args = json.loads(response_message["function_call"]["arguments"])
    # 将当前操作空间中的全局变量添加到外部函数中
    #function_args['g']=globals() 
    # 将函数参数输入到函数中，获取函数计算结果
    
    
    function_response = fuction_to_call(**function_args)
    feedback(f'⏳Query internal knowledge done!')
    #print("执行结果：")
    #print(function_response)
    response_message['content']=' '
    messages.append(response_message)  
    # messages中拼接函数输出结果
    messages.append(
        {
            "role": "function",
            "name": function_name,
            "content": function_response[0],
        }
    )  
    # 第二次调用模型
    second_response = openai.ChatCompletion.create(
        engine=CHAT_DEPLOYMENT_NAME,
        messages = [system_message]+messages,
        functions=[fetch_related_content_desc], 
        function_call='auto',
        max_tokens=800,
        stream=True
    )  
    
    # 获取最终结果
    #final_response = second_response["choices"][0]["message"]
    #print(final_response["content"])
    ret=''
    for chunk in second_response:
        #print(chunk)
        if chunk.choices:
            if 'content' in chunk.choices[0].delta:
                c=chunk.choices[0].delta.content
                ret+=c
                #feedback(ret+'▌')
                yield c
    if len(function_response[1])>0:
        citText=''
        for cit in function_response[1]:
            citText+=f'''<details>  
    <summary>{cit['filepath']}</summary>  
      
    {cit['content']} 
</details> 
'''

        citations=f'''
<details>  
  <summary>View citations</summary>  
    
  {citText} 
</details>  
'''
    
        
    feedback(ret+citations)
    
    st.session_state.messages+= [{'role':'assistant','content':ret,'context':citText}]
    exp = st.expander('References')
    exp.markdown(citText,unsafe_allow_html=True)
    return ret

def getCitations(message):
    return message['context']
    
if "messages" not in st.session_state:
    st.session_state.messages = []

    
for message1 in st.session_state.messages:
    with st.chat_message(message1["role"]):
        st.markdown(message1["content"])
        if 'context' in message1:
            cit=message1['context']
            exp = st.expander('References')
            exp.markdown(cit,unsafe_allow_html=True)
            #st.markdown(cit,unsafe_allow_html=True)
            
        

def writeReply(cont,msg):
    #cont.write(msg,unsafe_allow_html=True)
    print(msg)
    pass

if prompt := st.chat_input():
    st.chat_message("user").write(prompt)
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("assistant"):
        
        #p=st.empty()
        #p.text("⏳...")
        p=None
        #re = run_conversation(prompt,lambda x:writeReply(p,x))
        st.write_stream( run_conversation(prompt,lambda x:writeReply(p,x)))
        #print(re)
        