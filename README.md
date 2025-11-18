🧱 Stages & Artifacts

Artifacts live in Knowledge/Schema/Artifacts/ and are imported into stages & agents.

Stage	Input Artifact	Output Artifact	File (Stage)
Identify	RawTextArtifact	RawTextArtifact	stages/identify_stage.py
Fetch	RawTextArtifact	RawTextArtifact	stages/fetch_stage.py
Chunk	RawTextArtifact	ChunksArtifact	stages/chunk_stage.py
Route	ChunksArtifact	RoutedChunksArtifact	stages/route_stage.py
Qualitative	RoutedChunksArtifact	QualResultsArtifact	stages/qual_stage.py + agents/qualitative.py
Quantitative	RoutedChunksArtifact	QuantResultsArtifact	stages/quant_stage.py + agents/quantitative.py
Summarize	Qual + Quant artifacts	SummaryArtifact	stages/summarize_stage.py + agents/summarizer.py
Stage 1 – Identify

File: Code/Agents/tenk_analyst/tenk_analyst/stages/identify_stage.py
Input: RawTextArtifact with company_cik set, no text yet.
Process:

Uses sec_client (Code/Assets/Tools/io/sec_client.py) to:

Fetch the list of submissions for that CIK

Filter for 10-K form type

Select the most recent 10-K accession

Output: RawTextArtifact with accession filled in.

Stage 2 – Fetch

File: Code/Agents/tenk_analyst/tenk_analyst/stages/fetch_stage.py
Input: RawTextArtifact with company_cik & accession.
Process:

Uses sec_client.fetch_10k_text() to download & clean the primary 10-K HTML.

Adds SEC EDGAR as a source via datasources.sec_edgar_api_source.

Optionally indexes the full cleaned text into Pinecone when rag_index=True:

Uses Code/Assets/Tools/rag/pinecone_client.RAG.

Output: RawTextArtifact with:

filing_type="10-K"

text containing full cleaned filing text

sources including SEC EDGAR (+ any configured notes)

Stage 3 – Chunk

File: Code/Agents/tenk_analyst/tenk_analyst/stages/chunk_stage.py
Input: RawTextArtifact (full text).
Process:

Uses Code/Assets/Tools/nlp/chunker.py to:

Strip HTML and boilerplate.

Detect and extract:

item_1a_risk_factors

item_7a_market_risk

item_8_financial_statements

Slice each section into chunks (paragraph-ish).

Annotate each chunk with:

chunk_id (UUID)

Section label

Raw & cleaned text

Output: ChunksArtifact (chunks.py).

Stage 4 – Route

File: Code/Agents/tenk_analyst/tenk_analyst/stages/route_stage.py
Input: ChunksArtifact.
Process:

Assigns routing labels based on section:

Risk Factors → qualitative-heavy

Market Risk → qualitative + quant context

Financial Statements → quant context / summary usage

Packages routed chunks into a single artifact.

Output: RoutedChunksArtifact (routed.py).

Stage 5 – Qualitative

Files:

Stage: stages/qual_stage.py

Agent: agents/qualitative.py

Models: models/qualitative.py

Input: RoutedChunksArtifact.
Process (per chunk routed to qual path):

Tone analysis (FinBERT)

Uses Code/Assets/Tools/nlp/finbert.FinBert (heavy=True)

Classifies tone: positive, neutral, or negative

Produces a QualResult with tone & confidence.

Optional RAG retrieval

Uses RagAgent (agents/rag_agent.py) wrapping RAG client.

Embeds chunk text and queries Pinecone (knowledgepinecone by default).

Returns top-k similar chunks or filings with:

id, score, text, metadata.

Signal extraction

Builds QualSignal objects encoding:

Tone evidence

Risk phrases

Any RAG-derived comparative context

Output: QualResultsArtifact (qual_results.py).

Stage 6 – Quantitative

Files:

Stage: stages/quant_stage.py

Agent: agents/quantitative.py

Models: models/quantitative.py

Finance helpers: Code/Assets/Tools/finance/ratios.py

SEC facts: Code/Assets/Tools/io/sec_facts_client.py

Input: RoutedChunksArtifact (for context) + CIK.
Process:

Pulls numeric data from SEC companyfacts:

Revenue

Net Income

Operating Cash Flow

Capital Expenditures

Total Assets

Total Liabilities

Computes derived metrics with ratios.py, e.g.:

Free Cash Flow = OCF – CapEx

Debt Ratio = Liabilities / Assets

Net Margin = Net Income / Revenue

Output: QuantResultsArtifact (quant_results.py).

Stage 7 – Summarize

Files:

Stage: stages/summarize_stage.py

Agent: agents/summarizer.py

Models: models/summary.py

Input:

QualResultsArtifact

QuantResultsArtifact

Process:

Aggregates qualitative signals:

Derives key_tone (majority tone).

Collects risk bullets with evidence snippets.

Formats quantitative metrics:

Human-readable financials structure.

Generates an LLM explanation (optional):

Uses Code/Assets/Tools/llm/openai_client.py if OPENAI_API_KEY is set.

Otherwise falls back to deterministic templated explanation.

Builds a SummaryReport model and wraps into SummaryArtifact.

Serializes to JSON and writes to:

Data/Outputs/reports/{CIK}_{timestamp}_report.txt


Indexes a rich text summary into Pinecone via RAG:

ID like {CIK}_{accession}

Text includes company name, tone, explanation, financial highlights, and sample qualitative lines.

Output: SummaryArtifact (summary.py).

📚 RAG System (Pinecone)

Core client: Code/Assets/Tools/rag/pinecone_client.py
Agent wrapper: Code/Agents/tenk_analyst/tenk_analyst/agents/rag_agent.py

What gets indexed?

Full filing text (optional) in Fetch Stage.

Condensed summary text in Summarize Stage.

Each indexed item has:

id: e.g., "0000077476_0000077476-25-000007"

text: long-form textual content (filing or summary).

metadata: company CIK, accession, tone, financial figures, etc.

What gets retrieved?

During qualitative analysis:

A chunk’s text is embedded and sent to Pinecone.

RAG returns top-k semantically similar vectors:

Exposing similar filings / similar sections.

The qualitative agent uses this for:

Peer comparison

Sector context

“Similar concerns noted by …” style commentary (if you choose to add it in the summarizer).

🔐 Data Sources

SEC EDGAR Submissions & Filings

10-K list and primary HTML content (sec_client.py).

SEC CompanyFacts

XBRL numeric facts for quantitative KPIs (sec_facts_client.py).

FinBERT

Financial sentiment model for chunk-level tone.

Pinecone

Vector DB for RAG.

OpenAI (Optional)

Used only for natural-language explanations in the Summarize stage.

⚙️ Setup & Prerequisites
1. Create & Activate Virtual Env
python -m venv .venv
source .venv/bin/activate        # macOS / Linux
# .venv\Scripts\activate         # Windows (PowerShell / cmd)

2. Install Dependencies
pip install --upgrade pip
pip install -r requirements.txt

3. Environment Variables (.env)

Create .env in the project root (same level as README.md):

SEC_USER_AGENT="Your Name your.email@example.com"
PINECONE_API_KEY=your-pinecone-api-key
PINECONE_INDEX=knowledgepinecone

# Optional for LLM explanations
OPENAI_API_KEY=sk-...


The SEC requires a proper User-Agent string.

🚀 Running the Pipeline

Main entry script: Workflow/10K_Analysis/run_from_sec.py

Make sure to set PYTHONPATH to the repo root so imports work.

Single CIK
PYTHONPATH="$PWD" python3 Workflow/10K_Analysis/run_from_sec.py \
  --cik 0000077476 \
  --limit 1 \
  --pinecone-collection knowledgepinecone

Multiple CIKs
PYTHONPATH="$PWD" python3 Workflow/10K_Analysis/run_from_sec.py \
  --cik 0000077476 \
  --cik 0000091767 \
  --limit 2 \
  --pinecone-collection knowledgepinecone


--cik can be passed multiple times.

--limit truncates the list (e.g. you can pass 20 CIKs but only process the first 5).

Wipe Pinecone Index

File: Workflow/10K_Analysis/wipe_pinecone.py

PYTHONPATH="$PWD" python3 Workflow/10K_Analysis/wipe_pinecone.py \
  --pinecone-collection knowledgepinecone

📤 Output Reports

Reports are saved under:

Data/Outputs/reports/{CIK}_{timestamp}_report.txt


Each file contains pretty-printed JSON, e.g.:

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

📁 Repository Structure

Matches your current tree:

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

🛠 Troubleshooting (Quick)

ModuleNotFoundError for Code.*:
Ensure you set PYTHONPATH="$PWD" when running.

SEC rate limit issues:
Reduce --limit or add sleeps in sec_client if you start hitting rate limits.

Pinecone errors:

Check PINECONE_API_KEY and PINECONE_INDEX.

Make sure the index exists and dimensions match your embedding model.

No financials in output:

SEC companyfacts may be missing some tags for that CIK.

Inspect sec_facts_client logs for missing facts.

🤝 Contributing / Extending

Add new derived ratios to Code/Assets/Tools/finance/ratios.py.

Extend qualitative signals in agents/qualitative.py.

Enhance summary formatting in agents/summarizer.py.

Add new stages by composing them in custom Pipeline instances via core/pipeline.py.

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