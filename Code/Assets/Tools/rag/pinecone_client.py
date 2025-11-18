"""
Thin RAG wrapper around Pinecone + SentenceTransformers.

Responsibilities:
- Connect to a single Pinecone index (collection).
- Clean raw text (strip HTML, scripts, weird whitespace).
- Filter out trivial / empty chunks.
- Embed with SentenceTransformer.
- Upsert/query vectors from Pinecone.
- Sanitize metadata so it conforms to Pinecone limits
  (no `null`/None values; reasonable string sizes).
"""

from __future__ import annotations

import os
import re
from html import unescape
from typing import Any, Dict, List, Optional, Tuple

from dotenv import load_dotenv
from pinecone import Pinecone
from sentence_transformers import SentenceTransformer


class RAG:
    """
    RAG client backed by a Pinecone index and a SentenceTransformer encoder.

    Typical usage:
        rag = RAG(collection="knowledgepinecone", namespace="10k_sections")
        rag.index(ids=[...], texts=[...], metadatas=[...])
        results = rag.query("what are the main risk factors?", top_k=5)
    """

    # Max length for any single metadata string value
    _MAX_META_STR_LEN = 8000

    def __init__(
        self,
        collection: str,
        namespace: Optional[str] = None,
        model_name: str = "all-MiniLM-L6-v2",
    ) -> None:
        """
        :param collection: Pinecone index name (e.g., "knowledgepinecone").
        :param namespace: Optional Pinecone namespace for logical grouping.
        :param model_name: SentenceTransformer model name to use.
        """
        load_dotenv()

        api_key = os.getenv("PINECONE_API_KEY")
        if not api_key:
            raise RuntimeError("PINECONE_API_KEY is not set in the environment.")

        # New Pinecone client style
        pc = Pinecone(api_key=api_key)

        self.collection: str = collection
        self.namespace: str = namespace or ""  # ensure attribute always exists

        # Underlying Pinecone index
        self._index = pc.Index(collection)
        print(f"RAG: connected to Pinecone index '{collection}'")

        # Embedding model
        self.model_name: str = model_name
        self._embedder = SentenceTransformer(model_name)
        print(f"RAG: SentenceTransformer model '{model_name}' loaded.")

    # ────────────────────────────────────────────────────────────────────────
    # Public API
    # ────────────────────────────────────────────────────────────────────────

    def index(
        self,
        ids: List[str],
        texts: List[str],
        metadatas: Optional[List[Dict[str, Any]]] = None,
    ) -> None:
        """
        Upsert a batch of (id, text, metadata) into Pinecone.

        - Cleans HTML/whitespace from texts.
        - Skips trivial / empty chunks.
        - Sanitizes metadata (drops None, truncates long strings).
        - **Adds the cleaned text itself into metadata["text"] for LLM context.**
        """
        if len(ids) != len(texts):
            raise ValueError("ids and texts must have the same length")

        if metadatas is None:
            metadatas = [{} for _ in ids]
        elif len(metadatas) != len(ids):
            raise ValueError("ids and metadatas must have the same length")

        # 1) Clean text & filter trivial chunks
        cleaned_texts: List[str] = []
        cleaned_ids: List[str] = []
        cleaned_metas_raw: List[Dict[str, Any]] = []

        cleaned_count = 0
        skipped_trivial = 0

        for _id, txt, meta in zip(ids, texts, metadatas):
            cleaned = self._clean_text(txt)
            cleaned_count += 1

            if self._is_trivial(cleaned):
                skipped_trivial += 1
                continue

            cleaned_texts.append(cleaned)
            cleaned_ids.append(_id)
            cleaned_metas_raw.append(meta)

        print(
            f"RAG: cleaned {cleaned_count}/{len(texts)} texts before embedding "
            "(removed HTML/script content)"
        )
        print(
            f"RAG: skipped {skipped_trivial}/{cleaned_count} "
            "trivial/HTML-only or code-like chunks (not indexed)"
        )

        if not cleaned_texts:
            print("RAG: no embeddings generated; nothing to upsert.")
            return

        # 2) Embed
        try:
            embeddings = self._embed(cleaned_texts)
        except Exception as e:
            print(f"RAG: embedding failed: {e}")
            return

        # 3) Attach cleaned text into metadata, then sanitize
        metas_with_text: List[Dict[str, Any]] = []
        for txt, meta in zip(cleaned_texts, cleaned_metas_raw):
            m = dict(meta) if meta else {}
            # store the cleaned text as 'text' for LLM context
            m["text"] = txt
            metas_with_text.append(m)

        sanitized_metas = [self._sanitize_metadata(m) for m in metas_with_text]

        # 4) Build vectors and upsert
        vectors = []
        for _id, emb, meta in zip(cleaned_ids, embeddings, sanitized_metas):
            vectors.append({"id": _id, "values": emb, "metadata": meta})

        try:
            self._index.upsert(
                vectors=vectors,
                namespace=self.namespace or None,
            )
            print(
                f"RAG: upserted {len(vectors)} vectors into index "
                f"'{self.collection}' (skipped {skipped_trivial})"
            )
        except Exception as e:
            # Do NOT raise here to keep pipeline resilient; just log.
            print(f"RAG: upsert batch failed: {e}")

    def query(
        self,
        query_text: str,
        top_k: int = 5,
        filter: Optional[Dict[str, Any]] = None,
        include_metadata: bool = True,
    ) -> Dict[str, Any]:
        """
        Query Pinecone for nearest neighbors to the given query text.

        :param query_text: Natural-language query.
        :param top_k: Number of nearest neighbors to return.
        :param filter: Optional Pinecone filter dict.
        :param include_metadata: Whether to return metadata with results.
        :return: Raw Pinecone query response as a dict.
        """
        cleaned_query = self._clean_text(query_text)

        if self._is_trivial(cleaned_query):
            print("RAG: query text is trivial after cleaning; returning empty result.")
            return {"matches": []}

        try:
            query_vec = self._embed([cleaned_query])[0]
        except Exception as e:
            print(f"RAG: embedding failed for query: {e}")
            return {"matches": []}

        try:
            res = self._index.query(
                vector=query_vec,
                top_k=top_k,
                include_metadata=include_metadata,
                namespace=self.namespace or None,
                filter=filter or {},
            )
            return res
        except Exception as e:
            print(f"RAG: query failed: {e}")
            return {"matches": []}
        
    def query_filing(
        self,
        cik: str,
        accession: str,
        query_text: str,
        top_k: int = 12,
    ) -> Dict[str, Any]:
        """
        Convenience helper: query only chunks for a single 10-K filing.

        Filters by:
          - company_cik == cik
          - accession  == accession
        and returns the normal Pinecone query response.
        """
        filter_dict = {
            "company_cik": cik,
            "accession": accession,
        }
        return self.query(
            query_text=query_text,
            top_k=top_k,
            filter=filter_dict,
            include_metadata=True,
        )        

    # ────────────────────────────────────────────────────────────────────────
    # Internal helpers
    # ────────────────────────────────────────────────────────────────────────

    def _embed(self, texts: List[str]) -> List[List[float]]:
        """Small wrapper so legacy code that calls self._embed still works."""
        return self._embedder.encode(texts, show_progress_bar=False).tolist()

    @staticmethod
    def _strip_html(text: str) -> str:
        """Remove basic HTML tags and script/style content."""
        # Remove script and style blocks completely
        text = re.sub(r"(?is)<(script|style).*?>.*?(</\1>)", " ", text)
        # Remove all remaining tags
        text = re.sub(r"(?s)<[^>]+>", " ", text)
        return text

    @classmethod
    def _clean_text(cls, text: str) -> str:
        """HTML/whitespace normalization similar to what you've been logging."""
        if not text:
            return ""

        # Unescape HTML entities
        text = unescape(text)

        # Strip HTML tags and scripts
        text = cls._strip_html(text)

        # Normalize whitespace
        text = re.sub(r"\s+", " ", text).strip()

        return text

    @staticmethod
    def _is_trivial(text: str) -> bool:
        """
        Heuristic to detect 'trivial' chunks that shouldn't be indexed:
        - Very short length
        - Too few alphanumeric characters
        """
        if not text:
            return True

        # Very short text is often just a heading or noise
        if len(text) < 20:
            return True

        alnum_count = sum(c.isalnum() for c in text)
        if alnum_count < 5:
            return True

        return False

    @classmethod
    def _truncate_str(cls, value: str) -> str:
        """Truncate long metadata strings to stay under Pinecone's size limits."""
        if len(value) <= cls._MAX_META_STR_LEN:
            return value
        return value[: cls._MAX_META_STR_LEN]

    @classmethod
    def _sanitize_metadata(cls, meta: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Pinecone constraints:
        - Values must be: string, number, boolean, or list of strings.
        - No `null` (None) values.
        - Total per-vector metadata must be <= 40KB, so we truncate long strings.
        """
        if not meta:
            return {}

        clean: Dict[str, Any] = {}

        for key, value in meta.items():
            # Drop None / null entirely
            if value is None:
                continue

            # Primitive allowed types
            if isinstance(value, (int, float, bool)):
                clean[key] = value
            elif isinstance(value, str):
                clean[key] = cls._truncate_str(value)
            elif isinstance(value, list):
                # Pinecone wants list of strings; coerce and drop Nones
                string_list = [cls._truncate_str(str(v)) for v in value if v is not None]
                clean[key] = string_list
            else:
                # Fallback: coerce to string and truncate
                clean[key] = cls._truncate_str(str(value))

        return clean
