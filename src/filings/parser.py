"""Filing parser identifying financial statement tables and footnote disclosure sections.

Parses SEC filing HTML/text to locate Item 8 Financial Statements and individual Footnotes,
preserving section titles, paragraph references, and structural lineage for traceability.
"""

from __future__ import annotations

import logging
import re
from typing import Any, Dict, List, Optional, Tuple

try:
    from bs4 import BeautifulSoup
    _BS4_AVAILABLE = True
except ImportError:
    _BS4_AVAILABLE = False

logger = logging.getLogger(__name__)


class FilingParser:
    """Parses SEC 10-K/10-Q filing documents to identify footnote disclosures and statement tables."""

    # Standard footnote topic regex patterns
    NOTE_PATTERNS = {
        "revenue_policies": [
            re.compile(r"Note\s+\d+[\s\.:–—\-]+(?:Summary\s+of\s+)?(?:Significant\s+)?Accounting\s+Policies", re.I),
            re.compile(r"Note\s+\d+[\s\.:–—\-]+Revenue(?:\s+Recognition)?", re.I),
            re.compile(r"Revenue\s+from\s+Contracts\s+with\s+Customers", re.I),
        ],
        "debt_financing": [
            re.compile(r"Note\s+\d+[\s\.:–—\-]+(?:Debt|Financing\s+Arrangements|Borrowings|Credit\s+Facilities|Commercial\s+Paper)", re.I),
            re.compile(r"Term\s+Loans|Senior\s+Notes|Line\s+of\s+Credit", re.I),
        ],
        "leases": [
            re.compile(r"Note\s+\d+[\s\.:–—\-]+Leases?", re.I),
            re.compile(r"Operating\s+Leases?|Finance\s+Leases?|ASC\s+842", re.I),
        ],
        "contingencies": [
            re.compile(r"Note\s+\d+[\s\.:–—\-]+(?:Commitments\s+and\s+)?Contingencies", re.I),
            re.compile(r"Note\s+\d+[\s\.:–—\-]+Legal\s+Proceedings", re.I),
            re.compile(r"Litigation(?:\s+and\s+Other\s+Contingencies)?", re.I),
        ],
        "segments": [
            re.compile(r"Note\s+\d+[\s\.:–—\-]+(?:Segment\s+Reporting|Segment\s+Information|Business\s+Segments)", re.I),
            re.compile(r"Geographic\s+Information|Segment\s+Disclosures", re.I),
        ],
        "taxes": [
            re.compile(r"Note\s+\d+[\s\.:–—\-]+(?:Income\s+)?Taxes?", re.I),
            re.compile(r"Deferred\s+Taxes?|Tax\s+Valuation\s+Allowance", re.I),
        ],
        "impairments": [
            re.compile(r"Note\s+\d+[\s\.:–—\-]+(?:Goodwill|Intangible\s+Assets?|Impairments?)", re.I),
            re.compile(r"Fair\s+Value\s+Measurements?|Asset\s+Impairment", re.I),
        ],
        "related_parties": [
            re.compile(r"Note\s+\d+[\s\.:–—\-]+Related(?:\s+|\-)Party\s+Transactions?", re.I),
        ],
        "accounting_changes": [
            re.compile(r"Note\s+\d+[\s\.:–—\-]+(?:Recently\s+Adopted|New)\s+Accounting\s+(?:Pronouncements|Standards|Policies)", re.I),
            re.compile(r"Restatement|Accounting\s+Changes", re.I),
        ],
        "capital_structure": [
            re.compile(r"Note\s+\d+[\s\.:–—\-]+(?:Stockholders[\'’]?\s+Equity|Share\s+Capital|Common\s+Stock)", re.I),
            re.compile(r"Share(?:\-|\s+)Based\s+Compensation|Stock\s+Incentive\s+Plan", re.I),
        ],
    }

    def __init__(self) -> None:
        pass

    def extract_text_and_sections(self, raw_content: str) -> Dict[str, Any]:
        """Parse raw HTML or text filing into structured sections and plain text."""
        if not raw_content:
            return {"plain_text": "", "sections": {}, "tables": []}

        # If BeautifulSoup is available and content looks like HTML
        if _BS4_AVAILABLE and ("<html" in raw_content.lower() or "<body" in raw_content.lower() or "<div" in raw_content.lower()):
            try:
                soup = BeautifulSoup(raw_content, "lxml")
            except Exception:
                soup = BeautifulSoup(raw_content, "html.parser")

            # Remove scripts, styles
            for elem in soup(["script", "style", "head", "meta"]):
                elem.decompose()

            plain_text = soup.get_text(separator="\n")
        else:
            # Simple tag stripper
            plain_text = re.sub(r"<[^>]+>", " ", raw_content)

        # Normalize whitespace while preserving paragraphs
        lines = [line.strip() for line in plain_text.splitlines() if line.strip()]
        clean_text = "\n".join(lines)

        sections = self._identify_footnote_sections(lines)
        return {
            "plain_text": clean_text,
            "sections": sections,
            "line_count": len(lines),
        }

    def _identify_footnote_sections(self, lines: List[str]) -> Dict[str, Dict[str, Any]]:
        """Identify discrete footnote sections from line sequence."""
        found_sections: Dict[str, Dict[str, Any]] = {}
        current_section_key: Optional[str] = None
        current_title: Optional[str] = None
        current_lines: List[str] = []
        current_start_line = 0

        note_header_re = re.compile(r"^(?:Note\s+\d+[\s\.:–—\-]+[A-Za-z0-9\s,\'’\(\)\-]{3,80})$", re.I)

        for line_idx, line in enumerate(lines):
            # Check if this line looks like a Note heading
            is_note_heading = False
            matched_category: Optional[str] = None

            if len(line) < 120 and ("note" in line.lower() or "item" in line.lower()):
                for cat_key, patterns in self.NOTE_PATTERNS.items():
                    for pat in patterns:
                        if pat.search(line):
                            is_note_heading = True
                            matched_category = cat_key
                            break
                    if is_note_heading:
                        break

                if not is_note_heading and note_header_re.match(line):
                    is_note_heading = True
                    matched_category = "other_material"

            if is_note_heading:
                # Save previous section if exists
                if current_section_key and current_lines:
                    text_content = "\n".join(current_lines[:150])  # Cap at 150 lines per section
                    found_sections[current_section_key] = {
                        "title": current_title or current_section_key,
                        "category_key": current_section_key.split("_")[0],
                        "text": text_content,
                        "start_line": current_start_line,
                        "line_count": len(current_lines),
                    }

                # Start new section
                current_section_key = f"{matched_category}_{line_idx}"
                current_title = line
                current_lines = [line]
                current_start_line = line_idx
            elif current_section_key:
                # Accumulate lines for current section
                current_lines.append(line)
                # Cap accumulation to prevent runaway sections (max 200 lines)
                if len(current_lines) > 200:
                    text_content = "\n".join(current_lines)
                    found_sections[current_section_key] = {
                        "title": current_title or current_section_key,
                        "category_key": current_section_key.split("_")[0],
                        "text": text_content,
                        "start_line": current_start_line,
                        "line_count": len(current_lines),
                    }
                    current_section_key = None
                    current_lines = []

        # Flush final section
        if current_section_key and current_lines:
            found_sections[current_section_key] = {
                "title": current_title or current_section_key,
                "category_key": current_section_key.split("_")[0],
                "text": "\n".join(current_lines[:150]),
                "start_line": current_start_line,
                "line_count": len(current_lines),
            }

        return found_sections

    def parse_statement_tables(self, raw_html: str) -> List[Dict[str, Any]]:
        """Extract candidate financial statement tables from HTML content."""
        if not _BS4_AVAILABLE or not raw_html:
            return []

        try:
            soup = BeautifulSoup(raw_html, "lxml")
        except Exception:
            soup = BeautifulSoup(raw_html, "html.parser")

        statement_tables: List[Dict[str, Any]] = []
        tables = soup.find_all("table")

        for t_idx, table in enumerate(tables):
            table_text = table.get_text()
            # Check for characteristic financial statement headers
            is_candidate = False
            title = f"Table {t_idx + 1}"

            if any(term in table_text.lower() for term in [
                "consolidated statements of operations",
                "consolidated statements of income",
                "consolidated statements of earnings",
                "condensed consolidated statements of operations",
            ]):
                is_candidate = True
                title = "Statements of Operations"
            elif any(term in table_text.lower() for term in [
                "consolidated balance sheets",
                "condensed consolidated balance sheets",
            ]):
                is_candidate = True
                title = "Balance Sheets"
            elif any(term in table_text.lower() for term in [
                "consolidated statements of cash flows",
                "condensed consolidated statements of cash flows",
            ]):
                is_candidate = True
                title = "Statements of Cash Flows"

            if is_candidate:
                rows_data: List[List[str]] = []
                for tr in table.find_all("tr"):
                    cells = [td.get_text(strip=True) for td in tr.find_all(["td", "th"])]
                    if any(c for c in cells):
                        rows_data.append(cells)

                if len(rows_data) >= 3:
                    statement_tables.append({
                        "title": title,
                        "table_index": t_idx,
                        "rows": rows_data,
                    })

        return statement_tables
