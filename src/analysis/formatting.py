"""Formatting and presentation table generators for historical financial analysis.

Transforms analytical results into structured, transparent pandas DataFrames
annotated with unit scales, currency indicators, and calculation status.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

import pandas as pd

from src.analysis.models import HistoricalAnalysisBundle


def format_currency_value(val: Optional[float], scale_divisor: float = 1.0) -> str:
    """Format numeric financial value to comma-separated string, or return '-' if missing."""
    if val is None or pd.isna(val):
        return "—"
    scaled = val / scale_divisor
    return f"{scaled:,.2f}"


def format_percentage_value(val: Optional[float]) -> str:
    """Format percentage value with one decimal place and % sign, or return '-' if missing."""
    if val is None or pd.isna(val):
        return "—"
    return f"{val:.1f}%"


def format_days_value(val: Optional[float]) -> str:
    """Format days value with one decimal place, or return '-' if missing."""
    if val is None or pd.isna(val):
        return "—"
    return f"{val:.1f} days"


def generate_income_statement_table(
    bundle: HistoricalAnalysisBundle,
    scale_divisor: float = 1_000_000.0,
) -> pd.DataFrame:
    """Generate structured multi-period Income Statement & Margin DataFrame."""
    period_labels = [p.label for p in bundle.periods]
    if not period_labels:
        return pd.DataFrame()

    row_definitions = [
        ("Revenue", "revenue", "currency", False),
        ("  YoY Revenue Growth", "revenue_growth", "percentage", True),
        ("Cost of Goods Sold (COGS)", "cogs", "raw_currency", False),
        ("Gross Profit", "gross_profit", "currency_metric", True),
        ("  Gross Profit Margin", "gross_margin", "percentage", True),
        ("Operating Expenses (OpEx)", "operating_expenses", "currency", False),
        ("EBITDA", "ebitda", "currency_metric", True),
        ("  EBITDA Margin", "ebitda_margin", "percentage", True),
        ("Depreciation & Amortization", "depreciation_amortization", "raw_currency", False),
        ("EBIT (Operating Profit)", "ebit", "currency", False),
        ("  EBIT Margin", "ebit_margin", "percentage", True),
        ("Profit Before Tax (PBT)", "profit_before_tax", "raw_currency", False),
        ("Income Tax Expense", "income_tax_expense", "raw_currency", False),
        ("  Effective Tax Rate", "effective_tax_rate", "percentage", True),
        ("Net Income", "net_income", "currency", False),
        ("  Net Profit Margin", "net_margin", "percentage", True),
    ]

    data_rows = []
    for display_label, code, val_type, is_derived in row_definitions:
        row: Dict[str, Any] = {
            "Line Item": display_label,
            "Type": "Derived / Calculated" if is_derived else "Reported",
        }
        for p in period_labels:
            p_metrics = bundle.metrics_by_period.get(p, {})
            raw_items = bundle.raw_line_items_by_period.get(p, {})

            if val_type == "currency":
                val = p_metrics[code].value if code in p_metrics else raw_items.get(code)
                row[p] = format_currency_value(val, scale_divisor)
            elif val_type == "raw_currency":
                val = raw_items.get(code)
                row[p] = format_currency_value(val, scale_divisor)
            elif val_type == "currency_metric":
                val = p_metrics[code].value if code in p_metrics else None
                row[p] = format_currency_value(val, scale_divisor)
            elif val_type == "percentage":
                val = p_metrics[code].value if code in p_metrics else None
                row[p] = format_percentage_value(val)

        data_rows.append(row)

    return pd.DataFrame(data_rows)


def generate_balance_sheet_table(
    bundle: HistoricalAnalysisBundle,
    scale_divisor: float = 1_000_000.0,
) -> pd.DataFrame:
    """Generate structured multi-period Balance Sheet & Working Capital DataFrame."""
    period_labels = [p.label for p in bundle.periods]
    if not period_labels:
        return pd.DataFrame()

    row_defs = [
        ("Cash & Cash Equivalents", "cash_and_equivalents", "raw", False),
        ("Accounts Receivable", "accounts_receivable", "raw", False),
        ("Inventory", "inventory", "raw", False),
        ("Other Current Assets", "other_current_assets", "raw", False),
        ("Total Current Assets", "total_current_assets", "ca", True),
        ("Property, Plant & Equipment (PP&E)", "ppe", "raw", False),
        ("Total Assets", "total_assets", "raw", False),
        ("Accounts Payable", "accounts_payable", "raw", False),
        ("Short-Term Debt", "short_term_debt", "raw", False),
        ("Other Current Liabilities", "other_current_liabilities", "raw", False),
        ("Total Current Liabilities", "total_current_liabilities", "cl", True),
        ("Long-Term Debt", "long_term_debt", "raw", False),
        ("Total Liabilities", "total_liabilities", "raw", False),
        ("Total Equity", "total_equity", "raw", False),
        ("Net Working Capital (CA - CL)", "nwc", "nwc", True),
        ("Operating Working Capital (AR + Inv - AP)", "op_nwc", "op_nwc", True),
        ("Change in Net Working Capital (ΔNWC)", "delta_nwc", "delta_nwc", True),
    ]

    data_rows = []
    for display_label, code, row_type, is_derived in row_defs:
        row: Dict[str, Any] = {
            "Balance Sheet Item": display_label,
            "Type": "Derived / Calculated" if is_derived else "Reported",
        }
        for p in period_labels:
            raw_items = bundle.raw_line_items_by_period.get(p, {})
            wc = bundle.working_capital.get(p)

            if row_type == "raw":
                val = raw_items.get(code)
            elif row_type == "ca":
                val = wc.current_assets if wc else raw_items.get("total_current_assets")
            elif row_type == "cl":
                val = wc.current_liabilities if wc else raw_items.get("total_current_liabilities")
            elif row_type == "nwc":
                val = wc.net_working_capital if wc else None
            elif row_type == "op_nwc":
                val = wc.operating_nwc if wc else None
            elif row_type == "delta_nwc":
                val = wc.delta_nwc if wc else None
            else:
                val = None

            row[p] = format_currency_value(val, scale_divisor)

        data_rows.append(row)

    return pd.DataFrame(data_rows)


def generate_cash_flow_table(
    bundle: HistoricalAnalysisBundle,
    scale_divisor: float = 1_000_000.0,
) -> pd.DataFrame:
    """Generate structured multi-period Cash Flow & Free Cash Flow DataFrame."""
    period_labels = [p.label for p in bundle.periods]
    if not period_labels:
        return pd.DataFrame()

    row_defs = [
        ("Cash Flow from Operating Activities (CFO)", "cfo", "currency", False),
        ("Capital Expenditure (CapEx magnitude)", "capex", "currency", False),
        ("  CapEx % of Revenue", "capex_pct", "percentage", True),
        ("Operating Cash Flow Less CapEx", "cfo_less_capex", "currency", True),
        ("Historical Unlevered Free Cash Flow (UFCF)", "ufcf", "currency", True),
    ]

    data_rows = []
    for display_label, code, row_type, is_derived in row_defs:
        row: Dict[str, Any] = {
            "Cash Flow Metric": display_label,
            "Classification": "Analytical Estimate" if code == "ufcf" else ("Calculated" if is_derived else "Reported"),
        }
        for p in period_labels:
            cf = bundle.cash_flow_metrics.get(p)
            if not cf:
                row[p] = "—"
                continue

            if code == "cfo":
                val = cf.operating_cash_flow
            elif code == "capex":
                val = cf.capex_magnitude
            elif code == "capex_pct":
                row[p] = format_percentage_value(cf.capex_pct_revenue)
                continue
            elif code == "cfo_less_capex":
                val = cf.cfo_less_capex
            elif code == "ufcf":
                val = cf.ufcf_estimate
            else:
                val = None

            row[p] = format_currency_value(val, scale_divisor)

        data_rows.append(row)

    return pd.DataFrame(data_rows)


def generate_efficiency_table(bundle: HistoricalAnalysisBundle) -> pd.DataFrame:
    """Generate structured multi-period Working Capital Efficiency (DSO, DIO, DPO, CCC) DataFrame."""
    period_labels = [p.label for p in bundle.periods]
    if not period_labels:
        return pd.DataFrame()

    row_defs = [
        ("Days Sales Outstanding (DSO)", "dso"),
        ("Days Inventory Outstanding (DIO)", "dio"),
        ("Days Payables Outstanding (DPO)", "dpo"),
        ("Cash Conversion Cycle (CCC = DSO + DIO - DPO)", "ccc"),
    ]

    data_rows = []
    for display_label, code in row_defs:
        row: Dict[str, Any] = {"Efficiency Metric": display_label}
        for p in period_labels:
            wc = bundle.working_capital.get(p)
            if not wc:
                row[p] = "—"
                continue

            if code == "dso":
                row[p] = format_days_value(wc.dso)
            elif code == "dio":
                row[p] = format_days_value(wc.dio)
            elif code == "dpo":
                row[p] = format_days_value(wc.dpo)
            elif code == "ccc":
                row[p] = format_days_value(wc.cash_conversion_cycle)

        data_rows.append(row)

    return pd.DataFrame(data_rows)
