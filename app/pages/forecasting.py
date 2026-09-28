"""Financial Forecasting and Multi-Year Projections interface.

Enables interactive configuration of revenue growth, profitability margins, working capital
drivers, and capital expenditures to project multi-year financial statements and Unlevered Free Cash Flows.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Ensure repository root is in sys.path
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st
import pandas as pd

from src.analysis.engine import HistoricalAnalysisEngine
from src.data.services import ProjectService
from src.forecasting.engine import FinancialForecastingEngine
from src.forecasting.formatting import (
    generate_forecast_statement_table,
    generate_ufcf_bridge_table,
)
from src.forecasting.models import ForecastAssumptions
from src.forecasting.services import ForecastService


def render_forecasting_page() -> None:
    """Render the Financial Forecasting & Projections Engine interface."""
    st.header("📈 Financial Forecasting & Projections Engine")
    st.markdown(
        "Build deterministic multi-year financial statement projections and Unlevered Free Cash Flow (UFCF) "
        "schedules. Forward-looking models are calibrated from verified historical actuals with user-editable drivers."
    )

    # 1. Project Context
    projects = ProjectService.list_projects()
    if not projects:
        st.warning("⚠️ No valuation projects found. Please create a company and valuation project first.")
        return

    proj_map = {p.id: f"{p.name} ({p.company.name if p.company else 'N/A'})" for p in projects}
    default_proj_id = st.session_state.get("selected_project_id", projects[0].id)
    if default_proj_id not in proj_map:
        default_proj_id = projects[0].id

    col_proj, col_curr = st.columns([3, 1])
    with col_proj:
        selected_project_id = st.selectbox(
            "Select Valuation Project *",
            options=list(proj_map.keys()),
            index=list(proj_map.keys()).index(default_proj_id),
            format_func=lambda pid: proj_map[pid],
            key="forecasting_project_select",
        )
        st.session_state["selected_project_id"] = selected_project_id

    current_proj = ProjectService.get_project(selected_project_id)
    comp = current_proj.company if current_proj else None
    base_currency = comp.currency if comp else "USD"

    with col_curr:
        st.write(f"**Reporting Currency:** `{base_currency}`")
        st.write(f"**Fiscal Year End:** `{comp.fiscal_year_end if comp else 'Dec 31'}`")

    # 2. Retrieve Historical Analysis Baseline
    try:
        hist_bundle = HistoricalAnalysisEngine.analyze_project(
            project_id=selected_project_id,
            period_type="annual",
            data_classification="reported_actual",
            selected_currency=base_currency,
        )
    except Exception as exc:
        st.error(f"Failed to retrieve historical actuals: {exc}")
        return

    if not hist_bundle.periods:
        st.info(
            "ℹ️ No annual historical actuals found for this project. "
            "Please go to **Company & Financial Data** to enter or import historical statements before building a forecast."
        )
        return

    baselines = FinancialForecastingEngine.extract_historical_baselines(hist_bundle)
    base_label = baselines.get("base_period_label", "FY2023")

    st.markdown("---")

    # 3. Forecast Scenario / Model Selection & Horizon Control
    st.subheader("⚙️ Forecast Model & Horizon Configuration")

    saved_models = ForecastService.list_forecast_models(selected_project_id)
    model_options = {"new": "➕ Create New Forecast Scenario"}
    model_options.update({m.id: f"📂 {m.name} ({m.horizon_years}Y from {m.base_period_label})" for m in saved_models})

    sc_col1, sc_col2 = st.columns([2, 1])
    with sc_col1:
        selected_model_key = st.selectbox(
            "Forecast Model Version",
            options=list(model_options.keys()),
            format_func=lambda k: model_options[k],
            key="saved_forecast_model_select",
        )

    # Load assumptions from saved model or create defaults from historical baselines
    if selected_model_key != "new":
        loaded_model = ForecastService.get_forecast_model(selected_model_key)
        if loaded_model:
            assumptions = ForecastAssumptions.from_json(loaded_model.assumptions_json)
        else:
            assumptions = FinancialForecastingEngine.create_default_assumptions(hist_bundle)
    else:
        assumptions = FinancialForecastingEngine.create_default_assumptions(hist_bundle)

    with sc_col2:
        horizon_years = st.slider(
            "Forecast Horizon (Years)",
            min_value=3,
            max_value=10,
            value=assumptions.horizon_years,
            step=1,
            key="forecast_horizon_slider",
        )
        assumptions.horizon_years = horizon_years

    # Ensure schedules have length equal to horizon_years
    def adjust_schedule(arr: list[float], default_val: float) -> list[float]:
        curr = list(arr)
        if len(curr) < horizon_years:
            fill_val = curr[-1] if curr else default_val
            curr.extend([fill_val] * (horizon_years - len(curr)))
        return curr[:horizon_years]

    assumptions.revenue_growth_rates = adjust_schedule(assumptions.revenue_growth_rates, 5.0)
    assumptions.gross_margin_rates = adjust_schedule(assumptions.gross_margin_rates, 40.0)
    assumptions.opex_pct_rates = adjust_schedule(assumptions.opex_pct_rates, 20.0)
    assumptions.da_pct_rates = adjust_schedule(assumptions.da_pct_rates, 4.0)
    assumptions.capex_pct_rates = adjust_schedule(assumptions.capex_pct_rates, 5.0)
    assumptions.dso_days = adjust_schedule(assumptions.dso_days, 45.0)
    assumptions.dio_days = adjust_schedule(assumptions.dio_days, 60.0)
    assumptions.dpo_days = adjust_schedule(assumptions.dpo_days, 40.0)
    assumptions.nwc_pct_revenue = adjust_schedule(assumptions.nwc_pct_revenue, 10.0)

    # 4. Assumption Editor Tabs
    st.markdown("### 🎛️ Forecast Driver Assumptions")
    st.caption(
        f"Calibrated from baseline **{base_label}**. Adjust constant drivers or expand to set individual annual rates:"
    )

    t_rev, t_profit, t_wc, t_capex_tax = st.tabs([
        "📈 Revenue Growth",
        "💰 Profitability & OpEx",
        "⏱️ Working Capital",
        "🏗️ CapEx & Tax Rate",
    ])

    with t_rev:
        st.markdown("#### Revenue Growth Drivers")
        hist_cagr_str = f"{hist_bundle.cagr_results['revenue_cagr'].value:+.1f}%" if "revenue_cagr" in hist_bundle.cagr_results and hist_bundle.cagr_results["revenue_cagr"].value is not None else "N/A"
        st.info(f"**Historical Context:** Baseline Revenue = `{base_currency} {baselines['base_revenue']:,.1f}` | Historical Multi-Year CAGR = `{hist_cagr_str}`")

        rev_mode = st.radio("Growth Input Mode", options=["Constant Annual Growth", "Year-by-Year Schedule"], horizontal=True)
        if rev_mode == "Constant Annual Growth":
            const_growth = st.number_input(
                "Annual Revenue Growth Rate (%)",
                value=float(assumptions.revenue_growth_rates[0]),
                step=0.5,
                format="%.2f",
            )
            assumptions.revenue_growth_rates = [const_growth] * horizon_years
        else:
            g_cols = st.columns(horizon_years)
            for y_i in range(horizon_years):
                with g_cols[y_i]:
                    val = st.number_input(
                        f"Year +{y_i+1} (%)",
                        value=float(assumptions.revenue_growth_rates[y_i]),
                        step=0.5,
                        format="%.1f",
                        key=f"g_rate_y_{y_i}",
                    )
                    assumptions.revenue_growth_rates[y_i] = val

    with t_profit:
        st.markdown("#### Profitability Margins & Operating Expenses")
        p_c1, p_c2 = st.columns(2)
        with p_c1:
            st.markdown(f"**Gross Profit Margin (% Revenue)** *(Historical: `{baselines.get('base_gross_margin', 40.0):.1f}%`)*")
            const_gm = st.number_input(
                "Gross Margin (%)",
                value=float(assumptions.gross_margin_rates[0]),
                step=0.5,
                format="%.2f",
            )
            assumptions.gross_margin_rates = [const_gm] * horizon_years

            st.markdown(f"**Operating Expenses (% Revenue)** *(Historical: `{baselines.get('suggested_opex_pct', 20.0):.1f}%`)*")
            const_opex = st.number_input(
                "OpEx (% Revenue)",
                value=float(assumptions.opex_pct_rates[0]),
                step=0.5,
                format="%.2f",
            )
            assumptions.opex_pct_rates = [const_opex] * horizon_years

        with p_c2:
            st.markdown(f"**Depreciation & Amortization (% Revenue)** *(Historical: `{baselines.get('suggested_da_pct', 4.0):.1f}%`)*")
            const_da = st.number_input(
                "D&A (% Revenue)",
                value=float(assumptions.da_pct_rates[0]),
                step=0.25,
                format="%.2f",
            )
            assumptions.da_pct_rates = [const_da] * horizon_years

            implied_ebitda_m = const_gm - const_opex
            implied_ebit_m = implied_ebitda_m - const_da
            st.success(
                f"**Implied Margins:** EBITDA Margin = `{implied_ebitda_m:.1f}%` | EBIT Margin = `{implied_ebit_m:.1f}%`"
            )

    with t_wc:
        st.markdown("#### Working Capital Drivers")
        st.caption("Forecast Accounts Receivable, Inventory, and Accounts Payable to project Operating NWC.")

        wc_method = st.radio(
            "Working Capital Projection Methodology",
            options=["Turnover Days (DSO / DIO / DPO)", "Operating NWC as % of Revenue"],
            index=0 if assumptions.use_working_capital_days else 1,
            horizontal=True,
        )
        assumptions.use_working_capital_days = (wc_method == "Turnover Days (DSO / DIO / DPO)")

        if assumptions.use_working_capital_days:
            wc1, wc2, wc3 = st.columns(3)
            with wc1:
                dso = st.number_input(
                    "Days Sales Outstanding (DSO)",
                    value=float(assumptions.dso_days[0]),
                    step=1.0,
                    format="%.1f",
                    help="Accounts Receivable = (Revenue * DSO) / 365",
                )
                assumptions.dso_days = [dso] * horizon_years
            with wc2:
                dio = st.number_input(
                    "Days Inventory Outstanding (DIO)",
                    value=float(assumptions.dio_days[0]),
                    step=1.0,
                    format="%.1f",
                    help="Inventory = (COGS * DIO) / 365",
                )
                assumptions.dio_days = [dio] * horizon_years
            with wc3:
                dpo = st.number_input(
                    "Days Payables Outstanding (DPO)",
                    value=float(assumptions.dpo_days[0]),
                    step=1.0,
                    format="%.1f",
                    help="Accounts Payable = (COGS * DPO) / 365",
                )
                assumptions.dpo_days = [dpo] * horizon_years
            implied_ccc = dso + dio - dpo
            st.info(f"**Implied Cash Conversion Cycle (CCC):** `{implied_ccc:.1f} days` (DSO + DIO - DPO)")
        else:
            nwc_pct = st.number_input(
                "Operating NWC (% of Revenue)",
                value=float(assumptions.nwc_pct_revenue[0]),
                step=0.5,
                format="%.2f",
            )
            assumptions.nwc_pct_revenue = [nwc_pct] * horizon_years

    with t_capex_tax:
        st.markdown("#### Capital Expenditures & Tax Assumptions")
        ct1, ct2 = st.columns(2)
        with ct1:
            st.markdown(f"**CapEx Intensity (% Revenue)** *(Historical: `{baselines.get('suggested_capex_pct', 5.0):.1f}%`)*")
            const_capex = st.number_input(
                "CapEx (% Revenue)",
                value=float(assumptions.capex_pct_rates[0]),
                step=0.5,
                format="%.2f",
            )
            assumptions.capex_pct_rates = [const_capex] * horizon_years

        with ct2:
            st.markdown(f"**Corporate Tax Rate for NOPAT (%)** *(Historical Effective: `{baselines.get('suggested_tax_rate', 25.0):.1f}%`)*")
            tax_rate = st.number_input(
                "Tax Rate (%)",
                value=float(assumptions.tax_rate),
                min_value=0.0,
                max_value=60.0,
                step=0.5,
                format="%.1f",
            )
            assumptions.tax_rate = tax_rate

    # Save Forecast Scenario
    st.markdown("---")
    with st.expander("💾 Save / Update Forecast Scenario Version"):
        with st.form("save_forecast_scenario_form"):
            s_col1, s_col2 = st.columns(2)
            with s_col1:
                scenario_name = st.text_input("Scenario Name *", value=assumptions.name)
            with s_col2:
                scenario_desc = st.text_input("Scenario Description", value=assumptions.description or "")
            submit_save = st.form_submit_button("Save Scenario to Project", type="primary")
            if submit_save:
                try:
                    assumptions.name = scenario_name.strip()
                    assumptions.description = scenario_desc.strip() or None
                    saved = ForecastService.save_forecast_model(
                        project_id=selected_project_id,
                        name=assumptions.name,
                        assumptions=assumptions,
                        base_period_label=base_label,
                        description=assumptions.description,
                    )
                    st.success(f"Forecast scenario '{saved.name}' saved successfully!")
                    st.rerun()
                except Exception as exc:
                    st.error(f"Failed to save forecast scenario: {exc}")

    # 5. Run Projections Engine
    try:
        forecast_result = FinancialForecastingEngine.project_financials(
            bundle=hist_bundle,
            assumptions=assumptions,
        )
    except Exception as exc:
        st.error(f"Projection calculation error: {exc}")
        return

    # Scale Options for display
    st.markdown("---")
    scale_c1, scale_c2 = st.columns([3, 1])
    with scale_c2:
        scale_option = st.selectbox(
            "Display Scale",
            options=["Millions (M)", "Thousands (K)", "Exact Units"],
            index=0,
            key="forecast_scale_select",
        )
    scale_divisor = 1_000_000.0 if "Millions" in scale_option else (1_000.0 if "Thousands" in scale_option else 1.0)
    scale_label = "Millions" if "Millions" in scale_option else ("Thousands" if "Thousands" in scale_option else "Units")

    # 6. Executive Forecast Summary Cards
    st.subheader("🎯 Forecast Summary")
    sum_c1, sum_c2, sum_c3, sum_c4, sum_c5 = st.columns(5)

    with sum_c1:
        last_f = forecast_result.annual_forecasts[-1]
        st.metric(
            f"Ending Revenue ({last_f.period_label.split()[0]})",
            f"{base_currency} {last_f.revenue / scale_divisor:,.1f} {scale_label[0]}",
            delta=f"{forecast_result.forecast_revenue_cagr:+.1f}% CAGR",
        )
    with sum_c2:
        st.metric("Avg EBITDA Margin", f"{forecast_result.avg_ebitda_margin:.1f}%")
    with sum_c3:
        st.metric("Avg EBIT Margin", f"{forecast_result.avg_ebit_margin:.1f}%")
    with sum_c4:
        st.metric(
            f"Ending UFCF ({last_f.period_label.split()[0]})",
            f"{base_currency} {last_f.ufcf / scale_divisor:,.1f} {scale_label[0]}",
        )
    with sum_c5:
        st.metric(
            f"Cumulative {horizon_years}Y UFCF",
            f"{base_currency} {forecast_result.total_projected_ufcf / scale_divisor:,.1f} {scale_label[0]}",
        )

    # 7. Tabbed Forecast Content: Statements, UFCF Bridge, Charts
    tab_stmt, tab_bridge, tab_charts, tab_notes = st.tabs([
        "📑 Multi-Period Financial Statement Table",
        "🌉 Unlevered Free Cash Flow (UFCF) Bridge",
        "📈 Projection Charts",
        "📋 Assumptions & Audit Notes",
    ])

    with tab_stmt:
        st.caption(
            f"Consolidated multi-period income statement, working capital, and cash flows. "
            f"Figures presented in **{base_currency} {scale_label}**."
        )
        df_stmt = generate_forecast_statement_table(hist_bundle, forecast_result, scale_divisor=scale_divisor)
        st.dataframe(df_stmt, use_container_width=True, hide_index=True)

    with tab_bridge:
        st.subheader("Unlevered Free Cash Flow (UFCF) Projection Bridge")
        st.caption(
            "Formula: UFCF = EBIT × (1 - Tax Rate) + D&A - CapEx - ΔOperating NWC. "
            f"Monetary figures in **{base_currency} {scale_label}**."
        )
        df_bridge = generate_ufcf_bridge_table(forecast_result, scale_divisor=scale_divisor)
        st.dataframe(df_bridge, use_container_width=True, hide_index=True)

    with tab_charts:
        st.subheader("1. Projected Revenue Growth Trajectory")
        hist_labels = [p.label for p in hist_bundle.periods]
        forecast_labels = [f.period_label for f in forecast_result.annual_forecasts]
        all_chart_labels = hist_labels + forecast_labels

        hist_rev = [(hist_bundle.metrics_by_period[p]["revenue"].value / scale_divisor) if hist_bundle.metrics_by_period[p]["revenue"].value is not None else None for p in hist_labels]
        fore_rev = [f.revenue / scale_divisor for f in forecast_result.annual_forecasts]
        all_rev = hist_rev + fore_rev

        fig_rev = go.Figure()
        fig_rev.add_trace(go.Bar(x=hist_labels, y=hist_rev, name="Historical Revenue", marker_color="#1E3A8A"))
        fig_rev.add_trace(go.Bar(x=forecast_labels, y=fore_rev, name="Projected Revenue", marker_color="#2563EB"))
        fig_rev.update_layout(
            height=380,
            margin=dict(l=40, r=40, t=30, b=40),
            yaxis_title=f"Revenue ({base_currency} {scale_label})",
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        )
        st.plotly_chart(fig_rev, use_container_width=True)

        st.markdown("---")

        st.subheader("2. Profitability Margins Horizon")
        fig_m = go.Figure()
        all_gm = [hist_bundle.metrics_by_period[p]["gross_margin"].value for p in hist_labels] + [f.gross_margin for f in forecast_result.annual_forecasts]
        all_ebitda_m = [hist_bundle.metrics_by_period[p]["ebitda_margin"].value for p in hist_labels] + [f.ebitda_margin for f in forecast_result.annual_forecasts]
        all_ebit_m = [hist_bundle.metrics_by_period[p]["ebit_margin"].value for p in hist_labels] + [f.ebit_margin for f in forecast_result.annual_forecasts]

        fig_m.add_trace(go.Scatter(x=all_chart_labels, y=all_gm, name="Gross Margin %", mode="lines+markers", line=dict(color="#2563EB", width=2)))
        fig_m.add_trace(go.Scatter(x=all_chart_labels, y=all_ebitda_m, name="EBITDA Margin %", mode="lines+markers", line=dict(color="#7C3AED", width=2)))
        fig_m.add_trace(go.Scatter(x=all_chart_labels, y=all_ebit_m, name="EBIT Margin %", mode="lines+markers", line=dict(color="#F59E0B", width=2)))
        fig_m.update_layout(
            height=380,
            margin=dict(l=40, r=40, t=30, b=40),
            yaxis_title="Margin (%)",
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        )
        st.plotly_chart(fig_m, use_container_width=True)

        st.markdown("---")

        st.subheader("3. Projected Unlevered Free Cash Flow (UFCF) and Components")
        nopat_vals = [f.nopat / scale_divisor for f in forecast_result.annual_forecasts]
        da_vals = [f.depreciation_amortization / scale_divisor for f in forecast_result.annual_forecasts]
        capex_vals = [f.capex / scale_divisor for f in forecast_result.annual_forecasts]
        delta_nwc_vals = [f.delta_operating_nwc / scale_divisor for f in forecast_result.annual_forecasts]
        ufcf_vals = [f.ufcf / scale_divisor for f in forecast_result.annual_forecasts]

        fig_ufcf = go.Figure()
        fig_ufcf.add_trace(go.Bar(x=forecast_labels, y=nopat_vals, name="NOPAT", marker_color="#3B82F6"))
        fig_ufcf.add_trace(go.Bar(x=forecast_labels, y=da_vals, name="+ D&A", marker_color="#10B981"))
        fig_ufcf.add_trace(go.Bar(x=forecast_labels, y=[-c for c in capex_vals], name="- CapEx", marker_color="#EF4444"))
        fig_ufcf.add_trace(go.Bar(x=forecast_labels, y=[-n for n in delta_nwc_vals], name="- ΔNWC", marker_color="#F59E0B"))
        fig_ufcf.add_trace(go.Scatter(x=forecast_labels, y=ufcf_vals, name="= Projected UFCF", mode="lines+markers", line=dict(color="#0F172A", width=3)))

        fig_ufcf.update_layout(
            height=400,
            barmode="relative",
            margin=dict(l=40, r=40, t=30, b=40),
            yaxis_title=f"Cash Flow ({base_currency} {scale_label})",
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        )
        st.plotly_chart(fig_ufcf, use_container_width=True)

    with tab_notes:
        st.subheader("📋 Assumptions Summary & Audit Trail")
        st.write(f"**Valuation Project:** {current_proj.name} (ID: {current_proj.id})")
        st.write(f"**Target Entity:** {comp.name if comp else 'N/A'}")
        st.write(f"**Baseline Anchor Period:** `{base_label}` ({baselines.get('base_period_year', 2023)})")
        st.write(f"**Base Revenue:** `{base_currency} {baselines.get('base_revenue', 0.0):,.2f}`")
        st.write(f"**Base Operating NWC:** `{base_currency} {baselines.get('base_operating_nwc', 0.0):,.2f}`")
        st.write(f"**Forecast Horizon:** `{horizon_years} years` ({', '.join(f.period_label for f in forecast_result.annual_forecasts)})")

        st.markdown("#### Driver Baseline Provenance")
        prov_rows = []
        for driver_key, source_val in assumptions.driver_sources.items():
            prov_rows.append({
                "Driver": driver_key.replace("_", " ").title(),
                "Source Origin": source_val.replace("_", " ").title(),
            })
        st.dataframe(pd.DataFrame(prov_rows), use_container_width=True, hide_index=True)

        st.markdown("#### Important Disclosure")
        st.caption(
            "Forecasts represent forward-looking mathematical models based strictly on user assumptions and "
            "historical actuals. They are not investment recommendations or guarantees of future performance. "
            "Discounting, WACC estimation, and DCF equity valuation are performed in subsequent phases."
        )


if __name__ == "__main__":
    from app.navigation import run_standalone_page
    run_standalone_page("Forecasting", render_forecasting_page)
