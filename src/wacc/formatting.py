"""Tabular formatting and visualization dataframes for WACC and capital structure.

Prepares clean pandas DataFrames and Plotly visualization specifications for
Streamlit presentation and audit reporting.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

import pandas as pd
import plotly.graph_objects as go

from src.wacc.models import WaccAssumptions, WaccResult


def build_capital_structure_dataframe(
    result: WaccResult,
    currency: str = "USD",
    unit: str = "millions",
) -> pd.DataFrame:
    """Build a detailed capital structure summary DataFrame."""
    cap = result.capital_structure
    rows: List[Dict[str, Any]] = []

    if cap.equity_value is not None:
        eq_type_label = "Book Value Proxy" if cap.is_book_value_proxy else "Market Value"
        rows.append({
            "Component": "Equity Capital (E)",
            "Valuation Basis": eq_type_label,
            f"Amount ({currency} {unit})": f"{cap.equity_value:,.2f}",
            "Weight (%)": f"{cap.equity_weight_pct:.2f}%" if cap.equity_weight_pct is not None else "[Missing]",
            "Status": "Proxy Used" if cap.is_book_value_proxy else "Verified Input",
        })

    if cap.debt_value is not None:
        rows.append({
            "Component": "Interest-Bearing Debt (D)",
            "Valuation Basis": "Reported Borrowings",
            f"Amount ({currency} {unit})": f"{cap.debt_value:,.2f}",
            "Weight (%)": f"{cap.debt_weight_pct:.2f}%" if cap.debt_weight_pct is not None else "[Missing]",
            "Status": "Verified Input",
        })

    if cap.total_capital is not None and cap.total_capital > 0:
        rows.append({
            "Component": "Total Capital Base (V)",
            "Valuation Basis": "Sum (E + D)",
            f"Amount ({currency} {unit})": f"{cap.total_capital:,.2f}",
            "Weight (%)": "100.00%",
            "Status": "Evaluated Base",
        })

    if not rows:
        return pd.DataFrame(columns=["Component", "Valuation Basis", f"Amount ({currency} {unit})", "Weight (%)", "Status"])

    return pd.DataFrame(rows)


def build_cost_of_capital_dataframe(
    result: WaccResult,
    assumptions: WaccAssumptions,
) -> pd.DataFrame:
    """Build a comprehensive cost of capital breakdown DataFrame."""
    ke_res = result.cost_of_equity
    kd_res = result.cost_of_debt
    cap_res = result.capital_structure

    rows: List[Dict[str, Any]] = []

    # 1. Cost of Equity
    rows.append({
        "Capital Component": "Cost of Equity (Ke)",
        "Underlying Formula": "CAPM: Rf + (Beta × ERP)",
        "Rate (%)": f"{ke_res.cost_of_equity:.2f}%" if ke_res.cost_of_equity is not None else "[Incomplete]",
        "Capital Weight": f"{cap_res.equity_weight_pct:.2f}%" if cap_res.equity_weight_pct is not None else "—",
        "WACC Contribution": f"{result.equity_contribution:.2f}%" if result.equity_contribution is not None else "—",
        "Source Category": assumptions.equity_inputs.rf_provenance.source_category.replace("_", " ").title(),
        "Notes": f"Rf: {ke_res.risk_free_rate or 0:.2f}%, Beta: {ke_res.equity_beta or 0:.2f}, ERP: {ke_res.equity_risk_premium or 0:.2f}%",
    })

    # 2. Pre-Tax Cost of Debt
    rows.append({
        "Capital Component": "Pre-Tax Cost of Debt (Kd)",
        "Underlying Formula": "Borrowing Spread / Accounting Rate",
        "Rate (%)": f"{kd_res.pre_tax_cost_of_debt:.2f}%" if kd_res.pre_tax_cost_of_debt is not None else "[Incomplete]",
        "Capital Weight": "—",
        "WACC Contribution": "—",
        "Source Category": assumptions.debt_inputs.provenance.source_category.replace("_", " ").title(),
        "Notes": assumptions.debt_inputs.provenance.source_reference or "Pre-tax borrowing rate",
    })

    # 3. Tax Rate
    rows.append({
        "Capital Component": "Marginal Corporate Tax Rate (t)",
        "Underlying Formula": "Debt Interest Deductibility Shield",
        "Rate (%)": f"{kd_res.tax_rate_applied:.2f}%" if kd_res.tax_rate_applied is not None else "[Incomplete]",
        "Capital Weight": "—",
        "WACC Contribution": "—",
        "Source Category": assumptions.tax_inputs.provenance.source_category.replace("_", " ").title(),
        "Notes": assumptions.tax_inputs.provenance.source_reference or "Applied to Pre-Tax Kd",
    })

    # 4. After-Tax Cost of Debt
    rows.append({
        "Capital Component": "After-Tax Cost of Debt (Kd_after)",
        "Underlying Formula": "Pre-Tax Kd × (1 - t)",
        "Rate (%)": f"{kd_res.after_tax_cost_of_debt:.2f}%" if kd_res.after_tax_cost_of_debt is not None else "[Incomplete]",
        "Capital Weight": f"{cap_res.debt_weight_pct:.2f}%" if cap_res.debt_weight_pct is not None else "—",
        "WACC Contribution": f"{result.debt_contribution:.2f}%" if result.debt_contribution is not None else "—",
        "Source Category": "Calculated Metric",
        "Notes": f"Tax Shield Benefit: {kd_res.tax_shield_benefit or 0:.2f}%",
    })

    # 5. Final WACC
    rows.append({
        "Capital Component": "Weighted Average Cost of Capital (WACC)",
        "Underlying Formula": "(We × Ke) + (Wd × Kd_after)",
        "Rate (%)": f"{result.wacc:.2f}%" if result.wacc is not None else "[Incomplete]",
        "Capital Weight": "100.00%",
        "WACC Contribution": f"{result.wacc:.2f}%" if result.wacc is not None else "—",
        "Source Category": "Blended Hurdle Rate",
        "Notes": result.formula_breakdown if result.is_complete else "Awaiting complete inputs",
    })

    return pd.DataFrame(rows)


def create_capital_structure_donut_chart(result: WaccResult) -> Optional[go.Figure]:
    """Generate an institutional Plotly donut chart of enterprise capital structure weights."""
    cap = result.capital_structure
    if cap.equity_weight_pct is None or cap.debt_weight_pct is None:
        return None

    labels = ["Equity Capital (We)", "Interest-Bearing Debt (Wd)"]
    values = [cap.equity_weight_pct, cap.debt_weight_pct]
    colors = ["#1f77b4", "#ff7f0e"]

    fig = go.Figure(
        data=[
            go.Pie(
                labels=labels,
                values=values,
                hole=0.55,
                marker=dict(colors=colors, line=dict(color="#ffffff", width=2)),
                textinfo="label+percent",
                hoverinfo="label+percent+value",
            )
        ]
    )

    fig.update_layout(
        title="<b>Capital Structure Weighting (V = E + D)</b>",
        title_font_size=14,
        margin=dict(l=20, r=20, t=40, b=20),
        height=320,
        showlegend=True,
        legend=dict(orientation="h", yanchor="bottom", y=-0.2, xanchor="center", x=0.5),
    )

    return fig


def create_wacc_contribution_bar_chart(result: WaccResult) -> Optional[go.Figure]:
    """Generate a horizontal stacked bar chart showing the composition of WACC."""
    if not result.is_complete or result.equity_contribution is None or result.debt_contribution is None:
        return None

    fig = go.Figure()

    fig.add_trace(
        go.Bar(
            name="Equity Contribution (We × Ke)",
            y=["WACC"],
            x=[result.equity_contribution],
            orientation="h",
            marker=dict(color="#1f77b4"),
            text=[f"{result.equity_contribution:.2f}%"],
            textposition="auto",
        )
    )

    fig.add_trace(
        go.Bar(
            name="Debt Contribution (Wd × Kd_after)",
            y=["WACC"],
            x=[result.debt_contribution],
            orientation="h",
            marker=dict(color="#ff7f0e"),
            text=[f"{result.debt_contribution:.2f}%"],
            textposition="auto",
        )
    )

    total_wacc = result.wacc or 0.0

    fig.update_layout(
        barmode="stack",
        title=f"<b>WACC Composition Breakdown (Total WACC = {total_wacc:.2f}%)</b>",
        title_font_size=14,
        xaxis_title="Percentage Contribution to WACC (%)",
        margin=dict(l=20, r=20, t=40, b=20),
        height=180,
        showlegend=True,
        legend=dict(orientation="h", yanchor="bottom", y=-0.5, xanchor="center", x=0.5),
    )

    return fig
