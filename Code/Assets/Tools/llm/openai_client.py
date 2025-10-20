"""Simple optional OpenAI LLM client used for qualitative explanations.

If OPENAI_API_KEY is not set or openai package is not available, the client falls back to
producing a deterministic explanation string constructed from signals and similar companies.
"""
import os
from typing import List, Dict


class LLMClient:
    def __init__(self, model: str = "gpt-3.5-turbo"):
        self.model = model
        self._client = None
        try:
            from openai import OpenAI
            api_key = os.getenv("OPENAI_API_KEY")
            if api_key:
                self._client = OpenAI(api_key=api_key)
        except Exception as e:
            print(f"Warning: Failed to initialize OpenAI client: {e}")
            self._client = None

    def explain_qualitative(self, company_name: str, qual_results: List[Dict], similar_companies: List[Dict]) -> str:
        """Return a natural-language explanation of qualitative signals and how conclusions were reached.

        qual_results: list of QualResult-like dicts (chunk_id, tone, signals, similar_companies)
        similar_companies: list of dicts with name/tone/similarity (may overlap with qual_results)
        """
        # If OpenAI available, call the API
        if self._client:
            prompt = self._build_prompt(company_name, qual_results, similar_companies)
            try:
                resp = self._client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": "You are an analyst assistant."},
                        {"role": "user", "content": prompt}
                    ],
                    max_tokens=512,
                    temperature=0.2
                )
                return resp.choices[0].message.content.strip()
            except Exception as e:
                print(f"Warning: OpenAI API call failed: {e}")
                # fallback to deterministic
                return self._deterministic_explanation(company_name, qual_results, similar_companies)

        return self._deterministic_explanation(company_name, qual_results, similar_companies)

    def _build_prompt(self, company_name: str, qual_results: List[Dict], similar_companies: List[Dict]) -> str:
        parts = [f"Provide a concise analytic explanation for {company_name}.\n\n"]
        parts.append("Observed qualitative signals and evidence:\n")
        for qr in qual_results:
            parts.append(f"Chunk {qr.get('chunk_id')}: tone={qr.get('tone')}\n")
            for s in qr.get('signals', []):
                ctx = f" (context: {s.get('context')})" if s.get('context') else ""
                parts.append(f" - {s.get('label')}: {s.get('evidence')}{ctx}\n")
        if similar_companies:
            parts.append("\nComparative context from similar companies:\n")
            for sc in similar_companies:
                parts.append(f" - {sc.get('name')}: tone={sc.get('tone')}, similarity={sc.get('similarity')}\n")
        parts.append("\nExplain how the conclusion (tone and risks) was reached and cite which chunks and similar companies were used.")
        return "".join(parts)

    def _deterministic_explanation(self, company_name: str, qual_results: List[Dict], similar_companies: List[Dict]) -> str:
        # Build a simple explanation string describing signals and references
        lines = [f"Qualitative explanation for {company_name}:\n"]
        tone_counts = {"positive": 0, "neutral": 0, "negative": 0}
        for qr in qual_results:
            tone = qr.get('tone', 'neutral')
            tone_counts[tone] = tone_counts.get(tone, 0) + 1
            lines.append(f"Chunk {qr.get('chunk_id')}: tone={tone}\n")
            for s in qr.get('signals', []):
                ctx = f" (noted in: {s.get('context')})" if s.get('context') else ""
                lines.append(f" - {s.get('label')}: {s.get('evidence')}{ctx}\n")
        majority = max(tone_counts.items(), key=lambda x: x[1])[0]
        lines.append(f"\nOverall tone: {majority}. This is based on the chunk-level tones and the signals above.\n")
        if similar_companies:
            lines.append("Comparative context: similar companies with notes:\n")
            for sc in similar_companies:
                lines.append(f" - {sc.get('name')}: tone={sc.get('tone')}, similarity={sc.get('similarity')}\n")
        return "".join(lines)
