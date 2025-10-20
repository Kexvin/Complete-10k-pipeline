# 10-K Form Agent Workflow

## System Architecture Diagram

```mermaid
graph TB
    %% Style definitions
    classDef process fill:#E6F3FF,stroke:#333,stroke-width:2px
    classDef document fill:#FFF,stroke:#333,stroke-width:2px
    classDef database fill:#D4F1F4,stroke:#333,stroke-width:2px
    classDef mlmodel fill:#FFE6CC,stroke:#333,stroke-width:2px
    classDef storage fill:#F3E6FF,stroke:#333,stroke-width:2px
    classDef decision fill:#FFE6E6,stroke:#333,stroke-width:2px

    %% Main Pipeline Components
    A[("Seed Artifact<br/>(RawTextArtifact)")]:::document
    B["FetchStage"]:::process
    C["ChunkStage"]:::process
    D{"RouteStage<br/>(Controller)"}:::decision
    E["QualitativeStage"]:::process
    F["QuantitativeStage"]:::process
    G["SummarizeStage"]:::process
    H[("Final Report")]:::document

    %% External Components
    DB[(Pinecone<br/>Vector DB)]:::database
    ML["FinBERT Model"]:::mlmodel
    SRC[("EDGAR/Kaggle")]:::storage
    EMB["Embedding<br/>Pipeline"]:::mlmodel

    %% Flow Connections
    A --> |company_cik + accession| B
    B --> |raw_text| C
    C --> |chunks| D
    D --> |qualitative_chunks| E
    D --> |quantitative_chunks| F
    E --> |qual_results| G
    F --> |quant_results| G
    G --> |final_summary| H
    
    %% External Connections
    SRC --> |fetch_filing| B
    ML --> |sentiment_analysis| E
    EMB --> |store_vectors| DB
    DB --> |semantic_search| E

    %% Subgraph Grouping
    subgraph Base_Pipeline ["Base Pipeline"]
        A
        B
        C
        D
    end

    subgraph Qualitative_Pipeline ["Qualitative Pipeline"]
        E
        DB
        ML
        EMB
    end

    subgraph Quantitative_Pipeline ["Quantitative Pipeline"]
        F
    end

    subgraph Final_Stage ["Final Stage"]
        G
        H
    end
```

## Component Details

### Base Pipeline
- **Seed Artifact**: Input container with company information
- **FetchStage**: Retrieves 10-K filing text from EDGAR/Kaggle
- **ChunkStage**: Splits text into manageable chunks
- **RouteStage**: Routes chunks to appropriate analysis pipeline

### Qualitative Pipeline
- **QualitativeStage**: Analyzes qualitative factors using FinBERT and RAG
- **Pinecone Vector DB**: Vector storage for semantic search
- **FinBERT Model**: Pre-trained financial sentiment model
- **Embedding Pipeline**: Sentence transformer embeddings

### Quantitative Pipeline
- **QuantitativeStage**: Analyzes quantitative metrics and ratios

### Final Stage
- **SummarizeStage**: Combines analyses into final report
- **Final Report**: Dictionary output with comprehensive analysis

## Data Flow

1. Process begins with empty RawTextArtifact containing company info
2. FetchStage retrieves filing text using provided company CIK and accession
3. ChunkStage splits text into manageable segments
4. RouteStage determines appropriate pipeline for each chunk
5. Parallel processing:
   - Qualitative: Semantic search and sentiment analysis
   - Quantitative: Financial metrics extraction
6. Results combined in SummarizeStage
7. Final Report generated with complete analysis