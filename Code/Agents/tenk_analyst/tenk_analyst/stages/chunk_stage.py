from __future__ import annotations

from typing import List, Dict, Tuple
import re

from Code.Assets.Tools.core.stage import Stage
from Knowledge.Schema.Artifacts.raw_text import RawTextArtifact
from Knowledge.Schema.Artifacts.chunks import ChunksArtifact
from Code.Agents.tenk_analyst.tenk_analyst.models.core import Chunk
from Code.Assets.Tools.nlp.chunker import simple_paragraph_chunker
from Code.Assets.Tools.rag.pinecone_client import RAG


# ──────────────────────────────────────────────────────────────────────────────
# Helpers: HTML cleaning and 10-K section extraction
# ──────────────────────────────────────────────────────────────────────────────

def _clean_html_to_text(raw_html: str) -> str:
    """Lightweight HTML → plain text cleaner for SEC 10-K filings.

    - Drops <script>/<style> blocks
    - Drops HTML comments
    - Strips remaining tags
    - Unescapes entities like &#8203; and &nbsp;
    - Collapses whitespace
    """
    if not isinstance(raw_html, str):
        try:
            raw_html = str(raw_html)
        except Exception:
            return ""

    # Remove script/style
    raw_html = re.sub(r"(?is)<(script|style).*?>.*?</\1>", " ", raw_html)
    # Remove comments
    raw_html = re.sub(r"(?is)<!--.*?-->", " ", raw_html)
    # Strip tags
    raw_html = re.sub(r"<[^>]+>", " ", raw_html)

    # Unescape basic numeric entities (e.g., &#8203;)
    def _unescape_numeric(m: re.Match) -> str:
        try:
            num = int(m.group(1))
            return chr(num)
        except Exception:
            return " "

    raw_html = re.sub(r"&#(\d+);", _unescape_numeric, raw_html)

    # Unescape named entities we see a lot in EDGAR
    raw_html = raw_html.replace("&nbsp;", " ").replace("&amp;", "&")

    # Collapse whitespace
    raw_html = re.sub(r"\s+", " ", raw_html).strip()
    return raw_html


def _find_last_match(pattern: re.Pattern, text: str) -> Tuple[int, int] | None:
    """Return (start, end) of the *last* match of pattern in text, or None."""
    last = None
    for m in pattern.finditer(text):
        last = (m.start(), m.end())
    return last


def _extract_10k_sections(clean_text: str) -> Dict[str, str]:
    """Extract key 10-K sections from cleaned text using last-heading heuristic.

    We:
    - Look for the last occurrence of each heading (to skip table-of-contents)
    - Then slice from that heading to the next heading (by position)
    """

    # Case-insensitive patterns for item headings
    section_patterns = {
        "item_1a_risk_factors": re.compile(
            r"item\s+1a\.\s*risk\s+factors", re.IGNORECASE
        ),
        "item_7a_market_risk": re.compile(
            r"item\s+7a\.\s*quantitative\s+and\s+qualitative\s+disclosures\s+about\s+market\s+risk",
            re.IGNORECASE,
        ),
        "item_8_financial_statements": re.compile(
            r"item\s+8\.\s*financial\s+statements\s+and\s+supplementary\s+data",
            re.IGNORECASE,
        ),
    }

    # Find last heading position for each item
    headings: List[Tuple[str, int]] = []  # (section_key, start_idx)
    for key, pat in section_patterns.items():
        last = _find_last_match(pat, clean_text)
        if last is None:
            print(f"[CHUNK DEBUG] No heading found for {key}")
            continue
        start, end = last
        print(
            f"[CHUNK DEBUG] Heading for {key} at [{start}, {end}] "
            f"preview='{clean_text[start:start+80]}...'"
        )
        headings.append((key, start))

    if not headings:
        print("[CHUNK DEBUG] No 10-K headings found; returning full cleaned text as one section.")
        return {"full_filing": clean_text}

    # Sort headings by position in file
    headings.sort(key=lambda t: t[1])

    sections: Dict[str, str] = {}
    n = len(headings)
    for i, (key, start) in enumerate(headings):
        end = len(clean_text)
        if i + 1 < n:
            end = headings[i + 1][1]

        snippet = clean_text[start:end].strip()
        sections[key] = snippet
        print(
            f"[CHUNK DEBUG] Extracted section '{key}' len={len(snippet)} "
            f"(start={start}, end={end})"
        )

    return sections


# ──────────────────────────────────────────────────────────────────────────────
# ChunkStage implementation
# ──────────────────────────────────────────────────────────────────────────────

class ChunkStage(Stage[RawTextArtifact, ChunksArtifact]):
    def __init__(self) -> None:
        super().__init__("chunk", RawTextArtifact, ChunksArtifact)

    def run(self, inp: RawTextArtifact, **kwargs) -> ChunksArtifact:
        raw_html = inp.text or ""
        print(f"[CHUNK DEBUG] Raw filing length = {len(raw_html)} chars")

        # 1) Clean the entire filing
        clean_text = _clean_html_to_text(raw_html)
        print(f"[CHUNK DEBUG] Cleaned filing length = {len(clean_text)} chars")

        # 2) Extract key 10-K sections (1A, 7A, 8) from cleaned text
        sections = _extract_10k_sections(clean_text)

        # 3) Re-chunk each section into paragraph-level Chunks
        all_chunks: List[Chunk] = []
        for section_key, section_text in sections.items():
            if not section_text or len(section_text) < 50:
                print(
                    f"[CHUNK DEBUG] Skipping very short section '{section_key}' "
                    f"(len={len(section_text)})"
                )
                continue

            # Use your existing paragraph-based chunker
            sec_chunks = simple_paragraph_chunker(
                inp.company_cik,
                inp.accession,
                section_text,
            )

            # Tag each chunk with the section name
            for ch in sec_chunks:
                # ensure section attribute exists
                try:
                    ch.section = section_key
                except Exception:
                    pass
                all_chunks.append(ch)

            print(
                f"[CHUNK DEBUG] Section '{section_key}' produced {len(sec_chunks)} "
                f"paragraph chunks."
            )

        print(f"[CHUNK DEBUG] Total chunks produced = {len(all_chunks)}")
        if all_chunks:
            print(
                f"[CHUNK DEBUG] First chunk preview='{all_chunks[0].text[:120]}...'"
            )

        # 4) Optionally index chunks into RAG (Pinecone)
        rag_index: bool = bool(kwargs.get("rag_index", False))
        rag_collection: str | None = kwargs.get("rag_collection")

        if rag_index and all_chunks:
            try:
                collection = rag_collection or "tenk_chunks"
                rag = RAG(collection=collection)
                print(
                    f"[CHUNK DEBUG] Indexing {len(all_chunks)} cleaned paragraph-chunks "
                    f"into RAG (collection='{collection}')."
                )

                ids: List[str] = []
                texts: List[str] = []
                metas: List[dict] = []

                for i, ch in enumerate(all_chunks):
                    cid = f"{inp.company_cik}_{inp.accession}_chunk_{i}"
                    ids.append(cid)
                    texts.append(ch.text)
                    metas.append(
                        {
                            "company_cik": inp.company_cik,
                            "accession": inp.accession,
                            "section": getattr(ch, "section", ""),
                            "chunk_index": i,
                        }
                    )

                rag.index(ids=ids, texts=texts, metadatas=metas)
            except Exception as e:
                # Don't let indexing break chunking
                print(f"[CHUNK DEBUG] RAG indexing failed: {e}")

        # 5) Return ChunksArtifact
        return ChunksArtifact(
            company_cik=inp.company_cik,
            accession=inp.accession,
            filing_type=getattr(inp, "filing_type", ""),
            chunks=all_chunks,
            sources=inp.sources,
        )
