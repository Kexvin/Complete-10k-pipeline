from Code.Agents.tenk_analyst.tenk_analyst.stages.identify_stage import IdentifyStage
from Code.Agents.tenk_analyst.tenk_analyst.stages.fetch_stage import FetchStage
from Code.Agents.tenk_analyst.tenk_analyst.stages.chunk_stage import ChunkStage
from Code.Agents.tenk_analyst.tenk_analyst.stages.route_stage import RouteStage
from Code.Agents.tenk_analyst.tenk_analyst.agents.controller import ControllerAgent
from Knowledge.Schema.Artifacts.raw_text import RawTextArtifact

import builtins


def test_chunk_stage_indexes_without_error(monkeypatch, tmp_path):
    # Provide a simple text and ensure chunking works with rag_index True.
    sample_text = "Section A\nFirst para.\nSecond para.\nSection B\nAnother para."

    # Mock RAG to avoid actual Pinecone calls
    class DummyRAG:
        def __init__(self, *args, **kwargs):
            pass

        def index(self, ids, texts, metadatas=None):
            # Basic sanity checks
            assert len(ids) == len(texts)
            return None

    monkeypatch.setattr("Code.Assets.Tools.rag.pinecone_client.RAG", DummyRAG)

    raw = RawTextArtifact(company_cik="0000001", accession="000-1", text=sample_text, sources=[])
    ch_st = ChunkStage()
    out = ch_st.run(raw, rag_index=True, rag_collection="test_collection")
    assert out.company_cik == "0000001"
    assert len(out.chunks) > 0


def test_integration_identify_fetch_chunk_route(monkeypatch):
    # Mock EDGAR client functions to avoid network
    def fake_lookup(ticker, user_agent=None):
        return "0000001"

    def fake_latest_10k(cik, user_agent=None):
        return "000-1"

    def fake_fetch_text(cik, accession, user_agent=None):
        return "Business\nCompany details.\nRisk Factors\nLots of risk.\nConsolidated balance sheet\nNumbers"

    monkeypatch.setattr("Code.Assets.Tools.io.sec_client.lookup_cik_by_ticker", fake_lookup)
    monkeypatch.setattr("Code.Assets.Tools.io.sec_client.latest_10k_accession", fake_latest_10k)
    monkeypatch.setattr("Code.Assets.Tools.io.sec_client.fetch_10k_text", fake_fetch_text)

    # Run identify -> fetch -> chunk -> route
    ident = IdentifyStage()
    fetch = FetchStage()
    chunk = ChunkStage()
    route = RouteStage(ControllerAgent())

    seed = RawTextArtifact(company_cik="", accession="", text="", sources=[])
    identified = ident.run(seed, ticker="FAKE", user_agent="test")
    assert identified.company_cik == "0000001"

    fetched = fetch.run(identified, ticker="FAKE", user_agent="test")
    assert fetched.text and "Business" in fetched.text

    chunks = chunk.run(fetched)
    assert len(chunks.chunks) > 0

    routed = route.run(chunks)
    # Ensure routed artifact has same company metadata
    assert routed.company_cik == chunks.company_cik
    assert routed.accession == chunks.accession
