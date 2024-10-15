import streamlit as st
from PyPDF2 import PdfReader
from qdrant_client import QdrantClient
from qdrant_client.models import VectorParams
import cohere
import uuid

# Initialize Qdrant and Cohere clients
qdrant_client = QdrantClient(
    url="https://d592a8e8-bf4f-42c2-8733-49bfdb35c394.europe-west3-0.gcp.cloud.qdrant.io:6333",
    api_key="d9oXnGCA1wBjcjUF977pT7rjAyBKh3-zgxOO2g95CQafCM9LAvf6VA",
)
cohere_client = cohere.Client('VCNuTSP7TApcHO6k7xwpiyED7AjDJRRRgK9ASpR7')

# Define vector size and collection name
vector_size = 4096  # Set to your Cohere model's output size
collection_name = "pdf_collection"  # Use a fixed collection name

def reset_collection():
    """Delete the existing collection if it exists and create a new one."""
    collections_info = qdrant_client.get_collections()
    existing_collections = [col.name for col in collections_info.collections]
    
    # Delete existing collection if it exists
    if collection_name in existing_collections:
        qdrant_client.delete_collection(collection_name)
    
    # Create a new collection
    qdrant_client.create_collection(
        collection_name=collection_name,
        vectors_config=VectorParams(size=vector_size, distance="Cosine")
    )

def embed_and_store(text):
    """Embed the text and store it in the Qdrant collection."""
    embeddings = cohere_client.embed(texts=[text]).embeddings[0]
    point_id = str(uuid.uuid4())  # Generate a UUID for the point ID
    qdrant_client.upsert(
        collection_name=collection_name,
        points=[
            {"id": point_id, "vector": embeddings, "payload": {"text": text}}
        ]
    )

def retrieve_documents(query, top_k=5):
    """Retrieve documents based on the query from the collection."""
    query_embedding = cohere_client.embed(texts=[query]).embeddings[0]
    results = qdrant_client.search(
        collection_name=collection_name,
        query_vector=query_embedding,
        limit=top_k
    )
    return results

def generate_response(query, retrieved_docs):
    """Generate a response based on the retrieved documents."""
    if not retrieved_docs:
        return "I'm sorry, I couldn't find any relevant information."
    else:
        context = " ".join([result.payload["text"] for result in retrieved_docs])
        response = cohere_client.generate(
            model='command-xlarge-nightly',
            prompt=f"Answer the question based on the context below in complete 100 words only.\n\nContext: {context}\n\n---\n\nQuestion: {query}\nAnswer:",
            temperature=0.5,
            max_tokens=100
        )
        return response.generations[0].text.strip()

# Streamlit UI
st.title("Interactive QA Bot")
st.subheader("Upload PDF documents and ask questions")

# Reset the collection
reset_collection()

uploaded_files = st.file_uploader("Upload PDF files", type=["pdf"], accept_multiple_files=True)

if uploaded_files:
    for uploaded_file in uploaded_files:
        reader = PdfReader(uploaded_file)
        text = ""
        for page in reader.pages:
            text += page.extract_text() + " "
        
        # Embed and store each document's text in the collection
        embed_and_store(text)
    st.success("Documents uploaded and processed successfully!")

user_query = st.text_input("Ask a question about the uploaded documents:")
if st.button("Submit"):
    if user_query:
        # Retrieve documents from the collection
        retrieved_docs = retrieve_documents(user_query)
        answer = generate_response(user_query, retrieved_docs)
        st.write("Chatbot:", answer)
    else:
        st.warning("Please enter a question.")
