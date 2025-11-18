# 10-K Form Analysis Agent

A complete, SEC-only pipeline for analyzing 10-K filings using:

- **SEC EDGAR APIs** for filings and company facts  
- **FinBERT** for financial tone & qualitative signals  
- **Pinecone-backed RAG** for comparative context across filings  
- **LLM (optional)** for natural-language explanations  

All text and numeric data comes directly from the SEC. No Kaggle dependency.

---

## 🧠 High-Level Overview

For each CIK you provide, the pipeline:

1. **Finds the latest 10-K** for that CIK via SEC submissions.
2. **Fetches the 10-K HTML**, cleans it, and optionally indexes it into Pinecone.
3. **Chunks the filing** into key sections (Item 1A, 7A, 8) and paragraph-level segments.
4. **Routes chunks** for qualitative and quantitative analysis.
5. **Runs qualitative analysis** using FinBERT and (optionally) RAG retrieval.
6. **Runs quantitative analysis** using SEC `companyfacts` data and financial ratios.
7. **Builds a `SummaryArtifact`** and writes a JSON report to `Data/Outputs/reports/`.
8. **Indexes a summary text into Pinecone** so future RAG queries can hit the report.

The pipeline is artifact-based: each stage consumes and produces typed artifacts defined in `Knowledge/Schema/Artifacts`.

---

## 🔁 Pipeline Workflow

### Mermaid workflow diagram

```mermaid
flowchart TD
  subgraph Data_Sources[Data Sources]
    SEC[SEC EDGAR\nsubmissions + companyfacts]
  end

  %% Base pipeline
  SEC --> A[Identify Stage\n(find latest 10-K for CIK)]
  A --> B[Fetch Stage\n(download 10-K HTML\n+ optional RAG index)]
  B --> C[Chunk Stage\n(clean + extract Item 1A/7A/8)]
  C --> D[Route Stage\n(label routed chunks)]

  %% Parallel analysis
  D --> E[Qualitative Stage\nFinBERT tone + risk signals\n+ optional RAG retrieval]
  D --> F[Quantitative Stage\nSEC companyfacts + ratios]

  %% RAG index
  subgraph RAG[Pinecone Vector DB]
    J[(knowledgepinecone)]
  end

  B -. index filing text .-> J
  E -. embed query .-> J
  J -. top-k similar .-> E
  H -. index report summary .-> J

  %% Summarize
  E --> G[Summarize Stage\ncombine qual + quant]
  F --> G
  G --> H((SummaryArtifact\nreport JSON))

  H --> I[Report file\nData/Outputs/reports]
