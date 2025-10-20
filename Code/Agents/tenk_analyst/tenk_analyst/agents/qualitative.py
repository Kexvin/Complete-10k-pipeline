from typing import List, Dict, Optional
from ..models.core import Chunk
from ..models.qualitative import QualResult, QualSignal
from Code.Assets.Tools.nlp.finbert import FinBert
from Code.Assets.Tools.rag.pinecone_client import RAG

class QualitativeAgent:
    """Analyzes narrative tone and risk mentions using FinBERT + RAG grounding."""

    def __init__(self, finbert: FinBert, rag: RAG):
        self.finbert = finbert
        self.rag = rag

    def find_similar_sections(self, text: str, top_k: int = 5) -> List[Dict]:
        """Find similar sections from other companies using RAG."""
        if not self.rag or not self.rag._index:
            return []
            
        # Get embeddings for the query text
        query_embedding = self.rag._embed([text])
        if not query_embedding:
            return []
            
        # Search for similar sections
        results = self.rag._index.query(
            vector=query_embedding[0],
            top_k=top_k,
            include_metadata=True
        )
        
        return results.matches if results else []

    def analyze_tone_with_context(self, text: str, similar_sections: List[Dict]) -> Dict[str, any]:
        """Analyze tone with contextual comparison to similar companies."""
        # Get base tone
        tone = self.finbert.predict_tone(text)
        
        # Analyze similar sections
        similar_tones = []
        for section in similar_sections:
            if section.metadata and "text" in section.metadata:
                similar_tone = self.finbert.predict_tone(section.metadata["text"])
                similar_tones.append({
                    "company": section.metadata.get("company", "Unknown"),
                    "tone": similar_tone,
                    "score": section.score
                })
                
        # Generate contextual analysis
        context = {
            "tone": tone,
            "similar_companies": similar_tones,
            "explanation": self._generate_tone_explanation(tone, similar_tones)
        }
        
        return context

    def _generate_tone_explanation(self, tone: str, similar_tones: List[Dict]) -> str:
        """Generate natural language explanation of tone analysis."""
        if not similar_tones:
            return f"The section exhibits a {tone} tone based on FinBERT analysis."
            
        # Count tones from similar companies
        tone_counts = {"positive": 0, "negative": 0, "neutral": 0}
        for t in similar_tones:
            tone_counts[t["tone"]] = tone_counts.get(t["tone"], 0) + 1
            
        # Generate comparison
        majority_tone = max(tone_counts.items(), key=lambda x: x[1])[0]
        
        if tone == majority_tone:
            explanation = f"The {tone} tone aligns with the majority of similar companies in the sector."
        else:
            explanation = f"The {tone} tone differs from the majority of similar companies, which show a {majority_tone} tone."
            
        return explanation

    def run(self, chunks: List[Chunk]) -> List[QualResult]:
        out: List[QualResult] = []
        risk_keywords = [
            "risk", "uncertainty", "potential loss", "adverse effect",
            "decline", "volatility", "competition", "regulatory",
            "litigation", "liability", "disruption", "market conditions",
            "economic factors", "industry trends"
        ]

        for c in chunks:
            # Find similar sections from other companies
            similar_sections = self.find_similar_sections(c.text)
            
            # Analyze tone with context
            tone_analysis = self.analyze_tone_with_context(c.text, similar_sections)
            signals = []

            # Risk signal detection
            for keyword in risk_keywords:
                if keyword in c.text.lower():
                    sentences = c.text.split(". ")
                    for sentence in sentences:
                        if keyword in sentence.lower():
                            # Compare with similar companies
                            similar_risks = []
                            for section in similar_sections:
                                if section.metadata and keyword in section.metadata["text"].lower():
                                    similar_risks.append(section.metadata.get("company", "Unknown"))
                                    
                            context = ""
                            if similar_risks:
                                context = f" Similar concerns noted by: {', '.join(similar_risks[:3])}"
                                
                            signals.append(QualSignal(
                                label="risk",
                                evidence=sentence.strip(),
                                context=context
                            ))

            # Add tone signal with explanation
            signals.append(QualSignal(
                label="tone",
                evidence=tone_analysis["explanation"]
            ))

            out.append(QualResult(
                chunk_id=c.id,
                tone=tone_analysis["tone"],
                signals=signals,
                similar_companies=[{
                    "company": t["company"],
                    "tone": t["tone"],
                    "similarity": t["score"]
                } for t in tone_analysis["similar_companies"]]
            ))

        return out
