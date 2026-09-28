"""Historical financial statement analysis package.

Provides deterministic calculation routines for revenue growth, multi-year CAGR,
profitability margins, operating expenses, capital expenditures, working capital
efficiency indicators (DSO, DIO, DPO, CCC), and historical cash flow metrics.
"""

from src.analysis.engine import HistoricalAnalysisEngine
from src.analysis.models import (
    DataQualityIssue,
    FinancialPeriod,
    HistoricalAnalysisBundle,
    MetricResult,
    WorkingCapitalMetrics,
    CashFlowAnalysisMetrics,
)
from src.analysis.formatting import (
    generate_income_statement_table,
    generate_balance_sheet_table,
    generate_cash_flow_table,
    generate_efficiency_table,
)

__all__ = [
    "HistoricalAnalysisEngine",
    "HistoricalAnalysisBundle",
    "FinancialPeriod",
    "MetricResult",
    "WorkingCapitalMetrics",
    "CashFlowAnalysisMetrics",
    "DataQualityIssue",
    "generate_income_statement_table",
    "generate_balance_sheet_table",
    "generate_cash_flow_table",
    "generate_efficiency_table",
]
