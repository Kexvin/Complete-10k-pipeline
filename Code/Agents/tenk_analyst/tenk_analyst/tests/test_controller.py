from Code.Agents.tenk_analyst.tenk_analyst.agents.controller import ControllerAgent
from Code.Agents.tenk_analyst.tenk_analyst.models.core import Chunk

def test_controller_routes_basic():
    ctrl = ControllerAgent()
    c1 = Chunk(id="1", company_cik="1", accession="a", section="Risk Factors", text="Risk is high.")
    c2 = Chunk(id="2", company_cik="1", accession="a", section=None, text="Consolidated statements show ...")
    out = ctrl.route([c1, c2])
    assert len(out) == 2
    assert {r.route for r in out} <= {"qualitative", "quantitative"}
