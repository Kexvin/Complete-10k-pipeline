"""Check Pinecone index configuration."""
import os
from pinecone import Pinecone

def check_pinecone_index():
    api_key = os.getenv("PINECONE_API_KEY")
    if not api_key:
        raise ValueError("PINECONE_API_KEY environment variable not set")
    
    pc = Pinecone(api_key=api_key)
    
    # List all indexes
    indexes = pc.list_indexes()
    print("Available indexes:", indexes.names())
    
    # Get details of our index
    if "knowledgepinecone" in indexes.names():
        index = pc.describe_index("knowledgepinecone")
        print("\nIndex details:")
        print(f"- Name: {index.name}")
        print(f"- Dimension: {index.dimension}")
        print(f"- Metric: {index.metric}")
        print(f"- Environment: {index.environment}")
        print(f"- Spec: {index.spec}")

if __name__ == "__main__":
    check_pinecone_index()