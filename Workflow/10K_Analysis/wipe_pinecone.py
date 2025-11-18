import os
from pinecone import Pinecone

# Make sure this env var is set in your shell or .env
api_key = os.environ["PINECONE_API_KEY"]

pc = Pinecone(api_key=api_key)

index_name = "knowledgepinecone"
index = pc.Index(index_name)

# ⚠️ This deletes ALL vectors in this index (all namespaces)
index.delete(deleteAll=True)

print(f"Deleted all vectors in index '{index_name}'.")
