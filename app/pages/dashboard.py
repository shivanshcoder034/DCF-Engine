"""Financial Dashboards & Interactive Visualizations page.

Provides unified, interactive visual exploration of company historical performance,
forecast trajectories, DCF valuation bridge waterfalls, and scenario/sensitivity results.
"""

from __future__ import annotations

import streamlit as st
import pandas as pd
from typing import Optional

from src.analysis.engine import HistoricalAnalysisEngine
from src.analysis.models import HistoricalAnalysisBundle
from src.dashboard.charts import (
    create_cash_flow_capex_chart,
    create_cash_flow_discounting_comparison_chart,
    create_forecast_driver_margins_chart,
    create_historical_trend_chart,
    create_margin_evolution_chart,
    create_monte_carlo_distribution_chart,
    create_revenue_actual_vs_projected_chart,
    create_scenario_comparison_chart,
    create_sensitivity_contour_chart,
    create_terminal_value_share_donut_chart,
    create_ufcf_trajectory_breakdown_chart,
    create_valuation_waterfall_chart,
    create_working_capital_cycle_chart,
)
from src.data.schemas import DataClassification, PeriodType
from src.data.services import ProjectService
from src.dcf.engine import DcfEngine
from src.dcf.models import DcfAssumptions, DcfValuationResult, TerminalValueMethod
from src.dcf.services import DcfService
from src.forecasting.engine import FinancialForecastingEngine
from src.forecasting.models import ForecastAssumptions, ForecastResult
from src.forecasting.services import ForecastService
from src.scenarios.engine import ScenarioEngine
from src.scenarios.formatting import build_assumption_audit_dataframe
from src.scenarios.models import ScenarioAnalysisAssumptions, ScenarioAnalysisResult
from src.scenarios.services import ScenarioService
from src.sensitivity.engine import SensitivityEngine
from src.sensitivity.formatting import build_monte_carlo_stats_dataframe
from src.sensitivity.models import SensitivityConfig, SensitivityMatrixResult, MonteCarloSimulationResult
from src.sensitivity.services import SensitivityService
from src.wacc.engine import WaccEngine
from src.wacc.models import WaccAssumptions, WaccResult
from src.wacc.services import WaccService


def render_dashboard_page() -> None:
    """Render the central financial dashboard interface."""
    st.header("📊 Financial Dashboards & Interactive Visualizations")
    st.markdown(
        "Interactive analytics and valuation exploration layer connecting historical actuals, "
        "forecast cash flows, DCF valuation waterfalls, and scenario/sensitivity results."
    )

    # 1. Project Selection
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
            key="dashboard_project_select",
        )
        st.session_state["selected_project_id"] = selected_project_id

    current_proj = ProjectService.get_project(selected_project_id)
    comp = current_proj.company if current_proj else None
    base_currency = comp.currency if comp else "USD"

    with col_curr:
        st.write(f"**Reporting Currency:** `{base_currency}`")
        st.write(f"**Fiscal Year End:** `{comp.fiscal_year_end if comp else 'Dec 31'}`")

    st.markdown("---")

    # 2. Scope & Model Selection Area
    st.subheader("⚙️ Model Selection & Analysis Scope")
    st.caption("Select saved records to connect into the dashboard views:")

    m_col1, m_col2, m_col3 = st.columns(3)

    # Historical scope
    with m_col1:
        freq_option = st.selectbox(
            "Historical Frequency",
            options=[PeriodType.ANNUAL.value, PeriodType.QUARTERLY.value],
            format_func=lambda x: PeriodType.display_name(x),
            key="dash_hist_freq_select",
        )
        class_option = st.selectbox(
            "Data Classification",
            options=[c.value for c in DataClassification],
            format_func=lambda x: DataClassification.display_name(x),
            key="dash_hist_class_select",
        )

    # Forecast & WACC models
    saved_forecasts = ForecastService.list_forecast_models(selected_project_id)
    forecast_options = {None: "None / Not Selected"}
    forecast_options.update({m.id: f"📂 {m.name} ({m.horizon_years}Y)" for m in saved_forecasts})

    saved_waccs = WaccService.list_wacc_models(selected_project_id)
    wacc_options = {None: "None / Not Selected"}
    wacc_options.update({m.id: f"📂 {m.name}" for m in saved_waccs})

    with m_col2:
        selected_fc_id = st.selectbox(
            "Forecast Model",
            options=list(forecast_options.keys()),
            format_func=lambda k: forecast_options[k],
            key="dash_fc_select",
        )
        selected_wacc_id = st.selectbox(
            "WACC Model",
            options=list(wacc_options.keys()),
            format_func=lambda k: wacc_options[k],
            key="dash_wacc_select",
        )

    # DCF, Scenarios, Sensitivity models
    saved_dcfs = DcfService.list_dcf_models(selected_project_id)
    dcf_options = {None: "None / Not Selected"}
    dcf_options.update({m.id: f"📂 {m.name}" for m in saved_dcfs})

    saved_scenarios = ScenarioService.list_scenario_models(selected_project_id)
    scen_options = {None: "None / Not Selected"}
    scen_options.update({m.id: f"📂 {m.name}" for m in saved_scenarios})

    saved_sens = SensitivityService.list_sensitivity_models(selected_project_id)
    sens_options = {None: "None / Not Selected"}
    sens_options.update({m.id: f"📂 {m.name}" for m in saved_sens})

    with m_col3:
        selected_dcf_id = st.selectbox(
            "DCF Valuation Case",
            options=list(dcf_options.keys()),
            format_func=lambda k: dcf_options[k],
            key="dash_dcf_select",
        )
        selected_scen_id = st.selectbox(
            "Scenario Set (Base/Bull/Bear)",
            options=list(scen_options.keys()),
            format_func=lambda k: scen_options[k],
            key="dash_scen_select",
        )
        selected_sens_id = st.selectbox(
            "Sensitivity Config",
            options=list(sens_options.keys()),
            format_func=lambda k: sens_options[k],
            key="dash_sens_select",
        )

    # Scale divisor control
    scale_c1, scale_c2 = st.columns([2, 2])
    with scale_c1:
        scale_option = st.selectbox(
            "Chart Display Scale",
            options=["Millions (M)", "Thousands (K)", "Exact Units"],
            index=0,
            key="dash_scale_select",
        )
        scale_divisor = 1_000_000.0 if "Millions" in scale_option else (1_000.0 if "Thousands" in scale_option else 1.0)
        scale_label = "Millions" if "Millions" in scale_option else ("Thousands" if "Thousands" in scale_option else "Units")

    # 3. Resolve and Evaluate Models
    diagnostics = []

    # Historical bundle
    hist_bundle: Optional[HistoricalAnalysisBundle] = None
    try:
        hist_bundle = HistoricalAnalysisEngine.analyze_project(
            project_id=selected_project_id,
            period_type=freq_option,
            data_classification=class_option,
            selected_currency=base_currency,
        )
    except Exception as exc:
        diagnostics.append(f"Historical analysis error: {exc}")

    # Forecast
    forecast_result: Optional[ForecastResult] = None
    forecast_assumptions: Optional[ForecastAssumptions] = None
    if selected_fc_id is not None:
        fc_model = ForecastService.get_forecast_model(selected_fc_id)
        if fc_model:
            try:
                forecast_assumptions = ForecastAssumptions.from_json(fc_model.assumptions_json)
                if hist_bundle and hist_bundle.periods:
                    forecast_result = FinancialForecastingEngine.generate_forecast(hist_bundle, forecast_assumptions)
                else:
                    diagnostics.append("Forecast cannot be calculated: historical statements are missing for the selected scope.")
            except Exception as exc:
                diagnostics.append(f"Forecast evaluation error: {exc}")
        else:
            diagnostics.append(f"Forecast model ID {selected_fc_id} was not found.")

    # WACC
    wacc_result: Optional[WaccResult] = None
    wacc_assumptions: Optional[WaccAssumptions] = None
    if selected_wacc_id is not None:
        w_model = WaccService.get_wacc_model(selected_wacc_id)
        if w_model:
            try:
                wacc_assumptions = WaccAssumptions.from_json(w_model.assumptions_json)
                wacc_result = WaccEngine.estimate_wacc(wacc_assumptions)
            except Exception as exc:
                diagnostics.append(f"WACC estimation error: {exc}")
        else:
            diagnostics.append(f"WACC model ID {selected_wacc_id} was not found.")

    # DCF
    dcf_result: Optional[DcfValuationResult] = None
    dcf_assumptions: Optional[DcfAssumptions] = None
    if selected_dcf_id is not None:
        d_model = DcfService.get_dcf_model(selected_dcf_id)
        if d_model:
            try:
                dcf_assumptions = DcfAssumptions.from_json(d_model.assumptions_json)
                # Resolve dependencies from linked models if not explicitly chosen
                active_fc = forecast_assumptions
                if not active_fc and d_model.forecast_model:
                    active_fc = ForecastAssumptions.from_json(d_model.forecast_model.assumptions_json)
                    if hist_bundle and hist_bundle.periods:
                        forecast_result = FinancialForecastingEngine.generate_forecast(hist_bundle, active_fc)

                active_wacc = wacc_assumptions
                if not active_wacc and d_model.wacc_model:
                    active_wacc = WaccAssumptions.from_json(d_model.wacc_model.assumptions_json)
                    wacc_result = WaccEngine.estimate_wacc(active_wacc)

                dcf_result = DcfEngine.evaluate_dcf(
                    assumptions=dcf_assumptions,
                    forecast_assumptions=active_fc,
                    wacc_assumptions=active_wacc,
                    bundle=hist_bundle,
                )
            except Exception as exc:
                diagnostics.append(f"DCF valuation error: {exc}")
        else:
            diagnostics.append(f"DCF model ID {selected_dcf_id} was not found.")

    # Scenarios
    scenario_result: Optional[ScenarioAnalysisResult] = None
    if selected_scen_id is not None:
        sc_model = ScenarioService.get_scenario_model(selected_scen_id)
        if sc_model:
            try:
                sc_assumptions = ScenarioAnalysisAssumptions.from_json(sc_model.assumptions_json)
                base_dcf = dcf_assumptions or (DcfAssumptions.from_json(sc_model.dcf_model.assumptions_json) if sc_model.dcf_model else None)
                base_fc = forecast_assumptions or (ForecastAssumptions.from_json(sc_model.forecast_model.assumptions_json) if sc_model.forecast_model else None)
                base_wacc = wacc_assumptions or (WaccAssumptions.from_json(sc_model.wacc_model.assumptions_json) if sc_model.wacc_model else None)

                if base_dcf and base_fc and base_wacc and hist_bundle:
                    scenario_result = ScenarioEngine.run_scenario_analysis(
                        assumptions=sc_assumptions,
                        bundle=hist_bundle,
                        base_forecast_assumptions=base_fc,
                        base_wacc_assumptions=base_wacc,
                        base_dcf_assumptions=base_dcf,
                        fc_model_name=sc_model.forecast_model.name if sc_model.forecast_model else "Base Forecast",
                        wacc_model_name=sc_model.wacc_model.name if sc_model.wacc_model else "Base WACC",
                        dcf_model_name=sc_model.dcf_model.name if sc_model.dcf_model else "Base DCF",
                        currency=base_currency,
                    )
                else:
                    diagnostics.append("Scenario set cannot be evaluated: missing baseline DCF, forecast, or WACC model.")
            except Exception as exc:
                diagnostics.append(f"Scenario analysis error: {exc}")
        else:
            diagnostics.append(f"Scenario model ID {selected_scen_id} was not found.")

    # Sensitivity
    sensitivity_matrix: Optional[SensitivityMatrixResult] = None
    monte_carlo_res: Optional[MonteCarloSimulationResult] = None
    if selected_sens_id is not None:
        sens_model = SensitivityService.get_sensitivity_model(selected_sens_id)
        if sens_model:
            try:
                sens_cfg = SensitivityConfig.from_json(sens_model.config_json)
                base_dcf = dcf_assumptions or (DcfAssumptions.from_json(sens_model.dcf_model.assumptions_json) if sens_model.dcf_model else None)
                base_fc = forecast_assumptions
                base_wacc = wacc_assumptions

                if base_dcf and base_fc and base_wacc and hist_bundle:
                    sensitivity_matrix = SensitivityEngine.compute_sensitivity_matrix(
                        dcf_assumptions=base_dcf,
                        base_fc_assumptions=base_fc,
                        base_wacc_assumptions=base_wacc,
                        bundle=hist_bundle,
                        axis_row_config=sens_cfg.axis_row,
                        axis_col_config=sens_cfg.axis_col,
                        metric=sens_cfg.metric,
                    )
                    if sens_cfg.run_monte_carlo:
                        monte_carlo_res = SensitivityEngine.run_monte_carlo_simulation(
                            dcf_assumptions=base_dcf,
                            base_fc_assumptions=base_fc,
                            base_wacc_assumptions=base_wacc,
                            bundle=hist_bundle,
                            config=sens_cfg,
                        )
                else:
                    diagnostics.append("Sensitivity analysis cannot be calculated: missing baseline DCF, forecast, or WACC.")
            except Exception as exc:
                diagnostics.append(f"Sensitivity evaluation error: {exc}")
        else:
            diagnostics.append(f"Sensitivity model ID {selected_sens_id} was not found.")

    # Show diagnostics if any
    if diagnostics:
        for diag in diagnostics:
            st.warning(f"⚠️ {diag}")

    st.markdown("---")

    # 4. Headline KPI Row
    st.subheader("📌 Headline Valuation & Performance KPIs")
    kpi_col1, kpi_col2, kpi_col3, kpi_col4, kpi_col5, kpi_col6, kpi_col7 = st.columns(7)

    # 1. Latest Hist Revenue
    latest_p = hist_bundle.periods[-1] if hist_bundle and hist_bundle.periods else None
    latest_m = hist_bundle.metrics_by_period.get(latest_p.label, {}) if latest_p and hist_bundle else {}
    rev_m = latest_m.get("revenue")
    growth_m = latest_m.get("revenue_growth")
    with kpi_col1:
        rev_str = f"{base_currency} {rev_m.value / scale_divisor:,.1f} {scale_label[0]}" if rev_m and rev_m.value is not None else "—"
        growth_str = f"{growth_m.value:+.1f}% YoY" if growth_m and growth_m.value is not None else None
        st.metric(f"Revenue ({latest_p.label if latest_p else 'Latest'})", rev_str, delta=growth_str)

    # 2. Latest Operating Margin
    ebit_m = latest_m.get("ebit_margin")
    with kpi_col2:
        ebit_str = f"{ebit_m.value:.1f}%" if ebit_m and ebit_m.value is not None else "—"
        st.metric("Operating Margin", ebit_str)

    # 3. Forecast Revenue / UFCF
    with kpi_col3:
        if forecast_result and forecast_result.annual_forecasts:
            last_f = forecast_result.annual_forecasts[-1]
            st.metric(
                f"UFCF ({last_f.period_label.split()[0]})",
                f"{base_currency} {last_f.ufcf / scale_divisor:,.1f} {scale_label[0]}",
                delta=f"{forecast_result.forecast_revenue_cagr:+.1f}% CAGR",
            )
        else:
            st.metric("Ending UFCF", "—")

    # 4. WACC
    with kpi_col4:
        wacc_val = wacc_result.wacc if wacc_result and wacc_result.is_valid else (dcf_result.wacc_applied if dcf_result else None)
        wacc_str = f"{wacc_val:.2f}%" if wacc_val is not None else "—"
        st.metric("WACC", wacc_str)

    # 5. Enterprise Value
    with kpi_col5:
        ev_val = dcf_result.enterprise_value if dcf_result and dcf_result.enterprise_value is not None else None
        ev_str = f"{base_currency} {ev_val / scale_divisor:,.1f} {scale_label[0]}" if ev_val is not None else "—"
        st.metric("Enterprise Value", ev_str)

    # 6. Equity Value
    with kpi_col6:
        eq_val = dcf_result.equity_value if dcf_result and dcf_result.equity_value is not None else None
        eq_str = f"{base_currency} {eq_val / scale_divisor:,.1f} {scale_label[0]}" if eq_val is not None else "—"
        st.metric("Equity Value", eq_str)

    # 7. Implied Value Per Share
    with kpi_col7:
        share_val = dcf_result.implied_value_per_share if dcf_result and dcf_result.implied_value_per_share is not None else None
        share_str = f"{base_currency} {share_val:,.2f}" if share_val is not None else "—"
        st.metric("Value / Share", share_str)

    st.markdown("---")

    # 5. Connected Dashboard Exploration Tabs
    t_hist, t_fore, t_val, t_scen_sens = st.tabs([
        "🏢 Historical Performance",
        "🔮 Forecast & Cash Flows",
        "💎 DCF Valuation & Bridge",
        "⚡ Scenario & Sensitivity",
    ])

    # =========================================================================
    # TAB 1: HISTORICAL FINANCIAL PERFORMANCE
    # =========================================================================
    with t_hist:
        st.subheader("🏢 Historical Financial Trends & Operational Indicators")
        st.caption("Interactive analysis of historical revenue, profitability margins, cash flows, and working capital cycles.")

        if not hist_bundle or not hist_bundle.periods:
            st.info("ℹ️ No historical periods found for this project and reporting frequency.")
        else:
            all_p_labels = [p.label for p in hist_bundle.periods]

            # Filters for historical charts
            f_col1, f_col2 = st.columns([2, 2])
            with f_col1:
                selected_p_filter = st.multiselect(
                    "Filter Fiscal Periods",
                    options=all_p_labels,
                    default=all_p_labels,
                    key="dash_hist_p_filter",
                )
            with f_col2:
                selected_line_metrics = st.multiselect(
                    "Display Line Items",
                    options=["Revenue", "Gross Profit", "EBITDA", "Net Income"],
                    default=["Revenue", "Gross Profit", "EBITDA", "Net Income"],
                    key="dash_hist_metrics_filter",
                )

            # Chart 1: Financial Line Items Trend
            fig_trend = create_historical_trend_chart(
                bundle=hist_bundle,
                selected_metrics=selected_line_metrics,
                period_filter=selected_p_filter,
                scale_divisor=scale_divisor,
                scale_label=scale_label,
                currency=base_currency,
            )
            if fig_trend:
                st.plotly_chart(fig_trend, use_container_width=True)

            st.markdown("---")

            c_row2_1, c_row2_2 = st.columns(2)
            with c_row2_1:
                # Chart 2: Profitability Margins
                fig_margins = create_margin_evolution_chart(bundle=hist_bundle, period_filter=selected_p_filter)
                if fig_margins:
                    st.plotly_chart(fig_margins, use_container_width=True)

            with c_row2_2:
                # Chart 3: Cash Flow vs CapEx
                fig_cf = create_cash_flow_capex_chart(
                    bundle=hist_bundle,
                    period_filter=selected_p_filter,
                    scale_divisor=scale_divisor,
                    scale_label=scale_label,
                    currency=base_currency,
                )
                if fig_cf:
                    st.plotly_chart(fig_cf, use_container_width=True)

            st.markdown("---")

            # Chart 4: Working Capital Efficiency
            fig_eff = create_working_capital_cycle_chart(bundle=hist_bundle, period_filter=selected_p_filter)
            if fig_eff:
                st.plotly_chart(fig_eff, use_container_width=True)
            else:
                st.info("ℹ️ Working capital cycle metrics (DSO/DIO/DPO) require Accounts Receivable, Inventory, Accounts Payable, and COGS line items.")

    # =========================================================================
    # TAB 2: FORECAST & CASH-FLOW TRAJECTORY
    # =========================================================================
    with t_fore:
        st.subheader("🔮 Forward-Looking Forecast & Cash-Flow Trajectory")

        if not forecast_result or not forecast_result.annual_forecasts:
            st.info("ℹ️ No forecast model selected or active. Select a saved forecast model above or navigate to the Forecasting engine to create one.")
            if st.button("➕ Go to Financial Forecasting Engine", key="btn_go_forecasting"):
                st.session_state["app_nav_selection"] = "Forecasting"
                st.rerun()
        else:
            # Historical vs Projected Revenue
            if hist_bundle:
                fig_fore_rev = create_revenue_actual_vs_projected_chart(
                    bundle=hist_bundle,
                    forecast=forecast_result,
                    scale_divisor=scale_divisor,
                    scale_label=scale_label,
                    currency=base_currency,
                )
                if fig_fore_rev:
                    st.plotly_chart(fig_fore_rev, use_container_width=True)

            st.markdown("---")

            fc_c1, fc_c2 = st.columns(2)
            with fc_c1:
                # Margin Horizon
                if hist_bundle:
                    fig_fc_margins = create_forecast_driver_margins_chart(bundle=hist_bundle, forecast=forecast_result)
                    if fig_fc_margins:
                        st.plotly_chart(fig_fc_margins, use_container_width=True)

            with fc_c2:
                # Forecast summary cards
                st.markdown("#### 📋 Forecast Parameters Summary")
                st.write(f"**Forecast Horizon:** `{len(forecast_result.annual_forecasts)} years`")
                st.write(f"**Revenue CAGR:** `{forecast_result.forecast_revenue_cagr:+.1f}%`")
                st.write(f"**Average EBITDA Margin:** `{forecast_result.avg_ebitda_margin:.1f}%`")
                st.write(f"**Average EBIT Margin:** `{forecast_result.avg_ebit_margin:.1f}%`")
                st.write(f"**Cumulative {len(forecast_result.annual_forecasts)}Y UFCF:** `{base_currency} {forecast_result.total_projected_ufcf / scale_divisor:,.1f} {scale_label[0]}`")

                st.caption(
                    "To modify forecast drivers or scenario schedules, visit the Financial Forecasting page. "
                    "Assumptions are safely locked in the dashboard presentation layer."
                )
                if st.button("✏️ Edit Forecast Assumptions", key="btn_edit_forecast"):
                    st.session_state["app_nav_selection"] = "Forecasting"
                    st.rerun()

            st.markdown("---")

            # UFCF Derivation Breakdown
            fig_ufcf = create_ufcf_trajectory_breakdown_chart(
                forecast=forecast_result,
                scale_divisor=scale_divisor,
                scale_label=scale_label,
                currency=base_currency,
            )
            if fig_ufcf:
                st.plotly_chart(fig_ufcf, use_container_width=True)

    # =========================================================================
    # TAB 3: DCF VALUATION & EQUITY BRIDGE
    # =========================================================================
    with t_val:
        st.subheader("💎 DCF Valuation Bridge & Enterprise-to-Equity Transition")

        if not dcf_result or not dcf_result.is_valid:
            st.info("ℹ️ No DCF valuation case selected or the selected model has missing dependencies. Select a saved DCF model above or configure one in DCF Valuation.")
            if st.button("➕ Go to DCF Valuation Engine", key="btn_go_dcf"):
                st.session_state["app_nav_selection"] = "DCF Valuation"
                st.rerun()
        else:
            # 1. Valuation Waterfall Chart
            fig_waterfall = create_valuation_waterfall_chart(
                result=dcf_result,
                scale_divisor=scale_divisor,
                scale_label=scale_label,
                currency=base_currency,
            )
            if fig_waterfall:
                st.plotly_chart(fig_waterfall, use_container_width=True)

            st.markdown("---")

            val_c1, val_c2 = st.columns(2)
            with val_c1:
                # Cash Flow Discounting Comparison
                fig_disc = create_cash_flow_discounting_comparison_chart(
                    result=dcf_result,
                    scale_divisor=scale_divisor,
                    scale_label=scale_label,
                    currency=base_currency,
                )
                if fig_disc:
                    st.plotly_chart(fig_disc, use_container_width=True)

            with val_c2:
                # Terminal Value Donut
                fig_tv = create_terminal_value_share_donut_chart(result=dcf_result)
                if fig_tv:
                    st.plotly_chart(fig_tv, use_container_width=True)

            # High Terminal Value Concentration Diagnostic Alert
            tv_share = dcf_result.terminal_value_pct_ev or 0.0
            if tv_share > 75.0:
                st.warning(
                    f"⚠️ **High Terminal Value Concentration:** Terminal value constitutes **{tv_share:.1f}%** of total Enterprise Value. "
                    "In institutional practice, when terminal value exceeds 75–80% of enterprise value, valuation sensitivity to perpetual growth "
                    "or exit multiple assumptions increases substantially. Verify that terminal growth does not exceed long-term GDP growth."
                )

            st.markdown("---")

            # Compact DCF Assumptions and Accounting Bridge Summary
            st.markdown("#### 📐 Selected Valuation Parameters")
            p_c1, p_c2, p_c3, p_c4 = st.columns(4)
            with p_c1:
                st.write(f"**Terminal Method:** `{dcf_result.terminal_method.title()}`")
            with p_c2:
                st.write(f"**Timing Convention:** `{dcf_result.timing_convention.title()}`")
            with p_c3:
                st.write(f"**Discount Rate (WACC):** `{dcf_result.wacc_applied:.2f}%`")
            with p_c4:
                term_val_str = f"g = {dcf_result.terminal_parameter_applied:.2f}%" if dcf_result.terminal_method == TerminalValueMethod.GORDON_GROWTH.value else f"{dcf_result.terminal_parameter_applied:.2f}x EBITDA"
                st.write(f"**Terminal Driver:** `{term_val_str}`")

            if st.button("⚙️ Open Full DCF Valuation Workbench", key="btn_open_dcf_workbench"):
                st.session_state["app_nav_selection"] = "DCF Valuation"
                st.rerun()

    # =========================================================================
    # TAB 4: SCENARIO & SENSITIVITY EXPLORATION
    # =========================================================================
    with t_scen_sens:
        st.subheader("⚡ Scenario Analysis & Sensitivity Exploration")

        scen_subtab, sens_subtab = st.tabs([
            "📊 Scenario Comparisons (Base / Bull / Bear)",
            "🎲 Sensitivity Matrix & Monte Carlo",
        ])

        with scen_subtab:
            if not scenario_result:
                st.info("ℹ️ No saved scenario model selected. Select a scenario model in the dropdown above or go to the Scenarios workbench.")
                if st.button("➕ Go to Scenario Analysis Workbench", key="btn_go_scen"):
                    st.session_state["app_nav_selection"] = "Scenarios"
                    st.rerun()
            else:
                sc_opt = st.radio("Scenario Comparison Metric", options=["Valuation (EV & Equity)", "Implied Value per Share"], horizontal=True)
                metric_key = "valuation" if "Valuation" in sc_opt else "share_price"

                fig_scen = create_scenario_comparison_chart(
                    result=scenario_result,
                    metric_type=metric_key,
                    scale_divisor=scale_divisor,
                    scale_label=scale_label,
                    currency=base_currency,
                )
                if fig_scen:
                    st.plotly_chart(fig_scen, use_container_width=True)

                st.markdown("---")
                st.markdown("#### 📋 Scenario Overrides & Baseline Delta Audit")
                df_audit = build_assumption_audit_dataframe(scenario_result)
                st.dataframe(df_audit, use_container_width=True, hide_index=True)

                if st.button("⚙️ Configure Scenario Parameters", key="btn_cfg_scen"):
                    st.session_state["app_nav_selection"] = "Scenarios"
                    st.rerun()

        with sens_subtab:
            if not sensitivity_matrix:
                st.info("ℹ️ No sensitivity configuration selected. Select a saved sensitivity model in the dropdown above or configure one in Sensitivity Analysis.")
                if st.button("➕ Go to Sensitivity Analysis Workbench", key="btn_go_sens"):
                    st.session_state["app_nav_selection"] = "Sensitivity Analysis"
                    st.rerun()
            else:
                # 2D Heatmap
                fig_heat = create_sensitivity_contour_chart(result=sensitivity_matrix, currency=base_currency)
                if fig_heat:
                    st.plotly_chart(fig_heat, use_container_width=True)

                # Monte Carlo if available
                if monte_carlo_res:
                    st.markdown("---")
                    st.markdown("#### 🎲 Monte Carlo Simulation Distribution")
                    mc_c1, mc_c2 = st.columns([1, 2])
                    with mc_c1:
                        mc_metric_choice = st.selectbox(
                            "Simulation Metric",
                            options=["share_price", "enterprise_value", "equity_value"],
                            format_func=lambda x: "Implied Value / Share" if x == "share_price" else ("Enterprise Value" if x == "enterprise_value" else "Equity Value"),
                            key="dash_mc_metric_select",
                        )
                        st.caption(f"Valid Draws: **{monte_carlo_res.valid_iterations} / {monte_carlo_res.total_iterations}**")
                        if monte_carlo_res.invalid_iterations > 0:
                            st.warning(f"Discarded Draws: {monte_carlo_res.invalid_iterations} (WACC ≤ g)")

                    with mc_c2:
                        fig_mc = create_monte_carlo_distribution_chart(
                            result=monte_carlo_res,
                            metric_type=mc_metric_choice,
                            currency=base_currency,
                        )
                        if fig_mc:
                            st.plotly_chart(fig_mc, use_container_width=True)

                    st.markdown("#### Percentile Statistics Summary")
                    df_mc_stats = build_monte_carlo_stats_dataframe(
                        monte_carlo_res,
                        currency=base_currency,
                        unit=scale_label,
                    )
                    st.dataframe(df_mc_stats, use_container_width=True, hide_index=True)

                st.caption(
                    "Note: Sensitivity matrices and Monte Carlo simulations reflect verified saved configurations. "
                    "Simulations are never run automatically on page refresh. To adjust parameter ranges, visit the Sensitivity Analysis workbench."
                )
                if st.button("⚙️ Configure Sensitivity & Simulation Parameters", key="btn_cfg_sens"):
                    st.session_state["app_nav_selection"] = "Sensitivity Analysis"
                    st.rerun()
