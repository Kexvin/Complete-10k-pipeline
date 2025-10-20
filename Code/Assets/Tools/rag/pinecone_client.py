from __future__ import annotations
from typing import List, Optional
import os
from pinecone import Pinecone, ServerlessSpec

class RAG:
    """
    Minimal RAG client wrapper using Pinecone.
    - If pinecone/sentence-transformers are unavailable, falls back to no-op.
    """

    def __init__(self, persist_dir: str = "Knowledge/pinecone", collection: str = "finance_glossary"):
        self.persist_dir = persist_dir
        # Sanitize index name to only allow lowercase alphanumeric and hyphens
        self.index_name = "".join(c.lower() for c in collection if c.isalnum() or c == "-")
        self._index = None
        self._pc = None

        try:
            # Initialize Pinecone
            api_key = os.getenv("PINECONE_API_KEY")
            if not api_key:
                raise ValueError("PINECONE_API_KEY environment variable not set")
                
            self._pc = Pinecone(api_key=api_key)
            
            # Use existing index
            if self.index_name not in self._pc.list_indexes().names():
                raise ValueError(f"Index '{self.index_name}' does not exist. Please create it in the Pinecone console first.")
            self._index = self._pc.Index(self.index_name)

        except Exception as e:
            print(f"Warning: Failed to initialize Pinecone: {e}")
            self._index = None

        try:
            from sentence_transformers import SentenceTransformer
            self._embedder = SentenceTransformer("all-MiniLM-L6-v2")
        except Exception as e:
            print(f"Warning: Failed to initialize SentenceTransformer: {e}")
            self._embedder = None

    def _embed(self, texts: List[str]) -> Optional[List[List[float]]]:
        if self._embedder is None:
            return None
        embeddings = self._embedder.encode(texts, convert_to_numpy=True)
        return embeddings.tolist()

    def index(self, ids: List[str], texts: List[str], metadatas: Optional[List[dict]] = None) -> None:
        if self._index is None:
            return

        embeds = self._embed(texts)
        if not embeds:
            return

        # Prepare vectors for Pinecone
        vectors = [
            (id_, embed, meta or {})
            for id_, embed, meta in zip(ids, embeds, metadatas or [{}] * len(ids))
        ]
        
        # Prepare vectors for Pinecone
        vectors = []
        for id_, text, embed, meta in zip(ids, texts, embeds, metadatas or [{}] * len(ids)):
            meta = meta.copy()  # Create a copy to avoid modifying the original
            meta["text"] = text  # Store the text in metadata
            vectors.append({
                "id": id_,
                "values": embed,
                "metadata": meta
            })

        # Upsert in batches of 100 to avoid rate limits
        batch_size = 100
        for i in range(0, len(vectors), batch_size):
            batch = vectors[i:i + batch_size]
            self._index.upsert(vectors=batch)

    def retrieve(self, query: str, top_k: int = 3) -> List[str]:
        if self._index is None or self._embedder is None or not query.strip():
            return []

        query_embed = self._embed([query])
        if not query_embed:
            return []

        # Query Pinecone
        results = self._index.query(
            vector=query_embed[0],
            top_k=top_k,
            include_values=False,
            include_metadata=True
        )

        # Return matched documents (texts)
        return [match.metadata.get("text", "") for match in results.matches] if results.matches else []