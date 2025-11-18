# 10-K Analyst

A multi-stage pipeline for analyzing SEC 10-K filings using NLP, financial analysis, and RAG (Retrieval-Augmented Generation) capabilities.

## Overview

This system automatically processes 10-K filings through seven stages:
1. **Identify** - Locate the most recent 10-K filing
2. **Fetch** - Download and clean the filing text
3. **Chunk** - Extract and segment key sections
4. **Route** - Classify chunks for appropriate analysis
5. **Qualitative** - Perform sentiment and risk analysis
6. **Quantitative** - Extract and compute financial metrics
7. **Summarize** - Generate comprehensive reports with RAG indexing

## Features

- **Automated SEC Filing Retrieval** - Fetches the latest 10-K filings via SEC EDGAR API
- **Financial Analysis** - Extracts key metrics and computes derived ratios
- **Sentiment Analysis** - Uses FinBERT for tone classification
- **RAG Integration** - Semantic search across filings using Pinecone
- **Comprehensive Reports** - JSON-formatted summaries with qualitative and quantitative insights

## Pipeline Stages

### Stage 1 – Identify
- **File:** `stages/identify_stage.py`
- **Input:** `RawTextArtifact` with `company_cik`
- **Process:** Fetches submission list, filters for 10-K forms, selects most recent filing
- **Output:** `RawTextArtifact` with `accession` number

### Stage 2 – Fetch
- **File:** `stages/fetch_stage.py`
- **Input:** `RawTextArtifact` with `company_cik` and `accession`
- **Process:** 
  - Downloads and cleans 10-K HTML
  - Optionally indexes full text into Pinecone (`rag_index=True`)
- **Output:** `RawTextArtifact` with complete filing text

### Stage 3 – Chunk
- **File:** `stages/chunk_stage.py`
- **Input:** `RawTextArtifact` (full text)
- **Process:**
  - Strips HTML and boilerplate
  - Extracts key sections (Risk Factors, Market Risk, Financial Statements)
  - Segments into paragraph-level chunks with UUIDs
- **Output:** `ChunksArtifact`

### Stage 4 – Route
- **File:** `stages/route_stage.py`
- **Input:** `ChunksArtifact`
- **Process:** Assigns routing labels based on section type
  - Risk Factors → qualitative-heavy
  - Market Risk → qualitative + quant context
  - Financial Statements → quant context
- **Output:** `RoutedChunksArtifact`

### Stage 5 – Qualitative
- **Files:** `stages/qual_stage.py`, `agents/qualitative.py`, `models/qualitative.py`
- **Input:** `RoutedChunksArtifact`
- **Process:**
  - **Tone Analysis:** Uses FinBERT for sentiment classification (positive, neutral, negative)
  - **RAG Retrieval:** Embeds chunk text and queries Pinecone for similar filings
  - **Signal Extraction:** Builds `QualSignal` objects with tone evidence and risk phrases
- **Output:** `QualResultsArtifact`

### Stage 6 – Quantitative
- **Files:** `stages/quant_stage.py`, `agents/quantitative.py`, `models/quantitative.py`
- **Input:** `RoutedChunksArtifact` and CIK
- **Process:**
  - Pulls numeric data from SEC CompanyFacts (Revenue, Net Income, Operating Cash Flow, etc.)
  - Computes derived metrics:
    - Free Cash Flow = OCF - CapEx
    - Debt Ratio = Liabilities / Assets
    - Net Margin = Net Income / Revenue
- **Output:** `QuantResultsArtifact`

### Stage 7 – Summarize
- **Files:** `stages/summarize_stage.py`, `agents/summarizer.py`, `models/summary.py`
- **Input:** `QualResultsArtifact` and `QuantResultsArtifact`
- **Process:**
  - Aggregates qualitative signals (key tone, risk bullets)
  - Formats quantitative metrics
  - Generates LLM explanation (optional, requires OpenAI API key)
  - Indexes rich text summary into Pinecone
  - Writes JSON report to `Data/Outputs/reports/{CIK}_{timestamp}_report.txt`
- **Output:** `SummaryArtifact`

## RAG System (Pinecone)

**Core Files:**
- Client: `Code/Assets/Tools/rag/pinecone_client.py`
- Agent wrapper: `Code/Agents/tenk_analyst/tenk_analyst/agents/rag_agent.py`

### What Gets Indexed?
- Full filing text (optional, in Fetch stage)
- Condensed summary text (in Summarize stage)

Each indexed item includes:
- **ID:** `{CIK}_{accession}`
- **Text:** Long-form content (filing or summary)
- **Metadata:** Company CIK, accession, tone, financial figures

### What Gets Retrieved?
During qualitative analysis, chunk text is embedded and sent to Pinecone, returning top-k semantically similar vectors for:
- Peer comparison
- Sector context
- Similar filing identification

## Data Sources

- **SEC EDGAR** - Submissions and 10-K filing content (`sec_client.py`)
- **SEC CompanyFacts** - XBRL numeric facts for quantitative KPIs (`sec_facts_client.py`)
- **FinBERT** - Financial sentiment model for chunk-level tone analysis
- **Pinecone** - Vector database for RAG capabilities
- **OpenAI** (Optional) - Natural-language explanations in Summarize stage

## Setup & Prerequisites

### 1. Create & Activate Virtual Environment

```bash
python -m venv .venv
source .venv/bin/activate        # macOS / Linux
# .venv\Scripts\activate         # Windows (PowerShell / cmd)
```

### 2. Install Dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### 3. Environment Variables

Create a `.env` file in the project root:

```bash
SEC_USER_AGENT="Your Name your.email@example.com"
PINECONE_API_KEY=your-pinecone-api-key
PINECONE_INDEX=knowledgepinecone

# Optional for LLM explanations
OPENAI_API_KEY=sk-...
```

**Note:** The SEC requires a proper User-Agent string.

## Running the Pipeline

**Main entry script:** `Workflow/10K_Analysis/run_from_sec.py`

Set `PYTHONPATH` to the repo root so imports work correctly.

### Single CIK

```bash
PYTHONPATH="$PWD" python3 Workflow/10K_Analysis/run_from_sec.py \
  --cik 0000077476 \
  --limit 1 \
  --pinecone-collection knowledgepinecone
```

### Multiple CIKs

```bash
PYTHONPATH="$PWD" python3 Workflow/10K_Analysis/run_from_sec.py \
  --cik 0000077476 \
  --cik 0000091767 \
  --limit 2 \
  --pinecone-collection knowledgepinecone
```

**Options:**
- `--cik` can be passed multiple times
- `--limit` truncates the list (e.g., pass 20 CIKs but only process the first 5)

### Wipe Pinecone Index

```bash
PYTHONPATH="$PWD" python3 Workflow/10K_Analysis/wipe_pinecone.py \
  --pinecone-collection knowledgepinecone
```

## Output Reports

Reports are saved to: `Data/Outputs/reports/{CIK}_{timestamp}_report.txt`

### Sample Report Structure

```json
{
  "company_name": "PEPSICO INC",
  "cik": "0000077476",
  "accession": "0000077476-25-000007",
  "key_tone": "neutral",
  "tone_explanation": "...",
  "risks": [
    "Textual risk bullet with evidence..."
  ],
  "financials": {
    "revenue": { "value": 91854000000, "raw": "Revenue: $91,854,000,000", "currency": "USD" },
    "net_income": { "value": 9578000000, "raw": "Net Income: $9,578,000,000", "currency": "USD" },
    "operating_cash_flow": { ... },
    "capital_expenditures": { ... },
    "total_assets": { ... },
    "total_liabilities": { ... },
    "free_cash_flow": { ... },
    "debt_ratio": { "value": 81.73, "raw": "Debt Ratio: 81.73%" },
    "net_margin": { "value": 10.43, "raw": "Net Margin: 10.43%" }
  },
  "llm_explanation": "Natural-language summary of tone + financials...",
  "similar_companies": [
    { "name": "0000091767", "tone": "neutral", "similarity": 0.16 }
  ],
  "qualitative_analysis": [
    {
      "chunk_id": "uuid",
      "tone": "neutral",
      "signals": [
        { "label": "tone", "evidence": "Snippet from filing...", "context": null }
      ],
      "similar_companies": [...]
    }
  ],
  "sources": [
    {
      "type": "SEC_EDGAR_API",
      "name": "SEC EDGAR API",
      "url": "https://www.sec.gov/edgar",
      "notes": "10-K Filing Data"
    }
  ],
  "sic": 2080,
  "industry": "Beverages"
}
```

## Repository Structure

```
├── Code
│   ├── Agents
│   │   ├── agent_registry.json
│   │   ├── agent_registry.py
│   │   └── tenk_analyst
│   │       ├── pyproject.toml
│   │       └── tenk_analyst
│   │           ├── AGENT_README.md
│   │           ├── agents
│   │           │   ├── __init__.py
│   │           │   ├── qualitative.py
│   │           │   ├── quantitative.py
│   │           │   ├── rag_agent.py
│   │           │   └── summarizer.py
│   │           ├── models
│   │           │   ├── __init__.py
│   │           │   ├── core.py
│   │           │   ├── qualitative.py
│   │           │   ├── quantitative.py
│   │           │   └── summary.py
│   │           ├── README.md
│   │           ├── run.py
│   │           └── stages
│   │               ├── __init__.py
│   │               ├── chunk_stage.py
│   │               ├── fetch_stage.py
│   │               ├── identify_stage.py
│   │               ├── qual_stage.py
│   │               ├── quant_stage.py
│   │               ├── route_stage.py
│   │               └── summarize_stage.py
│   └── Assets
│       ├── Resources
│       ├── tool_registry.py
│       └── Tools
│           ├── core
│           │   ├── __init__.py
│           │   ├── artifact.py
│           │   ├── pipeline.py
│           │   └── stage.py
│           ├── finance
│           │   ├── __init__.py
│           │   └── ratios.py
│           ├── io
│           │   ├── sec_client.py
│           │   ├── sec_facts_client.py
│           │   └── store.py
│           ├── llm
│           │   └── openai_client.py
│           ├── nlp
│           │   ├── __init__.py
│           │   ├── chunker.py
│           │   └── finbert.py
│           ├── rag
│           │   ├── __init__.py
│           │   └── pinecone_client.py
│           └── router
│               └── routing.py
├── DEPENDENCIES.md
├── Knowledge
│   └── Schema
│       └── Artifacts
│           ├── __init__.py
│           ├── chunks.py
│           ├── datasources.py
│           ├── qual_results.py
│           ├── quant_results.py
│           ├── raw_text.py
│           ├── routed.py
│           └── summary.py
├── README_WORKFLOW.md
├── README.md
├── requirements.txt
└── Workflow
    ├── 10K_Analysis
    │   ├── README.md
    │   ├── run_from_sec.py
    │   └── wipe_pinecone.py
    └── workflow_diagram.md
```

## Troubleshooting

### ModuleNotFoundError for Code.*
Ensure you set `PYTHONPATH="$PWD"` when running scripts.

### SEC Rate Limit Issues
Reduce `--limit` or add delays in `sec_client.py` if encountering rate limits.

### Pinecone Errors
- Verify `PINECONE_API_KEY` and `PINECONE_INDEX` are set correctly
- Ensure the index exists and dimensions match your embedding model

### No Financials in Output
- SEC CompanyFacts may be missing tags for that CIK
- Check `sec_facts_client` logs for missing facts

## Contributing / Extending

### Adding New Features
- **New derived ratios:** Extend `Code/Assets/Tools/finance/ratios.py`
- **Enhanced qualitative signals:** Modify `agents/qualitative.py`
- **Custom summary formatting:** Update `agents/summarizer.py`
- **Additional stages:** Compose custom pipelines using `core/pipeline.py`

### Example: Custom Pipeline

```python
from Code.Assets.Tools.core.pipeline import Pipeline
from Code.Agents.tenk_analyst.tenk_analyst.stages import (
    IdentifyStage, FetchStage, ChunkStage, RouteStage,
    QualStage, QuantStage, SummarizeStage
)

pipeline = Pipeline([
    IdentifyStage(),
    FetchStage(),
    ChunkStage(),
    RouteStage(),
    QualStage(...),
    QuantStage(...),
    SummarizeStage(),
])
```

## License

[Add your license information here]

## Contact

[Add contact/support information here]