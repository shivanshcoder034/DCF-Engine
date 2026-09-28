"""SEC EDGAR API client for company identification, filing discovery, and document retrieval.

Complies strictly with SEC access policies, including identifiable User-Agent headers,
rate limiting (maximum 10 requests per second), polite backoff, and local caching.
"""

from __future__ import annotations

import json
import logging
import os
import re
import time
import urllib.request
import urllib.error
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.config import settings
from src.filings.models import FilingFormType, FilingMetadata

logger = logging.getLogger(__name__)


class SecEdgarClient:
    """Polite, rate-limited HTTP client for the official SEC EDGAR system."""

    DEFAULT_USER_AGENT = "DCFValuationEngine/1.0 (research@dcf-engine.org)"
    TICKERS_URL = "https://www.sec.gov/files/company_tickers.json"
    SUBMISSIONS_URL_TEMPLATE = "https://data.sec.gov/submissions/CIK{cik10}.json"
    COMPANY_FACTS_URL_TEMPLATE = "https://data.sec.gov/api/xbrl/companyfacts/CIK{cik10}.json"
    ARCHIVE_BASE_URL = "https://www.sec.gov/Archives/edgar/data"

    def __init__(
        self,
        user_agent: Optional[str] = None,
        cache_dir: Optional[Path] = None,
        min_request_delay_seconds: float = 0.15,
    ) -> None:
        self.user_agent = user_agent or os.getenv("SEC_USER_AGENT") or self.DEFAULT_USER_AGENT
        self.cache_dir = cache_dir or (settings.data_dir / "sec_filings")
        self.min_request_delay_seconds = min_request_delay_seconds
        self._last_request_time: float = 0.0
        self._tickers_cache: Optional[Dict[str, Dict[str, Any]]] = None

        # Ensure local filing cache directory exists
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _rate_limit(self) -> None:
        """Enforce rate limiting to comply with SEC's 10 requests/second threshold."""
        now = time.time()
        elapsed = now - self._last_request_time
        if elapsed < self.min_request_delay_seconds:
            time.sleep(self.min_request_delay_seconds - elapsed)
        self._last_request_time = time.time()

    def _request(self, url: str, headers: Optional[Dict[str, str]] = None, timeout: int = 15) -> bytes:
        """Execute an HTTP GET request with the required SEC User-Agent header."""
        self._rate_limit()
        req_headers = {
            "User-Agent": self.user_agent,
            "Accept-Encoding": "gzip, deflate",
            "Host": url.split("//")[1].split("/")[0],
        }
        if headers:
            req_headers.update(headers)

        req = urllib.request.Request(url, headers=req_headers)
        try:
            with urllib.request.urlopen(req, timeout=timeout) as response:
                raw = response.read()
                # Decompress gzip responses (SEC EDGAR often returns gzip-encoded content)
                encoding = response.headers.get('Content-Encoding', '')
                if encoding == 'gzip' or (len(raw) >= 2 and raw[0] == 0x1f and raw[1] == 0x8b):
                    import gzip as _gzip
                    try:
                        raw = _gzip.decompress(raw)
                    except Exception:
                        pass  # Not actually gzip, return as-is
                return raw
        except urllib.error.HTTPError as exc:
            logger.warning("SEC EDGAR HTTP error %d for URL: %s", exc.code, url)
            if exc.code == 403:
                raise PermissionError(
                    f"SEC EDGAR returned 403 Forbidden. Ensure your User-Agent header is polite and properly "
                    f"formatted: Current: '{self.user_agent}'"
                ) from exc
            if exc.code == 404:
                raise FileNotFoundError(f"Requested SEC resource not found at: {url}") from exc
            if exc.code == 429:
                raise RuntimeError("SEC EDGAR rate limit reached (HTTP 429). Please pause before retrying.") from exc
            raise RuntimeError(f"SEC EDGAR HTTP error: {exc.code} {exc.reason}") from exc
        except Exception as exc:
            logger.error("SEC EDGAR connection error for URL %s: %s", url, exc)
            raise ConnectionError(f"Could not connect to SEC EDGAR ({url}): {exc}") from exc

    def lookup_cik(self, ticker_or_cik: str) -> Optional[Dict[str, Any]]:
        """Resolve a ticker or raw CIK into official CIK and company name.

        Returns dict: {"cik": "0000320193", "ticker": "AAPL", "title": "Apple Inc."} or None.
        """
        cleaned = ticker_or_cik.strip().upper()
        if not cleaned:
            return None

        # Check if already a pure numeric CIK
        if cleaned.isdigit():
            cik_padded = cleaned.zfill(10)
            return {
                "cik": cik_padded,
                "ticker": None,
                "title": f"CIK {cik_padded}",
            }

        # Load ticker mapping
        tickers_map = self._get_tickers_map()
        if cleaned in tickers_map:
            return tickers_map[cleaned]

        return None

    def _get_tickers_map(self) -> Dict[str, Dict[str, Any]]:
        """Load or fetch the SEC ticker-to-CIK mapping dictionary."""
        if self._tickers_cache is not None:
            return self._tickers_cache

        cache_file = self.cache_dir / "company_tickers.json"
        data: Optional[Dict[str, Any]] = None

        # Use local cache if newer than 7 days
        if cache_file.exists():
            try:
                age_days = (time.time() - cache_file.stat().st_mtime) / 86400
                if age_days < 7:
                    with open(cache_file, "r", encoding="utf-8") as f:
                        data = json.load(f)
            except Exception as exc:
                logger.warning("Could not read local tickers cache: %s", exc)

        if data is None:
            try:
                raw_bytes = self._request(self.TICKERS_URL, timeout=12)
                data = json.loads(raw_bytes.decode("utf-8"))
                with open(cache_file, "w", encoding="utf-8") as f:
                    json.dump(data, f)
            except Exception as exc:
                logger.warning("Failed to download fresh company tickers from SEC: %s", exc)
                if cache_file.exists():
                    with open(cache_file, "r", encoding="utf-8") as f:
                        data = json.load(f)
                else:
                    return {}

        # Map by uppercase ticker
        result: Dict[str, Dict[str, Any]] = {}
        for entry in data.values():
            t = entry.get("ticker", "").upper()
            c = str(entry.get("cik_str", "")).zfill(10)
            title = entry.get("title", "")
            if t:
                result[t] = {
                    "cik": c,
                    "ticker": t,
                    "title": title,
                }
        self._tickers_cache = result
        return result

    def get_company_filings(
        self,
        cik: str,
        forms: Optional[List[str]] = None,
        limit: int = 50,
    ) -> List[FilingMetadata]:
        """Discover available 10-K and 10-Q filings for a given company CIK."""
        cik10 = cik.strip().zfill(10)
        forms_to_keep = set(forms or ["10-K", "10-Q", "10-K/A", "10-Q/A"])

        url = self.SUBMISSIONS_URL_TEMPLATE.format(cik10=cik10)
        cache_file = self.cache_dir / f"submissions_{cik10}.json"

        data: Optional[Dict[str, Any]] = None
        # Cache submissions for 2 hours
        if cache_file.exists():
            try:
                age_hours = (time.time() - cache_file.stat().st_mtime) / 3600
                if age_hours < 2:
                    with open(cache_file, "r", encoding="utf-8") as f:
                        data = json.load(f)
            except Exception as exc:
                logger.warning("Could not read cached submissions: %s", exc)

        if data is None:
            raw_bytes = self._request(url, timeout=15)
            data = json.loads(raw_bytes.decode("utf-8"))
            try:
                with open(cache_file, "w", encoding="utf-8") as f:
                    json.dump(data, f)
            except Exception as exc:
                logger.warning("Could not cache submissions: %s", exc)

        company_name = data.get("name", f"Entity CIK {cik10}")
        tickers = data.get("tickers", [])
        primary_ticker = tickers[0] if tickers else None

        recent = data.get("filings", {}).get("recent", {})
        if not recent or "form" not in recent:
            return []

        form_list = recent.get("form", [])
        filing_date_list = recent.get("filingDate", [])
        report_date_list = recent.get("reportDate", [])
        accession_list = recent.get("accessionNumber", [])
        primary_doc_list = recent.get("primaryDocument", [])

        results: List[FilingMetadata] = []
        cik_int = str(int(cik10))

        for idx, form in enumerate(form_list):
            if form in forms_to_keep:
                accession = accession_list[idx]
                filing_date = filing_date_list[idx]
                report_date = report_date_list[idx] if idx < len(report_date_list) else filing_date
                primary_doc = primary_doc_list[idx] if idx < len(primary_doc_list) else None

                # Build official document link
                doc_url: Optional[str] = None
                if primary_doc:
                    acc_clean = accession.replace("-", "")
                    doc_url = f"{self.ARCHIVE_BASE_URL}/{cik_int}/{acc_clean}/{primary_doc}"

                # Deduce fiscal year / period from report date
                fiscal_year: Optional[int] = None
                fiscal_period: Optional[str] = None
                if report_date and len(report_date) >= 4:
                    try:
                        fiscal_year = int(report_date[:4])
                    except ValueError:
                        pass

                if form.startswith("10-K"):
                    fiscal_period = "FY"
                elif form.startswith("10-Q"):
                    fiscal_period = "Q"

                is_amended = form.endswith("/A")

                meta = FilingMetadata(
                    ticker=primary_ticker,
                    cik=cik10,
                    company_name=company_name,
                    form_type=form,
                    accession_number=accession,
                    filing_date=filing_date,
                    report_date=report_date,
                    fiscal_year=fiscal_year,
                    fiscal_period=fiscal_period,
                    primary_document=primary_doc,
                    primary_doc_url=doc_url,
                    is_amended=is_amended,
                    status="Discovered",
                )
                results.append(meta)
                if len(results) >= limit:
                    break

        return results

    def get_company_facts(self, cik: str) -> Optional[Dict[str, Any]]:
        """Retrieve standardized official US-GAAP facts via SEC company facts API."""
        cik10 = cik.strip().zfill(10)
        cache_file = self.cache_dir / f"facts_{cik10}.json"

        # Cache company facts for 24 hours (large payload)
        if cache_file.exists():
            try:
                age_hours = (time.time() - cache_file.stat().st_mtime) / 3600
                if age_hours < 24:
                    with open(cache_file, "r", encoding="utf-8") as f:
                        return json.load(f)
            except Exception as exc:
                logger.warning("Could not read cached company facts: %s", exc)

        url = self.COMPANY_FACTS_URL_TEMPLATE.format(cik10=cik10)
        try:
            raw_bytes = self._request(url, timeout=20)
            data = json.loads(raw_bytes.decode("utf-8"))
            with open(cache_file, "w", encoding="utf-8") as f:
                json.dump(data, f)
            return data
        except Exception as exc:
            logger.error("Failed to retrieve company facts for CIK %s: %s", cik10, exc)
            return None

    def get_filing_document(self, filing: FilingMetadata, max_bytes: int = 5_000_000) -> Optional[str]:
        """Fetch and locally cache the primary HTML/text document of an SEC filing."""
        if not filing.primary_doc_url and filing.primary_document:
            cik_int = str(int(filing.cik))
            acc_clean = filing.accession_number.replace("-", "")
            filing.primary_doc_url = f"{self.ARCHIVE_BASE_URL}/{cik_int}/{acc_clean}/{filing.primary_document}"

        if not filing.primary_doc_url:
            raise ValueError(f"Filing {filing.accession_number} has no primary document URL.")

        filing_folder = self.cache_dir / f"{filing.cik}_{filing.accession_number}"
        filing_folder.mkdir(parents=True, exist_ok=True)
        filename = filing.primary_document or "filing_doc.htm"
        doc_path = filing_folder / filename

        # Read from local cache if already downloaded
        if doc_path.exists() and doc_path.stat().st_size > 0:
            try:
                with open(doc_path, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()
                    filing.local_cache_path = str(doc_path)
                    filing.status = "Retrieved"
                    return content
            except Exception as exc:
                logger.warning("Could not read cached document: %s", exc)

        # Download from SEC
        try:
            raw_bytes = self._request(filing.primary_doc_url, timeout=25)
            if len(raw_bytes) > max_bytes:
                # Save full file but notify
                logger.info("Filing document is %d bytes; reading up to limit", len(raw_bytes))

            text = raw_bytes.decode("utf-8", errors="ignore")
            with open(doc_path, "w", encoding="utf-8", errors="ignore") as f:
                f.write(text)

            filing.local_cache_path = str(doc_path)
            filing.status = "Retrieved"
            return text
        except Exception as exc:
            logger.error("Failed to download filing document from %s: %s", filing.primary_doc_url, exc)
            raise
