"""Plotly chart visualizers and analytical diagrams for financial dashboards.

Provides reusable, presentation-grade interactive Plotly figures for historical
performance trends, forecast cash flows, DCF valuation waterfalls, scenario
comparisons, and sensitivity simulations.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from src.analysis.models import HistoricalAnalysisBundle
from src.dcf.models import DcfValuationResult, TerminalValueMethod
from src.forecasting.models import ForecastResult
from src.scenarios.models import ScenarioAnalysisResult, ScenarioCaseResult
from src.sensitivity.models import (
    MonteCarloSimulationResult,
    SensitivityMatrixResult,
    SensitivityMetric,
)


# Standardized color tokens for consistent dashboard styling
COLOR_NAVY = "#1E3A8A"
COLOR_BLUE = "#2563EB"
COLOR_LIGHT_BLUE = "#93C5FD"
COLOR_GREEN = "#10B981"
COLOR_EMERALD = "#059669"
COLOR_RED = "#DC2626"
COLOR_AMBER = "#F59E0B"
COLOR_PURPLE = "#7C3AED"
COLOR_SLATE = "#0F172A"
COLOR_GRAY = "#64748B"


# =============================================================================
# 1. Historical Financial Trend Visualizations
# =============================================================================

def create_historical_trend_chart(
    bundle: HistoricalAnalysisBundle,
    selected_metrics: Optional[List[str]] = None,
    period_filter: Optional[List[str]] = None,
    scale_divisor: float = 1_000_000.0,
    scale_label: str = "Millions",
    currency: str = "USD",
) -> Optional[go.Figure]:
    """Generate an interactive multi-line/bar chart for key historical financial line items."""
    if not bundle.periods:
        return None

    # Filter periods if specified
    periods = [p.label for p in bundle.periods if not period_filter or p.label in period_filter]
    if not periods:
        return None

    if selected_metrics is None:
        selected_metrics = ["Revenue", "Gross Profit", "EBITDA", "Net Income"]

    fig = go.Figure()

    metric_configs = [
        ("Revenue", "revenue", COLOR_NAVY, "circle", "solid"),
        ("Gross Profit", "gross_profit", COLOR_BLUE, "diamond", "solid"),
        ("EBITDA", "ebitda", COLOR_PURPLE, "square", "solid"),
        ("Net Income", "net_income", COLOR_GREEN, "triangle-up", "solid"),
    ]

    for label, code, color, symbol, dash in metric_configs:
        if label not in selected_metrics:
            continue

        y_vals: List[Optional[float]] = []
        for p in periods:
            m_dict = bundle.metrics_by_period.get(p, {})
            raw_dict = bundle.raw_line_items_by_period.get(p, {})

            val: Optional[float] = None
            if code in m_dict and m_dict[code].value is not None:
                val = m_dict[code].value
            elif code in raw_dict and raw_dict[code] is not None:
                val = raw_dict[code]

            y_vals.append((val / scale_divisor) if val is not None else None)

        fig.add_trace(
            go.Scatter(
                x=periods,
                y=y_vals,
                mode="lines+markers",
                name=label,
                line=dict(color=color, width=2.5, dash=dash),
                marker=dict(size=8, symbol=symbol),
                hovertemplate=f"<b>{label}</b> (%{{x}}): %{{y:,.2f}} {scale_label}<extra></extra>",
                connectgaps=False,  # Preserve gaps rather than silent interpolation
            )
        )

    fig.update_layout(
        title=f"<b>Historical Financial Performance Trends ({currency} {scale_label})</b>",
        title_font_size=14,
        yaxis_title=f"Amount ({currency} {scale_label})",
        xaxis_title="Fiscal Period",
        margin=dict(l=30, r=30, t=45, b=30),
        height=380,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        hovermode="x unified",
    )

    return fig


def create_margin_evolution_chart(
    bundle: HistoricalAnalysisBundle,
    period_filter: Optional[List[str]] = None,
) -> Optional[go.Figure]:
    """Generate an interactive line chart tracking historical profitability margins."""
    if not bundle.periods:
        return None

    periods = [p.label for p in bundle.periods if not period_filter or p.label in period_filter]
    if not periods:
        return None

    fig = go.Figure()

    margin_specs = [
        ("Gross Profit Margin", "gross_margin", COLOR_BLUE, "circle"),
        ("EBITDA Margin", "ebitda_margin", COLOR_PURPLE, "square"),
        ("EBIT Margin (Operating)", "ebit_margin", COLOR_AMBER, "diamond"),
        ("Net Profit Margin", "net_margin", COLOR_GREEN, "triangle-up"),
    ]

    for label, code, color, symbol in margin_specs:
        y_vals: List[Optional[float]] = []
        for p in periods:
            m_dict = bundle.metrics_by_period.get(p, {})
            val = m_dict[code].value if code in m_dict else None
            y_vals.append(val)

        fig.add_trace(
            go.Scatter(
                x=periods,
                y=y_vals,
                mode="lines+markers",
                name=label,
                line=dict(color=color, width=2.2),
                marker=dict(size=7, symbol=symbol),
                hovertemplate=f"<b>{label}</b> (%{{x}}): %{{y:.2f}}%<extra></extra>",
                connectgaps=False,
            )
        )

    fig.update_layout(
        title="<b>Historical Profitability Margins Evolution</b>",
        title_font_size=14,
        yaxis_title="Margin Percentage (%)",
        xaxis_title="Fiscal Period",
        margin=dict(l=30, r=30, t=45, b=30),
        height=360,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        hovermode="x unified",
    )

    return fig


def create_cash_flow_capex_chart(
    bundle: HistoricalAnalysisBundle,
    period_filter: Optional[List[str]] = None,
    scale_divisor: float = 1_000_000.0,
    scale_label: str = "Millions",
    currency: str = "USD",
) -> Optional[go.Figure]:
    """Generate an interactive chart comparing CFO, CapEx, and historical free cash flow."""
    if not bundle.periods:
        return None

    periods = [p.label for p in bundle.periods if not period_filter or p.label in period_filter]
    if not periods:
        return None

    cfo_vals: List[Optional[float]] = []
    capex_vals: List[Optional[float]] = []
    cfo_less_capex_vals: List[Optional[float]] = []
    ufcf_vals: List[Optional[float]] = []

    for p in periods:
        cf = bundle.cash_flow_metrics.get(p)
        if cf:
            cfo_vals.append((cf.operating_cash_flow / scale_divisor) if cf.operating_cash_flow is not None else None)
            capex_vals.append((cf.capex_magnitude / scale_divisor) if cf.capex_magnitude is not None else None)
            cfo_less_capex_vals.append((cf.cfo_less_capex / scale_divisor) if cf.cfo_less_capex is not None else None)
            ufcf_vals.append((cf.ufcf_estimate / scale_divisor) if cf.ufcf_estimate is not None else None)
        else:
            cfo_vals.append(None)
            capex_vals.append(None)
            cfo_less_capex_vals.append(None)
            ufcf_vals.append(None)

    fig = go.Figure()

    fig.add_trace(
        go.Bar(
            x=periods,
            y=cfo_vals,
            name="Operating Cash Flow (CFO)",
            marker_color=COLOR_BLUE,
            hovertemplate="<b>CFO</b> (%{x}): %{y:,.2f}<extra></extra>",
        )
    )

    fig.add_trace(
        go.Bar(
            x=periods,
            y=capex_vals,
            name="CapEx Magnitude",
            marker_color=COLOR_RED,
            hovertemplate="<b>CapEx</b> (%{x}): %{y:,.2f}<extra></extra>",
        )
    )

    fig.add_trace(
        go.Scatter(
            x=periods,
            y=cfo_less_capex_vals,
            name="CFO Less CapEx",
            mode="lines+markers",
            line=dict(color=COLOR_GREEN, width=3),
            marker=dict(size=8),
            hovertemplate="<b>CFO - CapEx</b> (%{x}): %{y:,.2f}<extra></extra>",
        )
    )

    if any(v is not None for v in ufcf_vals):
        fig.add_trace(
            go.Scatter(
                x=periods,
                y=ufcf_vals,
                name="Historical UFCF Est.",
                mode="lines+markers",
                line=dict(color=COLOR_SLATE, width=2.5, dash="dot"),
                marker=dict(size=7, symbol="diamond"),
                hovertemplate="<b>Hist. UFCF Est.</b> (%{x}): %{y:,.2f}<extra></extra>",
            )
        )

    fig.update_layout(
        title=f"<b>Cash Flow Dynamics & Capital Expenditures ({currency} {scale_label})</b>",
        title_font_size=14,
        barmode="group",
        yaxis_title=f"Amount ({currency} {scale_label})",
        xaxis_title="Fiscal Period",
        margin=dict(l=30, r=30, t=45, b=30),
        height=380,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        hovermode="x unified",
    )

    return fig


def create_working_capital_cycle_chart(
    bundle: HistoricalAnalysisBundle,
    period_filter: Optional[List[str]] = None,
) -> Optional[go.Figure]:
    """Generate an interactive chart for working capital efficiency (DSO, DIO, DPO, and CCC)."""
    if not bundle.periods:
        return None

    periods = [p.label for p in bundle.periods if not period_filter or p.label in period_filter]
    if not periods:
        return None

    dso_vals: List[Optional[float]] = []
    dio_vals: List[Optional[float]] = []
    dpo_vals: List[Optional[float]] = []
    ccc_vals: List[Optional[float]] = []

    for p in periods:
        wc = bundle.working_capital.get(p)
        if wc:
            dso_vals.append(wc.dso)
            dio_vals.append(wc.dio)
            dpo_vals.append(wc.dpo)
            ccc_vals.append(wc.cash_conversion_cycle)
        else:
            dso_vals.append(None)
            dio_vals.append(None)
            dpo_vals.append(None)
            ccc_vals.append(None)

    if not any(v is not None for v in ccc_vals):
        return None

    fig = go.Figure()

    fig.add_trace(go.Bar(x=periods, y=dso_vals, name="DSO (Receivables Days)", marker_color=COLOR_BLUE))
    fig.add_trace(go.Bar(x=periods, y=dio_vals, name="DIO (Inventory Days)", marker_color=COLOR_AMBER))
    fig.add_trace(go.Bar(x=periods, y=dpo_vals, name="DPO (Payables Days)", marker_color=COLOR_RED))
    fig.add_trace(
        go.Scatter(
            x=periods,
            y=ccc_vals,
            name="Cash Conversion Cycle (CCC)",
            mode="lines+markers",
            line=dict(color=COLOR_SLATE, width=3),
            marker=dict(size=8, symbol="circle"),
            hovertemplate="<b>CCC</b> (%{x}): %{y:.1f} days<extra></extra>",
        )
    )

    fig.update_layout(
        title="<b>Working Capital Efficiency & Cash Conversion Cycle (Days)</b>",
        title_font_size=14,
        barmode="group",
        yaxis_title="Days",
        xaxis_title="Fiscal Period",
        margin=dict(l=30, r=30, t=45, b=30),
        height=360,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        hovermode="x unified",
    )

    return fig


# =============================================================================
# 2. Forecast & Cash-Flow Visualizations
# =============================================================================

def create_revenue_actual_vs_projected_chart(
    bundle: HistoricalAnalysisBundle,
    forecast: ForecastResult,
    scale_divisor: float = 1_000_000.0,
    scale_label: str = "Millions",
    currency: str = "USD",
) -> Optional[go.Figure]:
    """Generate a combined actual vs projected revenue trajectory with distinct styling."""
    if not bundle.periods or not forecast.annual_forecasts:
        return None

    hist_labels = [p.label for p in bundle.periods]
    fore_labels = [f.period_label for f in forecast.annual_forecasts]

    hist_rev = [
        (bundle.metrics_by_period[p]["revenue"].value / scale_divisor)
        if "revenue" in bundle.metrics_by_period.get(p, {}) and bundle.metrics_by_period[p]["revenue"].value is not None
        else None
        for p in hist_labels
    ]
    fore_rev = [f.revenue / scale_divisor for f in forecast.annual_forecasts]

    fig = go.Figure()

    # Historical Bars
    fig.add_trace(
        go.Bar(
            x=hist_labels,
            y=hist_rev,
            name="Historical Revenue (Actual)",
            marker_color=COLOR_NAVY,
            text=[f"{v:,.1f}" if v is not None else "" for v in hist_rev],
            textposition="auto",
            hovertemplate="<b>Actual Revenue</b> (%{x}): %{y:,.2f}<extra></extra>",
        )
    )

    # Forecast Bars
    fig.add_trace(
        go.Bar(
            x=fore_labels,
            y=fore_rev,
            name="Projected Revenue (Forecast)",
            marker_color=COLOR_BLUE,
            marker_pattern_shape="/",  # Distinct pattern for accessibility
            text=[f"{v:,.1f}" for v in fore_rev],
            textposition="auto",
            hovertemplate="<b>Projected Revenue</b> (%{x}): %{y:,.2f}<extra></extra>",
        )
    )

    # Line overlay connecting baseline to projections
    last_hist_val = hist_rev[-1] if hist_rev else None
    line_x = [hist_labels[-1]] + fore_labels if hist_labels else fore_labels
    line_y = [last_hist_val] + fore_rev if hist_labels and last_hist_val is not None else fore_rev

    fig.add_trace(
        go.Scatter(
            x=line_x,
            y=line_y,
            mode="lines+markers",
            name="Revenue Trendline",
            line=dict(color=COLOR_AMBER, width=2.5, dash="dash"),
            marker=dict(size=6),
            hoverinfo="skip",
        )
    )

    fig.update_layout(
        title=f"<b>Historical vs. Projected Revenue Trajectory ({currency} {scale_label})</b>",
        title_font_size=14,
        yaxis_title=f"Revenue ({currency} {scale_label})",
        xaxis_title="Period Timeline",
        margin=dict(l=30, r=30, t=45, b=30),
        height=380,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )

    return fig


def create_forecast_driver_margins_chart(
    bundle: HistoricalAnalysisBundle,
    forecast: ForecastResult,
) -> Optional[go.Figure]:
    """Generate a combined historical and projected margin evolution chart."""
    if not forecast.annual_forecasts:
        return None

    hist_labels = [p.label for p in bundle.periods] if bundle.periods else []
    fore_labels = [f.period_label for f in forecast.annual_forecasts]
    all_labels = hist_labels + fore_labels

    hist_gm = [bundle.metrics_by_period[p]["gross_margin"].value if "gross_margin" in bundle.metrics_by_period.get(p, {}) else None for p in hist_labels]
    hist_ebitda = [bundle.metrics_by_period[p]["ebitda_margin"].value if "ebitda_margin" in bundle.metrics_by_period.get(p, {}) else None for p in hist_labels]
    hist_ebit = [bundle.metrics_by_period[p]["ebit_margin"].value if "ebit_margin" in bundle.metrics_by_period.get(p, {}) else None for p in hist_labels]

    fore_gm = [f.gross_margin for f in forecast.annual_forecasts]
    fore_ebitda = [f.ebitda_margin for f in forecast.annual_forecasts]
    fore_ebit = [f.ebit_margin for f in forecast.annual_forecasts]

    all_gm = hist_gm + fore_gm
    all_ebitda = hist_ebitda + fore_ebitda
    all_ebit = hist_ebit + fore_ebit

    fig = go.Figure()

    fig.add_trace(go.Scatter(x=all_labels, y=all_gm, name="Gross Margin %", mode="lines+markers", line=dict(color=COLOR_BLUE, width=2.5)))
    fig.add_trace(go.Scatter(x=all_labels, y=all_ebitda, name="EBITDA Margin %", mode="lines+markers", line=dict(color=COLOR_PURPLE, width=2.5)))
    fig.add_trace(go.Scatter(x=all_labels, y=all_ebit, name="EBIT Margin (Operating) %", mode="lines+markers", line=dict(color=COLOR_AMBER, width=2.5)))

    # Add vertical divider line at forecast boundary if history exists
    if hist_labels and fore_labels:
        boundary_idx = len(hist_labels) - 0.5
        fig.add_vline(
            x=boundary_idx,
            line_dash="dot",
            line_color=COLOR_GRAY,
            annotation_text="Forecast Horizon →",
            annotation_position="top right",
        )

    fig.update_layout(
        title="<b>Operating Profitability & Driver Margin Horizon (%)</b>",
        title_font_size=14,
        yaxis_title="Margin (%)",
        xaxis_title="Period Timeline",
        margin=dict(l=30, r=30, t=45, b=30),
        height=360,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        hovermode="x unified",
    )

    return fig


def create_ufcf_trajectory_breakdown_chart(
    forecast: ForecastResult,
    scale_divisor: float = 1_000_000.0,
    scale_label: str = "Millions",
    currency: str = "USD",
) -> Optional[go.Figure]:
    """Generate a year-by-year projected UFCF component breakdown and trajectory."""
    if not forecast.annual_forecasts:
        return None

    periods = [f.period_label for f in forecast.annual_forecasts]
    nopat_vals = [f.nopat / scale_divisor for f in forecast.annual_forecasts]
    da_vals = [f.depreciation_amortization / scale_divisor for f in forecast.annual_forecasts]
    capex_vals = [-f.capex / scale_divisor for f in forecast.annual_forecasts]
    delta_nwc_vals = [-f.delta_operating_nwc / scale_divisor for f in forecast.annual_forecasts]
    ufcf_vals = [f.ufcf / scale_divisor for f in forecast.annual_forecasts]

    fig = go.Figure()

    fig.add_trace(go.Bar(x=periods, y=nopat_vals, name="NOPAT", marker_color=COLOR_BLUE))
    fig.add_trace(go.Bar(x=periods, y=da_vals, name="+ Non-Cash D&A", marker_color=COLOR_GREEN))
    fig.add_trace(go.Bar(x=periods, y=capex_vals, name="- Capital Expenditures (CapEx)", marker_color=COLOR_RED))
    fig.add_trace(go.Bar(x=periods, y=delta_nwc_vals, name="- Change in Operating NWC (ΔNWC)", marker_color=COLOR_AMBER))

    fig.add_trace(
        go.Scatter(
            x=periods,
            y=ufcf_vals,
            name="= Projected UFCF",
            mode="lines+markers",
            line=dict(color=COLOR_SLATE, width=3.5),
            marker=dict(size=9, symbol="diamond"),
            hovertemplate="<b>Projected UFCF</b> (%{x}): %{y:,.2f}<extra></extra>",
        )
    )

    fig.update_layout(
        title=f"<b>Projected Unlevered Free Cash Flow (UFCF) Derivation ({currency} {scale_label})</b>",
        title_font_size=14,
        barmode="relative",
        yaxis_title=f"Cash Flow ({currency} {scale_label})",
        xaxis_title="Forecast Year",
        margin=dict(l=30, r=30, t=45, b=30),
        height=400,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )

    return fig


# =============================================================================
# 3. DCF Valuation & Bridge Visualizations
# =============================================================================

def create_valuation_waterfall_chart(
    result: DcfValuationResult,
    scale_divisor: float = 1_000_000.0,
    scale_label: str = "Millions",
    currency: str = "USD",
) -> Optional[go.Figure]:
    """Generate an institutional-grade valuation waterfall bridging PV of Cash Flows to Equity Value."""
    if result.pv_forecast_ufcf is None or result.pv_terminal_value is None or result.enterprise_value is None:
        return None

    b = result.bridge_result
    if not b:
        return None

    x_labels: List[str] = [
        "1. PV Forecast UFCF",
        "2. PV Terminal Value",
        "3. Enterprise Value (EV)",
        "4. (+) Cash & Equivalents",
        "5. (-) Interest Debt",
    ]
    measures: List[str] = ["relative", "relative", "total", "relative", "relative"]
    y_vals: List[float] = [
        result.pv_forecast_ufcf / scale_divisor,
        result.pv_terminal_value / scale_divisor,
        0.0,  # 'total' measure automatically computes cumulative sum in Plotly
        b.cash_added / scale_divisor,
        -b.debt_subtracted / scale_divisor,
    ]
    text_labels: List[str] = [
        f"+{result.pv_forecast_ufcf / scale_divisor:,.1f}",
        f"+{result.pv_terminal_value / scale_divisor:,.1f}",
        f"{result.enterprise_value / scale_divisor:,.1f}",
        f"+{b.cash_added / scale_divisor:,.1f}",
        f"-{b.debt_subtracted / scale_divisor:,.1f}",
    ]

    # Minority Interest
    if b.minority_interest_subtracted != 0.0:
        x_labels.append("6. (-) Minority Interest")
        measures.append("relative")
        y_vals.append(-b.minority_interest_subtracted / scale_divisor)
        text_labels.append(f"-{b.minority_interest_subtracted / scale_divisor:,.1f}")

    # Preferred Equity
    if b.preferred_equity_subtracted != 0.0:
        x_labels.append("7. (-) Preferred Stock")
        measures.append("relative")
        y_vals.append(-b.preferred_equity_subtracted / scale_divisor)
        text_labels.append(f"-{b.preferred_equity_subtracted / scale_divisor:,.1f}")

    # Other Adjustments
    if b.other_adjustments_net != 0.0:
        sign = "+" if b.other_adjustments_net > 0 else "-"
        x_labels.append("8. (+/-) Other Adjustments")
        measures.append("relative")
        y_vals.append(b.other_adjustments_net / scale_divisor)
        text_labels.append(f"{sign}{abs(b.other_adjustments_net / scale_divisor):,.1f}")

    # Final Total: Equity Value
    x_labels.append("Implied Equity Value")
    measures.append("total")
    y_vals.append(0.0)
    eq_val = result.equity_value or 0.0
    text_labels.append(f"{eq_val / scale_divisor:,.1f}")

    fig = go.Figure(
        go.Waterfall(
            name="Valuation Bridge",
            orientation="v",
            measure=measures,
            x=x_labels,
            textposition="outside",
            text=text_labels,
            y=y_vals,
            connector=dict(line=dict(color=COLOR_GRAY, width=1.5)),
            decreasing=dict(marker=dict(color=COLOR_RED)),
            increasing=dict(marker=dict(color=COLOR_GREEN)),
            totals=dict(marker=dict(color=COLOR_NAVY)),
        )
    )

    fig.update_layout(
        title=f"<b>DCF Enterprise-to-Equity Valuation Bridge ({currency} {scale_label})</b>",
        title_font_size=14,
        yaxis_title=f"Valuation Amount ({currency} {scale_label})",
        margin=dict(l=30, r=30, t=50, b=40),
        height=420,
        showlegend=False,
    )

    return fig


def create_terminal_value_share_donut_chart(result: DcfValuationResult) -> Optional[go.Figure]:
    """Generate a donut chart depicting the contribution of explicit cash flows vs terminal value."""
    if result.pv_forecast_ufcf is None or result.pv_terminal_value is None or result.enterprise_value is None:
        return None

    pv_fc = max(0.0, result.pv_forecast_ufcf)
    pv_tv = max(0.0, result.pv_terminal_value)

    labels = ["PV of Explicit Forecast UFCF", "PV of Terminal Value"]
    values = [pv_fc, pv_tv]
    colors = [COLOR_BLUE, COLOR_GREEN]

    tv_pct = result.terminal_value_pct_ev or 0.0

    fig = go.Figure(
        data=[
            go.Pie(
                labels=labels,
                values=values,
                hole=0.6,
                marker=dict(colors=colors, line=dict(color="#ffffff", width=2)),
                textinfo="label+percent",
                hoverinfo="label+percent+value",
            )
        ]
    )

    fig.update_layout(
        title=f"<b>Terminal Value Contribution to Enterprise Value ({tv_pct:.1f}%)</b>",
        title_font_size=14,
        margin=dict(l=20, r=20, t=40, b=20),
        height=320,
        showlegend=True,
        legend=dict(orientation="h", yanchor="bottom", y=-0.25, xanchor="center", x=0.5),
        annotations=[
            dict(
                text=f"<b>{tv_pct:.1f}%</b><br><span style='font-size:10px;'>TV Share</span>",
                x=0.5,
                y=0.5,
                font_size=16,
                showarrow=False,
            )
        ],
    )

    return fig


def create_cash_flow_discounting_comparison_chart(
    result: DcfValuationResult,
    scale_divisor: float = 1_000_000.0,
    scale_label: str = "Millions",
    currency: str = "USD",
) -> Optional[go.Figure]:
    """Generate a grouped bar chart comparing nominal UFCF vs present value of UFCF."""
    if not result.annual_discounting_schedule:
        return None

    periods = [item.period_label for item in result.annual_discounting_schedule]
    nominal_ufcf = [item.ufcf / scale_divisor for item in result.annual_discounting_schedule]
    pv_ufcf = [item.pv_ufcf / scale_divisor for item in result.annual_discounting_schedule]

    fig = go.Figure()

    fig.add_trace(
        go.Bar(
            name="Projected Nominal UFCF",
            x=periods,
            y=nominal_ufcf,
            marker_color=COLOR_LIGHT_BLUE,
            text=[f"{v:,.1f}" for v in nominal_ufcf],
            textposition="auto",
        )
    )

    fig.add_trace(
        go.Bar(
            name=f"Present Value (WACC: {result.wacc_applied:.2f}%)",
            x=periods,
            y=pv_ufcf,
            marker_color=COLOR_BLUE,
            text=[f"{v:,.1f}" for v in pv_ufcf],
            textposition="auto",
        )
    )

    fig.update_layout(
        barmode="group",
        title=f"<b>Cash Flow Discounting Trajectory ({currency} {scale_label})</b>",
        title_font_size=14,
        yaxis_title=f"Amount ({currency} {scale_label})",
        margin=dict(l=20, r=20, t=40, b=20),
        height=320,
        legend=dict(orientation="h", yanchor="bottom", y=-0.25, xanchor="center", x=0.5),
    )

    return fig


# =============================================================================
# 4. Scenario & Sensitivity Visualizations
# =============================================================================

def create_scenario_comparison_chart(
    result: ScenarioAnalysisResult,
    metric_type: str = "valuation",
    scale_divisor: float = 1_000_000.0,
    scale_label: str = "Millions",
    currency: str = "USD",
) -> Optional[go.Figure]:
    """Generate a grouped comparison chart for scenarios (Base / Bull / Bear)."""
    scenarios = ["Bear Case", "Base Case", "Bull Case"]
    cases = [result.bear_case, result.base_case, result.bull_case]

    if metric_type == "valuation":
        ev_vals = [(c.enterprise_value / scale_divisor) if c.is_valid and c.enterprise_value is not None else None for c in cases]
        eq_vals = [(c.equity_value / scale_divisor) if c.is_valid and c.equity_value is not None else None for c in cases]

        if all(v is None for v in ev_vals):
            return None

        fig = go.Figure()
        fig.add_trace(
            go.Bar(
                name="Enterprise Value (EV)",
                x=scenarios,
                y=[v if v is not None else 0.0 for v in ev_vals],
                marker_color=COLOR_NAVY,
                text=[f"{v:,.1f}" if v is not None else "Withheld" for v in ev_vals],
                textposition="auto",
            )
        )
        fig.add_trace(
            go.Bar(
                name="Equity Value",
                x=scenarios,
                y=[v if v is not None else 0.0 for v in eq_vals],
                marker_color=COLOR_GREEN,
                text=[f"{v:,.1f}" if v is not None else "Withheld" for v in eq_vals],
                textposition="auto",
            )
        )
        fig.update_layout(
            barmode="group",
            title=f"<b>Enterprise Value vs. Equity Value Across Scenarios ({currency} {scale_label})</b>",
            title_font_size=14,
            yaxis_title=f"Valuation ({currency} {scale_label})",
            margin=dict(l=20, r=20, t=40, b=20),
            height=340,
            legend=dict(orientation="h", yanchor="bottom", y=-0.25, xanchor="center", x=0.5),
        )
        return fig

    else:
        # Per share comparison
        share_vals = [c.implied_value_per_share if c.is_valid and c.implied_value_per_share is not None else None for c in cases]
        if all(v is None for v in share_vals):
            return None

        colors = [COLOR_RED, COLOR_BLUE, COLOR_GREEN]
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

        if result.base_case.is_valid and result.base_case.implied_value_per_share is not None:
            base_val = result.base_case.implied_value_per_share
            fig.add_hline(
                y=base_val,
                line_dash="dot",
                line_color=COLOR_NAVY,
                annotation_text=f"Base: {currency} {base_val:,.2f}",
                annotation_position="bottom right",
            )

        fig.update_layout(
            title=f"<b>Implied Value per Share Across Scenarios ({currency})</b>",
            title_font_size=14,
            yaxis_title=f"Implied Share Price ({currency})",
            margin=dict(l=20, r=20, t=40, b=20),
            height=340,
        )
        return fig


def create_sensitivity_contour_chart(
    result: SensitivityMatrixResult,
    currency: str = "USD",
) -> Optional[go.Figure]:
    """Generate an interactive Plotly Heatmap visualizing the 2D valuation sensitivity matrix."""
    if not result.cells or not result.row_values or not result.col_values:
        return None

    is_share_price = result.metric == SensitivityMetric.IMPLIED_SHARE_PRICE.value
    metric_title = SensitivityMetric.display_name(result.metric)

    x_labels: List[str] = []
    for c in result.col_values:
        is_b = abs(c - result.baseline_col_val) < 1e-4
        tag = "★ " if is_b else ""
        if "g" in result.col_param_name.lower():
            x_labels.append(f"{tag}g = {c:.2f}%")
        else:
            x_labels.append(f"{tag}{c:.2f}x")

    y_labels: List[str] = []
    for r in result.row_values:
        is_b = abs(r - result.baseline_row_val) < 1e-4
        tag = "★ " if is_b else ""
        y_labels.append(f"{tag}WACC = {r:.2f}%")

    z_matrix: List[List[Optional[float]]] = []
    text_matrix: List[List[str]] = []

    for r_idx in range(len(result.row_values)):
        z_row: List[Optional[float]] = []
        text_row: List[str] = []
        for c_idx in range(len(result.col_values)):
            cell = result.cells[r_idx][c_idx]
            val = (
                cell.implied_value_per_share if is_share_price
                else (cell.enterprise_value if result.metric == SensitivityMetric.ENTERPRISE_VALUE.value else cell.equity_value)
            ) if cell.is_valid else None

            z_row.append(val)
            if val is not None:
                star = " ★" if cell.is_baseline_intersection else ""
                if is_share_price:
                    text_row.append(f"{currency} {val:,.2f}{star}")
                else:
                    text_row.append(f"{val:,.1f}{star}")
            else:
                text_row.append("Invalid (WACC ≤ g)")
        z_matrix.append(z_row)
        text_matrix.append(text_row)

    fig = go.Figure(
        data=go.Heatmap(
            z=z_matrix,
            x=x_labels,
            y=y_labels,
            text=text_matrix,
            texttemplate="%{text}",
            textfont=dict(size=11),
            colorscale="Viridis",
            colorbar=dict(title=currency if is_share_price else "Valuation"),
            hoverongaps=False,
            hovertemplate=(
                "<b>" + result.row_param_name + ":</b> %{y}<br>"
                "<b>" + result.col_param_name + ":</b> %{x}<br>"
                "<b>" + metric_title + ":</b> %{text}<extra></extra>"
            ),
        )
    )

    fig.update_layout(
        title=f"<b>2D Valuation Sensitivity Matrix: {metric_title}</b>",
        title_font_size=14,
        xaxis_title=result.col_param_name,
        yaxis_title=result.row_param_name,
        margin=dict(l=40, r=40, t=50, b=40),
        height=400,
    )

    return fig


def create_monte_carlo_distribution_chart(
    result: MonteCarloSimulationResult,
    metric_type: str = "share_price",
    currency: str = "USD",
) -> Optional[go.Figure]:
    """Generate an interactive Plotly histogram showing simulated valuation distributions."""
    if metric_type == "share_price":
        values = result.sampled_share_prices
        stats = result.share_price_stats
        title_metric = f"Implied Value per Share ({currency})"
    elif metric_type == "enterprise_value":
        values = result.sampled_evs
        stats = result.ev_stats
        title_metric = f"Enterprise Value ({currency})"
    else:
        values = result.sampled_equities
        stats = result.equity_stats
        title_metric = f"Equity Value ({currency})"

    if not values or not stats:
        return None

    fig = go.Figure()

    fig.add_trace(
        go.Histogram(
            x=values,
            nbinsx=40,
            marker_color=COLOR_NAVY,
            opacity=0.75,
            name="Simulated Distribution",
        )
    )

    # Reference vertical lines for percentiles
    fig.add_vline(
        x=stats.median,
        line_width=2.5,
        line_color=COLOR_GREEN,
        line_dash="solid",
        annotation_text=f"Median: {stats.median:,.2f}",
        annotation_position="top left",
    )

    fig.add_vline(
        x=stats.p10,
        line_width=1.5,
        line_color=COLOR_RED,
        line_dash="dot",
        annotation_text=f"P10: {stats.p10:,.2f}",
        annotation_position="top left",
    )

    fig.add_vline(
        x=stats.p90,
        line_width=1.5,
        line_color=COLOR_AMBER,
        line_dash="dot",
        annotation_text=f"P90: {stats.p90:,.2f}",
        annotation_position="top right",
    )

    fig.update_layout(
        title=f"<b>Monte Carlo Distribution: {title_metric} ({stats.count} Valid Iterations)</b>",
        title_font_size=14,
        xaxis_title=title_metric,
        yaxis_title="Frequency / Draw Count",
        margin=dict(l=30, r=30, t=50, b=30),
        height=360,
        showlegend=False,
    )

    return fig
