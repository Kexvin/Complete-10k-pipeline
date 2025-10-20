from __future__ import annotations
from typing import List, Optional
import re
import uuid
from Code.Agents.tenk_analyst.tenk_analyst.models.core import Chunk

# Basic section headers commonly found in 10-Ks
SECTION_PATTERNS = [
    (re.compile(r"^\s*ITEM\s+1A\.\s*RISK\s+FACTORS\b", re.I), "Risk Factors"),
    (re.compile(r"^\s*ITEM\s+7\.\s*MANAGEMENT[’']?S\s+DISCUSSION.*\b", re.I), "MD&A"),
    (re.compile(r"^\s*MANAGEMENT[’']?S\s+DISCUSSION.*\b", re.I), "MD&A"),
    (re.compile(r"^\s*BUSINESS\b", re.I), "Business"),
]

def _detect_section(line: str) -> Optional[str]:
    for pat, name in SECTION_PATTERNS:
        if pat.search(line):
            return name
    return None

def smart_chunker(company_cik: str, accession: str, text: str) -> List[Chunk]:
    """
    Section-aware chunker:
    - Creates a new chunk when a section header is detected
    - Otherwise groups text by blank-line paragraph boundaries
    """
    lines = text.splitlines()
    chunks: List[Chunk] = []
    buf: List[str] = []
    cur_section: Optional[str] = None

    def flush():
        nonlocal buf, cur_section
        if not buf:
            return
        paragraph = "\n".join(buf).strip()
        if paragraph:
            chunks.append(Chunk(
                id=str(uuid.uuid4()),
                company_cik=company_cik,
                accession=accession,
                section=cur_section,
                text=paragraph
            ))
        buf = []

    for line in lines:
        sec = _detect_section(line)
        if sec:
            flush()
            cur_section = sec
            continue
        if not line.strip():
            # blank line: paragraph boundary
            flush()
        else:
            buf.append(line)
    flush()
    return chunks

def simple_paragraph_chunker(company_cik: str, accession: str, text: str) -> List[Chunk]:
    """Fallback: split by double newlines."""
    parts = [p.strip() for p in text.split("\n\n") if p.strip()]
    return [Chunk(id=str(uuid.uuid4()), company_cik=company_cik, accession=accession, text=p) for p in parts]
