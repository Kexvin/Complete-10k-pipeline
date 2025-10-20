from typing import List, Optional
from ..models.core import Chunk, RoutedChunk

# Heuristics for routing
QUAL_SECTIONS = {"Risk Factors", "MD&A", "Management’s Discussion", "Business"}
QUANT_CUES = {"balance sheet", "cash flow", "income", "consolidated"}


class ControllerAgent:
    """Routes chunks to qualitative or quantitative analysis.

    New behavior:
      - Accept optional filing metadata so routing decisions can consider filing type
      - If filing_type is present and not a 10-K, mark route as 'non-10k' so the pipeline
        can handle it differently (for example, fetch additional context or skip some
        quantitative extraction)
    """
    def route(self, chunks: List[Chunk], *, filing_type: Optional[str] = None) -> List[RoutedChunk]:
        out: List[RoutedChunk] = []

        # If filing_type is provided and it's not a 10-K, route all to 'non-10k'
        if filing_type and filing_type.strip().lower() != "10-k":
            for c in chunks:
                out.append(RoutedChunk(chunk=c, route="non-10k"))
            return out

        # Default per-chunk heuristics
        for c in chunks:
            text_l = c.text.lower()
            route = "qualitative"
            if any(k in text_l for k in QUANT_CUES) and (c.section not in QUAL_SECTIONS):
                route = "quantitative"
            out.append(RoutedChunk(chunk=c, route=route))
        return out
