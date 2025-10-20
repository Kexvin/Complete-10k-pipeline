"""Populate Pinecone RAG index with 5 sample company sections for testing.

Usage:
    python scripts/populate_rag.py --limit 5 --collection knowledgepinecone

This script will look for candidate 10-K texts in Data/Outputs/reports or Data/Primary/filings,
extract a representative section for each company, and index into the configured Pinecone index
using the RAG client wrapper.
"""
import os
import argparse
from pathlib import Path
from Code.Assets.Tools.rag.pinecone_client import RAG

REPORTS_DIR = Path("Data/Outputs/reports")
PRIMARY_FILINGS = Path("Data/Primary/filings")


def find_report_files(limit=5):
    if not REPORTS_DIR.exists():
        return []
    files = sorted(REPORTS_DIR.glob("*_report.txt"), key=lambda p: p.stat().st_mtime, reverse=True)
    return files[:limit]


def extract_text_from_report(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except Exception:
        return ""


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=5)
    parser.add_argument("--collection", type=str, default="finance_glossary",
                        help="Pinecone collection/index name to use")
    args = parser.parse_args()

    rag = RAG(collection=args.collection)
    if rag._index is None:
        print("Pinecone index not available. Set PINECONE_API_KEY and ensure index exists.")
        return

    files = find_report_files(limit=args.limit)
    if not files:
        print("No report files found in Data/Outputs/reports. Looking in Data/Primary/filings for raw filings.")
        # Try primary filings
        files = list(PRIMARY_FILINGS.glob("**/*.txt"))[:args.limit]

    ids = []
    texts = []
    metas = []
    for f in files[:args.limit]:
        txt = extract_text_from_report(f)
        if not txt:
            continue
        # Use filename-derived id
        id_ = f.stem
        ids.append(id_)
        texts.append(txt[:1500])  # index first 1500 chars
        metas.append({
            "company": id_.split("_")[0],
            "source_file": str(f)
        })

    if not ids:
        print("No documents to index.")
        return

    print(f"Indexing {len(ids)} documents into Pinecone index '{rag.index_name}'...")
    rag.index(ids=ids, texts=texts, metadatas=metas)
    print("Indexing complete.")


if __name__ == '__main__':
    main()
