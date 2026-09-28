"""Financial metric calculation routines for historical financial analysis.

Implements deterministic functions for revenue growth, multi-year CAGR,
profitability margins (Gross, EBITDA, EBIT, Net), and tax rate analysis.
"""

from __future__ import annotations

import math
from typing import Dict, List, Optional, Tuple

from src.analysis.models import MetricResult


def calculate_growth(
    current: Optional[float],
    previous: Optional[float],
    metric_code: str = "growth",
    metric_name: str = "Growth Rate",
    period_label: str = "",
) -> MetricResult:
    """Calculate period-over-period percentage growth rate."""
    if current is None or previous is None:
        return MetricResult(
            metric_code=metric_code,
            metric_name=metric_name,
            value=None,
            unit_or_type="percentage",
            period_label=period_label,
            status="unavailable",
            explanation="Prior period or current period figure is unavailable.",
        )

    if previous == 0.0:
        return MetricResult(
            metric_code=metric_code,
            metric_name=metric_name,
            value=None,
            unit_or_type="percentage",
            period_label=period_label,
            status="unavailable",
            explanation="Prior period figure is zero; percentage growth cannot be evaluated.",
        )

    # Standard percentage growth formula: (Current - Previous) / |Previous| * 100
    growth_val = ((current - previous) / abs(previous)) * 100.0

    return MetricResult(
        metric_code=metric_code,
        metric_name=metric_name,
        value=growth_val,
        unit_or_type="percentage",
        period_label=period_label,
        status="calculated",
    )


def calculate_cagr(
    start_val: Optional[float],
    end_val: Optional[float],
    num_years: float,
    metric_code: str = "cagr",
    metric_name: str = "Compound Annual Growth Rate (CAGR)",
    period_label: str = "",
) -> MetricResult:
    """Calculate Compound Annual Growth Rate over a multi-year interval."""
    if start_val is None or end_val is None:
        return MetricResult(
            metric_code=metric_code,
            metric_name=metric_name,
            value=None,
            unit_or_type="percentage",
            period_label=period_label,
            status="unavailable",
            explanation="Start or end period value is missing.",
        )

    if num_years <= 0:
        return MetricResult(
            metric_code=metric_code,
            metric_name=metric_name,
            value=None,
            unit_or_type="percentage",
            period_label=period_label,
            status="unavailable",
            explanation=f"Interval length ({num_years} years) must be greater than zero.",
        )

    if start_val <= 0.0 or end_val <= 0.0:
        return MetricResult(
            metric_code=metric_code,
            metric_name=metric_name,
            value=None,
            unit_or_type="percentage",
            period_label=period_label,
            status="unavailable",
            explanation=(
                f"Conventional CAGR is mathematically undefined for non-positive figures "
                f"(Start: {start_val}, End: {end_val})."
            ),
        )

    cagr_val = ((end_val / start_val) ** (1.0 / num_years) - 1.0) * 100.0

    return MetricResult(
        metric_code=metric_code,
        metric_name=metric_name,
        value=cagr_val,
        unit_or_type="percentage",
        period_label=period_label,
        status="calculated",
        explanation=f"Measured across {num_years:.1f} annual elapsed intervals.",
    )


def calculate_gross_profit_and_margin(
    revenue: Optional[float],
    cogs: Optional[float],
    reported_gp: Optional[float],
    period_label: str = "",
) -> Tuple[MetricResult, MetricResult]:
    """Determine Gross Profit and calculate Gross Profit Margin.

    Uses reported gross profit if present; derives from Revenue - COGS if missing.
    """
    gp_val: Optional[float] = None
    is_reported = False
    source_items = []
    status = "calculated"
    explanation = None

    if reported_gp is not None:
        gp_val = reported_gp
        is_reported = True
        source_items = ["gross_profit"]
        status = "reported"
    elif revenue is not None and cogs is not None:
        # Standard accounting: COGS could be stored positive or negative
        cogs_magnitude = abs(cogs)
        gp_val = revenue - cogs_magnitude
        is_reported = False
        source_items = ["revenue", "cogs"]
        status = "calculated"
        explanation = "Derived from Revenue - Cost of Goods Sold."
    else:
        status = "unavailable"
        explanation = "Gross Profit line item is not reported and cannot be derived (Revenue or COGS missing)."

    gp_metric = MetricResult(
        metric_code="gross_profit",
        metric_name="Gross Profit",
        value=gp_val,
        unit_or_type="currency",
        period_label=period_label,
        is_reported=is_reported,
        source_line_items=source_items,
        status=status,
        explanation=explanation,
    )

    # Margin calculation
    if gp_val is not None and revenue is not None and revenue > 0:
        margin_val = (gp_val / revenue) * 100.0
        margin_status = "calculated"
        margin_expl = None
    else:
        margin_val = None
        margin_status = "unavailable"
        margin_expl = "Revenue is zero, negative, or unavailable."

    margin_metric = MetricResult(
        metric_code="gross_margin",
        metric_name="Gross Profit Margin",
        value=margin_val,
        unit_or_type="percentage",
        period_label=period_label,
        is_reported=False,
        source_line_items=["gross_profit", "revenue"],
        status=margin_status,
        explanation=margin_expl,
    )

    return gp_metric, margin_metric


def calculate_ebitda_and_margin(
    revenue: Optional[float],
    ebit: Optional[float],
    da: Optional[float],
    reported_ebitda: Optional[float],
    period_label: str = "",
) -> Tuple[MetricResult, MetricResult]:
    """Determine EBITDA and calculate EBITDA Margin.

    Uses reported EBITDA if available; derives from EBIT + D&A if missing.
    Flags discrepancy if both reported and derived exist and diverge.
    """
    ebitda_val: Optional[float] = None
    is_reported = False
    source_items = []
    status = "calculated"
    explanation = None

    derived_ebitda = None
    if ebit is not None and da is not None:
        derived_ebitda = ebit + abs(da)

    if reported_ebitda is not None:
        ebitda_val = reported_ebitda
        is_reported = True
        source_items = ["ebitda"]
        status = "reported"
        if derived_ebitda is not None and abs(reported_ebitda - derived_ebitda) > 0.01 * abs(reported_ebitda):
            explanation = (
                f"Note: Reported EBITDA ({reported_ebitda:,.2f}) differs from EBIT + D&A "
                f"({derived_ebitda:,.2f}). Using reported figure."
            )
    elif derived_ebitda is not None:
        ebitda_val = derived_ebitda
        is_reported = False
        source_items = ["ebit", "depreciation_amortization"]
        status = "calculated"
        explanation = "Derived from EBIT + Depreciation & Amortization."
    else:
        status = "unavailable"
        explanation = "EBITDA is not reported and cannot be derived (EBIT or D&A missing)."

    ebitda_metric = MetricResult(
        metric_code="ebitda",
        metric_name="EBITDA",
        value=ebitda_val,
        unit_or_type="currency",
        period_label=period_label,
        is_reported=is_reported,
        source_line_items=source_items,
        status=status,
        explanation=explanation,
    )

    # Margin calculation
    if ebitda_val is not None and revenue is not None and revenue > 0:
        margin_val = (ebitda_val / revenue) * 100.0
        margin_status = "calculated"
        margin_expl = None
    else:
        margin_val = None
        margin_status = "unavailable"
        margin_expl = "Revenue is zero, negative, or unavailable."

    margin_metric = MetricResult(
        metric_code="ebitda_margin",
        metric_name="EBITDA Margin",
        value=margin_val,
        unit_or_type="percentage",
        period_label=period_label,
        is_reported=False,
        source_line_items=["ebitda", "revenue"],
        status=margin_status,
        explanation=margin_expl,
    )

    return ebitda_metric, margin_metric


def calculate_ebit_and_margin(
    revenue: Optional[float],
    reported_ebit: Optional[float],
    period_label: str = "",
) -> Tuple[MetricResult, MetricResult]:
    """Evaluate reported EBIT and compute EBIT Margin."""
    if reported_ebit is not None:
        ebit_metric = MetricResult(
            metric_code="ebit",
            metric_name="EBIT",
            value=reported_ebit,
            unit_or_type="currency",
            period_label=period_label,
            is_reported=True,
            source_line_items=["ebit"],
            status="reported",
        )
    else:
        ebit_metric = MetricResult(
            metric_code="ebit",
            metric_name="EBIT",
            value=None,
            unit_or_type="currency",
            period_label=period_label,
            status="unavailable",
            explanation="EBIT line item is not reported in historical records.",
        )

    if reported_ebit is not None and revenue is not None and revenue > 0:
        margin_val = (reported_ebit / revenue) * 100.0
        margin_status = "calculated"
        margin_expl = None
    else:
        margin_val = None
        margin_status = "unavailable"
        margin_expl = "EBIT or Revenue is missing, zero, or negative."

    margin_metric = MetricResult(
        metric_code="ebit_margin",
        metric_name="EBIT Margin",
        value=margin_val,
        unit_or_type="percentage",
        period_label=period_label,
        source_line_items=["ebit", "revenue"],
        status=margin_status,
        explanation=margin_expl,
    )

    return ebit_metric, margin_metric


def calculate_net_income_and_margin(
    revenue: Optional[float],
    reported_net_income: Optional[float],
    period_label: str = "",
) -> Tuple[MetricResult, MetricResult]:
    """Evaluate Net Income and Net Profit Margin, correctly preserving negative values."""
    if reported_net_income is not None:
        ni_metric = MetricResult(
            metric_code="net_income",
            metric_name="Net Income",
            value=reported_net_income,
            unit_or_type="currency",
            period_label=period_label,
            is_reported=True,
            source_line_items=["net_income"],
            status="reported",
        )
    else:
        ni_metric = MetricResult(
            metric_code="net_income",
            metric_name="Net Income",
            value=None,
            unit_or_type="currency",
            period_label=period_label,
            status="unavailable",
            explanation="Net Income line item is not reported.",
        )

    if reported_net_income is not None and revenue is not None and revenue > 0:
        # Net margin can legitimately be negative if company operated at a loss
        margin_val = (reported_net_income / revenue) * 100.0
        margin_status = "calculated"
        margin_expl = None
    else:
        margin_val = None
        margin_status = "unavailable"
        margin_expl = "Net Income or Revenue is missing, zero, or negative."

    margin_metric = MetricResult(
        metric_code="net_margin",
        metric_name="Net Profit Margin",
        value=margin_val,
        unit_or_type="percentage",
        period_label=period_label,
        source_line_items=["net_income", "revenue"],
        status=margin_status,
        explanation=margin_expl,
    )

    return ni_metric, margin_metric


def calculate_effective_tax_rate(
    pbt: Optional[float],
    tax_expense: Optional[float],
    period_label: str = "",
) -> MetricResult:
    """Calculate effective historical tax rate: Tax Expense / PBT.

    Normalizes negative accounting presentations and flags negative/zero PBT.
    """
    if pbt is None or tax_expense is None:
        return MetricResult(
            metric_code="effective_tax_rate",
            metric_name="Effective Tax Rate",
            value=None,
            unit_or_type="percentage",
            period_label=period_label,
            status="unavailable",
            explanation="Profit Before Tax or Income Tax Expense is missing.",
        )

    if pbt <= 0.0:
        return MetricResult(
            metric_code="effective_tax_rate",
            metric_name="Effective Tax Rate",
            value=None,
            unit_or_type="percentage",
            period_label=period_label,
            status="unavailable",
            explanation=f"Profit Before Tax ({pbt:,.2f}) is zero or negative; operating effective tax rate is not meaningful.",
        )

    # Tax expense is sometimes recorded as positive (expense magnitude) or negative (income statement subtraction)
    tax_magnitude = abs(tax_expense)
    effective_rate = (tax_magnitude / pbt) * 100.0

    return MetricResult(
        metric_code="effective_tax_rate",
        metric_name="Effective Tax Rate",
        value=effective_rate,
        unit_or_type="percentage",
        period_label=period_label,
        source_line_items=["profit_before_tax", "income_tax_expense"],
        status="calculated",
    )
