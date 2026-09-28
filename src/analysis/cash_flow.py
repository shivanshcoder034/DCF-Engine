"""Historical cash flow and Unlevered Free Cash Flow (UFCF) analysis.

Computes Operating Cash Flow (CFO), Capital Expenditure intensity,
CFO less CapEx, and historical Unlevered Free Cash Flow analytical estimates.
"""

from __future__ import annotations

from typing import Dict, List, Optional

from src.analysis.models import CashFlowAnalysisMetrics, FinancialPeriod


def calculate_period_cash_flow_metrics(
    current_period: FinancialPeriod,
    current_items: Dict[str, float],
    delta_nwc: Optional[float] = None,
) -> CashFlowAnalysisMetrics:
    """Compute operating cash flow and historical free cash flow indicators for a period."""
    notes: List[str] = []
    missing_ufcf: List[str] = []

    # 1. Operating Cash Flow (Reported)
    cfo = current_items.get("cfo")
    if cfo is None:
        notes.append("Cash Flow from Operating Activities (CFO) is not reported.")

    # 2. Capital Expenditure (CapEx)
    capex_raw = current_items.get("capex")
    capex_mag: Optional[float] = None
    capex_pct: Optional[float] = None

    if capex_raw is not None:
        capex_mag = abs(capex_raw)
        revenue = current_items.get("revenue")
        if revenue is not None and revenue > 0:
            capex_pct = (capex_mag / revenue) * 100.0

    # 3. Operating Cash Flow Less CapEx
    cfo_less_capex: Optional[float] = None
    if cfo is not None and capex_mag is not None:
        cfo_less_capex = cfo - capex_mag

    # 4. Historical Unlevered Free Cash Flow (UFCF) Estimate
    # Formula: EBIT * (1 - T) + D&A - CapEx - Delta_NWC
    ebit = current_items.get("ebit")
    da = current_items.get("depreciation_amortization")
    pbt = current_items.get("profit_before_tax")
    tax_exp = current_items.get("income_tax_expense")

    if ebit is None:
        missing_ufcf.append("EBIT")
    if da is None:
        missing_ufcf.append("Depreciation & Amortization")
    if capex_mag is None:
        missing_ufcf.append("Capital Expenditures (CapEx)")
    if delta_nwc is None:
        missing_ufcf.append("Change in Net Working Capital (ΔNWC)")

    # Tax Rate calculation for UFCF
    effective_t: Optional[float] = None
    if pbt is not None and tax_exp is not None and pbt > 0:
        raw_rate = abs(tax_exp) / pbt
        # Bound rate between 0% and 50% for realistic historical analytical estimate
        effective_t = min(max(raw_rate, 0.0), 0.50)
    else:
        if pbt is None or tax_exp is None:
            missing_ufcf.append("Effective Tax Rate (PBT or Tax Expense missing)")
        elif pbt <= 0:
            # If company lost money, NOPAT = EBIT (effective tax 0%)
            effective_t = 0.0
            notes.append("PBT is zero or negative; applied 0% effective tax rate to operating profit.")

    ufcf_val: Optional[float] = None
    if not missing_ufcf and ebit is not None and da is not None and capex_mag is not None and delta_nwc is not None:
        tax_multiplier = (1.0 - effective_t) if effective_t is not None else 1.0
        nopat = ebit * tax_multiplier
        ufcf_val = nopat + abs(da) - capex_mag - delta_nwc
        notes.append("UFCF is a historical analytical estimate: NOPAT + D&A - CapEx - ΔNWC.")

    return CashFlowAnalysisMetrics(
        period_label=current_period.label,
        operating_cash_flow=cfo,
        capex_magnitude=capex_mag,
        capex_pct_revenue=capex_pct,
        cfo_less_capex=cfo_less_capex,
        ufcf_estimate=ufcf_val,
        effective_tax_rate=(effective_t * 100.0) if effective_t is not None else None,
        ufcf_missing_inputs=missing_ufcf,
        notes=notes,
    )
