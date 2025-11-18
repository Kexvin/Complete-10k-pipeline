"""
Run the 10-K analysis pipeline pulling EVERYTHING from the SEC APIs
(text + quantitative facts), no Kaggle dataset required.

Usage example:
    PYTHONPATH="$PWD" python3 Workflow/10K_Analysis/run_from_sec.py \
        --cik 0000003116 \
        --limit 1 \
        --pinecone-collection knowledgepinecone
"""

import os
import json
import argparse
from datetime import datetime
from typing import List

from dotenv import load_dotenv
import pandas as pd  # kept in case you later re-add CSV-driven flows

# ── Pipeline core ──────────────────────────────────────────────────────────────
from Code.Assets.Tools.core.pipeline import Pipeline

from Code.Agents.tenk_analyst.tenk_analyst.stages.identify_stage import IdentifyStage
from Code.Agents.tenk_analyst.tenk_analyst.stages.fetch_stage import FetchStage
from Code.Agents.tenk_analyst.tenk_analyst.stages.chunk_stage import ChunkStage
from Code.Agents.tenk_analyst.tenk_analyst.stages.route_stage import RouteStage
from Code.Agents.tenk_analyst.tenk_analyst.stages.qual_stage import QualStage
from Code.Agents.tenk_analyst.tenk_analyst.stages.quant_stage import QuantStage
from Code.Agents.tenk_analyst.tenk_analyst.stages.summarize_stage import SummarizeStage

# ── Agents + tools ────────────────────────────────────────────────────────────
from Code.Agents.tenk_analyst.tenk_analyst.agents.qualitative import QualitativeAgent
from Code.Agents.tenk_analyst.tenk_analyst.agents.quantitative import QuantitativeAgent
from Code.Agents.tenk_analyst.tenk_analyst.agents.rag_agent import RagAgent

from Code.Assets.Tools.nlp.finbert import FinBert
from Code.Assets.Tools.io.sec_client import (
    get_company_industry as get_sic_info,
    get_company_profile,
)
from Code.Assets.Tools.io.sec_facts_client import build_financials_from_sec_facts

# ── Canonical artifact classes ────────────────────────────────────────────────
from Knowledge.Schema.Artifacts.raw_text import RawTextArtifact
from Knowledge.Schema.Artifacts.routed import RoutedChunksArtifact
from Knowledge.Schema.Artifacts.qual_results import QualResultsArtifact
from Knowledge.Schema.Artifacts.quant_results import QuantResultsArtifact
from Knowledge.Schema.Artifacts.summary import SummaryArtifact

# ── Load environment (.env) ───────────────────────────────────────────────────
load_dotenv()

# ───────────────────────────────────────────────────────────────────────────────
# CLI argument parsing
# ───────────────────────────────────────────────────────────────────────────────

parser = argparse.ArgumentParser(
    description="Run 10-K analysis pipeline pulling filings & financials from SEC (no Kaggle)."
)
parser.add_argument(
    "--cik",
    action="append",
    required=True,
    help="CIK(s) to process. Can be passed multiple times, e.g. --cik 0000003116 --cik 0000001800",
)
parser.add_argument(
    "--limit",
    type=int,
    default=1,
    help="Number of CIKs from the provided list to process (default: 1)",
)
parser.add_argument(
    "--pinecone-collection",
    default="knowledgepinecone",
    help="Pinecone collection / index name (default: knowledgepinecone)",
)
args = parser.parse_args()

# Normalize CIKs and apply limit
ciks: List[str] = [str(c).zfill(10) for c in args.cik][: args.limit]

# ───────────────────────────────────────────────────────────────────────────────
# Main processing function
# ───────────────────────────────────────────────────────────────────────────────

def process_companies_from_sec(
    ciks: List[str],
    pinecone_collection: str = "knowledgepinecone",
) -> None:
    """Process one or more companies directly from SEC submissions + companyfacts."""
    print(">>> Running 10-K analysis pipeline from run_from_sec.py (SEC-only mode)")
    print(f"Processing {len(ciks)} companies from SEC (no Kaggle dataset).")

    # Output directory for JSON reports
    output_dir = "Data/Outputs/reports"
    os.makedirs(output_dir, exist_ok=True)

    # SEC user-agent (required by SEC)
    sec_user_agent = os.getenv("SEC_USER_AGENT", "YourName Contact@Email ExampleScript")

    for cik in ciks:
        print("\n" + "=" * 80)
        print(f"Processing CIK: {cik}")
        print("=" * 80)

        try:
            # ── Build pipelines ────────────────────────────────────────────
            base = Pipeline(
                [
                    IdentifyStage(),
                    FetchStage(),
                    ChunkStage(),
                    RouteStage(),
                ]
            )

            # Shared RAG agent (wraps the RAG tool)
            rag_agent = RagAgent(collection=pinecone_collection)

            qual = Pipeline([QualStage(QualitativeAgent(FinBert(heavy=True), rag_agent))])
            quant = Pipeline([QuantStage(QuantitativeAgent())])

            # ① Seed artifact: we give it just the CIK; IdentifyStage will choose latest 10-K
            seed: RawTextArtifact = RawTextArtifact(
                company_cik=cik,
                accession="",
                text="",
                sources=[],
            )

            # ── Run base pipeline: Identify → Fetch → Chunk → Route ────────
            print("Running base pipeline...")
            routed: RoutedChunksArtifact = base.run(
                seed,
                user_agent=sec_user_agent,
                rag_index=True,
                rag_collection=pinecone_collection,
            )
            assert isinstance(
                routed, RoutedChunksArtifact
            ), f"Expected RoutedChunksArtifact, got {type(routed)}"

            # ── Run qualitative + quantitative analysis ────────────────────
            print("Running analysis pipelines...")
            qual_result: QualResultsArtifact = qual.run(routed)
            quant_result: QuantResultsArtifact = quant.run(routed)
            assert isinstance(qual_result, QualResultsArtifact)
            assert isinstance(quant_result, QuantResultsArtifact)

            # ── Summarize into SummaryArtifact ─────────────────────────────
            print("Generating summary...")
            final: SummaryArtifact = SummarizeStage().run((qual_result, quant_result))
            assert isinstance(final, SummaryArtifact)

            # ── Pull official company profile (name + SIC + industry) ─────
            company_name = f"CIK {cik}"
            sic = None
            industry = None

            try:
                prof_name, prof_sic, prof_industry = get_company_profile(
                    cik, user_agent=sec_user_agent
                )
                if prof_name:
                    company_name = prof_name
                sic = prof_sic
                industry = prof_industry
            except Exception as prof_err:
                print(f"Warning: failed to fetch SEC profile for CIK {cik}: {prof_err}")
                # As a fallback, try the older helper for SIC only
                try:
                    sic, industry = get_sic_info(cik, user_agent=sec_user_agent)
                except Exception as sic_err:
                    print(f"Warning: failed to fetch SIC/industry for CIK {cik}: {sic_err}")
                # If we still don't have a name, fall back to LLM name if present
                if final.report and getattr(final.report, "company_name", ""):
                    company_name = final.report.company_name

            # Propagate corrected company name back into the summary report
            if final.report:
                final.report.company_name = company_name

            if sic or industry:
                print(f"SIC info for CIK {cik}: sic={sic}, sicDescription={industry}")

            # ── Persist SummaryArtifact to JSON report ─────────────────────
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            report_file = os.path.join(output_dir, f"{cik}_{timestamp}_report.txt")

            report = final.report

            # ── Merge & dedupe sources from report + artifacts ─────────────
            combined_sources = []

            # 1) Start with report-level sources (from SummarizerAgent), if any
            if report and getattr(report, "sources", None):
                for src in report.sources:
                    # assume dict-like; normalize fields
                    if isinstance(src, dict):
                        combined_sources.append(
                            {
                                "type": src.get("type"),
                                "name": src.get("name"),
                                "url": src.get("url"),
                                "version": src.get("version"),
                                "retrieved_at": src.get("retrieved_at"),
                                "notes": src.get("notes"),
                            }
                        )

            # 2) Add artifact-level sources (Qual + Quant) if not already present
            existing_keys = {
                (s.get("type"), s.get("name"), s.get("url")) for s in combined_sources
            }

            for s in (final.sources or []):
                # Dataclass DataSource → dict
                if hasattr(s, "__dict__"):
                    s_dict = {
                        "type": getattr(s, "type", None),
                        "name": getattr(s, "name", None),
                        "url": getattr(s, "url", None),
                        "version": getattr(s, "version", None),
                        "retrieved_at": getattr(s, "retrieved_at", None),
                        "notes": getattr(s, "notes", None),
                    }
                else:
                    # already dict-like
                    s_dict = {
                        "type": s.get("type"),
                        "name": s.get("name"),
                        "url": s.get("url"),
                        "version": s.get("version"),
                        "retrieved_at": s.get("retrieved_at"),
                        "notes": s.get("notes"),
                    }

                key = (s_dict.get("type"), s_dict.get("name"), s_dict.get("url"))
                if key not in existing_keys:
                    combined_sources.append(s_dict)
                    existing_keys.add(key)

            report_data = {
                "company_name": company_name,
                "cik": cik,
                "accession": final.accession,
                "key_tone": report.key_tone if report else "N/A",
                "tone_explanation": report.tone_explanation if report else "",
                "risks": report.risks if report else [],
                "financials": report.financials if report else {},
                "llm_explanation": report.llm_explanation if report else "",
                "similar_companies": report.similar_companies if report else [],
                "qualitative_analysis": [
                    {
                        "chunk_id": q.chunk_id,
                        "tone": q.tone,
                        "signals": [
                            {
                                "label": s.label,
                                "evidence": s.evidence,
                                "context": s.context,
                            }
                            for s in q.signals
                        ],
                        "similar_companies": [
                            {
                                "name": sc.company,
                                "tone": sc.tone,
                                "similarity": sc.similarity,
                            }
                            for sc in q.similar_companies
                        ],
                    }
                    for q in (report.qualitative_analysis if (report and report.qualitative_analysis) else [])
                ],
                # Use merged + deduped sources here
                "sources": combined_sources,
                "sic": sic,
                "industry": industry,
            }

            with open(report_file, "w") as f:
                json.dump(report_data, f, indent=2, default=str)
            print(f"Report saved to: {report_file}")

            # ── Build rich raw_text summary for Pinecone vector ────────────
            fin = report_data["financials"] or {}
            rev_val = (fin.get("revenue") or {}).get("value")
            ni_val = (fin.get("net_income") or {}).get("value")
            ocf_val = (fin.get("operating_cash_flow") or {}).get("value")
            capex_val = (fin.get("capital_expenditures") or {}).get("value")
            assets_val = (fin.get("total_assets") or {}).get("value")
            fcf_val = (fin.get("free_cash_flow") or {}).get("value")

            llm_expl = report_data["llm_explanation"] or ""

            qa_list = report_data["qualitative_analysis"] or []
            qa_lines = []
            for qa in qa_list[:5]:
                tone = qa.get("tone", "neutral")
                ev = ""
                if qa.get("signals"):
                    ev = qa["signals"][0].get("evidence", "")
                qa_lines.append(
                    f"Chunk {qa.get('chunk_id')}: tone={tone}, snippet={ev}"
                )
            qa_text = "\n".join(qa_lines)

            raw_text = (
                f"Company: {company_name} (CIK {cik}, Accession {final.accession})\n"
                f"Industry: {industry}\n"
                f"Overall tone: {report_data['key_tone']}\n"
                f"Tone explanation: {report_data['tone_explanation']}\n\n"
                "LLM summary:\n"
                f"{llm_expl}\n\n"
                "Core financials:\n"
                f"revenue: {rev_val} USD\n"
                f"net_income: {ni_val} USD\n"
                f"operating_cash_flow: {ocf_val} USD\n"
                f"free_cash_flow: {fcf_val} USD\n"
                f"capital_expenditures: {capex_val} USD\n"
                f"total_assets: {assets_val} USD\n\n"
                "Qualitative analysis (sample chunks):\n"
                f"{qa_text}\n"
            )

            # ── Index report summary into Pinecone ─────────────────────────
            try:
                doc_id = f"{cik}_{final.accession}"
                metadata = {
                    "company_name": company_name,
                    "cik": cik,
                    "accession": final.accession,
                    "key_tone": report_data["key_tone"],
                    "industry": industry,
                    "sic": sic,
                    "content_type": "10k_report_summary",
                    "revenue": rev_val,
                    "net_income": ni_val,
                    "operating_cash_flow": ocf_val,
                    "free_cash_flow": fcf_val,
                    "capital_expenditures": capex_val,
                    "total_assets": assets_val,
                    "report_json": json.dumps(report_data),
                }

                rag_agent.index(
                    ids=[doc_id],
                    texts=[raw_text],
                    metadatas=[metadata],
                )
                print("Indexed report into Pinecone as 10-K summary vector.")
            except Exception as index_err:
                print(f"Warning: failed to index report into Pinecone: {index_err}")

            # ── Human-readable CLI summary ────────────────────────────────
            print("\nAnalysis Summary:")
            print("----------------------------------------")
            print(f"Company: {company_name}")
            print(f"CIK: {cik}")
            if fin:
                print("\nFinancial Highlights:")
                for k, v in fin.items():
                    print(f"- {k}: {v.get('raw')}")

        except Exception as e:
            print(f"Error processing CIK {cik}: {str(e)}")
            continue

        print(f"\nCompleted processing: {company_name} ({cik})")


# ───────────────────────────────────────────────────────────────────────────────
# Script entrypoint
# ───────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    process_companies_from_sec(ciks, args.pinecone_collection)
