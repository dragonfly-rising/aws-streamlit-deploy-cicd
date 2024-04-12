import json
import boto3
import streamlit as st
import dotenv
from qdrant_client import QdrantClient

dotenv.load_dotenv()

st.title("Channel Rocket RAG Chat")

#QdrantClient#set_model("BAAI/bge-small-en-v1.5")
qdrant_client = QdrantClient(url="https://aa7be8d4-71bb-4a2a-852d-b1f8edaa2294.us-east-1-0.aws.cloud.qdrant.io:6334",
                             prefer_grpc=True,
                             api_key="Ovx-8bl07B5VAR1hnkJPTI0GDGiyqY0Gc6nm3jtMUuHlU0K8KQRVCQ")
#qdrant_client.set_model(embedding_model_name="BAAI/bge-small-en-v1.5")
collection_name = "channel_rocket_rag"

client = boto3.client("bedrock-runtime")

# model_id = "anthropic.claude-3-sonnet-20240229-v1:0"
model_id = "anthropic.claude-3-haiku-20240307-v1:0"

def search(text: str) -> str:
    search_result = qdrant_client.query(
        collection_name=collection_name,
        query_text=text,
        query_filter=None,  # If you don't want any filters for now
        limit=10,  # 5 the closest results are enough
    )
    # `search_result` contains found vector ids with similarity scores along with the stored payload
    # In this function you are interested in payload only
    metadata = [hit.document for hit in search_result]
    return ' '.join(metadata)

def parse_stream(stream):
    
    for event in stream:
        chunk = event.get('chunk')
        if chunk:
            message = json.loads(chunk.get("bytes").decode())
            if message['type'] == "content_block_delta": 
               yield message['delta']['text'] or ""
            elif message['type'] == "message_stop":
                return "\n"

if "messages" not in st.session_state:
    st.session_state.messages = []

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["text"])
        
if prompt := st.chat_input("Prompt"):
    context = search(prompt)
    #build this format!("<context> {} </context> <question>{}</question>",chunks.join("\n"),&question.to_string());
    body = json.dumps({
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": 1024,
        "system": "You are an AI assistant for a company called Channel Rocket, they specialize in CRM for channel management, use the context provided in the xml <context> tag and answer the question in the <question> tag.",
        "messages": [
            {
                "role": "user",
                "content": [{"type": "text", "text": f"<context>{context}</context><question>{prompt}</question>"}],
            }
        ],
    })
    
    streaming_response = client.invoke_model_with_response_stream(
        modelId=model_id,
        body=body,
    )

    st.session_state.messages.append({"role": "user", "text": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)
    
    ai_response = ""    
    with st.chat_message("assistant"):
        stream = streaming_response.get("body")  
        
        st.write_stream(parse_stream(stream))
        
    
    