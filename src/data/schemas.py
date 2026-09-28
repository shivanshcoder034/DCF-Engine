"""Standardized schemas, enumerations, and line-item catalogs for financial data.

Defines statement types, reporting period types, data classifications, units,
standard financial line-item codes, and validation result data structures.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from enum import Enum
from typing import Any, Dict, List, Optional


class StatementType(str, Enum):
    """Supported financial statement types."""
    INCOME_STATEMENT = "income_statement"
    BALANCE_SHEET = "balance_sheet"
    CASH_FLOW_STATEMENT = "cash_flow_statement"

    @classmethod
    def display_name(cls, value: str) -> str:
        names = {
            cls.INCOME_STATEMENT: "Income Statement",
            cls.BALANCE_SHEET: "Balance Sheet",
            cls.CASH_FLOW_STATEMENT: "Cash Flow Statement",
        }
        return names.get(value, value.replace("_", " ").title())


class PeriodType(str, Enum):
    """Supported financial reporting period frequencies."""
    ANNUAL = "annual"
    QUARTERLY = "quarterly"

    @classmethod
    def display_name(cls, value: str) -> str:
        names = {
            cls.ANNUAL: "Annual (12M)",
            cls.QUARTERLY: "Quarterly (3M)",
        }
        return names.get(value, value.title())


class DataClassification(str, Enum):
    """Classification of stored financial data points."""
    REPORTED_ACTUAL = "reported_actual"
    NORMALIZED = "normalized"
    ADJUSTMENT = "adjustment"
    ASSUMPTION = "assumption"

    @classmethod
    def display_name(cls, value: str) -> str:
        names = {
            cls.REPORTED_ACTUAL: "Reported Actual",
            cls.NORMALIZED: "Normalized Figure",
            cls.ADJUSTMENT: "Audit/Model Adjustment",
            cls.ASSUMPTION: "Model Assumption",
        }
        return names.get(value, value.replace("_", " ").title())

    @classmethod
    def description(cls, value: str) -> str:
        descs = {
            cls.REPORTED_ACTUAL: "Historical figures directly as reported in public regulatory filings or audits.",
            cls.NORMALIZED: "Historical figures adjusted for one-off, non-recurring items or accounting standard alignments.",
            cls.ADJUSTMENT: "Specific discretionary or pro-forma adjustments made by the financial analyst.",
            cls.ASSUMPTION: "Foundational baseline assumption placeholder for multi-period model calibration.",
        }
        return descs.get(value, "")


class SourceType(str, Enum):
    """Origin of financial data points."""
    MANUAL_ENTRY = "manual_entry"
    CSV_IMPORT = "csv_import"
    EXCEL_IMPORT = "excel_import"
    SEC_FILING = "sec_filing"
    DOCUMENT_EXTRACTION = "document_extraction"


class FinancialUnit(str, Enum):
    """Scale or multiplier applied to numeric financial figures."""
    UNITS = "units"
    THOUSANDS = "thousands"
    MILLIONS = "millions"
    BILLIONS = "billions"

    @classmethod
    def multiplier(cls, value: str) -> float:
        multipliers = {
            cls.UNITS: 1.0,
            cls.THOUSANDS: 1_000.0,
            cls.MILLIONS: 1_000_000.0,
            cls.BILLIONS: 1_000_000_000.0,
        }
        return multipliers.get(value, 1.0)


class ProjectStatus(str, Enum):
    """Status lifecycle for valuation projects."""
    ACTIVE = "Active"
    ARCHIVED = "Archived"


# ==============================================================================
# Standardized Financial Line Items Catalog
# ==============================================================================

@dataclass(frozen=True)
class LineItemDefinition:
    """Metadata definition for a standardized financial statement line item."""
    code: str
    display_name: str
    statement_type: StatementType
    description: str
    is_standard: bool = True


STANDARD_LINE_ITEMS: Dict[str, LineItemDefinition] = {
    # ---------------- Income Statement ----------------
    "revenue": LineItemDefinition(
        code="revenue",
        display_name="Revenue",
        statement_type=StatementType.INCOME_STATEMENT,
        description="Gross inflows of economic benefits from primary operating activities.",
    ),
    "cogs": LineItemDefinition(
        code="cogs",
        display_name="Cost of Goods Sold",
        statement_type=StatementType.INCOME_STATEMENT,
        description="Direct costs attributable to the production of goods sold or services rendered.",
    ),
    "gross_profit": LineItemDefinition(
        code="gross_profit",
        display_name="Gross Profit",
        statement_type=StatementType.INCOME_STATEMENT,
        description="Revenue minus Cost of Goods Sold.",
    ),
    "operating_expenses": LineItemDefinition(
        code="operating_expenses",
        display_name="Operating Expenses",
        statement_type=StatementType.INCOME_STATEMENT,
        description="Selling, general, administrative (SG&A), and R&D operating expenses.",
    ),
    "ebitda": LineItemDefinition(
        code="ebitda",
        display_name="EBITDA",
        statement_type=StatementType.INCOME_STATEMENT,
        description="Operating earnings before interest, taxes, depreciation, and amortization.",
    ),
    "depreciation_amortization": LineItemDefinition(
        code="depreciation_amortization",
        display_name="Depreciation and Amortization",
        statement_type=StatementType.INCOME_STATEMENT,
        description="Non-cash expense reflecting the consumption of tangible and intangible fixed assets.",
    ),
    "ebit": LineItemDefinition(
        code="ebit",
        display_name="EBIT",
        statement_type=StatementType.INCOME_STATEMENT,
        description="Operating profit before interest expenses and income taxes.",
    ),
    "interest_expense": LineItemDefinition(
        code="interest_expense",
        display_name="Interest Expense",
        statement_type=StatementType.INCOME_STATEMENT,
        description="Cost of borrowed funds and debt service.",
    ),
    "profit_before_tax": LineItemDefinition(
        code="profit_before_tax",
        display_name="Profit Before Tax",
        statement_type=StatementType.INCOME_STATEMENT,
        description="Earnings before corporate income tax provisions.",
    ),
    "income_tax_expense": LineItemDefinition(
        code="income_tax_expense",
        display_name="Income Tax Expense",
        statement_type=StatementType.INCOME_STATEMENT,
        description="Total current and deferred tax provision.",
    ),
    "net_income": LineItemDefinition(
        code="net_income",
        display_name="Net Income",
        statement_type=StatementType.INCOME_STATEMENT,
        description="Residual bottom-line net profit attributable to shareholders.",
    ),

    # ---------------- Balance Sheet ----------------
    "cash_and_equivalents": LineItemDefinition(
        code="cash_and_equivalents",
        display_name="Cash and Cash Equivalents",
        statement_type=StatementType.BALANCE_SHEET,
        description="Cash on hand, bank deposits, and highly liquid short-term investments.",
    ),
    "accounts_receivable": LineItemDefinition(
        code="accounts_receivable",
        display_name="Accounts Receivable",
        statement_type=StatementType.BALANCE_SHEET,
        description="Amounts owed to the company by customers for delivered goods or services.",
    ),
    "inventory": LineItemDefinition(
        code="inventory",
        display_name="Inventory",
        statement_type=StatementType.BALANCE_SHEET,
        description="Raw materials, work-in-progress, and finished goods held for sale.",
    ),
    "other_current_assets": LineItemDefinition(
        code="other_current_assets",
        display_name="Other Current Assets",
        statement_type=StatementType.BALANCE_SHEET,
        description="Prepaid expenses and short-term liquid receivables.",
    ),
    "total_current_assets": LineItemDefinition(
        code="total_current_assets",
        display_name="Total Current Assets",
        statement_type=StatementType.BALANCE_SHEET,
        description="Sum of all liquid assets expected to be converted to cash within 12 months.",
    ),
    "ppe": LineItemDefinition(
        code="ppe",
        display_name="Property, Plant and Equipment",
        statement_type=StatementType.BALANCE_SHEET,
        description="Net book value of tangible long-term productive assets.",
    ),
    "total_assets": LineItemDefinition(
        code="total_assets",
        display_name="Total Assets",
        statement_type=StatementType.BALANCE_SHEET,
        description="Sum of all current and non-current economic resources owned.",
    ),
    "accounts_payable": LineItemDefinition(
        code="accounts_payable",
        display_name="Accounts Payable",
        statement_type=StatementType.BALANCE_SHEET,
        description="Short-term obligations owed to suppliers for goods and services received.",
    ),
    "short_term_debt": LineItemDefinition(
        code="short_term_debt",
        display_name="Short-Term Debt",
        statement_type=StatementType.BALANCE_SHEET,
        description="Current portion of long-term borrowings and commercial paper due within one year.",
    ),
    "other_current_liabilities": LineItemDefinition(
        code="other_current_liabilities",
        display_name="Other Current Liabilities",
        statement_type=StatementType.BALANCE_SHEET,
        description="Accrued expenses, deferred revenues, and other short-term obligations.",
    ),
    "total_current_liabilities": LineItemDefinition(
        code="total_current_liabilities",
        display_name="Total Current Liabilities",
        statement_type=StatementType.BALANCE_SHEET,
        description="Sum of all obligations maturing within one fiscal year.",
    ),
    "long_term_debt": LineItemDefinition(
        code="long_term_debt",
        display_name="Long-Term Debt",
        statement_type=StatementType.BALANCE_SHEET,
        description="Outstanding loans, bonds, and notes payable due after one year.",
    ),
    "total_liabilities": LineItemDefinition(
        code="total_liabilities",
        display_name="Total Liabilities",
        statement_type=StatementType.BALANCE_SHEET,
        description="Sum of all current and non-current financial obligations.",
    ),
    "total_equity": LineItemDefinition(
        code="total_equity",
        display_name="Total Equity",
        statement_type=StatementType.BALANCE_SHEET,
        description="Total net assets: share capital, retained earnings, and reserves.",
    ),

    # ---------------- Cash Flow Statement ----------------
    "cfo": LineItemDefinition(
        code="cfo",
        display_name="Cash Flow from Operating Activities",
        statement_type=StatementType.CASH_FLOW_STATEMENT,
        description="Net cash generated from regular business operational transactions.",
    ),
    "capex": LineItemDefinition(
        code="capex",
        display_name="Capital Expenditure",
        statement_type=StatementType.CASH_FLOW_STATEMENT,
        description="Cash invested in purchasing or upgrading fixed physical assets (PP&E).",
    ),
    "cfi": LineItemDefinition(
        code="cfi",
        display_name="Cash Flow from Investing Activities",
        statement_type=StatementType.CASH_FLOW_STATEMENT,
        description="Net cash deployed into or received from investments and capital assets.",
    ),
    "cff": LineItemDefinition(
        code="cff",
        display_name="Cash Flow from Financing Activities",
        statement_type=StatementType.CASH_FLOW_STATEMENT,
        description="Net cash flows from debt issuance/repayments, equity issuance, and dividend distributions.",
    ),
    "net_change_in_cash": LineItemDefinition(
        code="net_change_in_cash",
        display_name="Net Change in Cash",
        statement_type=StatementType.CASH_FLOW_STATEMENT,
        description="Net aggregate increase or decrease in cash over the reporting period.",
    ),
}


def get_standard_items_by_statement(statement_type: StatementType | str) -> List[LineItemDefinition]:
    """Return all standard line item definitions for a given statement type."""
    target_val = statement_type.value if isinstance(statement_type, StatementType) else statement_type
    return [
        item for item in STANDARD_LINE_ITEMS.values()
        if item.statement_type.value == target_val
    ]


@dataclass
class ValidationIssue:
    """Represents a specific validation warning or error."""
    field: str
    message: str
    is_error: bool = True  # True = blocking error; False = review warning


@dataclass
class RecordValidationResult:
    """Validation outcome for an individual financial record."""
    is_valid: bool
    record_index: Optional[int] = None
    data: Optional[Dict[str, Any]] = None
    issues: List[ValidationIssue] = field(default_factory=list)

    @property
    def errors(self) -> List[ValidationIssue]:
        return [i for i in self.issues if i.is_error]

    @property
    def warnings(self) -> List[ValidationIssue]:
        return [i for i in self.issues if not i.is_error]
