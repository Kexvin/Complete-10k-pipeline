from __future__ import annotations
from typing import Optional
from Code.Assets.Tools.core.stage import Stage
from Knowledge.Schema.Artifacts.raw_text import RawTextArtifact
from Knowledge.Schema.Artifacts.datasources import sec_edgar_api_source, kaggle_company_facts_source
from Code.Assets.Tools.io.sec_client import lookup_cik_by_ticker, latest_10k_accession, fetch_10k_text
import csv
from pathlib import Path

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

        # 1) Determine CIK
        cik = inp.company_cik
        if not cik and ticker:
            cik = _lookup_cik_from_kaggle(Path(kaggle_csv)) if kaggle_csv else None  # type: ignore[arg-type]
            if not cik:
                cik = lookup_cik_by_ticker(ticker, user_agent=user_agent)

        if not cik:
            raise ValueError("Unable to resolve CIK. Provide inp.company_cik or kwargs['ticker'].")

        # 2) Determine latest 10-K accession
        accession = inp.accession or latest_10k_accession(cik, user_agent=user_agent)
        if not accession:
            raise ValueError(f"No 10-K accession found for CIK {cik}")

        # 3) Fetch 10-K full text
        text = inp.text or fetch_10k_text(cik, accession, user_agent=user_agent)

        # 4) Build sources and return artifact
        sources = list(inp.sources or [])
        if kaggle_csv:
            sources.append(kaggle_company_facts_source(notes=f"CSV path: {kaggle_csv}"))
        sources.append(sec_edgar_api_source())

        return RawTextArtifact(
            company_cik=cik,
            accession=accession,
            filing_period=inp.filing_period,
            text=text,
            sources=sources
        )
