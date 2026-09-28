"""Formatting, tabular schedules, and Plotly visualizations for DCF valuation.

Generates structured pandas DataFrames and interactive visual charts for
cash flow discounting schedules, terminal value bridges, and equity bridges.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

import pandas as pd
import plotly.graph_objects as go

from src.dcf.models import DcfValuationResult, TerminalValueMethod


def build_discounting_schedule_dataframe(
    result: DcfValuationResult,
    currency: str = "USD",
    unit: str = "millions",
) -> pd.DataFrame:
    """Generate a multi-year cash flow discounting schedule DataFrame."""
    if not result.annual_discounting_schedule:
        return pd.DataFrame()

    rows: List[Dict[str, Any]] = []
    for item in result.annual_discounting_schedule:
        rows.append({
            "Forecast Period": item.period_label,
            f"Projected UFCF ({currency} {unit})": f"{item.ufcf:,.2f}",
            "Discount Period (t)": f"{item.discount_period:.1f}",
            "Discount Factor": f"{item.discount_factor:.4f}",
            f"Present Value ({currency} {unit})": f"{item.pv_ufcf:,.2f}",
        })

    # Summary row
    if result.pv_forecast_ufcf is not None:
        rows.append({
            "Forecast Period": "Cumulative Forecast PV",
            f"Projected UFCF ({currency} {unit})": "—",
            "Discount Period (t)": "—",
            "Discount Factor": "—",
            f"Present Value ({currency} {unit})": f"{result.pv_forecast_ufcf:,.2f}",
        })

    return pd.DataFrame(rows)


def build_equity_bridge_dataframe(
    result: DcfValuationResult,
    currency: str = "USD",
    unit: str = "millions",
) -> pd.DataFrame:
    """Generate an Enterprise Value to Equity Value bridge DataFrame."""
    b = result.bridge_result
    if not b:
        return pd.DataFrame()

    ev_val = result.enterprise_value
    eq_val = result.equity_value

    rows: List[Dict[str, Any]] = []

    # 1. Enterprise Value
    rows.append({
        "Bridge Step": "1. Enterprise Value (EV)",
        "Accounting Operation": "Base Valuation",
        f"Amount ({currency} {unit})": f"{ev_val:,.2f}" if ev_val is not None else "[Withheld]",
        "Bridge Notes": "PV of Forecast UFCF + PV of Terminal Value",
    })

    # 2. Add Cash
    rows.append({
        "Bridge Step": "2. (+) Cash & Cash Equivalents",
        "Accounting Operation": "Add (+) Liquid Assets",
        f"Amount ({currency} {unit})": f"+{b.cash_added:,.2f}",
        "Bridge Notes": "Non-operating cash balance available to equity holders",
    })

    # 3. Deduct Debt
    rows.append({
        "Bridge Step": "3. (-) Interest-Bearing Debt",
        "Accounting Operation": "Subtract (-) Senior Obligations",
        f"Amount ({currency} {unit})": f"-{b.debt_subtracted:,.2f}",
        "Bridge Notes": "Short-term borrowings + Long-term debt claims",
    })

    # 4. Minority Interest
    if b.minority_interest_subtracted != 0.0:
        rows.append({
            "Bridge Step": "4. (-) Minority Interest",
            "Accounting Operation": "Subtract (-) Non-Controlling Claims",
            f"Amount ({currency} {unit})": f"-{b.minority_interest_subtracted:,.2f}",
            "Bridge Notes": "Claims of third-party minority shareholders in consolidated subs",
        })

    # 5. Preferred Equity
    if b.preferred_equity_subtracted != 0.0:
        rows.append({
            "Bridge Step": "5. (-) Preferred Stock",
            "Accounting Operation": "Subtract (-) Preferred Claims",
            f"Amount ({currency} {unit})": f"-{b.preferred_equity_subtracted:,.2f}",
            "Bridge Notes": "Senior non-common equity claims",
        })

    # 6. Other Adjustments
    if b.other_adjustments_net != 0.0:
        sign_str = "+" if b.other_adjustments_net > 0 else ""
        rows.append({
            "Bridge Step": "6. (+/-) Other Non-Operating Adjustments",
            "Accounting Operation": "Signed Adjustment",
            f"Amount ({currency} {unit})": f"{sign_str}{b.other_adjustments_net:,.2f}",
            "Bridge Notes": "Associates, non-operating investments, litigation claims",
        })

    # 7. Net Debt Impact
    rows.append({
        "Bridge Step": "— Net Debt Netting (Debt - Cash)",
        "Accounting Operation": "Net Senior Obligations",
        f"Amount ({currency} {unit})": f"{b.net_debt:,.2f}",
        "Bridge Notes": "Net debt subtracted from enterprise value",
    })

    # 8. Implied Equity Value
    rows.append({
        "Bridge Step": "7. (=) Implied Equity Value",
        "Accounting Operation": "Residual Equity Base",
        f"Amount ({currency} {unit})": f"{eq_val:,.2f}" if eq_val is not None else "[Withheld]",
        "Bridge Notes": "Total value of common equity ownership",
    })

    # 9. Shares Outstanding & Value per Share
    if result.diluted_shares_applied is not None and result.diluted_shares_applied > 0:
        rows.append({
            "Bridge Step": "8. (÷) Diluted Shares Outstanding",
            "Accounting Operation": "Common Share Count",
            f"Amount ({currency} {unit})": f"{result.diluted_shares_applied:,.2f} shares",
            "Bridge Notes": "Weighted average diluted shares",
        })

        per_share_val = result.implied_value_per_share
        rows.append({
            "Bridge Step": "9. (=) Implied Value per Share",
            "Accounting Operation": "Per-Share Intrinsic Target",
            f"Amount ({currency} {unit})": f"{currency} {per_share_val:,.2f}" if per_share_val is not None else "[Withheld]",
            "Bridge Notes": f"Equity Value / Diluted Common Shares",
        })

    return pd.DataFrame(rows)


def create_cash_flow_discounting_chart(
    result: DcfValuationResult,
    currency: str = "USD",
) -> Optional[go.Figure]:
    """Generate a Plotly bar chart comparing projected nominal UFCF vs present value."""
    if not result.annual_discounting_schedule:
        return None

    periods = [item.period_label for item in result.annual_discounting_schedule]
    nominal_ufcf = [item.ufcf for item in result.annual_discounting_schedule]
    pv_ufcf = [item.pv_ufcf for item in result.annual_discounting_schedule]

    fig = go.Figure()

    fig.add_trace(
        go.Bar(
            name="Projected Nominal UFCF",
            x=periods,
            y=nominal_ufcf,
            marker_color="#a6c8e0",
            text=[f"{v:,.1f}" for v in nominal_ufcf],
            textposition="auto",
        )
    )

    fig.add_trace(
        go.Bar(
            name=f"Present Value (WACC: {result.wacc_applied:.2f}%)",
            x=periods,
            y=pv_ufcf,
            marker_color="#1f77b4",
            text=[f"{v:,.1f}" for v in pv_ufcf],
            textposition="auto",
        )
    )

    fig.update_layout(
        barmode="group",
        title="<b>Cash Flow Discounting Trajectory (Nominal vs. Present Value)</b>",
        title_font_size=14,
        yaxis_title=f"Amount ({currency})",
        margin=dict(l=20, r=20, t=40, b=20),
        height=320,
        legend=dict(orientation="h", yanchor="bottom", y=-0.25, xanchor="center", x=0.5),
    )

    return fig


def create_ev_composition_donut_chart(result: DcfValuationResult) -> Optional[go.Figure]:
    """Generate a Plotly donut chart depicting the contribution of explicit cash flows vs terminal value."""
    if result.pv_forecast_ufcf is None or result.pv_terminal_value is None or result.enterprise_value is None:
        return None

    pv_fc = max(0.0, result.pv_forecast_ufcf)
    pv_tv = max(0.0, result.pv_terminal_value)

    labels = ["PV of Explicit Forecast Cash Flows", "PV of Terminal Value"]
    values = [pv_fc, pv_tv]
    colors = ["#1f77b4", "#2ca02c"]

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

    ev_disp = result.enterprise_value
    tv_pct = result.terminal_value_pct_ev or 0.0

    fig.update_layout(
        title=f"<b>Enterprise Value Composition (TV Share: {tv_pct:.1f}%)</b>",
        title_font_size=14,
        margin=dict(l=20, r=20, t=40, b=20),
        height=320,
        showlegend=True,
        legend=dict(orientation="h", yanchor="bottom", y=-0.25, xanchor="center", x=0.5),
    )

    return fig
