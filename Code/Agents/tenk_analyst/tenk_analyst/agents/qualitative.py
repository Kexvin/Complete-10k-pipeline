from typing import List, Dict
from ..models.core import Chunk
from ..models.qualitative import QualResult, QualSignal
from Code.Assets.Tools.nlp.finbert import FinBert
from Code.Assets.Tools.rag.pinecone_client import RAG


class QualitativeAgent:
    """Analyzes narrative tone and risk mentions using FinBERT + RAG grounding."""

    def __init__(self, finbert: FinBert, rag: RAG):
        self.finbert = finbert
        self.rag = rag

    # ------------- RAG helpers -------------------------------------------------

    def _clean_for_qual(self, text: str) -> str:
        """Use RAG's cleaning logic if available; otherwise return text."""
        if self.rag and hasattr(self.rag, "_clean_text"):
            return self.rag._clean_text(text)
        return text or ""

    def _is_code_like_for_qual(self, text: str) -> bool:
        """Use RAG's code-like heuristic if available."""
        if self.rag and hasattr(self.rag, "_is_code_like"):
            return self.rag._is_code_like(text)
        return False

    def find_similar_sections(self, text: str, top_k: int = 5) -> List[Dict]:
        """
        Find similar sections from other companies using the RAG vector index.

        Returns a list of Pinecone match objects (or empty list if RAG is unavailable).
        """
        if not self.rag or not getattr(self.rag, "_index", None):
            print("[QUAL DEBUG] RAG index not available; skipping similar-sections search.")
            return []

        # Get embeddings for the query text
        query_embedding = self.rag._embed([text])
        if not query_embedding:
            print("[QUAL DEBUG] Failed to embed query text; no similar sections found.")
            return []

        # Search for similar sections
        results = self.rag._index.query(
            vector=query_embedding[0],
            top_k=top_k,
            include_metadata=True,
        )

        matches = results.matches if results else []
        print(f"[QUAL DEBUG] Similar sections found: {len(matches)}")
        return matches

    def analyze_tone_with_context(self, text: str, similar_sections: List[Dict]) -> Dict[str, any]:
        """
        Analyze tone with contextual comparison to similar companies.

        Returns:
            {
              "tone": "positive|neutral|negative",
              "similar_companies": [{company, tone, score}, ...],
              "explanation": "natural-language explanation"
            }
        """
        # Base tone from FinBERT
        tone = self.finbert.predict_tone(text)

        # Analyze similar sections
        similar_tones = []
        for section in similar_sections:
            meta = getattr(section, "metadata", None) or {}
            sec_text = meta.get("text")
            if not sec_text:
                continue

            similar_tone = self.finbert.predict_tone(sec_text)
            similar_tones.append({
                "company": meta.get("company_name") or meta.get("company") or "Unknown",
                "tone": similar_tone,
                "score": getattr(section, "score", 0.0),
            })

        explanation = self._generate_tone_explanation(tone, similar_tones)
        return {
            "tone": tone,
            "similar_companies": similar_tones,
            "explanation": explanation,
        }

    def _generate_tone_explanation(self, tone: str, similar_tones: List[Dict]) -> str:
        """Generate natural language explanation of tone analysis."""
        if not similar_tones:
            return f"The section exhibits a {tone} tone based on FinBERT analysis."

        # Count tones from similar companies
        tone_counts = {"positive": 0, "negative": 0, "neutral": 0}
        for t in similar_tones:
            label = t["tone"]
            if label in tone_counts:
                tone_counts[label] += 1

        # Majority tone among similar companies
        majority_tone = max(tone_counts.items(), key=lambda x: x[1])[0]

        if tone == majority_tone:
            explanation = (
                f"The {tone} tone aligns with the majority of similar companies in the sector."
            )
        else:
            explanation = (
                f"The {tone} tone differs from the majority of similar companies, "
                f"which show a {majority_tone} tone."
            )

        return explanation

    # ------------- Main run() --------------------------------------------------

    def run(self, chunks: List[Chunk]) -> List[QualResult]:
        """
        Main qualitative analysis entrypoint.

        For each chunk:
          - Clean HTML/JS noise
          - Skip code-like boilerplate
          - Run FinBERT tone
          - Compare to similar sections from other companies (via RAG)
          - Detect risk-related sentences
          - Create QualResult with signals + similar_companies
        """
        out: List[QualResult] = []

        risk_keywords = [
            "risk", "uncertainty", "potential loss", "adverse effect",
            "decline", "volatility", "competition", "regulatory",
            "litigation", "liability", "disruption", "market conditions",
            "economic factors", "industry trends",
        ]

        for c in chunks:
            raw_text = c.text or ""
            cleaned_text = self._clean_for_qual(raw_text)
            cleaned_text = cleaned_text.strip()

            print(
                f"[QUAL DEBUG] chunk_id={c.id} raw_len={len(raw_text)} "
                f"clean_len={len(cleaned_text)} preview={cleaned_text[:200]!r}"
            )

            # Skip empty or code-like chunks after cleaning
            if not cleaned_text:
                print(f"[QUAL DEBUG] Skipping chunk_id={c.id} (empty after clean)")
                continue

            if self._is_code_like_for_qual(cleaned_text):
                print(f"[QUAL DEBUG] Skipping chunk_id={c.id} (code-like after clean)")
                continue

            # Find similar sections from other companies (via RAG)
            similar_sections = self.find_similar_sections(cleaned_text)

            # Analyze tone with sector context
            tone_analysis = self.analyze_tone_with_context(cleaned_text, similar_sections)
            tone = tone_analysis["tone"]
            print(
                f"[QUAL DEBUG] chunk_id={c.id} tone={tone} "
                f"similar_companies={len(tone_analysis['similar_companies'])}"
            )

            signals: List[QualSignal] = []

            # --- Risk signal detection ----------------------------------------
            lowered = cleaned_text.lower()
            for keyword in risk_keywords:
                if keyword in lowered:
                    sentences = cleaned_text.split(". ")
                    for sentence in sentences:
                        if keyword in sentence.lower():
                            # Compare with similar companies that mention the same keyword
                            similar_risks = []
                            for section in similar_sections:
                                meta = getattr(section, "metadata", None) or {}
                                sec_text = (meta.get("text") or "").lower()
                                if keyword in sec_text:
                                    similar_risks.append(
                                        meta.get("company_name")
                                        or meta.get("company")
                                        or "Unknown"
                                    )

                            context = ""
                            if similar_risks:
                                context = (
                                    f" Similar concerns noted by: "
                                    f"{', '.join(similar_risks[:3])}"
                                )

                            signals.append(
                                QualSignal(
                                    label="risk",
                                    evidence=sentence.strip(),
                                    context=context,
                                )
                            )

            # --- Tone signal (use cleaned text snippet as evidence) -----------
            tone_snippet = cleaned_text[:300]
            signals.append(
                QualSignal(
                    label="tone",
                    evidence=tone_snippet,
                    context=tone_analysis["explanation"],
                )
            )

            # --- Similar companies payload -----------------------------------
            similar_companies_payload = [
                {
                    "company": t["company"],
                    "tone": t["tone"],
                    "similarity": t["score"],
                }
                for t in tone_analysis["similar_companies"]
            ]

            out.append(
                QualResult(
                    chunk_id=c.id,
                    tone=tone,
                    signals=signals,
                    similar_companies=similar_companies_payload,
                )
            )

        return out
