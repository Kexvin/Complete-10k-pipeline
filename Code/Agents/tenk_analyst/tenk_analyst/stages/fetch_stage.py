from __future__ import annotations
from typing import Optional

from Code.Assets.Tools.core.stage import Stage
from Knowledge.Schema.Artifacts.raw_text import RawTextArtifact
from Knowledge.Schema.Artifacts.datasources import sec_edgar_api_source
from Code.Assets.Tools.io import sec_client
from Code.Assets.Tools.rag.pinecone_client import RAG


class FetchStage(Stage[RawTextArtifact, RawTextArtifact]):
    """
    Fetches the latest 10-K text for a given company.

    Input RawTextArtifact may have just company_cik (or nothing),
    and kwargs may include:
      - ticker: str
      - user_agent: str
      - rag_index: bool
      - rag_collection: str
    """
    def __init__(self) -> None:
        super().__init__("fetch", RawTextArtifact, RawTextArtifact)

    def run(self, inp: RawTextArtifact, **kwargs) -> RawTextArtifact:
        ticker: Optional[str] = kwargs.get("ticker")
        user_agent: Optional[str] = kwargs.get("user_agent")

        # RAG options
        rag_index: bool = bool(kwargs.get("rag_index", False))
        rag_collection: Optional[str] = kwargs.get("rag_collection")

        # 1) Determine CIK
        cik = inp.company_cik
        if not cik and ticker:
            cik = sec_client.lookup_cik_by_ticker(ticker, user_agent=user_agent)

        if not cik:
            raise ValueError("Unable to resolve CIK. Provide inp.company_cik or kwargs['ticker'].")

        # 2) Determine latest 10-K accession
        accession = inp.accession or sec_client.latest_10k_accession(cik, user_agent=user_agent)
        if not accession:
            raise ValueError(f"No 10-K accession found for CIK {cik}")

        # 3) Fetch 10-K full text
        text = inp.text or sec_client.fetch_10k_text(cik, accession, user_agent=user_agent)

        # 4) Build sources and return artifact
        sources = list(inp.sources or [])
        sources.append(sec_edgar_api_source())

        filing_type = "10-K" if accession else None

        artifact = RawTextArtifact(
            company_cik=cik,
            accession=accession,
            filing_period=inp.filing_period,
            filing_type=filing_type,
            text=text,
            sources=sources,
        )

        # Optional: index the fetched filing into a RAG store (Pinecone)
        if rag_index:
            try:
                collection = rag_collection or "tenk_filings"
                rag = RAG(collection=collection)
                doc_id = f"{cik}_{accession}"
                rag.index(
                    ids=[doc_id],
                    texts=[text],
                    metadatas=[
                        {
                            "company_cik": cik,
                            "accession": accession,
                            "filing_period": inp.filing_period,
                        }
                    ],
                )
            except Exception:
                # Indexing failure shouldn't break fetch
                pass

        return artifact
