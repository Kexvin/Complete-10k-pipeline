"""Test the fetch stage functionality."""
import pytest
from tenk_analyst.stages.fetch_stage import FetchStage
from Knowledge.Schema.Artifacts.raw_text import RawTextArtifact

def test_fetch_stage():
    """Test that the fetch stage correctly retrieves a filing."""
    stage = FetchStage()
    # Use Apple's CIK
    input_artifact = RawTextArtifact(company_cik="0000320193", accession="", text="", sources=[])
    
    result = stage.run(input_artifact, user_agent="EdgarTest/1.0")
    
    assert result.text != ""  # Should have fetched content
    assert "10-K" in result.sources[0]  # Should be a 10-K filing
    assert result.accession != ""  # Should have an accession number