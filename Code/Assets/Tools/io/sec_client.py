from __future__ import annotations

from typing import Optional, Tuple, Dict, Any
import requests
from requests import exceptions as req_exc
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# ──────────────────────────────────────────────────────────────────────────────
# SEC endpoints
# ──────────────────────────────────────────────────────────────────────────────

# Submissions + company profile (includes SIC and sicDescription)
SUBMISSIONS_URL = "https://data.sec.gov/submissions/CIK{cik_padded}.json"

# Archive URL for individual filing documents (primaryDocument)
FILING_ARCHIVE_URL = (
    "https://www.sec.gov/Archives/edgar/data/{cik_nolead}/{acc_nodash}/{primary_doc}"
)

# IX viewer URL that wraps the same primaryDocument (fallback)
IX_VIEWER_URL = (
    "https://www.sec.gov/ixviewer/doc?action=load&doc=/Archives/edgar/data/"
    "{cik_nolead}/{acc_nodash}/{primary_doc}"
)

# Ticker → CIK mapping
COMPANY_TICKERS_URL = "https://www.sec.gov/files/company_tickers.json"


# ──────────────────────────────────────────────────────────────────────────────
# Small helpers
# ──────────────────────────────────────────────────────────────────────────────

def _ua(user_agent: Optional[str]) -> Dict[str, str]:
    """Build headers with a required user-agent (SEC requires this)."""
    if not user_agent:
        raise ValueError("A user agent string is required for SEC API requests")
    return {"User-Agent": user_agent}


def pad_cik(cik: str) -> str:
    """Left-pad CIK to 10 digits for data.sec.gov endpoints."""
    return str(cik).zfill(10)


def strip_cik(cik: str) -> str:
    """Remove leading zeros for archive paths."""
    return str(int(cik))


def _sec_session(headers: Dict[str, str]) -> requests.Session:
    """
    Create a requests.Session with retries configured.

    - Retries on 429/5xx with backoff.
    - Applies to all HTTPS/HTTP requests from this session.
    """
    session = requests.Session()
    retry = Retry(
        total=3,
        backoff_factor=1.0,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET"],
        raise_on_status=False,
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    session.headers.update(headers)
    return session


# ──────────────────────────────────────────────────────────────────────────────
# Core functions
# ──────────────────────────────────────────────────────────────────────────────

def latest_10k_accession(cik: str, user_agent: Optional[str] = None) -> Optional[str]:
    """
    Return the accessionNumber of the most recent 10-K for the given CIK.
    """
    headers = _ua(user_agent)
    cik_padded = pad_cik(cik)
    print(f"Fetching submissions for CIK: {cik_padded}")

    resp = requests.get(SUBMISSIONS_URL.format(cik_padded=cik_padded), headers=headers, timeout=30)
    resp.raise_for_status()
    data = resp.json()

    filings = data.get("filings", {}).get("recent", {})
    forms = filings.get("form", [])
    accs = filings.get("accessionNumber", [])

    print(f"Found {len(forms)} filings")
    for i, (form, acc) in enumerate(zip(forms, accs)):
        print(f"Filing {i+1}: {form} - {acc}")
        if form == "10-K":
            print(f"Found latest 10-K: {acc}")
            return acc

    print("No 10-K filing found")
    return None


def fetch_company_profile(cik: str, user_agent: Optional[str] = None) -> Dict[str, Any]:
    """
    Fetch the submissions JSON which also serves as a basic company profile.

    Returns dict including fields like:
      - 'cik'
      - 'name'
      - 'sic'
      - 'sicDescription'
    """
    headers = _ua(user_agent)
    cik_padded = pad_cik(cik)
    print(f"Fetching company profile for CIK: {cik_padded}")
    resp = requests.get(SUBMISSIONS_URL.format(cik_padded=cik_padded), headers=headers, timeout=30)
    resp.raise_for_status()
    return resp.json()


def get_company_profile(
    cik: str, user_agent: Optional[str] = None
) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    """
    Convenience wrapper around fetch_company_profile.

    Returns:
        (company_name, sic, sic_description)
    """
    try:
        profile = fetch_company_profile(cik, user_agent=user_agent)
    except Exception as e:
        print(f"Error fetching company profile for CIK {cik}: {e}")
        return None, None, None

    name = profile.get("name")
    sic = profile.get("sic")
    sic_desc = profile.get("sicDescription")
    print(f"Profile for CIK {cik}: name={name}, sic={sic}, sicDescription={sic_desc}")
    return name, sic, sic_desc


def get_company_industry(cik: str, user_agent: Optional[str] = None) -> Tuple[Optional[str], Optional[str]]:
    """
    Return (sic, industry_description) for a company CIK using submissions JSON.
    """
    try:
        profile = fetch_company_profile(cik, user_agent=user_agent)
    except Exception as e:
        print(f"Error fetching company industry for CIK {cik}: {e}")
        return None, None

    sic = profile.get("sic")
    sic_desc = profile.get("sicDescription")
    print(f"SIC info for CIK {cik}: sic={sic}, sicDescription={sic_desc}")
    return sic, sic_desc


def fetch_10k_text(cik: str, accession: str, user_agent: Optional[str] = None) -> str:
    """
    Fetch the actual 10-K filing document as text.

    Strategy:
      1. Re-read submissions JSON.
      2. Find row where form == "10-K" and accessionNumber == accession.
      3. Use 'primaryDocument' from that row to build archive URL.
      4. If archive fetch times out/fails, fall back to IX viewer with same primaryDocument.
      5. As a last resort, try old {acc_nodash}.htm pattern.
    """
    headers = _ua(user_agent)
    session = _sec_session(headers)

    cik_padded = pad_cik(cik)
    cik_nolead = strip_cik(cik)
    acc_nodash = accession.replace("-", "")

    # 1) Load submissions JSON so we can find primaryDocument
    try:
        print(f"[SEC] Reloading submissions for 10-K text: CIK={cik}, accession={accession}")
        r = session.get(SUBMISSIONS_URL.format(cik_padded=cik_padded), timeout=30)
        r.raise_for_status()
        data = r.json()
    except Exception as e:
        raise RuntimeError(f"Failed to load submissions for CIK {cik}: {e}")

    filings = data.get("filings", {}).get("recent", {})
    forms = filings.get("form", [])
    accs = filings.get("accessionNumber", [])
    primary_docs = filings.get("primaryDocument", [])

    primary_doc: Optional[str] = None

    # 2) Try to match the exact accession
    for form, acc, doc in zip(forms, accs, primary_docs):
        if form == "10-K" and acc == accession:
            primary_doc = doc
            break

    # 3) If we didn't find an exact match, fall back to the first 10-K
    if primary_doc is None:
        for form, acc, doc in zip(forms, accs, primary_docs):
            if form == "10-K":
                primary_doc = doc
                print(
                    f"[SEC] Exact accession not found for 10-K; "
                    f"falling back to first 10-K: {acc} with primaryDocument={doc}"
                )
                accession = acc
                acc_nodash = accession.replace("-", "")
                break

    # Helper to try a URL with better timeout and nice logs
    def _try_get(url: str, label: str) -> Optional[str]:
        print(f"[SEC] Fetching 10-K {label}: {url}")
        try:
            resp = session.get(url, timeout=120)  # longer timeout for big 10-Ks
            if resp.ok:
                return resp.text
            print(f"[SEC] {label} fetch failed with status {resp.status_code}")
            return None
        except req_exc.ReadTimeout:
            print(f"[SEC] {label} fetch timed out (ReadTimeout).")
            return None
        except Exception as e:
            print(f"[SEC] {label} fetch error: {e}")
            return None

    # 4) Primary document path (preferred)
    if primary_doc:
        archive_url = FILING_ARCHIVE_URL.format(
            cik_nolead=cik_nolead,
            acc_nodash=acc_nodash,
            primary_doc=primary_doc,
        )
        text = _try_get(archive_url, "primary document")
        if text:
            return text

        # Try IX viewer with same primaryDocument
        ix_url = IX_VIEWER_URL.format(
            cik_nolead=cik_nolead,
            acc_nodash=acc_nodash,
            primary_doc=primary_doc,
        )
        text = _try_get(ix_url, "IX viewer")
        if text:
            return text

    # 5) Last-resort fallback: old {acc_nodash}.htm pattern
    fallback_doc = f"{acc_nodash}.htm"
    fallback_url = FILING_ARCHIVE_URL.format(
        cik_nolead=cik_nolead,
        acc_nodash=acc_nodash,
        primary_doc=fallback_doc,
    )
    text = _try_get(fallback_url, "fallback .htm")
    if text:
        return text

    # If everything failed, raise a clear error so the pipeline can log and continue
    raise RuntimeError(
        f"Unable to fetch 10-K text for CIK={cik}, accession={accession} "
        f"(primaryDocument, IX viewer, and fallback .htm all failed)"
    )


def lookup_cik_by_ticker(ticker: str, user_agent: Optional[str] = None) -> Optional[str]:
    """
    Look up CIK from ticker using the SEC's company_tickers.json file.
    """
    headers = _ua(user_agent)
    ticker_up = ticker.upper()
    print(f"Looking up CIK for ticker: {ticker_up}")

    resp = requests.get(COMPANY_TICKERS_URL, headers=headers, timeout=30)
    resp.raise_for_status()
    data = resp.json()
    # format: {"0": {"cik_str": 320193, "ticker": "AAPL", "title": "Apple Inc."}, ...}

    for _, row in data.items():
        if row.get("ticker", "").upper() == ticker_up:
            cik_str = str(row.get("cik_str"))
            title = row.get("title", "Unknown Company")
            print(f"Found CIK: {cik_str} for {title}")
            return cik_str

    print(f"No CIK found for ticker: {ticker_up}")
    return None
