# Complete 10-K SEC Analysis Pipeline (Agentic Workflow)

A workflow-specific example of an **agentic 10-K analysis system** built on:

- **SEC EDGAR** (submissions + companyfacts) as the *only* data source  
- **Agentic architecture**: qualitative, quantitative, RAG, and summarizer agents  
- **RAG (Pinecone)** for cross-company, text-based retrieval  
- **FinBERT + LLMs** for tone, risk, and natural-language explanations  

The pipeline starts from a list of CIKs, fetches the latest 10-K filings, analyzes them through specialized agents, and stores:

- A **structured JSON-style report** per company  
- **Vector embeddings** of filings, chunks, and reports in Pinecone for downstream RAG use  

---

## 🔎 High-Level Flow

For each CIK you pass in:

1. **Identify the latest 10-K** via the SEC submission API.  
2. **Fetch the full 10-K HTML** and clean it.  
3. **Chunk** out key sections (Item 1A, Item 7A, Item 8) into paragraph-level chunks.  
4. **Route** chunks and metadata into the appropriate agents:
   - `Qualitative10KAgent` (FinBERT + RAG + risk signals)
   - `Quant10KAgent` (SEC companyfacts + ratios from `ratios.py`)
5. **RagAgent** uses Pinecone to retrieve **similar sections** across previously-indexed filings.  
6. **TenKReportSummarizer** merges qualitative + quantitative results into one `SummaryArtifact`.  
7. The summary is **serialized to JSON** (saved as a `.txt` file) and also **indexed back into Pinecone** as a high-level summary vector.

---

## 🤖 Agents vs Stages

This repo is intentionally **agentic**:

### Agents (decision / reasoning units)

Located in: `Code/Agents/tenk_analyst/tenk_analyst/agents/`

- **`RagAgent`**
  - Wraps `Code.Assets.Tools.rag.pinecone_client.RAG`
  - API: `retrieve(text_query, top_k, company_filters, section_filters)`
  - Used by qualitative analysis to find **similar chunks / filings**.
  - Only operates on **text embeddings** (filing text, chunks, summaries) — it **does not** use numeric facts directly.

- **`Qualitative10KAgent`**
  - Consumes routed 10-K text chunks.
  - Uses **FinBERT** (financial sentiment model) to get tone per chunk.
  - Calls `RagAgent` to retrieve similar chunks from other companies.
  - Emits **risk & tone signals** + similar-company context as `QualResultsArtifact`.

- **`Quantitative10KAgent`**
  - Reads numeric facts via `sec_facts_client.build_financials_from_sec_facts`.
  - Computes **ratios and KPIs** using `Code.Assets.Tools.finance.ratios`.
  - Produces `QuantResultsArtifact` with fields like revenue, net income, FCF, debt ratio, net margin, etc.
  - **Does not call RAG** — all numeric logic is deterministic.

- **`TenKReportSummarizer`**
  - Takes both `QualResultsArtifact` and `QuantResultsArtifact`.
  - Optionally uses OpenAI (if `OPENAI_API_KEY` set) for a narrative explanation.
  - Produces a `SummaryArtifact` + serializable report dict.

### Stages (data-flow orchestration)

Located in: `Code/Agents/tenk_analyst/tenk_analyst/stages/`

- `IdentifyStage` – Find latest 10-K accession for a CIK (from SEC submissions).  
- `FetchStage` – Fetch & clean 10-K HTML; optional RAG indexing of raw text.  
- `ChunkStage` – Extract Item 1A / 7A / 8, then create paragraph chunks.  
- `RouteStage` – Build `RoutedChunksArtifact` that indicates which chunks go to which agents.  
- `QualStage` – Wraps `Qualitative10KAgent`.  
- `QuantStage` – Wraps `Quantitative10KAgent`.  
- `SummarizeStage` – Wraps `TenKReportSummarizer`.  

Each stage consumes and produces **artifacts** from `Knowledge/Schema/Artifacts`.

---

## 🧠 Agentic Workflow Diagram (with RAG Emphasis)

> ✅ This diagram is GitHub-compatible Mermaid (no `\n` line breaks).

```mermaid
flowchart LR
  %% External sources
  subgraph Sources["External Data Sources"]
    SECSub["SEC EDGAR<br/>submissions API"]
    SECFacts["SEC companyfacts<br/>(numeric facts)"]
  end

  %% Pipeline + agents
  subgraph Pipeline["10-K SEC Analysis Pipeline (Agentic)"]
    Seed["Seed Input<br/>CIK list"] --> ID["IdentifyStage<br/>(latest 10-K)"]
    ID --> F["FetchStage<br/>(download & clean 10-K)"]
    F --> C["ChunkStage<br/>(Item 1A / 7A / 8)"]
    C --> R["RouteStage<br/>(build RoutedChunksArtifact)"]

    R --> QQual["QualStage<br/>→ Qualitative10KAgent"]
    R --> QQuant["QuantStage<br/>→ Quant10KAgent"]

    QQual --> S["SummarizeStage<br/>→ TenKReportSummarizer"]
    QQuant --> S
    S --> Out["SummaryArtifact + JSON<br/>Data/Outputs/reports"]
  end

  SECSub --> ID
  SECSub --> F
  SECFacts --> QQuant

  %% RAG / vector DB
  subgraph RAG["RAG Layer (Text-Only Retrieval)"]
    RagAgentNode["RagAgent<br/>(wraps RAG client)"]
    Pinecone["Pinecone index<br/>knowledgepinecone"]
  end

  %% Indexing paths (no numeric data)
  F -. "index full 10-K text" .-> Pinecone
  C -. "index section chunks" .-> Pinecone
  Out -. "index textual summary" .-> Pinecone

  %% Retrieval path (qualitative only)
  QQual -. "similar chunks<br/>RagAgent.retrieve()" .-> RagAgentNode
  RagAgentNode --> Pinecone
