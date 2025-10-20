from __future__ import annotations
from typing import Optional, Tuple
import requests
import re

SUBMISSIONS_URL = "https://data.sec.gov/submissions/CIK{cik_padded}.json"
FILING_TXT_URL = "https://www.sec.gov/Archives/edgar/data/{cik_nolead}/{acc_nodash}/{acc_nodash}.txt"
COMPANY_TICKERS_URL = "https://www.sec.gov/files/company_tickers.json"

def _ua(user_agent: Optional[str]) -> dict:
    return {"User-Agent": user_agent or "YourName Contact@Email"}

def pad_cik(cik: str) -> str:
    return str(cik).zfill(10)

def strip_cik(cik: str) -> str:
    return str(int(cik))  # remove leading zeros

def latest_10k_accession(cik: str, user_agent: Optional[str] = None) -> Optional[str]:
    r = requests.get(SUBMISSIONS_URL.format(cik_padded=pad_cik(cik)), headers=_ua(user_agent), timeout=30)
    r.raise_for_status()
    data = r.json()
    filings = data.get("filings", {}).get("recent", {})
    forms = filings.get("form", [])
    accs = filings.get("accessionNumber", [])
    for form, acc in zip(forms, accs):
        if form == "10-K":
            return acc
    return None

def fetch_10k_text(cik: str, accession: str, user_agent: Optional[str] = None) -> str:
    acc_nodash = accession.replace("-", "")
    url = FILING_TXT_URL.format(cik_nolead=strip_cik(cik), acc_nodash=acc_nodash)
    r = requests.get(url, headers=_ua(user_agent), timeout=60)
    r.raise_for_status()
    return r.text

def lookup_cik_by_ticker(ticker: str, user_agent: Optional[str] = None) -> Optional[str]:
    r = requests.get(COMPANY_TICKERS_URL, headers=_ua(user_agent), timeout=30)
    r.raise_for_status()
    data = r.json()
    # format: {"0": {"cik_str": 320193, "ticker": "AAPL", "title": "Apple Inc."}, ...}
    ticker_up = ticker.upper()
    for _, row in data.items():
        if row.get("ticker", "").upper() == ticker_up:
            return str(row.get("cik_str"))
    return None
