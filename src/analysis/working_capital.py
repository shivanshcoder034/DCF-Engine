"""Historical working capital and cash conversion cycle efficiency analysis.

Computes Net Working Capital (NWC), Operating Working Capital, period-over-period
working capital changes, DSO, DIO, DPO, and the Cash Conversion Cycle (CCC).
"""

from __future__ import annotations

from typing import Dict, List, Optional, Tuple

from src.analysis.models import FinancialPeriod, WorkingCapitalMetrics


def calculate_period_working_capital(
    current_period: FinancialPeriod,
    current_items: Dict[str, float],
    prior_period: Optional[FinancialPeriod] = None,
    prior_items: Optional[Dict[str, float]] = None,
) -> WorkingCapitalMetrics:
    """Compute comprehensive working capital and efficiency indicators for a period."""
    notes: List[str] = []

    # 1. Total Current Assets & Total Current Liabilities
    ca = current_items.get("total_current_assets")
    cl = current_items.get("total_current_liabilities")

    # If totals are missing, attempt non-overlapping component derivation
    if ca is None:
        cash = current_items.get("cash_and_equivalents")
        ar = current_items.get("accounts_receivable")
        inv = current_items.get("inventory")
        other_ca = current_items.get("other_current_assets", 0.0)
        if cash is not None and ar is not None and inv is not None:
            ca = cash + ar + inv + other_ca
            notes.append("Current Assets derived from cash, receivables, inventory, and other liquid assets.")

    if cl is None:
        ap = current_items.get("accounts_payable")
        st_debt = current_items.get("short_term_debt", 0.0)
        other_cl = current_items.get("other_current_liabilities", 0.0)
        if ap is not None:
            cl = ap + st_debt + other_cl
            notes.append("Current Liabilities derived from payables, short-term debt, and other current liabilities.")

    nwc = (ca - cl) if (ca is not None and cl is not None) else None

    # 2. Operating Net Working Capital (Excludes cash and interest-bearing debt)
    ar = current_items.get("accounts_receivable")
    inv = current_items.get("inventory")
    ap = current_items.get("accounts_payable")

    if ar is not None and inv is not None and ap is not None:
        op_nwc: Optional[float] = ar + inv - ap
    else:
        op_nwc = None
        missing = []
        if ar is None: missing.append("Accounts Receivable")
        if inv is None: missing.append("Inventory")
        if ap is None: missing.append("Accounts Payable")
        notes.append(f"Operating NWC unavailable (missing components: {', '.join(missing)}).")

    # 3. Change in Net Working Capital (Period over period)
    delta_nwc: Optional[float] = None
    if nwc is not None and prior_items is not None:
        prior_ca = prior_items.get("total_current_assets")
        prior_cl = prior_items.get("total_current_liabilities")
        if prior_ca is not None and prior_cl is not None:
            prior_nwc = prior_ca - prior_cl
            delta_nwc = nwc - prior_nwc

    # 4. Working Capital Efficiency (DSO, DIO, DPO, CCC)
    revenue = current_items.get("revenue")
    cogs_raw = current_items.get("cogs")
    cogs = abs(cogs_raw) if cogs_raw is not None else None

    days_in_period = current_period.duration_days
    # Fallback to standard 365 or 90 days if dates indicate standard reporting
    if current_period.period_type == "annual" and (days_in_period < 350 or days_in_period > 370):
        days_in_period = 365
    elif current_period.period_type == "quarterly" and (days_in_period < 80 or days_in_period > 100):
        days_in_period = 91

    is_ending_balance = False

    # Accounts Receivable Average
    avg_ar: Optional[float] = None
    if ar is not None:
        if prior_items is not None and prior_items.get("accounts_receivable") is not None:
            avg_ar = (ar + prior_items["accounts_receivable"]) / 2.0
        else:
            avg_ar = ar
            is_ending_balance = True

    # Inventory Average
    avg_inv: Optional[float] = None
    if inv is not None:
        if prior_items is not None and prior_items.get("inventory") is not None:
            avg_inv = (inv + prior_items["inventory"]) / 2.0
        else:
            avg_inv = inv
            is_ending_balance = True

    # Accounts Payable Average
    avg_ap: Optional[float] = None
    if ap is not None:
        if prior_items is not None and prior_items.get("accounts_payable") is not None:
            avg_ap = (ap + prior_items["accounts_payable"]) / 2.0
        else:
            avg_ap = ap
            is_ending_balance = True

    if is_ending_balance:
        notes.append("Efficiency metrics use ending balance approximation due to absent prior period balance.")

    # DSO = (Average AR / Revenue) * Days
    dso: Optional[float] = None
    if avg_ar is not None and revenue is not None and revenue > 0:
        dso = (avg_ar / revenue) * days_in_period

    # DIO = (Average Inventory / COGS) * Days
    dio: Optional[float] = None
    if avg_inv is not None and cogs is not None and cogs > 0:
        dio = (avg_inv / cogs) * days_in_period

    # DPO = (Average AP / COGS) * Days
    dpo: Optional[float] = None
    if avg_ap is not None and cogs is not None and cogs > 0:
        dpo = (avg_ap / cogs) * days_in_period

    # CCC = DSO + DIO - DPO
    ccc: Optional[float] = None
    if dso is not None and dio is not None and dpo is not None:
        ccc = dso + dio - dpo

    return WorkingCapitalMetrics(
        period_label=current_period.label,
        current_assets=ca,
        current_liabilities=cl,
        net_working_capital=nwc,
        operating_nwc=op_nwc,
        delta_nwc=delta_nwc,
        dso=dso,
        dio=dio,
        dpo=dpo,
        cash_conversion_cycle=ccc,
        is_ending_balance_approx=is_ending_balance,
        notes=notes,
    )
