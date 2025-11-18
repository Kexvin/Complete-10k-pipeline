# Code/Agents/tenk_analyst/tenk_analyst/stages/summarize_stage.py

from Code.Assets.Tools.core.stage import Stage
from Knowledge.Schema.Artifacts.qual_results import QualResultsArtifact
from Knowledge.Schema.Artifacts.quant_results import QuantResultsArtifact
from Knowledge.Schema.Artifacts.summary import SummaryArtifact
from Code.Agents.tenk_analyst.tenk_analyst.agents.summarizer import SummarizerAgent


class SummarizeStage(Stage[tuple[QualResultsArtifact, QuantResultsArtifact], SummaryArtifact]):
    """
    Combines outputs of QualResultsArtifact and QuantResultsArtifact into SummaryArtifact.

    NOTE:
      - Use this stage directly (not in the linear Pipeline) or pass a tuple as the prior stage output.
      - company_name is taken from QualResultsArtifact if available; otherwise we fall back to
        source metadata or an empty string.
    """

    def __init__(self) -> None:
        super().__init__("summarize", tuple, SummaryArtifact)
        self.summarizer = SummarizerAgent()

    def run(self, inp: tuple[QualResultsArtifact, QuantResultsArtifact], **kwargs) -> SummaryArtifact:
        qual_art, quant_art = inp

        # Prefer company_name attribute on QualResultsArtifact if present
        company_name = ""
        try:
            company_name = getattr(qual_art, "company_name", "") or ""
        except Exception:
            company_name = ""

        # Fallback to first source name if we still don't have anything meaningful
        if not company_name and qual_art.sources:
            try:
                first_src = qual_art.sources[0]
                company_name = getattr(first_src, "name", "") or ""
            except Exception:
                company_name = ""

        report = self.summarizer.combine(
            company_name,
            qual_art.company_cik,
            qual_art.accession,
            qual_art.results,
            quant_art.results,
        )

        return SummaryArtifact(
            company_cik=report.cik,
            accession=report.accession,
            report=report,
            sources=(qual_art.sources or []) + (quant_art.sources or []),
        )
