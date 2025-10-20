from typing import List
from ..models.core import Chunk
from ..models.qualitative import QualResult, QualSignal
from Code.Assets.Tools.nlp.finbert import FinBert
from Code.Assets.Tools.rag.pinecone_client import RAG

class QualitativeAgent:
    """Analyzes narrative tone and risk mentions using FinBERT + optional RAG grounding."""

    def __init__(self, finbert: FinBert, rag: RAG):
        self.finbert = finbert
        self.rag = rag

    def run(self, chunks: List[Chunk]) -> List[QualResult]:
        out: List[QualResult] = []
        for c in chunks:
            tone = self.finbert.predict_tone(c.text)  # "positive"/"neutral"/"negative"
            signals = []
            if "risk" in c.text.lower():
                signals.append(QualSignal(label="risk", evidence="..."))
            out.append(QualResult(chunk_id=c.id, tone=tone, signals=signals))
        return out
