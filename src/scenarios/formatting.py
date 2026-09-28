"""Formatting, tabular schedules, and Plotly visualizations for multi-scenario DCF analysis.

Builds structured pandas DataFrames for scenario comparison and audit tables,
and interactive Plotly charts for Enterprise Value, Equity Value, Implied Share Price,
and Cash Flow trajectories across Base, Bull, and Bear cases.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

import pandas as pd
import plotly.graph_objects as go

from src.dcf.models import TerminalValueMethod
from src.scenarios.models import ScenarioAnalysisResult, ScenarioCaseResult


def _format_curr(val: Optional[float], currency: str = "USD", unit: str = "millions") -> str:
    if val is None:
        return "[Withheld / Unavailable]"
    return f"{currency} {val:,.2f} {unit}".strip()


def _format_share_price(val: Optional[float], currency: str = "USD") -> str:
    if val is None:
        return "[Withheld / Unavailable]"
    return f"{currency} {val:,.2f}"


def build_scenario_comparison_dataframe(
    result: ScenarioAnalysisResult,
    currency: str = "USD",
    unit: str = "millions",
) -> pd.DataFrame:
    """Build a consolidated cross-scenario comparison DataFrame."""
    cases = [
        ("Base Case", result.base_case),
        ("Bull Case", result.bull_case),
        ("Bear Case", result.bear_case),
    ]

    def fmt_rev_growth(c: ScenarioCaseResult) -> str:
        avg = c.effective_revenue_growth_avg
        if avg is None:
            return "—"
        delta = c.overrides.revenue_growth_delta_pp
        if delta == 0.0:
            return f"{avg:.2f}%"
        sign = "+" if delta > 0 else ""
        return f"{avg:.2f}% ({sign}{delta:.2f} pp)"

    def fmt_op_margin(c: ScenarioCaseResult) -> str:
        avg = c.effective_operating_margin_avg
        if avg is None:
            return "—"
        delta = c.overrides.margin_delta_pp
        if delta == 0.0:
            return f"{avg:.2f}%"
        sign = "+" if delta > 0 else ""
        return f"{avg:.2f}% ({sign}{delta:.2f} pp)"

    def fmt_wacc(c: ScenarioCaseResult) -> str:
        w = c.effective_wacc
        if w is None:
            return "—"
        delta_bps = c.overrides.wacc_delta_bps
        if delta_bps == 0.0:
            return f"{w:.2f}%"
        sign = "+" if delta_bps > 0 else ""
        return f"{w:.2f}% ({sign}{delta_bps:+.0f} bps)"

    def fmt_term_param(c: ScenarioCaseResult) -> str:
        p = c.effective_terminal_param
        if p is None:
            return "—"
        if c.terminal_method == TerminalValueMethod.GORDON_GROWTH.value:
            delta_bps = c.overrides.perpetual_growth_delta_bps
            if delta_bps == 0.0:
                return f"g = {p:.2f}%"
            return f"g = {p:.2f}% ({delta_bps:+.0f} bps)"
        else:
            delta_x = c.overrides.exit_multiple_delta
            if delta_x == 0.0:
                return f"{p:.2f}x EBITDA"
            return f"{p:.2f}x ({delta_x:+.2f}x)"

    rows: List[Dict[str, Any]] = [
        {
            "Metric / Parameter": "Calculation Status",
            "Base Case": "✅ Validated" if result.base_case.is_valid else f"⚠️ {result.base_case.status.title()}",
            "Bull Case": "✅ Validated" if result.bull_case.is_valid else f"⚠️ {result.bull_case.status.title()}",
            "Bear Case": "✅ Validated" if result.bear_case.is_valid else f"⚠️ {result.bear_case.status.title()}",
        },
        {
            "Metric / Parameter": "Avg. Revenue Growth (% & pp shift)",
            "Base Case": fmt_rev_growth(result.base_case),
            "Bull Case": fmt_rev_growth(result.bull_case),
            "Bear Case": fmt_rev_growth(result.bear_case),
        },
        {
            "Metric / Parameter": "Avg. Operating Margin (% & pp shift)",
            "Base Case": fmt_op_margin(result.base_case),
            "Bull Case": fmt_op_margin(result.bull_case),
            "Bear Case": fmt_op_margin(result.bear_case),
        },
        {
            "Metric / Parameter": "Discount Rate / WACC (% & bps shift)",
            "Base Case": fmt_wacc(result.base_case),
            "Bull Case": fmt_wacc(result.bull_case),
            "Bear Case": fmt_wacc(result.bear_case),
        },
        {
            "Metric / Parameter": "Terminal Method & Assumption",
            "Base Case": fmt_term_param(result.base_case),
            "Bull Case": fmt_term_param(result.bull_case),
            "Bear Case": fmt_term_param(result.bear_case),
        },
        {
            "Metric / Parameter": f"PV of Forecast UFCF ({currency} {unit})",
            "Base Case": f"{result.base_case.pv_forecast_ufcf:,.2f}" if result.base_case.pv_forecast_ufcf is not None else "[Withheld]",
            "Bull Case": f"{result.bull_case.pv_forecast_ufcf:,.2f}" if result.bull_case.pv_forecast_ufcf is not None else "[Withheld]",
            "Bear Case": f"{result.bear_case.pv_forecast_ufcf:,.2f}" if result.bear_case.pv_forecast_ufcf is not None else "[Withheld]",
        },
        {
            "Metric / Parameter": f"PV of Terminal Value ({currency} {unit})",
            "Base Case": f"{result.base_case.pv_terminal_value:,.2f}" if result.base_case.pv_terminal_value is not None else "[Withheld]",
            "Bull Case": f"{result.bull_case.pv_terminal_value:,.2f}" if result.bull_case.pv_terminal_value is not None else "[Withheld]",
            "Bear Case": f"{result.bear_case.pv_terminal_value:,.2f}" if result.bear_case.pv_terminal_value is not None else "[Withheld]",
        },
        {
            "Metric / Parameter": f"Enterprise Value (EV) ({currency} {unit})",
            "Base Case": f"{result.base_case.enterprise_value:,.2f}" if result.base_case.enterprise_value is not None else "[Withheld]",
            "Bull Case": f"{result.bull_case.enterprise_value:,.2f}" if result.bull_case.enterprise_value is not None else "[Withheld]",
            "Bear Case": f"{result.bear_case.enterprise_value:,.2f}" if result.bear_case.enterprise_value is not None else "[Withheld]",
        },
        {
            "Metric / Parameter": f"Equity Value ({currency} {unit})",
            "Base Case": f"{result.base_case.equity_value:,.2f}" if result.base_case.equity_value is not None else "[Withheld]",
            "Bull Case": f"{result.bull_case.equity_value:,.2f}" if result.bull_case.equity_value is not None else "[Withheld]",
            "Bear Case": f"{result.bear_case.equity_value:,.2f}" if result.bear_case.equity_value is not None else "[Withheld]",
        },
        {
            "Metric / Parameter": f"Implied Value per Share ({currency})",
            "Base Case": f"{result.base_case.implied_value_per_share:,.2f}" if result.base_case.implied_value_per_share is not None else "[Withheld]",
            "Bull Case": f"{result.bull_case.implied_value_per_share:,.2f}" if result.bull_case.implied_value_per_share is not None else "[Withheld]",
            "Bear Case": f"{result.bear_case.implied_value_per_share:,.2f}" if result.bear_case.implied_value_per_share is not None else "[Withheld]",
        },
        {
            "Metric / Parameter": "Validation / Diagnostics",
            "Base Case": "All baseline inputs verified" if result.base_case.is_valid else "; ".join(result.base_case.missing_inputs or result.base_case.warnings),
            "Bull Case": "All assumptions verified" if result.bull_case.is_valid else "; ".join(result.bull_case.missing_inputs or result.bull_case.warnings),
            "Bear Case": "All assumptions verified" if result.bear_case.is_valid else "; ".join(result.bear_case.missing_inputs or result.bear_case.warnings),
        },
    ]

    return pd.DataFrame(rows)


def build_assumption_audit_dataframe(result: ScenarioAnalysisResult) -> pd.DataFrame:
    """Build a detailed auditability DataFrame tracing baseline values, overrides, and resulting assumptions."""
    base = result.base_case
    bull = result.bull_case
    bear = result.bear_case

    is_gordon = base.terminal_method == TerminalValueMethod.GORDON_GROWTH.value

    rows: List[Dict[str, Any]] = [
        {
            "Assumption Driver": "Revenue Growth Rate",
            "Baseline Value": f"{base.effective_revenue_growth_avg:.2f}% (avg)" if base.effective_revenue_growth_avg is not None else "—",
            "Bull Override": f"{bull.overrides.revenue_growth_delta_pp:+.2f} pp",
            "Bull Scenario Result": f"{bull.effective_revenue_growth_avg:.2f}%" if bull.effective_revenue_growth_avg is not None else "—",
            "Bear Override": f"{bear.overrides.revenue_growth_delta_pp:+.2f} pp",
            "Bear Scenario Result": f"{bear.effective_revenue_growth_avg:.2f}%" if bear.effective_revenue_growth_avg is not None else "—",
            "Adjustment Units": "Percentage points (pp) added to each year's rate",
            "Linked Baseline Source": f"Forecast: {base.linked_forecast_name or 'Current'}",
        },
        {
            "Assumption Driver": "Operating Margin (EBIT Margin)",
            "Baseline Value": f"{base.effective_operating_margin_avg:.2f}% (avg)" if base.effective_operating_margin_avg is not None else "—",
            "Bull Override": f"{bull.overrides.margin_delta_pp:+.2f} pp",
            "Bull Scenario Result": f"{bull.effective_operating_margin_avg:.2f}%" if bull.effective_operating_margin_avg is not None else "—",
            "Bear Override": f"{bear.overrides.margin_delta_pp:+.2f} pp",
            "Bear Scenario Result": f"{bear.effective_operating_margin_avg:.2f}%" if bear.effective_operating_margin_avg is not None else "—",
            "Adjustment Units": "Percentage points (pp) added to gross margin",
            "Linked Baseline Source": f"Forecast: {base.linked_forecast_name or 'Current'}",
        },
        {
            "Assumption Driver": "Cost of Capital (WACC)",
            "Baseline Value": f"{base.effective_wacc:.2f}%" if base.effective_wacc is not None else "—",
            "Bull Override": f"{bull.overrides.wacc_delta_bps:+.0f} bps",
            "Bull Scenario Result": f"{bull.effective_wacc:.2f}%" if bull.effective_wacc is not None else "—",
            "Bear Override": f"{bear.overrides.wacc_delta_bps:+.0f} bps",
            "Bear Scenario Result": f"{bear.effective_wacc:.2f}%" if bear.effective_wacc is not None else "—",
            "Adjustment Units": "Basis points (bps, 100 bps = 1.00%)",
            "Linked Baseline Source": f"WACC: {base.linked_wacc_name or 'Current'}",
        },
    ]

    if is_gordon:
        rows.append({
            "Assumption Driver": "Perpetual Growth Rate (g)",
            "Baseline Value": f"{base.effective_terminal_param:.2f}%" if base.effective_terminal_param is not None else "—",
            "Bull Override": f"{bull.overrides.perpetual_growth_delta_bps:+.0f} bps",
            "Bull Scenario Result": f"{bull.effective_terminal_param:.2f}%" if bull.effective_terminal_param is not None else "—",
            "Bear Override": f"{bear.overrides.perpetual_growth_delta_bps:+.0f} bps",
            "Bear Scenario Result": f"{bear.effective_terminal_param:.2f}%" if bear.effective_terminal_param is not None else "—",
            "Adjustment Units": "Basis points (bps, 100 bps = 1.00%)",
            "Linked Baseline Source": f"DCF: {base.linked_dcf_name or 'Current'}",
        })
    else:
        rows.append({
            "Assumption Driver": "Exit Multiple (EV/EBITDA)",
            "Baseline Value": f"{base.effective_terminal_param:.2f}x" if base.effective_terminal_param is not None else "—",
            "Bull Override": f"{bull.overrides.exit_multiple_delta:+.2f}x",
            "Bull Scenario Result": f"{bull.effective_terminal_param:.2f}x" if bull.effective_terminal_param is not None else "—",
            "Bear Override": f"{bear.overrides.exit_multiple_delta:+.2f}x",
            "Bear Scenario Result": f"{bear.effective_terminal_param:.2f}x" if bear.effective_terminal_param is not None else "—",
            "Adjustment Units": "Multiple expansion / contraction (+/- x)",
            "Linked Baseline Source": f"DCF: {base.linked_dcf_name or 'Current'}",
        })

    return pd.DataFrame(rows)


def create_scenario_ev_equity_bar_chart(
    result: ScenarioAnalysisResult,
    currency: str = "USD",
) -> Optional[go.Figure]:
    """Generate a grouped bar chart comparing Enterprise Value and Equity Value across scenarios."""
    scenarios = ["Bear Case", "Base Case", "Bull Case"]
    cases = [result.bear_case, result.base_case, result.bull_case]

    ev_vals = [c.enterprise_value if c.is_valid else None for c in cases]
    eq_vals = [c.equity_value if c.is_valid else None for c in cases]

    if all(v is None for v in ev_vals):
        return None

    fig = go.Figure()

    fig.add_trace(
        go.Bar(
            name="Enterprise Value (EV)",
            x=scenarios,
            y=[v if v is not None else 0.0 for v in ev_vals],
            marker_color="#1f77b4",
            text=[f"{v:,.1f}" if v is not None else "Withheld" for v in ev_vals],
            textposition="auto",
        )
    )

    fig.add_trace(
        go.Bar(
            name="Equity Value",
            x=scenarios,
            y=[v if v is not None else 0.0 for v in eq_vals],
            marker_color="#2ca02c",
            text=[f"{v:,.1f}" if v is not None else "Withheld" for v in eq_vals],
            textposition="auto",
        )
    )

    fig.update_layout(
        barmode="group",
        title="<b>Enterprise Value vs. Equity Value by Scenario Case</b>",
        title_font_size=14,
        yaxis_title=f"Valuation ({currency})",
        margin=dict(l=20, r=20, t=40, b=20),
        height=340,
        legend=dict(orientation="h", yanchor="bottom", y=-0.25, xanchor="center", x=0.5),
    )

    return fig


def create_scenario_share_price_chart(
    result: ScenarioAnalysisResult,
    currency: str = "USD",
) -> Optional[go.Figure]:
    """Generate a comparison chart for Implied Value per Share across Bear, Base, and Bull cases."""
    scenarios = ["Bear Case", "Base Case", "Bull Case"]
    cases = [result.bear_case, result.base_case, result.bull_case]
    share_vals = [c.implied_value_per_share if c.is_valid else None for c in cases]

    if all(v is None for v in share_vals):
        return None

    colors = ["#d62728", "#1f77b4", "#2ca02c"]

    fig = go.Figure()

    fig.add_trace(
        go.Bar(
            x=scenarios,
            y=[v if v is not None else 0.0 for v in share_vals],
            marker_color=colors,
            text=[f"{currency} {v:,.2f}" if v is not None else "Withheld" for v in share_vals],
            textposition="auto",
            showlegend=False,
        )
    )

    # Reference line for Base Case
    if result.base_case.is_valid and result.base_case.implied_value_per_share is not None:
        base_val = result.base_case.implied_value_per_share
        fig.add_hline(
            y=base_val,
            line_dash="dot",
            line_color="#1f77b4",
            annotation_text=f"Base: {currency} {base_val:,.2f}",
            annotation_position="bottom right",
        )

    fig.update_layout(
        title="<b>Implied Intrinsic Value per Diluted Share by Scenario</b>",
        title_font_size=14,
        yaxis_title=f"Implied Share Price ({currency})",
        margin=dict(l=20, r=20, t=40, b=20),
        height=340,
    )

    return fig


def create_scenario_cash_flow_trajectory_chart(
    result: ScenarioAnalysisResult,
    currency: str = "USD",
) -> Optional[go.Figure]:
    """Generate an interactive line chart comparing projected UFCF trajectories across scenarios."""
    fig = go.Figure()

    def get_series(c: ScenarioCaseResult) -> Tuple[List[str], List[float]]:
        if not c.forecast_result or not c.forecast_result.annual_forecasts:
            return [], []
        labels = [yf.period_label for yf in c.forecast_result.annual_forecasts]
        vals = [yf.ufcf if yf.ufcf is not None else 0.0 for yf in c.forecast_result.annual_forecasts]
        return labels, vals

    base_labels, base_vals = get_series(result.base_case)
    bull_labels, bull_vals = get_series(result.bull_case)
    bear_labels, bear_vals = get_series(result.bear_case)

    if not base_labels and not bull_labels and not bear_labels:
        return None

    periods = base_labels or bull_labels or bear_labels

    if bear_vals:
        fig.add_trace(
            go.Scatter(
                x=periods,
                y=bear_vals,
                mode="lines+markers",
                name="Bear Case UFCF",
                line=dict(color="#d62728", width=2.5, dash="dash"),
                marker=dict(size=8, symbol="triangle-down"),
            )
        )

    if base_vals:
        fig.add_trace(
            go.Scatter(
                x=periods,
                y=base_vals,
                mode="lines+markers",
                name="Base Case UFCF",
                line=dict(color="#1f77b4", width=3),
                marker=dict(size=9, symbol="circle"),
            )
        )

    if bull_vals:
        fig.add_trace(
            go.Scatter(
                x=periods,
                y=bull_vals,
                mode="lines+markers",
                name="Bull Case UFCF",
                line=dict(color="#2ca02c", width=2.5, dash="dash"),
                marker=dict(size=8, symbol="triangle-up"),
            )
        )

    fig.update_layout(
        title="<b>Projected Unlevered Free Cash Flow (UFCF) Trajectory by Scenario</b>",
        title_font_size=14,
        yaxis_title=f"Projected UFCF ({currency})",
        margin=dict(l=20, r=20, t=40, b=20),
        height=320,
        legend=dict(orientation="h", yanchor="bottom", y=-0.25, xanchor="center", x=0.5),
    )

    return fig


def create_scenario_ev_composition_bar_chart(
    result: ScenarioAnalysisResult,
    currency: str = "USD",
) -> Optional[go.Figure]:
    """Generate a stacked bar chart illustrating PV of Forecast UFCF vs PV of Terminal Value."""
    scenarios = ["Bear Case", "Base Case", "Bull Case"]
    cases = [result.bear_case, result.base_case, result.bull_case]

    pv_fc_vals = [c.pv_forecast_ufcf if c.is_valid else 0.0 for c in cases]
    pv_tv_vals = [c.pv_terminal_value if c.is_valid else 0.0 for c in cases]

    if all(v == 0.0 for v in pv_fc_vals) and all(v == 0.0 for v in pv_tv_vals):
        return None

    fig = go.Figure()

    fig.add_trace(
        go.Bar(
            name="PV of Forecast UFCF",
            x=scenarios,
            y=pv_fc_vals,
            marker_color="#1f77b4",
            text=[f"{v:,.1f}" if v > 0 else "" for v in pv_fc_vals],
            textposition="inside",
        )
    )

    fig.add_trace(
        go.Bar(
            name="PV of Terminal Value",
            x=scenarios,
            y=pv_tv_vals,
            marker_color="#ff7f0e",
            text=[f"{v:,.1f}" if v > 0 else "" for v in pv_tv_vals],
            textposition="inside",
        )
    )

    fig.update_layout(
        barmode="stack",
        title="<b>Enterprise Value Composition (Explicit Cash Flows vs. Terminal Value)</b>",
        title_font_size=14,
        yaxis_title=f"Present Value ({currency})",
        margin=dict(l=20, r=20, t=40, b=20),
        height=340,
        legend=dict(orientation="h", yanchor="bottom", y=-0.25, xanchor="center", x=0.5),
    )

    return fig
