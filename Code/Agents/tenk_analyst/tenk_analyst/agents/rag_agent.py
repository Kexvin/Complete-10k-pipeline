from __future__ import annotations
from typing import List, Optional, Dict, Any

from Code.Assets.Tools.rag.pinecone_client import RAG


class RagAgent:
    """
    TenKRAGRetriever

    Agent-level wrapper around the RAG (Pinecone) client.
    This corresponds to `rag-agent` in agent_registry.json.

    Responsibilities:
      - Accept a text query (+ optional filters)
      - Use the RAG client to retrieve relevant 10-K chunks
      - Optionally index documents into Pinecone
    """

    def __init__(self, collection: str = "knowledgepinecone"):
        self.collection = collection
        self.client = RAG(collection=collection)

    # --- low-level passthrough for compatibility ---------------------------

    def query(
        self,
        texts: List[str],
        top_k: int = 5,
        filters: Optional[Dict[str, Any]] = None,
    ):
        """
        Thin wrapper around the underlying RAG client's query method.

        This keeps backward compatibility with any code that expects
        a `.query(...)` on the object (like your old use of `RAG`).
        """
        return self.client.query(
            texts=texts,
            top_k=top_k,
            filters=filters,
        )

    # --- high-level "agent" API -------------------------------------------

    def retrieve(
        self,
        text_query: str,
        top_k: int = 5,
        company_filters: Optional[Dict[str, Any]] = None,
        section_filters: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Retrieve relevant chunks for a natural-language query.

        Returns list of dicts like:
          {
            "id": ...,
            "score": ...,
            "text": ...,
            "metadata": {...}
          }
        """

        filters: Optional[Dict[str, Any]] = None
        if company_filters or section_filters:
            filters = {
                **(company_filters or {}),
                **(section_filters or {}),
            }

        results = self.query(
            texts=[text_query],
            top_k=top_k,
            filters=filters,
        )

        out: List[Dict[str, Any]] = []
        for r in results:
            out.append(
                {
                    "id": getattr(r, "id", None),
                    "score": getattr(r, "score", None),
                    "text": getattr(r, "text", None),
                    "metadata": getattr(r, "metadata", {}),
                }
            )
        return out

    # --- indexing API ------------------------------------------------------

    def index(
        self,
        ids: List[str],
        texts: List[str],
        metadatas: Optional[List[Dict[str, Any]]] = None,
    ):
        """
        Proxy through to the underlying RAG client's index method.
        Used in run_from_sec.py to index summary vectors.
        """
        return self.client.index(
            ids=ids,
            texts=texts,
            metadatas=metadatas,
        )
