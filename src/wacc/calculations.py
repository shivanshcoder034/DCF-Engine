"""Deterministic calculations for WACC, CAPM, borrowing costs, and capital weights.

Implements pure, independent mathematical logic for each component of the
Weighted Average Cost of Capital with strict numerical validation and auditability.
"""

from __future__ import annotations

import math
from typing import List, Optional

from src.wacc.models import (
    CapitalStructureInputs,
    CapitalStructureResult,
    CostOfDebtInputs,
    CostOfDebtResult,
    CostOfEquityInputs,
    CostOfEquityResult,
    TaxRateInputs,
    WaccAssumptions,
    WaccResult,
)


def _is_finite_number(val: Any) -> bool:
    """Check if value is a valid real number that is not NaN or infinite."""
    if val is None:
        return False
    try:
        f_val = float(val)
        return not (math.isnan(f_val) or math.isinf(f_val))
    except (TypeError, ValueError):
        return False


def calculate_cost_of_equity(inputs: CostOfEquityInputs) -> CostOfEquityResult:
    """Calculate Cost of Equity using the Capital Asset Pricing Model (CAPM).

    Formula:
        Cost of Equity (Ke) = Risk-Free Rate (Rf) + Beta * Equity Risk Premium (ERP)
    """
    missing_inputs: List[str] = []
    warnings: List[str] = []

    rf = inputs.risk_free_rate
    beta = inputs.equity_beta
    erp = inputs.equity_risk_premium

    if not _is_finite_number(rf):
        missing_inputs.append("Risk-Free Rate (Rf)")
    if not _is_finite_number(beta):
        missing_inputs.append("Equity Beta")
    if not _is_finite_number(erp):
        missing_inputs.append("Equity Risk Premium (ERP)")

    if missing_inputs:
        rf_str = f"{rf:.2f}%" if _is_finite_number(rf) else "[Missing]"
        beta_str = f"{beta:.2f}" if _is_finite_number(beta) else "[Missing]"
        erp_str = f"{erp:.2f}%" if _is_finite_number(erp) else "[Missing]"
        formula = f"Ke = {rf_str} + ({beta_str} × {erp_str}) [Incomplete]"

        return CostOfEquityResult(
            cost_of_equity=None,
            risk_free_rate=rf,
            equity_beta=beta,
            equity_risk_premium=erp,
            formula_display=formula,
            status="incomplete",
            missing_inputs=missing_inputs,
            warnings=warnings,
        )

    # All inputs are present numbers
    rf_val = float(rf)
    beta_val = float(beta)
    erp_val = float(erp)

    # Domain sanity validations
    if rf_val < 0.0:
        warnings.append(f"Negative Risk-Free Rate entered ({rf_val:.2f}%). Sovereign benchmark yields are rarely negative.")
    if beta_val < 0.0:
        warnings.append(f"Negative Equity Beta entered ({beta_val:.2f}). Indicates inverse correlation to benchmark index.")
    elif beta_val > 3.0:
        warnings.append(f"Unusually high Equity Beta entered ({beta_val:.2f}). Implies extreme enterprise volatility.")
    if erp_val <= 0.0:
        warnings.append(f"Non-positive Equity Risk Premium entered ({erp_val:.2f}%). Rational markets require positive risk compensation.")

    ke = rf_val + (beta_val * erp_val)
    formula = f"Ke = {rf_val:.2f}% + ({beta_val:.2f} × {erp_val:.2f}%) = {ke:.2f}%"

    return CostOfEquityResult(
        cost_of_equity=round(ke, 4),
        risk_free_rate=rf_val,
        equity_beta=beta_val,
        equity_risk_premium=erp_val,
        formula_display=formula,
        status="complete",
        missing_inputs=[],
        warnings=warnings,
    )


def calculate_cost_of_debt(
    debt_inputs: CostOfDebtInputs,
    tax_inputs: TaxRateInputs,
) -> CostOfDebtResult:
    """Calculate Pre-Tax and Effective After-Tax Cost of Debt.

    Formula:
        After-Tax Cost of Debt (Kd_after) = Pre-Tax Kd * (1 - Marginal Tax Rate)
    """
    missing_inputs: List[str] = []
    warnings: List[str] = []
    notes: List[str] = []

    kd = debt_inputs.pre_tax_cost_of_debt
    t = tax_inputs.tax_rate

    if not _is_finite_number(kd):
        missing_inputs.append("Pre-Tax Cost of Debt (Kd)")
    if not _is_finite_number(t):
        missing_inputs.append("Tax Rate (t)")

    if debt_inputs.use_historical_estimate and debt_inputs.historical_calculation_notes:
        notes.append(debt_inputs.historical_calculation_notes)

    if missing_inputs:
        kd_str = f"{kd:.2f}%" if _is_finite_number(kd) else "[Missing]"
        t_str = f"{t:.2f}%" if _is_finite_number(t) else "[Missing]"
        formula = f"After-Tax Kd = {kd_str} × (1 - {t_str}) [Incomplete]"

        return CostOfDebtResult(
            pre_tax_cost_of_debt=kd,
            after_tax_cost_of_debt=None,
            tax_rate_applied=t,
            tax_shield_benefit=None,
            formula_display=formula,
            status="incomplete",
            missing_inputs=missing_inputs,
            notes=notes,
            warnings=warnings,
        )

    kd_val = float(kd)
    t_val = float(t)

    # Domain sanity validations
    if kd_val < 0.0:
        warnings.append(f"Negative Pre-Tax Cost of Debt entered ({kd_val:.2f}%). Creditors do not pay borrowers to borrow.")
    if t_val < 0.0:
        warnings.append(f"Negative tax rate entered ({t_val:.2f}%). Resulting in a negative interest tax shield.")
    elif t_val > 50.0:
        warnings.append(f"Unusually high corporate tax rate entered ({t_val:.2f}%). Statutory rates rarely exceed 50%.")

    # Formula calculation: Kd_after = Kd * (1 - t/100)
    tax_fraction = t_val / 100.0
    kd_after = kd_val * (1.0 - tax_fraction)
    tax_shield = kd_val - kd_after

    formula = f"After-Tax Kd = {kd_val:.2f}% × (1 - {t_val:.2f}%) = {kd_after:.2f}%"

    return CostOfDebtResult(
        pre_tax_cost_of_debt=round(kd_val, 4),
        after_tax_cost_of_debt=round(kd_after, 4),
        tax_rate_applied=round(t_val, 4),
        tax_shield_benefit=round(tax_shield, 4),
        formula_display=formula,
        status="complete",
        missing_inputs=[],
        notes=notes,
        warnings=warnings,
    )


def calculate_capital_structure(inputs: CapitalStructureInputs) -> CapitalStructureResult:
    """Calculate enterprise debt and equity capital structure weights.

    Formula:
        Total Capital (V) = Equity Value (E) + Debt Value (D)
        Equity Weight (We) = E / V
        Debt Weight (Wd) = D / V
    """
    missing_inputs: List[str] = []
    warnings: List[str] = []

    eq = inputs.equity_value
    dt = inputs.debt_value

    if not _is_finite_number(eq):
        missing_inputs.append("Equity Capitalization / Value (E)")
    if not _is_finite_number(dt):
        missing_inputs.append("Interest-Bearing Debt Balance (D)")

    is_proxy = (inputs.equity_value_type == "book_value_proxy")
    if is_proxy:
        warnings.append(
            "Proxy Notice: Book value of equity is used as a proxy because market capitalization was not provided. "
            "Book value often differs substantially from market enterprise valuation and may bias WACC weights."
        )

    if missing_inputs:
        eq_str = f"{eq:,.0f}" if _is_finite_number(eq) else "[Missing]"
        dt_str = f"{dt:,.0f}" if _is_finite_number(dt) else "[Missing]"
        formula = f"We = {eq_str} / ({eq_str} + {dt_str}) [Incomplete]"

        return CapitalStructureResult(
            equity_value=eq,
            debt_value=dt,
            total_capital=None,
            equity_weight=None,
            debt_weight=None,
            equity_weight_pct=None,
            debt_weight_pct=None,
            is_book_value_proxy=is_proxy,
            formula_display=formula,
            status="incomplete",
            missing_inputs=missing_inputs,
            warnings=warnings,
        )

    eq_val = float(eq)
    dt_val = float(dt)

    # Sanity checks on non-negative capital base
    if eq_val < 0.0:
        warnings.append(f"Negative equity value ({eq_val:,.2f}) is invalid for capital structure weighting.")
        return CapitalStructureResult(
            equity_value=eq_val,
            debt_value=dt_val,
            total_capital=None,
            equity_weight=None,
            debt_weight=None,
            equity_weight_pct=None,
            debt_weight_pct=None,
            is_book_value_proxy=is_proxy,
            formula_display="Invalid: Equity capital cannot be negative",
            status="invalid",
            missing_inputs=["Valid non-negative Equity Value"],
            warnings=warnings,
        )

    if dt_val < 0.0:
        warnings.append(f"Negative debt balance ({dt_val:,.2f}) is invalid for capital structure weighting.")
        return CapitalStructureResult(
            equity_value=eq_val,
            debt_value=dt_val,
            total_capital=None,
            equity_weight=None,
            debt_weight=None,
            equity_weight_pct=None,
            debt_weight_pct=None,
            is_book_value_proxy=is_proxy,
            formula_display="Invalid: Debt balance cannot be negative",
            status="invalid",
            missing_inputs=["Valid non-negative Debt Balance"],
            warnings=warnings,
        )

    total_capital = eq_val + dt_val

    if total_capital <= 0.0:
        warnings.append("Total enterprise capital base (Equity + Debt) is zero. Cannot compute percentage weights.")
        return CapitalStructureResult(
            equity_value=eq_val,
            debt_value=dt_val,
            total_capital=0.0,
            equity_weight=None,
            debt_weight=None,
            equity_weight_pct=None,
            debt_weight_pct=None,
            is_book_value_proxy=is_proxy,
            formula_display="Invalid: Total capital base is zero",
            status="invalid",
            missing_inputs=["Non-zero total enterprise capital"],
            warnings=warnings,
        )

    we = eq_val / total_capital
    wd = dt_val / total_capital
    we_pct = we * 100.0
    wd_pct = wd * 100.0

    formula = (
        f"Total Capital = {total_capital:,.0f} | "
        f"We = {we_pct:.1f}% ({eq_val:,.0f}) | "
        f"Wd = {wd_pct:.1f}% ({dt_val:,.0f})"
    )

    return CapitalStructureResult(
        equity_value=round(eq_val, 2),
        debt_value=round(dt_val, 2),
        total_capital=round(total_capital, 2),
        equity_weight=round(we, 6),
        debt_weight=round(wd, 6),
        equity_weight_pct=round(we_pct, 2),
        debt_weight_pct=round(wd_pct, 2),
        is_book_value_proxy=is_proxy,
        formula_display=formula,
        status="complete",
        missing_inputs=[],
        warnings=warnings,
    )


def calculate_wacc(assumptions: WaccAssumptions) -> WaccResult:
    """Orchestrate end-to-end WACC estimation from all configured input blocks.

    Formula:
        WACC = (Equity Weight * Cost of Equity) + (Debt Weight * After-Tax Cost of Debt)
    """
    ke_result = calculate_cost_of_equity(assumptions.equity_inputs)
    kd_result = calculate_cost_of_debt(assumptions.debt_inputs, assumptions.tax_inputs)
    cap_result = calculate_capital_structure(assumptions.capital_inputs)

    all_missing: List[str] = []
    all_warnings: List[str] = []

    all_missing.extend(ke_result.missing_inputs)
    all_missing.extend(kd_result.missing_inputs)
    all_missing.extend(cap_result.missing_inputs)

    all_warnings.extend(ke_result.warnings)
    all_warnings.extend(kd_result.warnings)
    all_warnings.extend(cap_result.warnings)

    can_compute = (
        ke_result.cost_of_equity is not None
        and kd_result.after_tax_cost_of_debt is not None
        and cap_result.equity_weight is not None
        and cap_result.debt_weight is not None
    )

    if not can_compute:
        return WaccResult(
            wacc=None,
            is_complete=False,
            cost_of_equity=ke_result,
            cost_of_debt=kd_result,
            capital_structure=cap_result,
            formula_breakdown="WACC estimation incomplete: missing required inputs or invalid capital base.",
            equity_contribution=None,
            debt_contribution=None,
            missing_inputs=all_missing,
            warnings=all_warnings,
        )

    we = cap_result.equity_weight
    ke = ke_result.cost_of_equity
    wd = cap_result.debt_weight
    kd_after = kd_result.after_tax_cost_of_debt

    eq_contribution = we * ke
    dt_contribution = wd * kd_after
    final_wacc = eq_contribution + dt_contribution

    formula_str = (
        f"WACC = ({cap_result.equity_weight_pct:.1f}% We × {ke:.2f}% Ke) + "
        f"({cap_result.debt_weight_pct:.1f}% Wd × {kd_after:.2f}% After-Tax Kd) = "
        f"{final_wacc:.2f}%"
    )

    return WaccResult(
        wacc=round(final_wacc, 4),
        is_complete=True,
        cost_of_equity=ke_result,
        cost_of_debt=kd_result,
        capital_structure=cap_result,
        formula_breakdown=formula_str,
        equity_contribution=round(eq_contribution, 4),
        debt_contribution=round(dt_contribution, 4),
        missing_inputs=[],
        warnings=all_warnings,
    )
