from typing import List
from ..models.core import Chunk, RoutedChunk

QUAL_SECTIONS = {"Risk Factors", "MD&A", "Management’s Discussion", "Business"}
QUANT_CUES = {"balance sheet", "cash flow", "income", "consolidated"}

class ControllerAgent:
    """Routes chunks to qualitative or quantitative analysis."""
    def route(self, chunks: List[Chunk]) -> List[RoutedChunk]:
        out: List[RoutedChunk] = []
        for c in chunks:
            text_l = c.text.lower()
            route = "qualitative"
            if any(k in text_l for k in QUANT_CUES) and (c.section not in QUAL_SECTIONS):
                route = "quantitative"
            out.append(RoutedChunk(chunk=c, route=route))
        return out
