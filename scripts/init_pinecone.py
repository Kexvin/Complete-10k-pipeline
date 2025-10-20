"""Initialize Pinecone index for the 10-K analysis pipeline."""
import os
from pinecone import Pinecone, ServerlessSpec

def create_pinecone_index():
    # Get API key from environment
    api_key = os.getenv("PINECONE_API_KEY")
    if not api_key:
        raise ValueError("PINECONE_API_KEY environment variable not set")
    
    # Initialize Pinecone client
    pc = Pinecone(api_key=api_key)
    
    # Index configuration
    index_name = "knowledgepinecone"
    dimension = 384  # dimension for all-MiniLM-L6-v2 embeddings
    metric = "cosine"
    
    # Create index if it doesn't exist
    if index_name not in pc.list_indexes().names():
        pc.create_index(
            name=index_name,
            dimension=dimension,
            metric=metric,
            spec=ServerlessSpec(
                cloud='aws',
                region='us-east-1'  # Free tier region
            )
        )
        print(f"Created new index: {index_name}")
    else:
        print(f"Index {index_name} already exists")

if __name__ == "__main__":
    create_pinecone_index()