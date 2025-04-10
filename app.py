import streamlit as st
from PyPDF2 import PdfReader
from qdrant_client import QdrantClient, models
from qdrant_client.models import VectorParams
import cohere
import uuid

# Initialize Qdrant and Cohere clients
qdrant_client = QdrantClient(
    url="https://cb6bb304-967d-4cb2-821a-8b66a9adc943.europe-west3-0.gcp.cloud.qdrant.io:6333", 
    api_key="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJhY2Nlc3MiOiJtIn0.3BHvg0Zl5ylf1Zi9MSqKNk2LBjBm5XfO9TQTw0qQr3o",
)
cohere_client = cohere.Client('GJ7ahzxVR1uJ1A517IowWn0K14jBZ0K1ag4SFYGz')

def reset_collection():
    """Delete the existing collection if it exists and create a new one."""
    collections_info = qdrant_client.get_collections()
    existing_collections = [col.name for col in collections_info.collections]

    # Delete existing collection if it exists
    if 'pdf_collection' in existing_collections:
        qdrant_client.delete_collection('pdf_collection')
        st.success("Existing collection deleted.")

    # Create a new collection
    try:
        qdrant_client.create_collection(
            collection_name='pdf_collection',
            vectors_config=VectorParams(size=4096, distance=models.Distance.COSINE)
        )
        st.success("New collection created.")
    except Exception as e:
        st.warning(f"Could not create collection: {e}")

def embed_and_store(text):
    """Embed the text and store it in the Qdrant collection."""
    embeddings = cohere_client.embed(texts=[text]).embeddings[0]
    point_id = str(uuid.uuid4())  # Generate a UUID for the point ID
    qdrant_client.upsert(
        collection_name='pdf_collection',
        points=[{"id": point_id, "vector": embeddings, "payload": {"text": text}}]
    )

def retrieve_documents(query, top_k=5):
    """Retrieve documents based on the query from the collection."""
    query_embedding = cohere_client.embed(texts=[query]).embeddings[0]
    results = qdrant_client.search(
        collection_name='pdf_collection',
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
        response = cohere_client.chat(
            model='command-r7b-12-2024',
            message=f"Answer the question based on the context below in complete 100 words only.\n\nContext: {context}\n\n---\n\nQuestion: {query}\nAnswer:",
            temperature=0.5,
            max_tokens=1000
        )
        return response.text.strip()
    
    

# Streamlit UI
st.title("AI chatbot for answering queries from document")
st.subheader("Upload PDF documents and ask questions")

# Button to reset the collection
if st.button("Reset Collection"):
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
