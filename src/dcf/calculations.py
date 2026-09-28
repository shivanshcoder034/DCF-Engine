"""Deterministic mathematical calculations for DCF cash flow discounting, terminal value, and equity bridge.

Implements pure, independent mathematical logic for discounting projected UFCF,
evaluating Gordon Growth and Exit Multiple terminal values, and deriving implied value per share.
"""

from __future__ import annotations

import math
from typing import Any, List, Optional, Tuple

from src.dcf.models import (
    DcfValuationResult,
    DiscountingConvention,
    EquityBridgeInputs,
    EquityBridgeResult,
    TerminalValueInputs,
    TerminalValueMethod,
    TerminalValueResult,
    YearDiscountingResult,
)


def _is_finite_number(val: Any) -> bool:
    """Check if value is a valid real number that is not None, NaN, or infinite."""
    if val is None:
        return False
    try:
        f_val = float(val)
        return not (math.isnan(f_val) or math.isinf(f_val))
    except (TypeError, ValueError):
        return False


def calculate_discount_factor(wacc_pct: float, period: float) -> float:
    """Calculate the discount factor for a given discount period.

    Formula:
        Discount Factor = 1 / (1 + WACC / 100)^period
    """
    wacc_rate = wacc_pct / 100.0
    discount_base = 1.0 + wacc_rate
    if discount_base <= 0.0:
        raise ValueError(f"Discount base (1 + WACC) must be positive, got {discount_base:.4f}.")
    return 1.0 / (discount_base ** period)


def discount_cash_flow_series(
    ufcf_series: List[Tuple[str, float]],
    wacc_pct: float,
    convention: str = DiscountingConvention.END_OF_YEAR.value,
) -> Tuple[List[YearDiscountingResult], float]:
    """Discount an explicit multi-year UFCF projection series.

    Conventions:
        - End-of-year: t = 1.0, 2.0, ..., N
        - Mid-year: t = 0.5, 1.5, ..., N - 0.5
    """
    schedule: List[YearDiscountingResult] = []
    total_pv = 0.0
    is_mid_year = (convention == DiscountingConvention.MID_YEAR.value)

    for i, (period_label, ufcf_val) in enumerate(ufcf_series, start=1):
        t = (i - 0.5) if is_mid_year else float(i)
        df = calculate_discount_factor(wacc_pct, t)
        pv = ufcf_val * df
        total_pv += pv

        schedule.append(
            YearDiscountingResult(
                year_index=i,
                period_label=period_label,
                ufcf=round(ufcf_val, 4),
                discount_period=t,
                discount_factor=round(df, 6),
                pv_ufcf=round(pv, 4),
            )
        )

    return schedule, round(total_pv, 4)


def calculate_terminal_value_gordon_growth(
    ufcf_n: float,
    wacc_pct: float,
    perpetual_growth_rate_pct: float,
    terminal_discount_period: float,
) -> TerminalValueResult:
    """Calculate terminal value using the Gordon Growth Perpetuity Model.

    Formula:
        UFCF_{N+1} = UFCF_N * (1 + g)
        Terminal Value = UFCF_{N+1} / (WACC - g)
        PV of Terminal Value = Terminal Value * Discount Factor_N
    """
    warnings: List[str] = []
    notes: List[str] = []

    if perpetual_growth_rate_pct is None or not _is_finite_number(perpetual_growth_rate_pct):
        return TerminalValueResult(
            method=TerminalValueMethod.GORDON_GROWTH.value,
            terminal_value=None,
            discount_period=terminal_discount_period,
            discount_factor=0.0,
            pv_terminal_value=None,
            formula_display="TV = Incomplete: Perpetual growth rate missing",
            status="incomplete",
            missing_inputs=["Perpetual Growth Rate (g)"],
        )

    # Condition: WACC must be strictly greater than perpetual growth rate (g)
    if wacc_pct <= perpetual_growth_rate_pct:
        err_msg = (
            f"Invalid Gordon Growth condition: Discount rate WACC ({wacc_pct:.2f}%) must be strictly "
            f"greater than the perpetual growth rate ({perpetual_growth_rate_pct:.2f}%). "
            f"Denominator (WACC - g) is non-positive."
        )
        warnings.append(err_msg)
        return TerminalValueResult(
            method=TerminalValueMethod.GORDON_GROWTH.value,
            terminal_value=None,
            discount_period=terminal_discount_period,
            discount_factor=0.0,
            pv_terminal_value=None,
            formula_display=f"Invalid: WACC ({wacc_pct:.2f}%) <= g ({perpetual_growth_rate_pct:.2f}%)",
            status="invalid",
            warnings=warnings,
            missing_inputs=["Valid condition WACC > g"],
        )

    g_rate = perpetual_growth_rate_pct / 100.0
    wacc_rate = wacc_pct / 100.0
    denominator = wacc_rate - g_rate

    # Normalized terminal year cash flow
    ufcf_n1 = ufcf_n * (1.0 + g_rate)
    tv = ufcf_n1 / denominator
    df_term = calculate_discount_factor(wacc_pct, terminal_discount_period)
    pv_tv = tv * df_term

    if perpetual_growth_rate_pct > 4.0:
        warnings.append(
            f"Unusually high perpetual growth rate ({perpetual_growth_rate_pct:.2f}%). "
            f"Long-term perpetuity growth generally should not exceed long-term GDP growth (2-3%)."
        )

    formula_str = (
        f"TV = [{ufcf_n:,.1f} × (1 + {perpetual_growth_rate_pct:.2f}%)] / "
        f"({wacc_pct:.2f}% - {perpetual_growth_rate_pct:.2f}%) = {tv:,.1f}"
    )

    notes.append(f"Normalized UFCF(N+1) = {ufcf_n1:,.2f} discounted at rate spread {(wacc_pct - perpetual_growth_rate_pct):.2f}%.")

    return TerminalValueResult(
        method=TerminalValueMethod.GORDON_GROWTH.value,
        terminal_value=round(tv, 4),
        discount_period=terminal_discount_period,
        discount_factor=round(df_term, 6),
        pv_terminal_value=round(pv_tv, 4),
        formula_display=formula_str,
        status="complete",
        notes=notes,
        warnings=warnings,
        missing_inputs=[],
    )


def calculate_terminal_value_exit_multiple(
    terminal_ebitda: float,
    exit_multiple: float,
    wacc_pct: float,
    terminal_discount_period: float,
) -> TerminalValueResult:
    """Calculate terminal value using the Exit Multiple Method.

    Formula:
        Terminal Value = Terminal Year EBITDA * Exit Multiple
        PV of Terminal Value = Terminal Value * Discount Factor_N
    """
    warnings: List[str] = []
    notes: List[str] = []

    if exit_multiple is None or not _is_finite_number(exit_multiple):
        return TerminalValueResult(
            method=TerminalValueMethod.EXIT_MULTIPLE.value,
            terminal_value=None,
            discount_period=terminal_discount_period,
            discount_factor=0.0,
            pv_terminal_value=None,
            formula_display="TV = Incomplete: Exit Multiple missing",
            status="incomplete",
            missing_inputs=["Exit Multiple (x)"],
        )

    if exit_multiple < 0.0:
        warnings.append(f"Negative exit multiple entered ({exit_multiple:.1f}x). Multiples cannot be negative.")
        return TerminalValueResult(
            method=TerminalValueMethod.EXIT_MULTIPLE.value,
            terminal_value=None,
            discount_period=terminal_discount_period,
            discount_factor=0.0,
            pv_terminal_value=None,
            formula_display="Invalid: Negative exit multiple",
            status="invalid",
            warnings=warnings,
            missing_inputs=["Non-negative exit multiple"],
        )

    if terminal_ebitda is None or not _is_finite_number(terminal_ebitda):
        return TerminalValueResult(
            method=TerminalValueMethod.EXIT_MULTIPLE.value,
            terminal_value=None,
            discount_period=terminal_discount_period,
            discount_factor=0.0,
            pv_terminal_value=None,
            formula_display="TV = Incomplete: Terminal year EBITDA unavailable in forecast",
            status="incomplete",
            missing_inputs=["Terminal Year EBITDA"],
        )

    if terminal_ebitda <= 0.0:
        warnings.append(
            f"Terminal year EBITDA is non-positive ({terminal_ebitda:,.1f}). "
            f"Applying an EV/EBITDA multiple to negative or zero EBITDA produces invalid enterprise value."
        )

    tv = terminal_ebitda * exit_multiple
    df_term = calculate_discount_factor(wacc_pct, terminal_discount_period)
    pv_tv = tv * df_term

    formula_str = f"TV = Terminal EBITDA ({terminal_ebitda:,.1f}) × Exit Multiple ({exit_multiple:.1f}x) = {tv:,.1f}"
    notes.append(f"Assumes an exit EV/EBITDA multiple of {exit_multiple:.1f}x applied to final explicit forecast year EBITDA.")

    return TerminalValueResult(
        method=TerminalValueMethod.EXIT_MULTIPLE.value,
        terminal_value=round(tv, 4),
        discount_period=terminal_discount_period,
        discount_factor=round(df_term, 6),
        pv_terminal_value=round(pv_tv, 4),
        formula_display=formula_str,
        status="complete",
        notes=notes,
        warnings=warnings,
        missing_inputs=[],
    )


def calculate_equity_bridge(
    enterprise_value: Optional[float],
    bridge_inputs: EquityBridgeInputs,
) -> EquityBridgeResult:
    """Calculate the bridge from Enterprise Value to Equity Value.

    Formula:
        Equity Value = Enterprise Value + Cash - Debt - Minority Interest - Preferred Equity + Other Adjustments
        Net Debt = Debt - Cash
    """
    warnings: List[str] = []
    missing_inputs: List[str] = []

    cash = float(bridge_inputs.cash_and_equivalents) if bridge_inputs.cash_and_equivalents is not None else 0.0
    debt = float(bridge_inputs.debt_value) if bridge_inputs.debt_value is not None else 0.0
    mi = float(bridge_inputs.minority_interest) if bridge_inputs.minority_interest is not None else 0.0
    pe = float(bridge_inputs.preferred_equity) if bridge_inputs.preferred_equity is not None else 0.0
    adj = float(bridge_inputs.other_adjustments) if bridge_inputs.other_adjustments is not None else 0.0

    if bridge_inputs.cash_and_equivalents is None:
        missing_inputs.append("Cash and Cash Equivalents (set to 0 if not applicable)")
    if bridge_inputs.debt_value is None:
        missing_inputs.append("Interest-Bearing Debt Balance (set to 0 if not applicable)")

    if debt < 0.0:
        warnings.append(f"Negative debt balance entered ({debt:,.1f}).")
    if cash < 0.0:
        warnings.append(f"Negative cash balance entered ({cash:,.1f}).")

    net_debt = debt - cash

    if enterprise_value is None or not _is_finite_number(enterprise_value):
        return EquityBridgeResult(
            enterprise_value=None,
            cash_added=round(cash, 4),
            debt_subtracted=round(debt, 4),
            minority_interest_subtracted=round(mi, 4),
            preferred_equity_subtracted=round(pe, 4),
            other_adjustments_net=round(adj, 4),
            net_debt=round(net_debt, 4),
            equity_value=None,
            status="incomplete",
            warnings=warnings,
            missing_inputs=missing_inputs,
        )

    ev = float(enterprise_value)
    eq_val = ev + cash - debt - mi - pe + adj

    if eq_val < 0.0:
        warnings.append(
            f"Negative Equity Value computed ({eq_val:,.1f}). "
            f"Enterprise Value is insufficient to cover Net Debt and senior claim obligations."
        )

    return EquityBridgeResult(
        enterprise_value=round(ev, 4),
        cash_added=round(cash, 4),
        debt_subtracted=round(debt, 4),
        minority_interest_subtracted=round(mi, 4),
        preferred_equity_subtracted=round(pe, 4),
        other_adjustments_net=round(adj, 4),
        net_debt=round(net_debt, 4),
        equity_value=round(eq_val, 4),
        status="complete",
        warnings=warnings,
        missing_inputs=[],
    )


def calculate_dcf_valuation(
    ufcf_series: List[Tuple[str, float]],
    terminal_ebitda: Optional[float],
    wacc_pct: Optional[float],
    convention: str,
    terminal_inputs: TerminalValueInputs,
    bridge_inputs: EquityBridgeInputs,
    diluted_shares: Optional[float],
) -> DcfValuationResult:
    """Execute end-to-end DCF valuation orchestrating discounting, terminal value, and equity bridge."""
    missing_inputs: List[str] = []
    warnings: List[str] = []

    # 1. Validate WACC
    if wacc_pct is None or not _is_finite_number(wacc_pct):
        missing_inputs.append("Valid WACC discount rate from Phase 5")
        return DcfValuationResult(
            enterprise_value=None,
            equity_value=None,
            implied_value_per_share=None,
            diluted_shares_applied=diluted_shares,
            pv_forecast_ufcf=None,
            terminal_value=None,
            pv_terminal_value=None,
            terminal_value_pct_ev=None,
            pv_ufcf_pct_ev=None,
            wacc_applied=None,
            discounting_convention_applied=convention,
            is_complete=False,
            missing_inputs=missing_inputs,
            warnings=warnings,
        )

    wacc_val = float(wacc_pct)
    if wacc_val <= 0.0:
        warnings.append(f"Non-positive WACC entered ({wacc_val:.2f}%). Hurdle rate should be positive.")

    # 2. Validate Forecast UFCF series
    if not ufcf_series:
        missing_inputs.append("Projected UFCF cash flow series from Phase 4 forecast")
        return DcfValuationResult(
            enterprise_value=None,
            equity_value=None,
            implied_value_per_share=None,
            diluted_shares_applied=diluted_shares,
            pv_forecast_ufcf=None,
            terminal_value=None,
            pv_terminal_value=None,
            terminal_value_pct_ev=None,
            pv_ufcf_pct_ev=None,
            wacc_applied=wacc_val,
            discounting_convention_applied=convention,
            is_complete=False,
            missing_inputs=missing_inputs,
            warnings=warnings,
        )

    # 3. Discount explicit forecast UFCF series
    schedule, pv_ufcf = discount_cash_flow_series(ufcf_series, wacc_val, convention)

    # 4. Terminal value discount period
    # Consistent with final forecast year index N
    n_years = len(ufcf_series)
    term_discount_period = float(n_years)  # Terminal value is at the horizon end (t = N)

    # 5. Evaluate Terminal Value
    ufcf_n = ufcf_series[-1][1]

    if terminal_inputs.method == TerminalValueMethod.GORDON_GROWTH.value:
        term_res = calculate_terminal_value_gordon_growth(
            ufcf_n=ufcf_n,
            wacc_pct=wacc_val,
            perpetual_growth_rate_pct=terminal_inputs.perpetual_growth_rate or 2.5,
            terminal_discount_period=term_discount_period,
        )
    else:
        term_res = calculate_terminal_value_exit_multiple(
            terminal_ebitda=terminal_ebitda or 0.0,
            exit_multiple=terminal_inputs.exit_multiple or 10.0,
            wacc_pct=wacc_val,
            terminal_discount_period=term_discount_period,
        )

    warnings.extend(term_res.warnings)
    missing_inputs.extend(term_res.missing_inputs)

    # 6. Enterprise Value Calculation
    if term_res.pv_terminal_value is not None:
        ev = pv_ufcf + term_res.pv_terminal_value
        ev = round(ev, 4)

        if ev != 0.0:
            pv_ufcf_pct = (pv_ufcf / ev) * 100.0
            pv_tv_pct = (term_res.pv_terminal_value / ev) * 100.0
        else:
            pv_ufcf_pct = 0.0
            pv_tv_pct = 0.0
    else:
        ev = None
        pv_ufcf_pct = None
        pv_tv_pct = None

    # 7. Equity Bridge Calculation
    bridge_res = calculate_equity_bridge(ev, bridge_inputs)
    warnings.extend(bridge_res.warnings)
    missing_inputs.extend(bridge_res.missing_inputs)

    # 8. Implied Value Per Share
    implied_per_share: Optional[float] = None
    if bridge_res.equity_value is not None and diluted_shares is not None:
        if diluted_shares > 0.0:
            implied_per_share = round(bridge_res.equity_value / diluted_shares, 2)
        else:
            warnings.append("Diluted shares outstanding must be greater than zero to compute per-share value.")
    elif diluted_shares is None:
        warnings.append("Diluted shares outstanding not provided: implied value per share is withheld.")

    is_complete = (ev is not None and bridge_res.equity_value is not None and len(missing_inputs) == 0)

    return DcfValuationResult(
        enterprise_value=ev,
        equity_value=bridge_res.equity_value,
        implied_value_per_share=implied_per_share,
        diluted_shares_applied=diluted_shares,
        pv_forecast_ufcf=round(pv_ufcf, 4),
        terminal_value=term_res.terminal_value,
        pv_terminal_value=term_res.pv_terminal_value,
        terminal_value_pct_ev=round(pv_tv_pct, 2) if pv_tv_pct is not None else None,
        pv_ufcf_pct_ev=round(pv_ufcf_pct, 2) if pv_ufcf_pct is not None else None,
        wacc_applied=round(wacc_val, 4),
        discounting_convention_applied=convention,
        annual_discounting_schedule=schedule,
        terminal_result=term_res,
        bridge_result=bridge_res,
        is_complete=is_complete,
        missing_inputs=missing_inputs,
        warnings=warnings,
    )
