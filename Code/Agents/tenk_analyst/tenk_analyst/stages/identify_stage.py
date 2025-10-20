from __future__ import annotations
from typing import Optional
from Code.Assets.Tools.core.stage import Stage
from Knowledge.Schema.Artifacts.raw_text import RawTextArtifact
from Code.Assets.Tools.io import sec_client


class IdentifyStage(Stage[RawTextArtifact, RawTextArtifact]):
    """Resolves company identifiers and filing type without fetching full text.

    Behavior:
      - If `company_cik` present, uses it; otherwise tries `ticker` from kwargs
      - Determines if a 10-K exists (sets filing_type to '10-K' when found)
      - Does not fetch filing text
    """
    def __init__(self) -> None:
        super().__init__("identify", RawTextArtifact, RawTextArtifact)

    def run(self, inp: RawTextArtifact, **kwargs) -> RawTextArtifact:
        ticker: Optional[str] = kwargs.get("ticker")
        user_agent: Optional[str] = kwargs.get("user_agent")

        cik = inp.company_cik
        if not cik and ticker:
            cik = sec_client.lookup_cik_by_ticker(ticker, user_agent=user_agent)

        filing_type = None
        accession = inp.accession
        if cik:
            # Check if a 10-K exists
            acc = sec_client.latest_10k_accession(cik, user_agent=user_agent)
            if acc:
                filing_type = "10-K"
                accession = accession or acc

        return RawTextArtifact(
            company_cik=cik or "",
            accession=accession or "",
            filing_period=inp.filing_period,
            filing_type=filing_type,
            text=inp.text,
            sources=inp.sources
        )
