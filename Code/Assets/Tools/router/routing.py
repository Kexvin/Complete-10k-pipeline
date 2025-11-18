from __future__ import annotations
from typing import List, Optional


from Code.Agents.tenk_analyst.tenk_analyst.models.core import Chunk, RoutedChunk


_QUAL_SECTIONS = {
    "Risk Factors",
    "MD&A",
    "Management’s Discussion",
    "Business",
}
_QUANT_CUES = {
    "balance sheet",
    "cash flow",
    "income",
    "consolidated",
}


def _is_non_10k(filing_type: Optional[str]) -> bool:
    if not filing_type:
        return False
    return filing_type.strip().lower() != "10-k"


def route_chunks(
    chunks: List[Chunk],
    filing_type: Optional[str] = None,
) -> List[RoutedChunk]:
    """
    Route each chunk to 'qualitative', 'quantitative', or 'non-10k'
    using simple section/text heuristics.

    This is the tools version of the old ControllerAgent.route.
    """
    routed: List[RoutedChunk] = []

    # case 1: not a 10-K → everything goes to 'non-10k'
    if _is_non_10k(filing_type):
        for c in chunks:
            routed.append(RoutedChunk(chunk=c, route="non-10k"))
        return routed

    # case 2: 10-K or unspecified → per-chunk heuristics
    for c in chunks:
        text_l = c.text.lower()
        route = "qualitative"
        # quant if: text has quant cue AND the section is not clearly qualitative
        if any(k in text_l for k in _QUANT_CUES) and (c.section not in _QUAL_SECTIONS):
            route = "quantitative"
        routed.append(RoutedChunk(chunk=c, route=route))

    return routed
