"""Formatting, tabular matrices, and Plotly visualizations for sensitivity analysis.

Builds readable 2D tabular sensitivity matrices, interactive heatmaps,
Monte Carlo distribution histograms, and statistical summary tables.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd
import plotly.graph_objects as go

from src.sensitivity.models import (
    MonteCarloSimulationResult,
    MonteCarloSummaryStats,
    SensitivityMatrixResult,
    SensitivityMetric,
)


def _get_cell_value(cell, metric: str) -> Optional[float]:
    if not cell.is_valid:
        return None
    if metric == SensitivityMetric.ENTERPRISE_VALUE.value:
        return cell.enterprise_value
    elif metric == SensitivityMetric.EQUITY_VALUE.value:
        return cell.equity_value
    else:
        return cell.implied_value_per_share


def build_sensitivity_matrix_dataframe(
    result: SensitivityMatrixResult,
    currency: str = "USD",
    unit: str = "millions",
) -> pd.DataFrame:
    """Construct a clean 2D pandas DataFrame representing the sensitivity matrix."""
    col_headers: List[str] = []
    is_share_price = result.metric == SensitivityMetric.IMPLIED_SHARE_PRICE.value

    for col_val in result.col_values:
        is_base = abs(col_val - result.baseline_col_val) < 1e-4
        base_marker = " (Base)" if is_base else ""
        if "g" in result.col_param_name.lower():
            col_headers.append(f"g = {col_val:.2f}%{base_marker}")
        else:
            col_headers.append(f"{col_val:.2f}x{base_marker}")

    rows: List[Dict[str, Any]] = []

    for r_idx, row_wacc in enumerate(result.row_values):
        is_base_row = abs(row_wacc - result.baseline_row_val) < 1e-4
        row_label = f"WACC = {row_wacc:.2f}%{' (Base)' if is_base_row else ''}"

        row_dict: Dict[str, Any] = {"WACC Discount Rate": row_label}

        for c_idx, col_header in enumerate(col_headers):
            cell = result.cells[r_idx][c_idx]
            val = _get_cell_value(cell, result.metric)

            if val is not None:
                star = " ★" if cell.is_baseline_intersection else ""
                if is_share_price:
                    row_dict[col_header] = f"{currency} {val:,.2f}{star}"
                else:
                    row_dict[col_header] = f"{val:,.2f}{star}"
            else:
                row_dict[col_header] = f"[Invalid: {cell.reason or 'WACC <= g'}]"

        rows.append(row_dict)

    return pd.DataFrame(rows)


def create_sensitivity_heatmap_chart(
    result: SensitivityMatrixResult,
    currency: str = "USD",
) -> Optional[go.Figure]:
    """Generate an interactive Plotly Heatmap visualizing the 2D sensitivity matrix."""
    if not result.cells or not result.row_values or not result.col_values:
        return None

    is_share_price = result.metric == SensitivityMetric.IMPLIED_SHARE_PRICE.value
    metric_title = SensitivityMetric.display_name(result.metric)

    # Prepare labels
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
            val = _get_cell_value(cell, result.metric)
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
        title=f"<b>2D Valuation Sensitivity Heatmap: {metric_title}</b>",
        title_font_size=14,
        xaxis_title=result.col_param_name,
        yaxis_title=result.row_param_name,
        margin=dict(l=40, r=40, t=50, b=40),
        height=420,
    )

    return fig


def build_monte_carlo_stats_dataframe(
    result: MonteCarloSimulationResult,
    currency: str = "USD",
    unit: str = "millions",
) -> pd.DataFrame:
    """Build a tabular summary of Monte Carlo simulation percentile statistics."""
    rows: List[Dict[str, Any]] = []

    def add_row(metric_name: str, stats: Optional[MonteCarloSummaryStats], is_share: bool = False):
        if not stats:
            rows.append({
                "Valuation Metric": metric_name,
                "Valid Draws": f"{result.valid_iterations} / {result.total_iterations}",
                "Mean": "—",
                "Median (P50)": "—",
                "Std Dev": "—",
                "Min": "—",
                "10th Pct (P10)": "—",
                "25th Pct (P25)": "—",
                "75th Pct (P75)": "—",
                "90th Pct (P90)": "—",
                "Max": "—",
            })
            return

        fmt = (lambda v: f"{currency} {v:,.2f}") if is_share else (lambda v: f"{v:,.2f}")
        rows.append({
            "Valuation Metric": metric_name,
            "Valid Draws": f"{stats.count} / {result.total_iterations}",
            "Mean": fmt(stats.mean),
            "Median (P50)": fmt(stats.median),
            "Std Dev": fmt(stats.std_dev),
            "Min": fmt(stats.min),
            "10th Pct (P10)": fmt(stats.p10),
            "25th Pct (P25)": fmt(stats.p25),
            "75th Pct (P75)": fmt(stats.p75),
            "90th Pct (P90)": fmt(stats.p90),
            "Max": fmt(stats.max),
        })

    add_row(f"Enterprise Value ({currency} {unit})", result.ev_stats, is_share=False)
    add_row(f"Equity Value ({currency} {unit})", result.equity_stats, is_share=False)
    add_row(f"Implied Intrinsic Value / Share ({currency})", result.share_price_stats, is_share=True)

    return pd.DataFrame(rows)


def create_monte_carlo_histogram(
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
            marker_color="#1f77b4",
            opacity=0.75,
            name="Simulated Distribution",
        )
    )

    # Reference vertical lines
    fig.add_vline(
        x=stats.median,
        line_width=2.5,
        line_color="#2ca02c",
        line_dash="solid",
        annotation_text=f"Median: {stats.median:,.2f}",
        annotation_position="top left",
    )

    fig.add_vline(
        x=stats.p10,
        line_width=1.5,
        line_color="#d62728",
        line_dash="dot",
        annotation_text=f"P10: {stats.p10:,.2f}",
        annotation_position="top left",
    )

    fig.add_vline(
        x=stats.p90,
        line_width=1.5,
        line_color="#ff7f0e",
        line_dash="dot",
        annotation_text=f"P90: {stats.p90:,.2f}",
        annotation_position="top right",
    )

    fig.update_layout(
        title=f"<b>Monte Carlo Simulation Distribution: {title_metric} ({stats.count} Valid Iterations)</b>",
        title_font_size=14,
        xaxis_title=title_metric,
        yaxis_title="Frequency / Draw Count",
        margin=dict(l=30, r=30, t=50, b=30),
        height=360,
        showlegend=False,
    )

    return fig
