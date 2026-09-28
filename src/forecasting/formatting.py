"""Formatting and presentation table generators for financial forecasts.

Combines historical performance actuals with multi-year forecast projections
into unified, auditable financial statement and cash flow bridge tables.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

import pandas as pd

from src.analysis.formatting import format_currency_value, format_percentage_value
from src.analysis.models import HistoricalAnalysisBundle
from src.forecasting.models import ForecastResult


def generate_forecast_statement_table(
    bundle: HistoricalAnalysisBundle,
    forecast: ForecastResult,
    scale_divisor: float = 1_000_000.0,
) -> pd.DataFrame:
    """Generate structured multi-period statement table combining historical actuals and forecast years."""
    hist_periods = [p.label for p in bundle.periods]
    forecast_periods = [f.period_label for f in forecast.annual_forecasts]
    all_period_labels = hist_periods + forecast_periods

    row_definitions = [
        ("Revenue", "revenue", "currency"),
        ("  YoY Revenue Growth", "revenue_growth", "percentage"),
        ("Cost of Goods Sold (COGS)", "cogs", "currency"),
        ("Gross Profit", "gross_profit", "currency"),
        ("  Gross Profit Margin", "gross_margin", "percentage"),
        ("Operating Expenses (OpEx)", "operating_expenses", "currency"),
        ("EBITDA", "ebitda", "currency"),
        ("  EBITDA Margin", "ebitda_margin", "percentage"),
        ("Depreciation & Amortization", "depreciation_amortization", "currency"),
        ("EBIT (Operating Profit)", "ebit", "currency"),
        ("  EBIT Margin", "ebit_margin", "percentage"),
        ("Income Tax Expense", "tax_expense", "currency"),
        ("NOPAT", "nopat", "currency"),
        ("Operating Net Working Capital", "operating_nwc", "currency"),
        ("  Change in Operating NWC", "delta_operating_nwc", "currency"),
        ("Capital Expenditure (CapEx)", "capex", "currency"),
        ("Unlevered Free Cash Flow (UFCF)", "ufcf", "currency"),
    ]

    data_rows = []
    for display_label, code, val_type in row_definitions:
        row: Dict[str, Any] = {"Financial Line Item": display_label}

        # Historical Columns
        for hp in hist_periods:
            p_metrics = bundle.metrics_by_period.get(hp, {})
            raw_items = bundle.raw_line_items_by_period.get(hp, {})
            wc = bundle.working_capital.get(hp)
            cf = bundle.cash_flow_metrics.get(hp)

            val: Optional[float] = None
            if code == "revenue": val = p_metrics.get("revenue").value if "revenue" in p_metrics else raw_items.get("revenue")
            elif code == "revenue_growth": val = p_metrics.get("revenue_growth").value if "revenue_growth" in p_metrics else None
            elif code == "cogs": val = abs(raw_items.get("cogs")) if "cogs" in raw_items else None
            elif code == "gross_profit": val = p_metrics.get("gross_profit").value if "gross_profit" in p_metrics else None
            elif code == "gross_margin": val = p_metrics.get("gross_margin").value if "gross_margin" in p_metrics else None
            elif code == "operating_expenses": val = raw_items.get("operating_expenses")
            elif code == "ebitda": val = p_metrics.get("ebitda").value if "ebitda" in p_metrics else None
            elif code == "ebitda_margin": val = p_metrics.get("ebitda_margin").value if "ebitda_margin" in p_metrics else None
            elif code == "depreciation_amortization": val = abs(raw_items.get("depreciation_amortization")) if "depreciation_amortization" in raw_items else None
            elif code == "ebit": val = p_metrics.get("ebit").value if "ebit" in p_metrics else None
            elif code == "ebit_margin": val = p_metrics.get("ebit_margin").value if "ebit_margin" in p_metrics else None
            elif code == "tax_expense": val = abs(raw_items.get("income_tax_expense")) if "income_tax_expense" in raw_items else None
            elif code == "nopat":
                ebit_val = p_metrics.get("ebit").value if "ebit" in p_metrics else None
                tax_rate_val = p_metrics.get("effective_tax_rate").value if "effective_tax_rate" in p_metrics else None
                if ebit_val is not None and tax_rate_val is not None:
                    val = ebit_val * (1.0 - tax_rate_val / 100.0)
            elif code == "operating_nwc": val = wc.operating_nwc if wc else None
            elif code == "delta_operating_nwc": val = wc.delta_nwc if wc else None
            elif code == "capex": val = cf.capex_magnitude if cf else None
            elif code == "ufcf": val = cf.ufcf_estimate if cf else None

            if val_type == "currency":
                row[hp] = format_currency_value(val, scale_divisor)
            elif val_type == "percentage":
                row[hp] = format_percentage_value(val)

        # Forecast Columns
        for f in forecast.annual_forecasts:
            fp = f.period_label
            val = getattr(f, code, None)
            if val_type == "currency":
                row[fp] = format_currency_value(val, scale_divisor)
            elif val_type == "percentage":
                row[fp] = format_percentage_value(val)

        data_rows.append(row)

    return pd.DataFrame(data_rows)


def generate_ufcf_bridge_table(
    forecast: ForecastResult,
    scale_divisor: float = 1_000_000.0,
) -> pd.DataFrame:
    """Generate detailed Unlevered Free Cash Flow (UFCF) derivation bridge table."""
    forecast_periods = [f.period_label for f in forecast.annual_forecasts]

    bridge_rows = [
        ("EBIT (Operating Profit)", "ebit", False),
        ("Less: Taxes on Operating Profit", "tax_expense", True),
        ("NOPAT (Net Operating Profit After Tax)", "nopat", False),
        ("Plus: Depreciation & Amortization (Non-cash)", "depreciation_amortization", False),
        ("Less: Capital Expenditures (CapEx)", "capex", True),
        ("Less: Change in Operating Working Capital (ΔNWC)", "delta_operating_nwc", True),
        ("Equals: Unlevered Free Cash Flow (UFCF)", "ufcf", False),
    ]

    table_data = []
    for label, code, is_deduction in bridge_rows:
        row: Dict[str, Any] = {"UFCF Component": label}
        for f in forecast.annual_forecasts:
            fp = f.period_label
            raw_val = getattr(f, code, 0.0)
            # Prefix deductions visually if desired or keep standard
            display_val = raw_val
            row[fp] = format_currency_value(display_val, scale_divisor)
        table_data.append(row)

    return pd.DataFrame(table_data)
