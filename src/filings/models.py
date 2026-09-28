"""Data structures, enums, and dataclasses for SEC filing discovery and AI analysis.

Defines schemas for filing metadata, extracted statement line items,
footnote disclosure categories, and AI-assisted observations.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from enum import Enum
from typing import Any, Dict, List, Optional


class FilingFormType(str, Enum):
    """Supported SEC filing types."""
    FORM_10K = "10-K"
    FORM_10Q = "10-Q"
    FORM_10K_A = "10-K/A"
    FORM_10Q_A = "10-Q/A"

    @classmethod
    def is_amended(cls, value: str) -> bool:
        return value.endswith("/A")


class FootnoteCategory(str, Enum):
    """Categorization for accounting footnote disclosures and AI observations."""
    ACCOUNTING_POLICIES = "Revenue Recognition & Accounting Policies"
    DEBT_FINANCING = "Debt, Credit Facilities & Interest Covenants"
    LEASES = "Leases & Lease Obligations (ASC 842)"
    CONTINGENCIES = "Commitments, Contingencies & Litigation (ASC 450)"
    SEGMENTS = "Segment Reporting & Geographical Breakdown (ASC 280)"
    TAXES = "Income Taxes & Deferred Tax Valuation (ASC 740)"
    IMPAIRMENTS = "Impairments, Goodwill & Intangibles (ASC 350/820)"
    RELATED_PARTIES = "Related-Party Transactions & Governance (ASC 850)"
    ACCOUNTING_CHANGES = "Changes in Accounting Estimates & Standards"
    OTHER_MATERIAL = "Capital Structure & Material Disclosures"

    @classmethod
    def icon(cls, value: str) -> str:
        icons = {
            cls.ACCOUNTING_POLICIES: "📜",
            cls.DEBT_FINANCING: "💳",
            cls.LEASES: "🏢",
            cls.CONTINGENCIES: "⚖️",
            cls.SEGMENTS: "🌐",
            cls.TAXES: "🏛️",
            cls.IMPAIRMENTS: "📉",
            cls.RELATED_PARTIES: "🤝",
            cls.ACCOUNTING_CHANGES: "🔄",
            cls.OTHER_MATERIAL: "📌",
        }
        return icons.get(value, "📝")


class ObservationReviewStatus(str, Enum):
    """User audit and review status for AI-assisted observations."""
    PENDING = "pending"
    REVIEWED = "reviewed"
    RELEVANT = "relevant"
    NOT_RELEVANT = "not_relevant"
    REQUIRES_FOLLOWUP = "requires_followup"

    @classmethod
    def display_name(cls, value: str) -> str:
        names = {
            cls.PENDING: "Pending Review",
            cls.REVIEWED: "Reviewed",
            cls.RELEVANT: "Flagged Relevant",
            cls.NOT_RELEVANT: "Not Relevant",
            cls.REQUIRES_FOLLOWUP: "Requires Follow-up",
        }
        return names.get(value, value.title())


@dataclass
class FilingMetadata:
    """Metadata describing a discovered or ingested SEC filing."""
    ticker: Optional[str]
    cik: str
    company_name: str
    form_type: str
    accession_number: str
    filing_date: str
    report_date: str
    fiscal_year: Optional[int] = None
    fiscal_period: Optional[str] = None
    primary_document: Optional[str] = None
    primary_doc_url: Optional[str] = None
    local_cache_path: Optional[str] = None
    is_amended: bool = False
    amends_accession: Optional[str] = None
    status: str = "Discovered"  # Discovered, Retrieved, Parsed, Analyzed
    id: Optional[int] = None
    company_id: Optional[int] = None

    @property
    def display_label(self) -> str:
        """Formatted human-readable filing label."""
        amend_badge = " [AMENDED]" if self.is_amended else ""
        period_str = f"FY{self.fiscal_year}" if self.fiscal_year else f"Period {self.report_date}"
        if self.fiscal_period and self.fiscal_period != "FY":
            period_str = f"{self.fiscal_period} {self.fiscal_year or ''}".strip()
        return f"{self.form_type}{amend_badge} • {period_str} (Filed: {self.filing_date}) - {self.accession_number}"


@dataclass
class ExtractedStatementItem:
    """Candidate financial statement line item extracted from filing or XBRL facts."""
    statement_type: str  # income_statement, balance_sheet, cash_flow_statement
    line_item_code: str  # Standard canonical code
    display_name: str
    source_label: str  # Label in filing (e.g. 'Revenues', 'SalesRevenueNet')
    period_start_date: str
    period_end_date: str
    period_type: str  # annual, quarterly
    value: float
    currency: str = "USD"
    unit: str = "units"
    is_derived: bool = False
    confidence_score: float = 1.0
    source_location: str = "SEC EDGAR XBRL / Statement Table"
    selected: bool = True  # User review toggle for import


@dataclass
class FootnoteObservationData:
    """Structured AI-generated or NLP-extracted disclosure observation."""
    category: str
    summary: str
    source_section: str
    source_location: str
    source_quote: Optional[str] = None
    explicit_facts: Optional[str] = None
    potential_implications: Optional[str] = None
    confidence_score: float = 1.0
    review_status: str = "pending"
    user_notes: Optional[str] = None
    id: Optional[int] = None
    filing_id: Optional[int] = None


@dataclass
class FilingAnalysisBundle:
    """Consolidated container holding parsed statements, observations, and raw filing info."""
    filing: FilingMetadata
    extracted_items: List[ExtractedStatementItem] = field(default_factory=list)
    observations: List[FootnoteObservationData] = field(default_factory=list)
    footnote_sections: Dict[str, str] = field(default_factory=dict)
    retrieval_timestamp: str = field(default_factory=lambda: datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC"))
    diagnostic_notes: List[str] = field(default_factory=list)
