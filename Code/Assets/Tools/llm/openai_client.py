"""
LLM client for qualitative + RAG-powered 10-K explanations.

- Uses OpenAI chat completions (gpt-4.1-mini by default).
- `explain_qualitative`: legacy chunk-only explanation.
- `explain_company_with_rag`: full-company explanation that uses:
    - qualitative chunk signals,
    - financial KPIs,
    - RAG chunks from Pinecone (risk factors, market risk, financial statements),
    - similar companies.
"""

from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None  # type: ignore[misc]


class LLMClient:
    def __init__(self, model: str = "gpt-4.1-mini") -> None:
        """
        :param model: OpenAI chat model name (default: gpt-4.1-mini).
        """
        self.model: str = model
        self._client: Optional[Any] = None

        api_key = os.getenv("OPENAI_API_KEY")
        if OpenAI is not None and api_key:
            try:
                self._client = OpenAI(api_key=api_key)
            except Exception as e:
                print(f"Warning: failed to initialize OpenAI client: {e}")
                self._client = None
        else:
            if not api_key:
                print("Warning: OPENAI_API_KEY not set; LLMClient will use deterministic fallback.")
            if OpenAI is None:
                print("Warning: openai package not installed; LLMClient will use deterministic fallback.")

    # ────────────────────────────────────────────────────────────────────────
    # Legacy qualitative-only explanation
    # ────────────────────────────────────────────────────────────────────────

    def explain_qualitative(
        self,
        company_name: str,
        qual_results: List[Dict[str, Any]],
        similar_companies: List[Dict[str, Any]],
    ) -> str:
        """
        Return a natural-language explanation of qualitative signals and how conclusions were reached.

        qual_results: list of QualResult-like dicts (chunk_id, tone, signals, similar_companies)
        similar_companies: list of dicts with name/tone/similarity (may overlap with qual_results)
        """
        if self._client is None:
            return self._deterministic_explanation(company_name, qual_results, similar_companies)

        prompt = self._build_qual_prompt(company_name, qual_results, similar_companies)
        try:
            resp = self._client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are an analyst assistant for 10-K filings."},
                    {"role": "user", "content": prompt},
                ],
                max_tokens=512,
                temperature=0.2,
            )
            return resp.choices[0].message.content.strip()
        except Exception as e:
            print(f"Warning: OpenAI API call failed in explain_qualitative: {e}")
            return self._deterministic_explanation(company_name, qual_results, similar_companies)

    def _build_qual_prompt(
        self,
        company_name: str,
        qual_results: List[Dict[str, Any]],
        similar_companies: List[Dict[str, Any]],
    ) -> str:
        parts: List[str] = [f"Provide a concise analytic explanation for {company_name}.\n\n"]
        parts.append("Observed qualitative signals and evidence:\n")
        for qr in qual_results:
            parts.append(f"Chunk {qr.get('chunk_id')}: tone={qr.get('tone')}\n")
            for s in qr.get("signals", []):
                ctx = f" (context: {s.get('context')})" if s.get("context") else ""
                parts.append(f" - {s.get('label')}: {s.get('evidence')}{ctx}\n")
        if similar_companies:
            parts.append("\nComparative context from similar companies:\n")
            for sc in similar_companies:
                parts.append(
                    f" - {sc.get('name')}: tone={sc.get('tone')}, similarity={sc.get('similarity')}\n"
                )
        parts.append(
            "\nExplain how the overall tone and key risks were reached from these signals. "
            "Start with one or two sentences summarizing the tone and main risk themes."
        )
        return "".join(parts)

    def _deterministic_explanation(
        self,
        company_name: str,
        qual_results: List[Dict[str, Any]],
        similar_companies: List[Dict[str, Any]],
    ) -> str:
        lines: List[str] = [f"Qualitative explanation for {company_name}:\n"]
        tone_counts: Dict[str, int] = {"positive": 0, "neutral": 0, "negative": 0}
        for qr in qual_results:
            tone = qr.get("tone", "neutral")
            tone_counts[tone] = tone_counts.get(tone, 0) + 1
            lines.append(f"Chunk {qr.get('chunk_id')}: tone={tone}\n")
            for s in qr.get("signals", []):
                ctx = f" (noted in: {s.get('context')})" if s.get("context") else ""
                lines.append(f" - {s.get('label')}: {s.get('evidence')}{ctx}\n")

        majority = max(tone_counts.items(), key=lambda x: x[1])[0]
        lines.append(f"\nOverall tone: {majority}. This is based on the chunk-level tones and the signals above.\n")
        if similar_companies:
            lines.append("\nComparative context: similar companies with notes:\n")
            for sc in similar_companies:
                lines.append(
                    f" - {sc.get('name')}: tone={sc.get('tone')}, similarity={sc.get('similarity')}\n"
                )
        return "".join(lines)

    # ────────────────────────────────────────────────────────────────────────
    # Full company-level explanation with RAG
    # ────────────────────────────────────────────────────────────────────────

    # ────────────────────────────────────────────────────────────────────────
    # Full company-level explanation with RAG
    # ────────────────────────────────────────────────────────────────────────

    def explain_company_with_rag(
        self,
        *,
        company_name: str,
        cik: str,
        accession: str,
        key_tone: str,
        risks: List[str],
        financials: Dict[str, Dict[str, Any]],
        qual_results: List[Dict[str, Any]],
        similar_companies: List[Dict[str, Any]],
        rag_chunks: List[Dict[str, Any]],
    ) -> str:
        """
        Full-company explanation using:
        - qualitative chunk signals,
        - quantitative KPIs,
        - RAG chunks from Pinecone (risk, market risk, financial statements),
        - similar companies.

        This is what drives `llm_explanation` in SummaryReport.
        """

        # ── Group RAG chunks by section (Item 1A / 7A / 8 / other) ─────────
        rag_by_section: Dict[str, List[str]] = {
            "item_1a": [],
            "item_7a": [],
            "item_8": [],
            "other": [],
        }

        for ch in rag_chunks:
            section_raw = (ch.get("section") or ch.get("content_type") or "").lower()
            text = (ch.get("text") or "").replace("\n", " ")
            if len(text) > 1000:
                text = text[:1000] + "..."

            if "item_1a" in section_raw:
                rag_by_section["item_1a"].append(text)
            elif "item_7a" in section_raw:
                rag_by_section["item_7a"].append(text)
            elif "item_8" in section_raw:
                rag_by_section["item_8"].append(text)
            else:
                rag_by_section["other"].append(text)

        def _block(snips: List[str], label: str) -> str:
            if not snips:
                return f"No {label} chunks retrieved."
            lines: List[str] = []
            for i, t in enumerate(snips[:3], 1):
                lines.append(f"{i}. {t}")
            return "\n".join(lines)

        item1a_block = _block(rag_by_section["item_1a"], "Item 1A risk-factor")
        item7a_block = _block(rag_by_section["item_7a"], "Item 7A market-risk")
        item8_block = _block(rag_by_section["item_8"], "Item 8 financial-statement")
        other_block = _block(rag_by_section["other"], "other 10-K")

        # ── Financial KPI block (from structured 'financials') ─────────────
        fin_lines: List[str] = []
        for k, v in financials.items():
            raw = v.get("raw")
            if raw:
                fin_lines.append(f"- {k}: {raw}")
        fin_block = "\n".join(fin_lines) if fin_lines else "No financial KPIs available."

        # ── Extracted high-level risk evidences (from QualitativeAgent) ─────
        risk_block = "; ".join(risks) if risks else "No specific risk evidences extracted."

        # ── Qualitative chunk summary (tones + signals) ─────────────────────
        qual_lines: List[str] = []
        for qr in qual_results[:6]:
            tone = qr.get("tone", "neutral")
            sig_parts: List[str] = []
            for s in qr.get("signals", [])[:3]:
                lbl = s.get("label")
                ev = s.get("evidence")
                if lbl and ev:
                    sig_parts.append(f"{lbl}: {ev}")
            sig_str = "; ".join(sig_parts) if sig_parts else "no signals"
            qual_lines.append(
                f"- chunk={qr.get('chunk_id')}, tone={tone}, signals=[{sig_str}]"
            )
        qual_block = "\n".join(qual_lines) if qual_lines else "No qualitative chunk info."

        # ── Similar companies block ─────────────────────────────────────────
        sim_lines: List[str] = []
        for sc in similar_companies[:5]:
            name = sc.get("name", "Unknown")
            tone = sc.get("tone", "neutral")
            sim = sc.get("similarity")
            if sim is not None:
                sim_lines.append(f"- {name}: tone={tone}, similarity={sim}")
            else:
                sim_lines.append(f"- {name}: tone={tone}")
        sim_block = "\n".join(sim_lines) if sim_lines else "No similar companies retrieved."

        # ── Fallback if no OpenAI client ────────────────────────────────────
        if self._client is None:
            return self._deterministic_company_with_rag(
                company_name=company_name,
                cik=cik,
                accession=accession,
                key_tone=key_tone,
                risks=risk_block,
                fin_block=fin_block,
            )

        # ── System message: what the model is & what it MUST do ─────────────
        system_msg = (
            "You are a financial analyst who summarizes U.S. SEC Form 10-K filings.\n"
            "You receive:\n"
            "- Basic company identifiers (name, CIK, accession)\n"
            "- A high-level tone label\n"
            "- Structured financial metrics (revenue, net income, cash flows, assets, liabilities, ratios)\n"
            "- Optional qualitative risk signals extracted from 10-K text\n"
            "- RAG chunks already grouped by section: Item 1A (Risk Factors), "
            "Item 7A (Quantitative and Qualitative Disclosures about Market Risk), "
            "Item 8 (Financial Statements and Supplementary Data), and 'other'.\n\n"
            "Your job is to write a grounded, section-aware explanation.\n"
            "IMPORTANT:\n"
            "- Do NOT invent numbers. Only use numeric values that appear in the financial metrics block below.\n"
            "You MUST ground your narrative in the provided quantitative metrics when they exist.\n"
            "- When discussing Item 1A, Item 7A, or Item 8, rely on the corresponding RAG snippet blocks.\n"
            "- If a block says no chunks were retrieved for a section, explicitly say that in your explanation.\n"
            "- Do NOT mention RAG, embeddings, Pinecone, or any internal tooling."
        )

        # ── User message: all context + explicit instructions ───────────────
        user_msg = f"""
Company: {company_name}
CIK: {cik}
Accession: {accession}

Final tone label: {key_tone}

Extracted risk evidences (from qualitative analysis):
{risk_block}

Structured financial metrics (DO NOT change these numbers):
{fin_block}

Qualitative chunk summary (tones & signals):
{qual_block}

Item 1A RAG snippets (Risk Factors):
{item1a_block}

Item 7A RAG snippets (Quantitative and Qualitative Disclosures about Market Risk):
{item7a_block}

Item 8 RAG snippets (Financial Statements and Supplementary Data):
{item8_block}

Other 10-K RAG snippets:
{other_block}

Similar companies (optional context):
{sim_block}

TASK:

Using ONLY the information above, write a structured narrative with the following parts:

1. Risk Factors (Item 1A)
   - Explicitly refer to this as "Item 1A" in your prose.
   - Summarize 3–6 concrete risk themes based primarily on the Item 1A snippets.
   - Examples of themes: macroeconomic conditions, global supply chain concentration, tariffs, regulatory change,
     geopolitical tensions, natural disasters, climate-related disruptions, etc.
   - If the Item 1A block says no chunks were retrieved, say so and only discuss risks at a generic, high level.

2. Market Risk (Item 7A)
   - Explicitly refer to this as "Item 7A".
   - Focus on exposures to interest rates, foreign exchange rates, commodity prices, or other market risks based on
     the Item 7A snippets.
   - If the text provides concrete numbers (e.g., impact of a 100 basis-point interest-rate move, VAR estimates),
     restate them as given.
   - If the Item 7A block says no chunks were retrieved, clearly state that and only describe market risk in general terms.

3. Financial Statements & Performance (Items 7 & 8)
   - Explicitly refer to "Item 8" when describing financial statements.
   - Use ONLY the numeric values from the financial metrics block when discussing revenue, net income, margins,
     cash flows, leverage, and asset base.
   - Interpret what these numbers imply about scale, profitability, cash generation, and leverage.
   - Do NOT fabricate any additional metrics, years, or ratios beyond what is provided.

4. Tone & Overall Assessment
   - Explain why the overall tone label is "{key_tone}" instead of being clearly bullish or clearly distressed.
   - Tie this explanation to both the risk discussions (Item 1A & Item 7A) and the financial performance.

5. Peer & Macro Context (Generic)
   - Without naming specific peers, briefly compare this risk/return profile to what is typical for large public
     companies in a similar sector (e.g., leverage higher/lower than typical, margins stronger/weaker than average,
     risk disclosures more/less extensive than usual).

Formatting rules:
- Write in clear, well-structured paragraphs, not bullet points.
- Do NOT mention RAG, Pinecone, embeddings, or internal tools.
- Do NOT claim access to any information beyond what you see above.
"""

        try:
            resp = self._client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_msg},
                    {"role": "user", "content": user_msg},
                ],
                max_tokens=900,
                temperature=0.2,
            )
            return resp.choices[0].message.content.strip()
        except Exception as e:
            print(f"Warning: OpenAI API call failed in explain_company_with_rag: {e}")
            return self._deterministic_company_with_rag(
                company_name=company_name,
                cik=cik,
                accession=accession,
                key_tone=key_tone,
                risks=risk_block,
                fin_block=fin_block,
            )

    @staticmethod
    def _deterministic_company_with_rag(
        *,
        company_name: str,
        cik: str,
        accession: str,
        key_tone: str,
        risks: str,
        fin_block: str,
    ) -> str:
        """
        Fallback explanation when the OpenAI client is unavailable.
        Does NOT use RAG content but still references tone and basic financials.
        """
        lines: List[str] = [
            f"Explanation for {company_name} (CIK {cik}, Accession {accession}):",
            "",
            f"Overall tone: {key_tone}",
            "",
            "Risk overview (Item 1A and Item 7A, high level):",
            risks,
            "",
            "Key financial metrics (Items 7 & 8):",
            fin_block,
            "",
            "This fallback explanation is based on extracted risk themes and structured financial metrics only, ",
            "since the language model API was not available.",
        ]
        return "\n".join(lines)
