"""Test the identification stage functionality."""
import pytest
from tenk_analyst.stages.identify_stage import IdentifyStage
from Knowledge.Schema.Artifacts.raw_text import RawTextArtifact

def test_identify_stage():
    """Test that the identify stage correctly resolves ticker to CIK."""
    stage = IdentifyStage()
    seed = RawTextArtifact(company_cik="", accession="", text="", sources=[])
    
    result = stage.run(seed, ticker="AAPL", kaggle_csv="Data/Primary/kaggle_info/company_facts.csv")
    
    assert result.company_cik is not None
    assert result.company_cik != ""  # Should have found a CIK