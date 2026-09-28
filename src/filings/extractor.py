"""Financial statement line-item extractor mapping SEC XBRL facts and statement tables to canonical items.

Maps official US-GAAP taxonomy tags to the platform's standardized line-item catalog,
providing side-by-side original label and candidate mapping for user verification.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Tuple

from src.data.schemas import STANDARD_LINE_ITEMS, StatementType
from src.filings.models import ExtractedStatementItem, FilingMetadata

logger = logging.getLogger(__name__)


# Standard US-GAAP taxonomy concepts mapped to platform canonical line-item codes
US_GAAP_TAG_MAPPING: Dict[str, Dict[str, Any]] = {
    # ---------------- Income Statement ----------------
    "revenue": {
        "statement_type": "income_statement",
        "tags": [
            "RevenueFromContractWithCustomerExcludingAssessedTax",
            "Revenues",
            "SalesRevenueNet",
            "SalesRevenueGoodsNet",
            "TotalRevenuesAndOtherIncome",
        ],
        "display_name": "Revenue",
    },
    "cogs": {
        "statement_type": "income_statement",
        "tags": [
            "CostOfGoodsAndServicesSold",
            "CostOfGoodsSold",
            "CostOfRevenue",
        ],
        "display_name": "Cost of Goods Sold",
    },
    "gross_profit": {
        "statement_type": "income_statement",
        "tags": [
            "GrossProfit",
        ],
        "display_name": "Gross Profit",
    },
    "operating_expenses": {
        "statement_type": "income_statement",
        "tags": [
            "OperatingExpenses",
            "SellingGeneralAndAdministrativeExpense",
        ],
        "display_name": "Operating Expenses",
    },
    "depreciation_amortization": {
        "statement_type": "income_statement",
        "tags": [
            "DepreciationAndAmortization",
            "DepreciationDepletionAndAmortization",
            "Depreciation",
            "AmortizationOfIntangibleAssets",
        ],
        "display_name": "Depreciation and Amortization",
    },
    "ebit": {
        "statement_type": "income_statement",
        "tags": [
            "OperatingIncomeLoss",
        ],
        "display_name": "EBIT",
    },
    "interest_expense": {
        "statement_type": "income_statement",
        "tags": [
            "InterestExpense",
            "InterestAndDebtExpense",
        ],
        "display_name": "Interest Expense",
    },
    "profit_before_tax": {
        "statement_type": "income_statement",
        "tags": [
            "IncomeLossFromContinuingOperationsBeforeIncomeTaxesMinorityInterestAndIncomeLossFromEquityMethodInvestments",
            "IncomeLossFromContinuingOperationsBeforeIncomeTaxesExtraordinaryItemsNoncontrollingInterest",
        ],
        "display_name": "Profit Before Tax",
    },
    "income_tax_expense": {
        "statement_type": "income_statement",
        "tags": [
            "IncomeTaxExpenseBenefit",
        ],
        "display_name": "Income Tax Expense",
    },
    "net_income": {
        "statement_type": "income_statement",
        "tags": [
            "NetIncomeLoss",
            "ProfitLoss",
        ],
        "display_name": "Net Income",
    },

    # ---------------- Balance Sheet ----------------
    "cash_and_equivalents": {
        "statement_type": "balance_sheet",
        "tags": [
            "CashAndCashEquivalentsAtCarryingValue",
            "CashCashEquivalentsAndShortTermInvestments",
            "Cash",
        ],
        "display_name": "Cash and Cash Equivalents",
    },
    "accounts_receivable": {
        "statement_type": "balance_sheet",
        "tags": [
            "AccountsReceivableNetCurrent",
            "NontradeReceivablesCurrent",
        ],
        "display_name": "Accounts Receivable",
    },
    "inventory": {
        "statement_type": "balance_sheet",
        "tags": [
            "InventoryNet",
            "Inventories",
        ],
        "display_name": "Inventory",
    },
    "other_current_assets": {
        "statement_type": "balance_sheet",
        "tags": [
            "OtherAssetsCurrent",
            "PrepaidExpenseAndOtherAssetsCurrent",
        ],
        "display_name": "Other Current Assets",
    },
    "total_current_assets": {
        "statement_type": "balance_sheet",
        "tags": [
            "AssetsCurrent",
        ],
        "display_name": "Total Current Assets",
    },
    "ppe": {
        "statement_type": "balance_sheet",
        "tags": [
            "PropertyPlantAndEquipmentNet",
        ],
        "display_name": "Property, Plant and Equipment",
    },
    "total_assets": {
        "statement_type": "balance_sheet",
        "tags": [
            "Assets",
        ],
        "display_name": "Total Assets",
    },
    "accounts_payable": {
        "statement_type": "balance_sheet",
        "tags": [
            "AccountsPayableCurrent",
        ],
        "display_name": "Accounts Payable",
    },
    "short_term_debt": {
        "statement_type": "balance_sheet",
        "tags": [
            "DebtCurrent",
            "ShortTermBorrowings",
            "CommercialPaper",
        ],
        "display_name": "Short-Term Debt",
    },
    "other_current_liabilities": {
        "statement_type": "balance_sheet",
        "tags": [
            "OtherLiabilitiesCurrent",
            "AccruedLiabilitiesCurrent",
        ],
        "display_name": "Other Current Liabilities",
    },
    "total_current_liabilities": {
        "statement_type": "balance_sheet",
        "tags": [
            "LiabilitiesCurrent",
        ],
        "display_name": "Total Current Liabilities",
    },
    "long_term_debt": {
        "statement_type": "balance_sheet",
        "tags": [
            "LongTermDebtNoncurrent",
            "LongTermDebtAndCapitalLeaseObligations",
            "LongTermDebt",
        ],
        "display_name": "Long-Term Debt",
    },
    "total_liabilities": {
        "statement_type": "balance_sheet",
        "tags": [
            "Liabilities",
        ],
        "display_name": "Total Liabilities",
    },
    "total_equity": {
        "statement_type": "balance_sheet",
        "tags": [
            "StockholdersEquity",
            "StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest",
        ],
        "display_name": "Total Equity",
    },

    # ---------------- Cash Flow Statement ----------------
    "cfo": {
        "statement_type": "cash_flow_statement",
        "tags": [
            "NetCashProvidedByUsedInOperatingActivities",
        ],
        "display_name": "Cash Flow from Operating Activities",
    },
    "capex": {
        "statement_type": "cash_flow_statement",
        "tags": [
            "PaymentsToAcquirePropertyPlantAndEquipment",
            "PaymentsToAcquireProductiveAssets",
        ],
        "display_name": "Capital Expenditure",
    },
    "cfi": {
        "statement_type": "cash_flow_statement",
        "tags": [
            "NetCashProvidedByUsedInInvestingActivities",
        ],
        "display_name": "Cash Flow from Investing Activities",
    },
    "cff": {
        "statement_type": "cash_flow_statement",
        "tags": [
            "NetCashProvidedByUsedInFinancingActivities",
        ],
        "display_name": "Cash Flow from Financing Activities",
    },
}


class StatementExtractor:
    """Extracts candidate financial statement line items from official SEC facts and table parsing."""

    def __init__(self) -> None:
        pass

    def extract_from_company_facts(
        self,
        company_facts: Dict[str, Any],
        filing: FilingMetadata,
    ) -> List[ExtractedStatementItem]:
        """Extract statement items matching the specific filing from official SEC US-GAAP facts."""
        if not company_facts or "facts" not in company_facts:
            return []

        us_gaap = company_facts.get("facts", {}).get("us-gaap", {})
        if not us_gaap:
            return []

        extracted_items: List[ExtractedStatementItem] = []
        filing_accn = filing.accession_number
        is_annual = filing.form_type.startswith("10-K")
        period_type = "annual" if is_annual else "quarterly"

        for code, mapping in US_GAAP_TAG_MAPPING.items():
            tags = mapping["tags"]
            statement_type = mapping["statement_type"]
            display_name = mapping["display_name"]

            matched_fact: Optional[Dict[str, Any]] = None
            matched_tag: Optional[str] = None

            for tag in tags:
                if tag in us_gaap:
                    tag_data = us_gaap[tag]
                    units_dict = tag_data.get("units", {})
                    # Standard financial figures in USD or shares
                    unit_key = "USD" if "USD" in units_dict else (list(units_dict.keys())[0] if units_dict else None)
                    if not unit_key:
                        continue

                    records = units_dict.get(unit_key, [])

                    # Match by accession number first
                    candidates = [r for r in records if r.get("accn") == filing_accn]

                    # If not matched by accession directly, match by form, fiscal year, and end date
                    if not candidates and filing.fiscal_year and filing.report_date:
                        target_form = filing.form_type.split("/")[0]  # Strip /A
                        candidates = [
                            r for r in records
                            if r.get("form") in (target_form, filing.form_type)
                            and str(r.get("end")) == filing.report_date
                        ]

                    if candidates:
                        # For income/cash flow statements, choose the 12-month (annual) or 3-month (quarterly) slice
                        if statement_type in ("income_statement", "cash_flow_statement") and len(candidates) > 1:
                            if is_annual:
                                # Pick record with longest frame or start/end ~360 days apart
                                best = candidates[0]
                                for c in candidates:
                                    start = c.get("start")
                                    end = c.get("end")
                                    if start and end:
                                        try:
                                            days = (date_from_str(end) - date_from_str(start)).days
                                            if 330 <= days <= 380:
                                                best = c
                                                break
                                        except Exception:
                                            pass
                                matched_fact = best
                            else:
                                # Quarterly: pick ~90 days
                                best = candidates[0]
                                for c in candidates:
                                    start = c.get("start")
                                    end = c.get("end")
                                    if start and end:
                                        try:
                                            days = (date_from_str(end) - date_from_str(start)).days
                                            if 80 <= days <= 100:
                                                best = c
                                                break
                                        except Exception:
                                            pass
                                matched_fact = best
                        else:
                            matched_fact = candidates[-1]

                        matched_tag = tag
                        break

            if matched_fact is not None and matched_tag is not None:
                val = float(matched_fact.get("val", 0.0))
                end_date = str(matched_fact.get("end", filing.report_date))
                start_date = str(matched_fact.get("start", end_date))

                item = ExtractedStatementItem(
                    statement_type=statement_type,
                    line_item_code=code,
                    display_name=display_name,
                    source_label=f"us-gaap:{matched_tag}",
                    period_start_date=start_date,
                    period_end_date=end_date,
                    period_type=period_type,
                    value=val,
                    currency="USD",
                    unit="units",
                    is_derived=False,
                    confidence_score=0.98,
                    source_location=f"SEC EDGAR XBRL (accn: {matched_fact.get('accn', filing_accn)})",
                    selected=True,
                )
                extracted_items.append(item)

        # Derive Gross Profit if Revenue & COGS exist and Gross Profit wasn't directly tagged
        has_gp = any(i.line_item_code == "gross_profit" for i in extracted_items)
        rev_item = next((i for i in extracted_items if i.line_item_code == "revenue"), None)
        cogs_item = next((i for i in extracted_items if i.line_item_code == "cogs"), None)

        if not has_gp and rev_item and cogs_item:
            gp_val = rev_item.value - cogs_item.value
            extracted_items.append(
                ExtractedStatementItem(
                    statement_type="income_statement",
                    line_item_code="gross_profit",
                    display_name="Gross Profit",
                    source_label="Derived: Revenue - COGS",
                    period_start_date=rev_item.period_start_date,
                    period_end_date=rev_item.period_end_date,
                    period_type=period_type,
                    value=gp_val,
                    currency="USD",
                    unit="units",
                    is_derived=True,
                    confidence_score=0.95,
                    source_location="Calculated from extracted Revenue and COGS",
                    selected=True,
                )
            )

        # Derive EBITDA if EBIT and D&A exist and EBITDA wasn't directly tagged
        has_ebitda = any(i.line_item_code == "ebitda" for i in extracted_items)
        ebit_item = next((i for i in extracted_items if i.line_item_code == "ebit"), None)
        dna_item = next((i for i in extracted_items if i.line_item_code == "depreciation_amortization"), None)

        if not has_ebitda and ebit_item and dna_item:
            ebitda_val = ebit_item.value + dna_item.value
            extracted_items.append(
                ExtractedStatementItem(
                    statement_type="income_statement",
                    line_item_code="ebitda",
                    display_name="EBITDA",
                    source_label="Derived: EBIT + D&A",
                    period_start_date=ebit_item.period_start_date,
                    period_end_date=ebit_item.period_end_date,
                    period_type=period_type,
                    value=ebitda_val,
                    currency="USD",
                    unit="units",
                    is_derived=True,
                    confidence_score=0.95,
                    source_location="Calculated from extracted EBIT and D&A",
                    selected=True,
                )
            )

        return extracted_items


def date_from_str(s: str):
    """Helper to parse YYYY-MM-DD string into date object."""
    from datetime import datetime
    return datetime.strptime(s.strip()[:10], "%Y-%m-%d").date()
