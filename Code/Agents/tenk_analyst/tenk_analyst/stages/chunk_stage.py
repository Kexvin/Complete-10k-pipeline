from typing import List
from Code.Assets.Tools.core.stage import Stage
from Knowledge.Schema.Artifacts.raw_text import RawTextArtifact
from Knowledge.Schema.Artifacts.chunks import ChunksArtifact
from Code.Agents.tenk_analyst.tenk_analyst.models.core import Chunk
from Code.Assets.Tools.nlp.chunker import simple_paragraph_chunker
from Code.Assets.Tools.rag.pinecone_client import RAG

class ChunkStage(Stage[RawTextArtifact, ChunksArtifact]):
    def __init__(self) -> None:
        super().__init__("chunk", RawTextArtifact, ChunksArtifact)

    def run(self, inp: RawTextArtifact, **kwargs) -> ChunksArtifact:
        parts: List[Chunk] = simple_paragraph_chunker(inp.company_cik, inp.accession, inp.text)

        # Optionally index chunks into RAG (Pinecone)
        rag_index: bool = bool(kwargs.get("rag_index", False))
        rag_collection: str | None = kwargs.get("rag_collection")

        if rag_index:
            try:
                collection = rag_collection or "tenk_chunks"
                rag = RAG(collection=collection)
                ids = []
                texts = []
                metas = []
                for i, ch in enumerate(parts):
                    cid = f"{inp.company_cik}_{inp.accession}_chunk_{i}"
                    ids.append(cid)
                    texts.append(ch.text)
                    metas.append({
                        "company_cik": inp.company_cik,
                        "accession": inp.accession,
                        "section": ch.section,
                        "chunk_index": i,
                    })
                rag.index(ids=ids, texts=texts, metadatas=metas)
            except Exception:
                # Don't let indexing break chunking
                pass

        return ChunksArtifact(
            company_cik=inp.company_cik,
            accession=inp.accession,
            filing_type=getattr(inp, "filing_type", ""),
            chunks=parts,
            sources=inp.sources,
        )
