from typing import List
from Code.Agents.tenk_analyst.tenk_analyst.models.quantitative import QuantResult


class QuantitativeAgent:
	"""Minimal quantitative agent used in tests.

	The real implementation should extract financial ratios and metrics from text.
	This test-friendly implementation returns a single QuantResult per chunk with placeholder values.
	"""

	def run(self, chunks: List[object]) -> List[QuantResult]:
		results: List[QuantResult] = []
		for c in chunks:
			cid = getattr(c, "id", getattr(c, "chunk_id", ""))
			# Very small/safe extraction: if 'revenue' in text give dummy numbers
			txt = getattr(c, "text", "") or ""
			if "revenue" in txt.lower():
				notes = "found revenue"
			else:
				notes = "no revenue found"
			results.append(QuantResult(chunk_id=str(cid), notes=notes))
		return results

