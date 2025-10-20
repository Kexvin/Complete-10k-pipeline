# 10-K Form Analysis Agent

A comprehensive pipeline for analyzing SEC 10-K filings using structured financial data from Kaggle, RAG-based comparative analysis, and LLM-powered qualitative insights.

## Overview

This project processes company 10-K filings to generate comprehensive financial analysis reports that include:
- **Quantitative Metrics**: Financial ratios and metrics extracted from Kaggle's structured dataset
- **Qualitative Analysis**: Tone analysis and risk detection from 10-K text using FinBERT
- **Comparative Context**: RAG-based retrieval of similar companies for sector comparison
- **LLM Explanations**: Natural language explanations of findings and methodology

### What This Pipeline Does

The 10-K Analysis Agent is an intelligent system that:

1. **Identifies Companies**: Loads company data from Kaggle's CompanyFacts dataset
- Processes up to `--limit` companies (specified in command line)
- Each company becomes a seed for the pipeline
5. **Extracts Financial Metrics**: Pulls structured financial data from Kaggle's dataset (not by parsing text)
6. **Calculates Ratios**: Computes debt ratios, free cash flow, and profit margins
7. **Generates Insights**: Creates LLM-powered explanations of findings with evidence citations
8. **Produces Reports**: Outputs comprehensive JSON reports with all analysis results

- Filters for form type "10-K" (annual reports)
- Selects the most recent filing by date
- Downloads the full text content via EDGAR document API
- Text typically 50,000-200,000 words
### The Big Picture

The pipeline operates as an **artifact-based data flow system**. Each stage consumes an artifact (structured data object), processes it, and produces a new artifact for the next stage. This design ensures clean separation of concerns and makes the pipeline easy to test and extend.

#### Mermaid workflow diagram

```mermaid
flowchart TD
  subgraph Data_Sources[Data Sources]
    A[Kaggle CompanyFacts CSV]
    S[SEC EDGAR]
  end

  A --> B[Identify Stage\n(get CIK, latest 10-K accession)]
  B --> C[Fetch Stage\n(download 10-K text from SEC)]
  S --> C
  C --> D[Chunk Stage\n(split 10-K into chunks)]
  D --> E[Route Stage\n(route chunks to analysis)]

  %% Parallel analysis
  E --> F[Qualitative Stage\nFinBERT tone + risk keywords]
  E --> G[Quantitative Stage\nKaggle metrics + ratios]

  %% RAG interactions
  subgraph RAG[Pinecone Vector DB]
    J[(knowledgepinecone)]
  end
  F -. embed query .-> J
  J -. top 5 similar .-> F

  %% Summarize
  F --> H[Summarize Stage]
  G --> H
  H --> I((Report JSON\nData/Outputs/reports))

  %% Offline RAG population
  subgraph Offline_RAG_Population
    K[populate_rag.py\nindex reports into Pinecone]
  end
  I --> K --> J
```

```
- Each chunk assigned a unique UUID
- Chunks preserve sequential order
- All chunks routed to qualitative analysis (quantitative uses Kaggle data directly)
              Company    10-K Text   Chunks   Routing    Analysis      Final Report
              Metadata               Array     Labels     Results
```

- **Tone Detection**: FinBERT (financial BERT) classifies sentiment as positive/neutral/negative

#### Stage 1: IDENTIFY STAGE
**Input**: Company CIK from Kaggle dataset  
- **Context Addition**: Annotates findings with "Similar concerns noted by: {CIKs}"
**Process**: 
**Risk keywords monitored (14 total)**:
- Financial: "risk", "uncertainty", "potential loss", "adverse effect", "decline", "volatility"
- Competitive: "competition", "market conditions"
- Legal/Regulatory: "regulatory", "litigation", "liability"
- Operational: "disruption"

**Output**: `IdentifiedArtifact` with CIK and accession number

**Important**: This stage does NOT parse 10-K text. Instead, it queries Kaggle's pre-structured dataset.

Process:
1. Filters `companyfacts.csv` by company CIK and form "10-K"
2. Finds most recent filing date
3. Extracts XBRL financial facts

---
- **Revenue**: From `RevenueFromContractWithCustomer` or `Revenues`
- **Net Income**: From `NetIncomeLoss`
- **Operating Cash Flow**: From `NetCashProvidedByUsedInOperatingActivities`
- **Capital Expenditures**: From `PaymentsToAcquirePropertyPlantAndEquipment`
- **Total Assets**: From `Assets`
- **Total Liabilities**: From `Liabilities`
- Optionally indexes the document into RAG database for future comparisons

- **Debt Ratio** = Total Liabilities / Total Assets × 100
  - Measures financial leverage
  - Higher = more debt relative to assets
  
- **Free Cash Flow (FCF)** = Operating Cash Flow - Capital Expenditures
  - Cash available after maintaining/growing assets
  - Negative FCF = company investing more than generating from operations
  
- **Net Margin** = (Net Income / Revenue) × 100
  - Profitability percentage per dollar of sales
  - Highly variable by industry (tech ~20%, retail ~5%)

---

#### Stage 3: CHUNK STAGE
**Input**: `RawTextArtifact` (full 10-K text)  
- Determines overall tone by majority vote
**Process**:
- Generates LLM explanation:
  - **With OpenAI API key**: GPT-3.5-turbo writes natural language explanation
  - **Without API key**: Deterministic template with all same data/references
- Creates structured JSON report
- Saves to `Data/Outputs/reports/{CIK}_{timestamp}_report.txt`
- Report includes all chunk-level details for traceability
- Preserves text ordering and context

**Output**: `ChunksArtifact` (array of text chunks with IDs)

**Why This Matters**: 
- LLMs and NLP models have token limits
- Smaller chunks enable more precise analysis
- Each chunk can be independently analyzed and compared via RAG

---

#### Stage 4: ROUTE STAGE
**Input**: `ChunksArtifact`  
**Process**:
- Labels each chunk for analysis type
- Currently routes all chunks to qualitative analysis
- Quantitative analysis uses Kaggle data directly, not text parsing

**Output**: `RoutedChunksArtifact` (chunks with analysis labels)

**Why This Matters**: 
- Separates narrative analysis from numerical analysis
- Prevents unreliable text parsing of financial numbers
- Ensures clean data source separation (text for qualitative, Kaggle for quantitative)

---

#### Stage 5: QUALITATIVE STAGE
**Input**: `RoutedChunksArtifact` (chunks labeled for qualitative analysis)  
**Process** (for each chunk):

1. **Tone Analysis with FinBERT**:
   - FinBERT is a BERT model fine-tuned on financial texts
   - Classifies chunk sentiment: positive, neutral, or negative
   - Outputs confidence scores for each classification

2. **RAG-Based Similar Company Retrieval**:
   - Embeds chunk text using sentence-transformers (all-MiniLM-L6-v2)
   - Queries Pinecone vector database for semantically similar chunks
   - Retrieves top 5 most similar chunks from other companies
   - Returns company CIK, tone, and similarity score (cosine similarity)

3. **Risk Keyword Detection**:
   - Scans chunk for 14 risk-related keywords
   - Keywords: "risk", "uncertainty", "potential loss", "adverse effect", "decline", "volatility", "competition", "regulatory", "litigation", "liability", "disruption", "market conditions", etc.
   - Extracts evidence sentences containing keywords
   - Adds comparative context: "Similar concerns noted by: [Company A, Company B]"

**Output**: `QualResultsArtifact` containing:
```python
{
  "chunk_id": "uuid",
  "tone": "neutral",
  "signals": [
    {
      "label": "risk" | "tone",
      "evidence": "Quote from 10-K",
      "context": "Similar companies and their findings"
    }
  ],
  "similar_companies": [
    {"name": "CIK", "tone": "neutral", "similarity": 0.85}
  ]
}
```

**Why This Matters**:
- **FinBERT**: Understands financial language nuances (e.g., "exposure" in finance vs. general meaning)
- **RAG System**: Provides comparative context - "Is this risk unique or industry-wide?"
- **Evidence-Based**: Every claim backed by actual text from the filing

---

#### Stage 6: QUANTITATIVE STAGE
**Input**: `RoutedChunksArtifact` + Company CIK  
**Process**:

1. **Load Kaggle Data**:
   - Reads `companyfacts.csv` (92M+ rows of structured XBRL data)
   - Filters by company CIK and form type (10-K)
   - Finds most recent filing date

2. **Extract Metrics**:
   - Revenue (from `RevenueFromContractWithCustomer` or `Revenues`)
   - Net Income (from `NetIncomeLoss`)
   - Operating Cash Flow (from `NetCashProvidedByUsedInOperatingActivities`)
   - Capital Expenditures (from `PaymentsToAcquirePropertyPlantAndEquipment`)
   - Total Assets (from `Assets`)
   - Total Liabilities (from `Liabilities`)

3. **Calculate Ratios**:
   - **Debt Ratio** = Total Liabilities / Total Assets
     - Measures financial leverage
     - Higher = more debt relative to assets
   
   - **Free Cash Flow (FCF)** = Operating Cash Flow - CapEx
     - Cash available after maintaining assets
     - Negative FCF means company spending more on assets than generating from operations
   
   - **Net Margin** = Net Income / Revenue
     - Profitability per dollar of sales
     - Higher = more efficient profit generation

**Output**: `QuantResultsArtifact` containing:
```python
{
  "company_cik": "0000001750",
  "revenue": 12600000,
  "net_income": 90200000,
  "ocf": 23300000,
  "capex": 29500000,
  "assets": 1833100000,
  "liabilities": null,
  "debt_ratio": 0.45,
  "fcf": -6200000,
  "net_margin": 7.1587
}
```

**Why This Matters**:
- **Structured Data**: Kaggle's dataset is pre-parsed XBRL, much more reliable than text extraction
- **Standardized Metrics**: All companies use same accounting tags (XBRL taxonomy)
- **No Text Parsing**: Avoids errors from PDF/HTML parsing, table extraction, or OCR issues

---

#### Stage 7: SUMMARIZE STAGE
**Input**: `QualResultsArtifact` + `QuantResultsArtifact`  
**Process**:

1. **Aggregate Qualitative Signals**:
   - Collects all tone classifications across chunks
   - Determines overall tone (majority vote)
   - Compiles all risk statements with evidence

2. **Format Financial Data**:
   - Converts numbers to readable strings
   - Groups metrics into "Financial Highlights"

3. **Generate LLM Explanation**:
   - **If OpenAI API key available**:
     - Calls GPT-3.5-turbo with prompt containing all signals and context
     - Generates natural language explanation of methodology
     - Explains how conclusion was reached based on evidence
   
   - **If no API key (fallback)**:
     - Constructs deterministic explanation from templates
     - Still includes all chunk references and comparative context
     - Professional but more formulaic output

4. **Create Final Report**:
   - Combines all artifacts into `SummaryArtifact`
   - Serializes to JSON format
   - Saves to `Data/Outputs/reports/`

**Output**: `SummaryArtifact` (see Report Structure section below)

**Why This Matters**:
- **Comprehensive**: Single report contains quantitative metrics, qualitative insights, and comparative context
- **Traceable**: Every claim linked to specific chunks and evidence
- **Actionable**: LLM explanation helps humans understand the "why" behind the data

### Artifacts

Each stage produces an artifact that flows to the next stage:

| Stage | Input Artifact | Output Artifact | Description |
|-------|---------------|-----------------|-------------|
| Identify | RawTextArtifact | IdentifiedArtifact | Company CIK and accession |
| Fetch | IdentifiedArtifact | RawTextArtifact | 10-K text content |
| Chunk | RawTextArtifact | ChunksArtifact | Text split into chunks |
| Route | ChunksArtifact | RoutedChunksArtifact | Chunks labeled for analysis |
| Qualitative | RoutedChunksArtifact | QualResultsArtifact | Tone & risk signals |
| Quantitative | RoutedChunksArtifact | QuantResultsArtifact | Financial metrics |
| Summarize | (QualResults, QuantResults) | SummaryArtifact | Final report |

---

## How the RAG System Works

### What is RAG?

**RAG (Retrieval-Augmented Generation)** is a technique that enhances AI analysis by retrieving relevant context from a knowledge base before generating insights. In this pipeline, RAG enables comparative analysis across companies.

### RAG Architecture

```
Query Chunk Text
    ↓
[Sentence Transformer]  ← Embeds text into 384-dimensional vector
    ↓
[Pinecone Vector DB]    ← Searches for similar vectors
    ↓
Top 5 Similar Chunks    ← Returns matches with similarity scores
    ↓
[Qualitative Agent]     ← Uses context to generate insights
```

### Step-by-Step RAG Process

#### 1. Indexing Phase (Populating RAG)

When you run `populate_rag.py`, the system:

1. **Reads existing reports** from `Data/Outputs/reports/`
2. **Extracts key information**:
  - Company CIK
  - Overall tone (neutral/positive/negative)
  - First 1500 characters of text (containing executive summary and key points)
3. **Creates embeddings**:
  - Uses `sentence-transformers/all-MiniLM-L6-v2` model
  - Converts text to 384-dimensional vector
  - Vector captures semantic meaning (e.g., "revenue decline" ≈ "sales decrease")
4. **Stores in Pinecone**:
  - Vector stored with metadata: `{cik, tone, text_snippet}`
  - Indexed by cosine similarity for fast retrieval

**Example indexed record**:
```python
{
  "id": "0000001750_chunk_1",
  "values": [0.123, -0.456, ...],  # 384 dimensions
  "metadata": {
   "cik": "0000001750",
   "tone": "neutral",
   "text": "AAR CORP operates in aerospace..."
  }
}
```

#### 2. Retrieval Phase (During Analysis)

When analyzing a new 10-K chunk:

1. **Embed the query chunk**:
  - Same sentence-transformer model
  - Converts chunk to 384-dimensional vector

2. **Query Pinecone**:
  - Finds top 5 most similar vectors using cosine similarity
  - Similarity score ranges from -1 (opposite) to 1 (identical)
  - Typical scores: 0.05-0.30 for related companies

3. **Return context**:
  - Retrieves metadata for each match
  - Returns: CIK, tone, similarity score

4. **Enrich analysis**:
  - Agent compares current chunk's tone with similar companies
  - Identifies if concerns are company-specific or industry-wide
  - Adds context: "Similar concerns noted by: [Company A, Company B]"

**Example retrieval result**:
```python
similar_companies = [
  {"name": "0000001750", "tone": "neutral", "similarity": 0.161},
  {"name": "0000002098", "tone": "neutral", "similarity": 0.074},
  {"name": "0000002034", "tone": "neutral", "similarity": 0.071},
]
```

### Why RAG is Valuable Here

1. **Sector Benchmarking**: "Is this risk level normal for the industry?"
2. **Trend Detection**: "Are multiple companies mentioning supply chain issues?"
3. **Outlier Identification**: "Is this company's tone unusually negative?"
4. **Evidence-Based Context**: Every comparison backed by actual similarity scores

### RAG vs. Traditional Analysis

| Traditional | With RAG |
|------------|----------|
| "Company mentions regulatory risks" | "Company mentions regulatory risks (similar to 3 other companies in sector)" |
| "Neutral tone detected" | "Neutral tone detected, consistent with 80% of comparable companies" |
| "High debt ratio" | "High debt ratio (45% vs. industry average 32% from similar filings)" |

---

## Data Sources

1. **SEC EDGAR API**: Downloads 10-K text for qualitative narrative analysis
2. **Kaggle CompanyFacts Dataset**: Provides structured XBRL financial metrics (92M+ rows)
3. **Pinecone RAG Database**: Stores embedded 10-K chunks for similarity-based retrieval
4. **FinBERT Model**: Pre-trained financial sentiment classifier
5. **Sentence Transformers**: Generates semantic embeddings for RAG

## Prerequisites

### Environment Variables

**Option 1: Using .env file (Recommended)**

Create a `.env` file in the project root directory:

```bash
# .env file
SEC_USER_AGENT=YourName your.email@example.com
PINECONE_API_KEY=your-pinecone-api-key-here

# Optional (for enhanced LLM explanations)
OPENAI_API_KEY=sk-your-openai-api-key-here
```

The pipeline automatically loads this file using `python-dotenv`.

**Option 2: PowerShell Environment Variables**

Alternatively, set environment variables in PowerShell:

```powershell
# Required
$env:SEC_USER_AGENT = "YourName your.email@example.com"
$env:PINECONE_API_KEY = "your-pinecone-api-key"

# Optional (for enhanced LLM explanations)
$env:OPENAI_API_KEY = "your-openai-api-key"
```

### Python Dependencies

Install required packages:

```powershell
pip install pandas numpy pinecone-client sentence-transformers openai pydantic requests python-dotenv
```

### Data Setup

1. **Kaggle Dataset**: Download the SEC CompanyFacts dataset and place at:
   ```
   Data/Primary/kaggle_facts/companyfacts.csv
   ```

2. **Pinecone Index**: Create a Pinecone index named `knowledgepinecone`:
   - Dimension: 384 (for sentence-transformers all-MiniLM-L6-v2)
   - Metric: cosine

## Running the Pipeline

### Setup

1. **Create .env file** with your API keys (see Prerequisites section)
2. **Download Kaggle dataset** to `Data/Primary/kaggle_facts/companyfacts.csv`
3. **Populate RAG database** (optional but recommended for comparative analysis)

### Quick Start

Process one company from the Kaggle dataset:

```powershell
python scripts/run_from_kaggle.py --limit 1 --pinecone-collection knowledgepinecone
```

### Process Multiple Companies

Analyze 5 companies:

```powershell
python scripts/run_from_kaggle.py --limit 5 --pinecone-collection knowledgepinecone
```

### Populate RAG Database

Before running analysis, populate the RAG database with company data for comparison:

```powershell
# First, run the pipeline for 5+ companies to generate reports
python scripts/run_from_kaggle.py --limit 5

# Then index the reports into Pinecone
python scripts/populate_rag.py --limit 5 --collection knowledgepinecone
```

### Custom CSV Path

Use a different companyfacts.csv location:

```powershell
python scripts/run_from_kaggle.py --csv path/to/companyfacts.csv --limit 1
```

## Output

### Report Location

Reports are saved to:
```
Data/Outputs/reports/{CIK}_{timestamp}_report.txt
```

### Understanding the Report File (report.txt)

Each report is saved as a `.txt` file but contains **valid JSON**. The filename format is `{CIK}_{timestamp}_report.txt` (e.g., `0000001750_20251020_185837_report.txt`).

#### Complete Report Structure

The report is a comprehensive JSON object with the following top-level fields:

```json
{
  "company_name": "Company Name",
  "cik": "0000001750",
  "accession": "0001410578-25-001475",
  "key_tone": "neutral",
  "tone_explanation": "Brief explanation of overall tone",
  "risks": [
    "Risk statement 1 with evidence",
    "Risk statement 2 with context"
  ],
  "financials": [
    "Revenue: $12,600,000",
    "Net Income: $90,200,000",
    "Operating Cash Flow: $23,300,000",
    "Free Cash Flow: $-6,200,000",
    "Debt Ratio: 45.23%",
    "Net Margin: 7.15%"
  ],
  "llm_explanation": "Detailed explanation of analysis methodology...",
  "similar_companies": [
    {
      "name": "0000001800",
      "tone": "neutral",
      "similarity": 0.85
    }
  ],
  "qualitative_analysis": [
    {
      "chunk_id": "uuid",
      "tone": "neutral",
      "signals": [
        {
          "label": "risk",
          "evidence": "Risk statement from filing",
          "context": "Similar concerns noted by: Company A, Company B"
        }
      ],
      "similar_companies": [...]
    }
  ],
  "sources": [
    {
      "type": "SEC_EDGAR_API",
      "name": "SEC EDGAR API",
      "url": "https://www.sec.gov/edgar",
      "version": "1.0",
      "retrieved_at": "2025-10-20",
      "notes": "10-K Filing Data"
    }
  ]
}
```

#### Field-by-Field Explanation

##### Top-Level Metadata

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `company_name` | string | Official company name from SEC | "AAR CORP" |
| `cik` | string | Central Index Key (unique SEC identifier) | "0000001750" |
| `accession` | string | Unique filing identifier | "0001410578-25-001475" |

##### Qualitative Summary

| Field | Type | Description | How It's Generated |
|-------|------|-------------|-------------------|
| `key_tone` | string | Overall sentiment classification | **Majority vote** across all chunk analyses. Values: "positive", "neutral", "negative". Determined by FinBERT AI model. |
| `tone_explanation` | string | Why this tone was assigned | Generated by LLM (or fallback) referencing specific chunks and comparative context from RAG similar companies. |
| `risks` | array[string] | Risk statements found in filing | Extracted when risk keywords detected. Format: "{Evidence quote from filing} (Similar concerns noted by: {Company CIKs})" |

**Example risk entry**:
```json
"risks": [
  "The company faces regulatory uncertainty in international markets (Similar concerns noted by: 0000001800, 0000002098)"
]
```

##### Quantitative Summary

| Field | Type | Description | Data Source |
|-------|------|-------------|-------------|
| `financials` | array[string] | Human-readable financial metrics | Extracted from **Kaggle CompanyFacts CSV**, formatted as strings. Includes: Revenue, Net Income, OCF, CapEx, Assets, FCF (calculated), Debt Ratio (calculated), Net Margin (calculated). |

**Example financials array**:
```json
"financials": [
  "Revenue: $12,600,000",           // From Kaggle: RevenueFromContractWithCustomer
  "Net Income: $90,200,000",        // From Kaggle: NetIncomeLoss
  "Operating Cash Flow: $23,300,000", // From Kaggle: NetCashProvidedByUsedInOperatingActivities
  "Capital Expenditures: $29,500,000", // From Kaggle: PaymentsToAcquirePropertyPlantAndEquipment
  "Total Assets: $1,833,100,000",   // From Kaggle: Assets
  "Free Cash Flow: $-6,200,000",    // Calculated: OCF - CapEx
  "Net Margin: 715.87%"             // Calculated: (Net Income / Revenue) * 100
]
```

⚠️ **Note on Net Margin Anomaly**: Values >100% often indicate data mismatches (e.g., quarterly revenue vs. annual net income from different filing periods).

##### LLM Analysis

| Field | Type | Description | Generation Method |
|-------|------|-------------|------------------|
| `llm_explanation` | string | Detailed methodology explanation | **If OpenAI API key set**: GPT-3.5-turbo generates natural language explanation. **Otherwise**: Deterministic template fills in chunk references and RAG context. Both versions cite specific evidence. |

**Example LLM explanation structure**:
```
"The conclusion regarding the {company} was reached by analyzing multiple chunks of data. 
The observed qualitative signals from chunks {chunk_id_1, chunk_id_2, ...} all indicated 
a {tone} tone, consistent with the majority of similar companies in the sector.

Furthermore, the comparative context from similar companies such as {CIK_1, CIK_2, ...}, 
which also exhibited a {tone} tone, helped support the conclusion. The similarity scores 
provided additional context for understanding how closely related the company's tone was 
to these comparable companies.

By considering the tone analysis from multiple chunks and comparing it to similar companies, 
the conclusion of a {tone} tone was reinforced. Additionally, the lack of significant 
deviations in tone or risks from the sector norm further supported the overall assessment."
```

##### Comparative Context (RAG Results)

| Field | Type | Description | How It Works |
|-------|------|-------------|--------------|
| `similar_companies` | array[object] | Top 5 most similar companies overall | **Aggregated** across all chunk-level RAG queries. Each entry contains: `name` (CIK), `tone` (classification), `similarity` (cosine score 0-1). |

**Example**:
```json
"similar_companies": [
  {
    "name": "0000001750",      // Company CIK
    "tone": "neutral",         // That company's overall tone
    "similarity": 0.161808521  // Cosine similarity (0-1 scale)
  }
]
```

**Similarity Score Interpretation**:
- **0.15-0.30**: Highly related (likely same sector or similar business model)
- **0.05-0.15**: Moderately related (overlapping concerns or themes)
- **0.00-0.05**: Weakly related (some shared terminology)
- **Negative**: Opposite semantic meaning (rare)

##### Detailed Chunk-Level Analysis

| Field | Type | Description | Structure |
|-------|------|-------------|-----------|
| `qualitative_analysis` | array[object] | Per-chunk analysis results | One entry per chunk analyzed (typically 10+ chunks per 10-K). Each entry contains: `chunk_id`, `tone`, `signals` array, `similar_companies` array. |

**Single chunk analysis object**:
```json
{
  "chunk_id": "e9eac96b-520e-46cf-afd0-b4de4846c323",  // Unique identifier
  "tone": "neutral",                                    // FinBERT classification
  "signals": [
    {
      "label": "tone",                // Signal type: "tone" or "risk"
      "evidence": "Quote from 10-K",  // Actual text evidence
      "context": null                 // Optional: comparative context
    },
    {
      "label": "risk",
      "evidence": "Company faces supply chain disruptions...",
      "context": "Similar concerns noted by: 0000001800, 0000002098"
    }
  ],
  "similar_companies": [
    // Top 5 most similar chunks from RAG query for THIS specific chunk
    {"name": "0000001750", "tone": "neutral", "similarity": 0.161}
  ]
}
```

**Signal Types**:
- **`tone` signals**: General sentiment observations, always present
- **`risk` signals**: Only present if risk keywords detected in chunk text

##### Data Provenance

| Field | Type | Description | Purpose |
|-------|------|-------------|---------|
| `sources` | array[object] | List of data sources used | Documents where data came from for transparency and reproducibility. Each source lists: `type`, `name`, `url`, `version`, `retrieved_at`, `notes`. |

**Example sources entry**:
```json
"sources": [
  {
    "type": "SEC_EDGAR_API",
    "name": "SEC EDGAR API",
    "url": "https://www.sec.gov/edgar",
    "version": null,
    "retrieved_at": null,
    "notes": null
  }
]
```

---

### How to Read the Report

#### Quick Analysis Workflow:

1. **Check `key_tone`**: Overall sentiment (positive/neutral/negative)
2. **Read `tone_explanation`**: Understand why that tone was assigned
3. **Review `financials`**: Get quantitative snapshot (revenue, profitability, cash flow)
4. **Scan `risks` array**: Identify specific concerns mentioned in filing
5. **Check `similar_companies`**: See how company compares to peers
6. **Dive into `qualitative_analysis`**: For detailed chunk-by-chunk evidence

#### For Comparative Analysis:

Compare the `similar_companies` field across multiple reports to identify:
- **Sector clusters**: Companies frequently similar to each other
- **Outliers**: Companies with low similarity scores to all others
- **Tone patterns**: Is negative sentiment company-specific or industry-wide?

#### For Risk Assessment:

1. Count risk signals across all chunks (in `qualitative_analysis`)
2. Look for risk context fields: "Similar concerns noted by: {CIKs}"
3. If many similar companies share the risk → industry-wide issue
4. If risk is unique → company-specific concern

#### For Financial Health:

Key metrics to focus on:
- **Free Cash Flow**: Negative means spending more than generating
- **Debt Ratio**: >50% indicates heavy leverage
- **Net Margin**: Compare to industry benchmarks (varies widely by sector)

## Workflow Details

### 1. Stock Identification

The pipeline starts by loading companies from the Kaggle dataset:
- Reads `companyfacts.csv` to get unique companies
- Extracts CIK (Central Index Key) and company name
- Processes up to `--limit` companies

### 2. 10-K Retrieval

For each company:
- Queries SEC EDGAR API for all filings
- Identifies the most recent 10-K filing
- Downloads the full text content

### 3. Text Processing

The 10-K text is:
- Split into chunks of ~500-1000 words
- Each chunk assigned a unique ID
- Routed to appropriate analysis pipelines

### 4. Qualitative Analysis

For each chunk:
- **Tone Detection**: FinBERT analyzes financial sentiment
- **RAG Retrieval**: Finds 5 most similar sections from other companies
- **Risk Detection**: Scans for risk-related keywords and extracts evidence
- **Comparative Analysis**: Compares tone with similar companies

Risk keywords monitored:
- risk, uncertainty, potential loss, adverse effect
- decline, volatility, competition, regulatory
- litigation, liability, disruption, market conditions

### 5. Quantitative Analysis

Metrics are extracted from Kaggle's structured dataset:

**Raw Metrics:**
- Revenue
- Net Income
- Operating Cash Flow
- Capital Expenditures
- Total Assets
- Total Liabilities

**Calculated Ratios:**
- **Debt Ratio** = Total Liabilities / Total Assets
- **Free Cash Flow** = Operating Cash Flow - CapEx
- **Net Margin** = Net Income / Revenue

### 6. Report Generation

The summarizer:
- Aggregates qualitative signals across all chunks
- Consolidates financial metrics
- Generates LLM explanation (using OpenAI API if available, else deterministic)
- Creates structured report with citations

## Key Features

### RAG-Based Comparative Analysis

- Uses Pinecone vector database
- Embeddings from `sentence-transformers/all-MiniLM-L6-v2`
- Finds similar company sections based on semantic similarity
- Provides context: "Similar concerns noted by: Company A, Company B"

### LLM Explanations

Two modes:
1. **OpenAI API** (if OPENAI_API_KEY set): GPT-3.5-turbo generates natural language explanations
2. **Deterministic Fallback**: Structured explanation from signals and data

### Data Sources Separation

- **Quantitative**: Pure Kaggle structured data (accurate, consistent)
- **Qualitative**: 10-K text + RAG comparison (contextual, narrative)

## File Structure

```
10-K_Form_Agent/
├── Code/
│   ├── Agents/
│   │   └── tenk_analyst/
│   │       └── tenk_analyst/
│   │           ├── agents/           # Analysis agents
│   │           │   ├── controller.py
│   │           │   ├── qualitative.py
│   │           │   ├── quantitative.py
│   │           │   └── summarizer.py
│   │           ├── models/           # Data models
│   │           │   ├── core.py
│   │           │   ├── qualitative.py
│   │           │   ├── quantitative.py
│   │           │   └── summary.py
│   │           └── stages/           # Pipeline stages
│   │               ├── identify_stage.py
│   │               ├── fetch_stage.py
│   │               ├── chunk_stage.py
│   │               ├── route_stage.py
│   │               ├── qual_stage.py
│   │               ├── quant_stage.py
│   │               └── summarize_stage.py
│   └── Assets/
│       └── Tools/
│           ├── core/                 # Pipeline framework
│           │   ├── artifact.py
│           │   ├── pipeline.py
│           │   └── stage.py
│           ├── finance/              # Financial calculations
│           │   └── ratios.py
│           ├── io/                   # Data I/O
│           │   ├── sec_client.py
│           │   ├── kaggle_data.py
│           │   └── store.py
│           ├── llm/                  # LLM integration
│           │   └── openai_client.py
│           ├── nlp/                  # NLP tools
│           │   ├── chunker.py
│           │   └── finbert.py
│           └── rag/                  # RAG system
│               └── pinecone_client.py
├── Data/
│   ├── Outputs/
│   │   └── reports/                  # Generated reports
│   └── Primary/
│       └── kaggle_facts/
│           └── companyfacts.csv      # Kaggle dataset
├── Knowledge/
│   └── Schema/
│       └── Artifacts/                # Artifact schemas
│           ├── chunks.py
│           ├── qual_results.py
│           ├── quant_results.py
│           ├── raw_text.py
│           ├── routed.py
│           └── summary.py
├── scripts/
│   ├── run_from_kaggle.py           # Main runner script
│   ├── populate_rag.py              # RAG indexing
│   └── init_pinecone.py             # Pinecone setup
└── README.md                         # This file
```

## Troubleshooting

### No Financial Metrics

**Issue**: `financials` array is empty

**Solution**: Ensure Kaggle dataset is at correct path and contains data for the company:
```powershell
python -c "import pandas as pd; df = pd.read_csv('Data/Primary/kaggle_facts/companyfacts.csv'); print(df[df['cik']==1750].head())"
```

### No Similar Companies

**Issue**: `similar_companies` array is empty

**Solution**: Populate RAG database first:
```powershell
python scripts/populate_rag.py --limit 5 --collection knowledgepinecone
```

### Rate Limiting

**Issue**: SEC API rate limiting errors

**Solution**: Add delays between requests or process fewer companies. SEC EDGAR has a 10 requests/second limit.

### Missing OpenAI Explanations

**Issue**: Getting deterministic explanations instead of LLM

**Solution**: Set OPENAI_API_KEY environment variable for enhanced explanations.

## Advanced Usage

### Custom Pipeline

Create a custom pipeline by composing stages:

```python
from Code.Assets.Tools.core.pipeline import Pipeline
from Code.Agents.tenk_analyst.tenk_analyst.stages import *

# Create custom pipeline
my_pipeline = Pipeline([
    IdentifyStage(),
    FetchStage(),
    ChunkStage(),
    # ... add your stages
])

# Run
result = my_pipeline.run(seed_artifact, user_agent=agent)
```

### Extend Quantitative Analysis

Add new financial metrics in `Code/Assets/Tools/io/kaggle_data.py`:

```python
def get_latest_metrics(self, cik: str, form: str = "10-K"):
    # ... existing code ...
    
    # Add new metric
    roe = latest_data[latest_data['companyFact'] == 'ReturnOnEquity']
    if not roe.empty:
        metrics['return_on_equity'] = float(roe.iloc[0]['val'])
```

### Custom Risk Detection

Modify risk keywords in `Code/Agents/tenk_analyst/tenk_analyst/agents/qualitative.py`:

```python
risk_keywords = [
    "risk", "uncertainty", "litigation",
    # Add your custom keywords
    "pandemic", "supply chain", "cybersecurity"
]
```

## Performance

Typical processing time per company:
- Identify & Fetch: 2-5 seconds
- Chunk & Route: < 1 second
- Qualitative Analysis: 3-5 seconds (with RAG)
- Quantitative Analysis: < 1 second (Kaggle lookup)
- Summary Generation: 1-2 seconds

Total: ~8-15 seconds per company

## Contributing

When adding new features:
1. Follow the artifact pattern for data flow
2. Add type hints to all functions
3. Update this README with new functionality
4. Test with multiple companies

## License

[Your License Here]

## Contact

[Your Contact Information]

---

## Complete System Summary

### The Full Data Flow

```
USER INPUT: --limit 5
    ↓
┌─────────────────────────────────────────────────────────────┐
│  STAGE 1: IDENTIFY                                          │
│  Input:  Kaggle CSV (companyfacts.csv)                      │
│  Action: Load 5 companies, get CIKs                         │
│  Output: IdentifiedArtifact (CIK + accession number)       │
└─────────────────────────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────────────────────────┐
│  STAGE 2: FETCH                                             │
│  Input:  IdentifiedArtifact                                 │
│  Action: Download 10-K text from SEC EDGAR                  │
│  Output: RawTextArtifact (50K-200K words)                   │
└─────────────────────────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────────────────────────┐
│  STAGE 3: CHUNK                                             │
│  Input:  RawTextArtifact                                    │
│  Action: Split into ~500-1000 word chunks                   │
│  Output: ChunksArtifact (array of 10+ chunks)               │
└─────────────────────────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────────────────────────┐
│  STAGE 4: ROUTE                                             │
│  Input:  ChunksArtifact                                     │
│  Action: Label all chunks for qualitative analysis          │
│  Output: RoutedChunksArtifact                               │
└─────────────────────────────────────────────────────────────┘
    ↓
┌────────────────────────────┬────────────────────────────────┐
│  STAGE 5: QUALITATIVE      │  STAGE 6: QUANTITATIVE         │
│                            │                                │
│  For Each Chunk:           │  Query Kaggle CSV:             │
│  1. FinBERT tone analysis  │  1. Filter by CIK + form       │
│  2. RAG similarity search  │  2. Extract XBRL metrics       │
│     ↓ Query Pinecone       │  3. Calculate ratios           │
│     ↓ Get 5 similar chunks │                                │
│  3. Risk keyword scan      │  Metrics:                      │
│  4. Add comparative context│  - Revenue, Net Income         │
│                            │  - OCF, CapEx, Assets          │
│  Output: QualResultsArtifact│  Output: QuantResultsArtifact│
└────────────────────────────┴────────────────────────────────┘
    ↓
┌─────────────────────────────────────────────────────────────┐
│  STAGE 7: SUMMARIZE                                         │
│  Input:  QualResultsArtifact + QuantResultsArtifact         │
│  Action:                                                    │
│  1. Aggregate tones → majority vote                         │
│  2. Compile risks → extract evidence                        │
│  3. Format financials → human-readable strings              │
│  4. Generate LLM explanation → OpenAI or fallback           │
│  5. Create JSON report with all artifacts                   │
│  Output: SummaryArtifact → report.txt file                  │
└─────────────────────────────────────────────────────────────┘
    ↓
OUTPUT: Data/Outputs/reports/{CIK}_{timestamp}_report.txt
```

### Key Design Principles

1. **Separation of Concerns**:
  - Qualitative = narrative analysis from 10-K text
  - Quantitative = structured metrics from Kaggle dataset
  - Never mix: no parsing of numbers from text

2. **Artifact-Based Flow**:
  - Each stage produces immutable artifact
  - Next stage consumes previous artifact
  - Easy to test, debug, and extend

3. **Evidence-Based Analysis**:
  - Every claim backed by text evidence
  - Every comparison backed by similarity score
  - Full traceability from conclusion to source

4. **RAG-Augmented Context**:
  - Not just "Company has risk X"
  - Instead: "Company has risk X (similar to 3 other sector companies)"
  - Enables sector benchmarking and outlier detection

5. **Dual LLM Strategy**:
  - OpenAI API: Natural, conversational explanations
  - Deterministic fallback: Ensures system works without API key
  - Both produce complete, traceable reports

### What Makes This System Unique

| Feature | Traditional Approach | This Pipeline |
|---------|---------------------|---------------|
| Financial Data | Parse from 10-K text (error-prone) | Kaggle XBRL dataset (structured, reliable) |
| Sentiment Analysis | Generic NLP models | FinBERT (finance-specific) |
| Company Comparison | Manual research | Automatic RAG-based similarity search |
| Risk Detection | Keyword matching only | Keywords + RAG context + evidence extraction |
| Explanation | Human analyst writes report | LLM generates with full citation trail |
| Reproducibility | Hard to trace decisions | Every field links to source artifact |

### When to Use This Pipeline

**Ideal for**:
- ✅ Batch processing multiple companies for sector analysis
- ✅ Identifying industry-wide trends vs. company-specific issues
- ✅ Automated due diligence screening
- ✅ Research projects needing reproducible methodology
- ✅ Learning how to combine structured data + LLMs + RAG

**Not ideal for**:
- ❌ Real-time trading signals (10-Ks are backward-looking)
- ❌ Deep-dive on single company (better to read 10-K manually)
- ❌ Non-public companies (requires SEC filings)
- ❌ International companies (SEC only covers US-registered entities)

### Performance Benchmarks

Based on testing with AAR CORP (CIK 0000001750):

| Stage | Time | Notes |
|-------|------|-------|
| Identify | 2-3s | SEC API query for filings list |
| Fetch | 2-3s | Download 10-K text (~100KB) |
| Chunk | <1s | Pure text processing |
| Route | <1s | Simple labeling |
| Qualitative | 3-5s | FinBERT + 10 RAG queries |
| Quantitative | <1s | Pandas DataFrame filter |
| Summarize | 1-2s | LLM call (if enabled) + JSON serialization |
| **Total** | **8-15s** | Per company |

**Scaling**: 
- 100 companies: ~15-25 minutes
- 1000 companies: ~2.5-4 hours
- Bottleneck: SEC API rate limit (10 req/sec) + RAG queries

### Future Enhancements

Potential improvements to consider:

1. **Enhanced Risk Detection**:
  - Add ML classification for risk severity (low/medium/high)
  - Extract specific risk categories (regulatory, market, operational)
  - Track risk evolution across multiple 10-K filings

2. **Better Financial Context**:
  - Add industry benchmarks from RAG-retrieved similar companies
  - Calculate year-over-year growth rates
  - Flag anomalous ratios (like the 715% net margin example)

3. **Expanded RAG Capabilities**:
  - Index by section (Risk Factors, MD&A, Financial Statements)
  - Support "show me companies with similar risk profiles"
  - Build sector taxonomy from clustering

4. **Multi-Period Analysis**:
  - Process 10-Qs (quarterly reports) in addition to 10-Ks
  - Track metrics over time (trend analysis)
  - Detect significant changes between filings

5. **Interactive Outputs**:
  - Generate HTML reports with clickable evidence
  - Create comparison dashboards (company vs. sector)
  - Export to Excel with pivot tables

---

## Quick Reference Card

### Essential Commands

```powershell
# Setup (one-time)
copy .env.example .env
notepad .env  # Fill in API keys
pip install -r requirements.txt

# Populate RAG database (first time)
python scripts/run_from_kaggle.py --limit 5
python scripts/populate_rag.py --limit 5 --collection knowledgepinecone

# Run analysis
python scripts/run_from_kaggle.py --limit 1 --pinecone-collection knowledgepinecone

# Check output
dir Data\Outputs\reports
```

### Key File Locations

| File/Folder | Purpose |
|------------|---------|
| `.env` | API keys and configuration |
| `Data/Primary/kaggle_facts/companyfacts.csv` | Kaggle financial dataset |
| `Data/Outputs/reports/` | Generated JSON reports |
| `scripts/run_from_kaggle.py` | Main pipeline runner |
| `Code/Agents/tenk_analyst/` | Analysis agents (qual/quant/summarize) |
| `Code/Assets/Tools/` | Utilities (RAG, FinBERT, ratios) |

### Environment Variables

| Variable | Required? | Purpose |
|----------|-----------|---------|
| `SEC_USER_AGENT` | ✅ Yes | SEC requires user identification |
| `PINECONE_API_KEY` | ✅ Yes | RAG database access |
| `OPENAI_API_KEY` | ❌ Optional | Enhanced LLM explanations |

### Common Issues

| Problem | Solution |
|---------|----------|
| "No module named 'dotenv'" | `pip install python-dotenv` |
| Empty financials array | Check Kaggle CSV path and CIK exists |
| No similar companies | Populate RAG database first |
| SEC rate limit errors | Add delay or reduce --limit |
| High net margin (>100%) | Data mismatch (different periods) - expected |
