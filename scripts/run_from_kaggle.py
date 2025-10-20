"""Run the 10-K pipeline using the real Kaggle companyfacts.csv.

Usage:
    python scripts/run_from_kaggle.py --limit 1
"""
import os
import json
import argparse
from datetime import datetime
import pandas as pd
from Code.Assets.Tools.core.pipeline import Pipeline
from Knowledge.Schema.Artifacts.raw_text import RawTextArtifact
from Code.Agents.tenk_analyst.tenk_analyst.stages.identify_stage import IdentifyStage
from Code.Agents.tenk_analyst.tenk_analyst.stages.fetch_stage import FetchStage
from Code.Agents.tenk_analyst.tenk_analyst.stages.chunk_stage import ChunkStage
from Code.Agents.tenk_analyst.tenk_analyst.stages.route_stage import RouteStage
from Code.Agents.tenk_analyst.tenk_analyst.stages.qual_stage import QualStage
from Code.Agents.tenk_analyst.tenk_analyst.stages.quant_stage import QuantStage
from Code.Agents.tenk_analyst.tenk_analyst.stages.summarize_stage import SummarizeStage
from Code.Agents.tenk_analyst.tenk_analyst.agents.controller import ControllerAgent
from Code.Agents.tenk_analyst.tenk_analyst.agents.qualitative import QualitativeAgent
from Code.Agents.tenk_analyst.tenk_analyst.agents.quantitative import QuantitativeAgent
from Code.Assets.Tools.nlp.finbert import FinBert
from Code.Assets.Tools.rag.pinecone_client import RAG
from dotenv import load_dotenv
load_dotenv()


def process_company_facts(csv_path: str, limit: int = 1, pinecone_collection: str = "knowledgepinecone"):
    """Process companies from the Kaggle dataset."""
    print(f"Loading company data from: {csv_path}")
    
    # Read unique companies from companyfacts.csv
    df = pd.read_csv(csv_path)
    companies = df[['cik', 'entityName']].drop_duplicates()
    companies = companies.head(limit)
    
    # Create output directory for reports
    output_dir = "Data/Outputs/reports"
    os.makedirs(output_dir, exist_ok=True)
    
    print(f"\nProcessing {len(companies)} companies:")
    
    for _, company in companies.iterrows():
        cik = str(company['cik']).zfill(10)
        name = company['entityName']
        print(f"\n{'='*80}")
        print(f"Processing: {name} (CIK: {cik})")
        print(f"{'='*80}")
        
        try:
            # Set up pipeline components
            base = Pipeline([IdentifyStage(), FetchStage(), ChunkStage(), RouteStage(ControllerAgent())])
            rag_client = RAG(collection=pinecone_collection)
            qual = Pipeline([QualStage(QualitativeAgent(FinBert(), rag_client))])
            quant = Pipeline([QuantStage(QuantitativeAgent())])
            
            # Create seed artifact
            seed = RawTextArtifact(company_cik=cik, accession="", text="", sources=[])
            
            # Run the pipeline stages
            print("Running base pipeline...")
            routed = base.run(seed, 
                            user_agent=os.getenv("SEC_USER_AGENT"),
                            rag_index=True,
                            rag_collection="knowledgepinecone")
            
            print("Running analysis pipelines...")
            qual_result = qual.run(routed)
            quant_result = quant.run(routed)
            
            # Generate final summary
            print("Generating summary...")
            final = SummarizeStage().run((qual_result, quant_result))
            
            # Save report to file
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            report_file = os.path.join(output_dir, f"{cik}_{timestamp}_report.txt")
            
            # Convert report to readable format
            report_data = {
                "company_name": name,
                "cik": cik,
                "accession": final.accession,
                "key_tone": final.report.key_tone if final.report else "N/A",
                "tone_explanation": final.report.tone_explanation if final.report else "",
                "risks": final.report.risks if final.report else [],
                "financials": final.report.financials if final.report else [],
                "llm_explanation": final.report.llm_explanation if final.report else "",
                "similar_companies": final.report.similar_companies if final.report else [],
                "qualitative_analysis": [
                    {
                        "chunk_id": q.chunk_id,
                        "tone": q.tone,
                        "signals": [{"label": s.label, "evidence": s.evidence, "context": s.context} for s in q.signals],
                        "similar_companies": [{"name": sc.company, "tone": sc.tone, "similarity": sc.similarity} for sc in q.similar_companies]
                    } for q in final.report.qualitative_analysis
                ] if final.report else [],
                "sources": [{
                    "type": s.type,
                    "name": s.name,
                    "url": s.url,
                    "version": s.version,
                    "retrieved_at": s.retrieved_at,
                    "notes": s.notes
                } for s in final.sources]
            }
            
            # Write report
            with open(report_file, 'w') as f:
                json.dump(report_data, f, indent=2, default=str)
            print(f"Report saved to: {report_file}")
            
            # Print summary
            print("\nAnalysis Summary:")
            print("-" * 40)
            print(f"Company: {name}")
            print(f"CIK: {cik}")
            if final.report.key_tone:
                print(f"Key Tone: {final.report.key_tone}")
            if final.report.risks:
                print("\nTop Risks:")
                for risk in final.report.risks:
                    print(f"- {risk}")
            if final.report.financials:
                print("\nFinancial Highlights:")
                for highlight in final.report.financials:
                    print(f"- {highlight}")
            
        except Exception as e:
            print(f"Error processing {name}: {str(e)}")
            continue
        
        print(f"\nCompleted processing: {name}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Process companies from Kaggle companyfacts.csv")
    parser.add_argument("--csv", default="Data/Primary/kaggle_facts/companyfacts.csv",
                       help="Path to Kaggle companyfacts.csv")
    parser.add_argument("--limit", type=int, default=1,
                       help="Maximum number of companies to process")
    parser.add_argument("--pinecone-collection", type=str, default="knowledgepinecone", help="Pinecone collection name for RAG client")
    args = parser.parse_args()

    # Verify environment variables
    if not os.getenv("SEC_USER_AGENT"):
        raise ValueError("SEC_USER_AGENT environment variable must be set")
    if not os.getenv("PINECONE_API_KEY"):
        raise ValueError("PINECONE_API_KEY environment variable must be set")

    # Process companies
    process_company_facts(args.csv, args.limit, args.pinecone_collection)