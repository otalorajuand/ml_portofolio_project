import os
import pickle
import streamlit as st
from langchain.chat_models import ChatOpenAI
from langchain.schema import (
    SystemMessage,
    HumanMessage,
    AIMessage
)
from datasets import load_dataset
import pinecone
import time
from langchain.embeddings.openai import OpenAIEmbeddings
from tqdm.auto import tqdm
from langchain.vectorstores import Pinecone

OPENAI_API_KEY = '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'

os.environ["OPENAI_API_KEY"] = os.getenv("OPENAI_API_KEY") or OPENAI_API_KEY

chat = ChatOpenAI(
    openai_api_key=os.environ["OPENAI_API_KEY"],
    model='gpt-3.5-turbo'
)


dataset = load_dataset(
    "otalorajuand/data_house_museum",
    split="train"
)


pinecone_api_key = "268d96a5-da56-4eae-af43-151efbfe5004"
# get API key from app.pinecone.io and environment from console
pinecone.init(
    api_key = os.environ.get('PINECONE_API_KEY') or pinecone_api_key,
    environment='gcp-starter'
)


index_name = 'llama-2-rag'

if index_name not in pinecone.list_indexes():
    pinecone.create_index(
        index_name,
        dimension=1536,
        metric='cosine'
    )
    # wait for index to finish initialization
    while not pinecone.describe_index(index_name).status['ready']:
        time.sleep(1)

index = pinecone.Index(index_name)


embed_model = OpenAIEmbeddings(model="text-embedding-ada-002")

data = dataset.to_pandas()  # this makes it easier to iterate over the dataset

batch_size = 100

for i in tqdm(range(0, len(data), batch_size)):
    i_end = min(len(data), i+batch_size)
    # get batch of data
    batch = data.iloc[i:i_end]
    # generate unique ids for each chunk
    ids = [f"{x['id']}" for i, x in batch.iterrows()]
    # get text to embed
    texts = [x['text_chunk'] for _, x in batch.iterrows()]
    # embed text
    embeds = embed_model.embed_documents(texts)
    # get metadata to store in Pinecone
    metadata = [
        {'text': x['text_chunk'],
         'title': x['title']} for i, x in batch.iterrows()
    ]
    # add to Pinecone
    index.upsert(vectors=zip(ids, embeds, metadata))


    text_field = "text"  # the metadata field that contains our text

# initialize the vector store object
vectorstore = Pinecone(
    index, embed_model.embed_query, text_field
)

