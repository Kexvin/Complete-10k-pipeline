from __future__ import annotations
from typing import Optional
from Code.Assets.Tools.core.stage import Stage
from Knowledge.Schema.Artifacts.raw_text import RawTextArtifact
from Knowledge.Schema.Artifacts.datasources import sec_edgar_api_source, kaggle_company_facts_source
from Code.Assets.Tools.io import sec_client
import csv
from pathlib import Path
from Code.Assets.Tools.rag.pinecone_client import RAG

def _lookup_cik_from_kaggle(kaggle_csv: Path, ticker: str) -> Optional[str]:
    """
    Tries to map ticker -> CIK from a Kaggle CSV extract.
    You can tailor column names here to match your export (e.g., 'ticker', 'cik').
    """
    if not kaggle_csv.exists():
        return None
    ticker_up = ticker.upper()
    with kaggle_csv.open("r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if str(row.get("ticker", "")).upper() == ticker_up and row.get("cik"):
                return str(row["cik"])
    return None

class FetchStage(Stage[RawTextArtifact, RawTextArtifact]):
    """
    New behavior:
      - Input RawTextArtifact may have just company metadata (no text yet)
      - kwargs: ticker: str, kaggle_csv: Optional[str], user_agent: Optional[str]
      - Resolves CIK using Kaggle or EDGAR mapping, gets latest 10-K, fetches text
    """
    def __init__(self) -> None:
        super().__init__("fetch", RawTextArtifact, RawTextArtifact)

    def run(self, inp: RawTextArtifact, **kwargs) -> RawTextArtifact:
        ticker: Optional[str] = kwargs.get("ticker")
        kaggle_csv: Optional[str] = kwargs.get("kaggle_csv")
        user_agent: Optional[str] = kwargs.get("user_agent")
        # RAG options
        rag_index: bool = bool(kwargs.get("rag_index", False))
        rag_collection: Optional[str] = kwargs.get("rag_collection")

        # 1) Determine CIK
        cik = inp.company_cik
        if not cik and ticker:
            cik = _lookup_cik_from_kaggle(Path(kaggle_csv), ticker) if kaggle_csv else None
            if not cik:
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
        if kaggle_csv:
            sources.append(kaggle_company_facts_source(notes=f"CSV path: {kaggle_csv}"))
        sources.append(sec_edgar_api_source())
        # Determine filing_type (10-K if accession exists)
        filing_type = "10-K" if accession else None

        artifact = RawTextArtifact(
            company_cik=cik,
            accession=accession,
            filing_period=inp.filing_period,
            filing_type=filing_type,
            text=text,
            sources=sources
        )

        # Optional: index the fetched filing into a RAG store (Pinecone)
        if rag_index:
            try:
                collection = rag_collection or "tenk_filings"
                rag = RAG(collection=collection)
                # Use a single-document index entry with metadata
                doc_id = f"{cik}_{accession}"
                rag.index(ids=[doc_id], texts=[text], metadatas=[{
                    "company_cik": cik,
                    "accession": accession,
                    "filing_period": inp.filing_period,
                }])
            except Exception:
                # Fail silently; indexing shouldn't break fetch
                pass

        return artifact
