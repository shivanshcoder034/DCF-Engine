"""Data models and output structures for historical financial analysis.

Defines typed dataclasses for reporting periods, individual metrics,
historical financial statement summaries, and complete analysis bundles.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Any, Dict, List, Optional


@dataclass(frozen=True)
class FinancialPeriod:
    """Represents a discrete financial reporting period."""
    start_date: date
    end_date: date
    period_type: str  # annual or quarterly
    label: str  # e.g. "FY2023" or "2023-12-31"

    @property
    def duration_days(self) -> int:
        return (self.end_date - self.start_date).days + 1


@dataclass
class MetricResult:
    """Calculated or reported financial metric for a specific period."""
    metric_code: str
    metric_name: str
    value: Optional[float]
    unit_or_type: str  # "percentage", "currency", "ratio", "days", "units"
    period_label: str
    is_reported: bool = False
    source_line_items: List[str] = field(default_factory=list)
    status: str = "calculated"  # "calculated", "reported", "unavailable", "warning"
    explanation: Optional[str] = None

    @property
    def is_available(self) -> bool:
        return self.value is not None


@dataclass
class WorkingCapitalMetrics:
    """Working capital and cash cycle indicators for a period."""
    period_label: str
    current_assets: Optional[float] = None
    current_liabilities: Optional[float] = None
    net_working_capital: Optional[float] = None
    operating_nwc: Optional[float] = None
    delta_nwc: Optional[float] = None
    dso: Optional[float] = None
    dio: Optional[float] = None
    dpo: Optional[float] = None
    cash_conversion_cycle: Optional[float] = None
    is_ending_balance_approx: bool = False
    notes: List[str] = field(default_factory=list)


@dataclass
class CashFlowAnalysisMetrics:
    """Operating cash flow, CapEx, and historical free cash flow measures."""
    period_label: str
    operating_cash_flow: Optional[float] = None
    capex_magnitude: Optional[float] = None
    capex_pct_revenue: Optional[float] = None
    cfo_less_capex: Optional[float] = None
    ufcf_estimate: Optional[float] = None
    effective_tax_rate: Optional[float] = None
    ufcf_missing_inputs: List[str] = field(default_factory=list)
    notes: List[str] = field(default_factory=list)


@dataclass
class DataQualityIssue:
    """Audit warning regarding data consistency or completeness."""
    severity: str  # "warning", "info", "error"
    category: str  # "missing_data", "conflict", "period_alignment", "zero_denominator"
    message: str
    affected_periods: List[str] = field(default_factory=list)
    affected_items: List[str] = field(default_factory=list)


@dataclass
class HistoricalAnalysisBundle:
    """Comprehensive historical financial analysis results for a valuation project."""
    project_id: int
    project_name: str
    company_name: str
    ticker: Optional[str]
    reporting_currency: str
    display_unit: str  # e.g. "millions" or "units"
    data_classification: str
    period_type: str
    periods: List[FinancialPeriod] = field(default_factory=list)
    metrics_by_period: Dict[str, Dict[str, MetricResult]] = field(default_factory=dict)
    working_capital: Dict[str, WorkingCapitalMetrics] = field(default_factory=dict)
    cash_flow_metrics: Dict[str, CashFlowAnalysisMetrics] = field(default_factory=dict)
    cagr_results: Dict[str, MetricResult] = field(default_factory=dict)
    raw_line_items_by_period: Dict[str, Dict[str, float]] = field(default_factory=dict)
    quality_issues: List[DataQualityIssue] = field(default_factory=list)
