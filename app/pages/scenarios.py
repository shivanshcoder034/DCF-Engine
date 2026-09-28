"""Scenario Analysis (Base, Bull, Bear) Streamlit Interface.

Provides multi-scenario DCF valuation modeling, user-editable assumption overrides
in percentage points (pp), basis points (bps), and multiple units (x),
comparative valuation tables, Plotly visualizations, and persistence.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Ensure repository root is in sys.path
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

import json
from typing import Dict, List, Optional

import pandas as pd
import streamlit as st

from src.analysis.engine import HistoricalAnalysisEngine
from src.data.services import ProjectService
from src.dcf.models import DcfAssumptions, TerminalValueMethod
from src.dcf.services import DcfService
from src.forecasting.models import ForecastAssumptions
from src.forecasting.services import ForecastService
from src.scenarios.engine import ScenarioEngine
from src.scenarios.formatting import (
    build_assumption_audit_dataframe,
    build_scenario_comparison_dataframe,
    create_scenario_cash_flow_trajectory_chart,
    create_scenario_ev_composition_bar_chart,
    create_scenario_ev_equity_bar_chart,
    create_scenario_share_price_chart,
)
from src.scenarios.models import (
    ScenarioAnalysisAssumptions,
    ScenarioAnalysisResult,
    ScenarioOverrides,
)
from src.scenarios.services import ScenarioService
from src.wacc.models import WaccAssumptions
from src.wacc.services import WaccService


def render_scenarios_page() -> None:
    """Render the Scenario Analysis (Base / Bull / Bear) application page."""
    st.header("🎭 Scenario Analysis Engine (Base / Bull / Bear)")
    st.markdown(
        "Evaluate and stress-test company valuation across **Base**, **Bull**, and **Bear** cases. "
        "The **Base case** reflects selected saved forecast and WACC baseline models without overrides. "
        "**Bull** and **Bear** cases apply user-configured adjustments in explicit units (**percentage points** and **basis points**). "
        "All calculations reuse the deterministic Phase 4 forecast, Phase 5 WACC, and Phase 6 DCF engines."
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
            key="scenario_project_select",
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
        hist_bundle = None
        st.info(f"Historical analysis baseline not available: {exc}")

    st.markdown("---")

    # 3. Model Dependencies: Select DCF Model or Forecast + WACC
    st.subheader("🔗 Baseline Model Dependencies")

    saved_dcf_models = DcfService.list_dcf_models(selected_project_id)
    saved_fc_models = ForecastService.list_forecast_models(selected_project_id)
    saved_wacc_models = WaccService.list_wacc_models(selected_project_id)

    col_dcf_link, col_nav_btn = st.columns([3, 1])
    with col_dcf_link:
        if saved_dcf_models:
            dcf_opts = {m.id: f"💰 {m.name} (Updated {m.updated_at.strftime('%Y-%m-%d')})" for m in saved_dcf_models}
            selected_dcf_id = st.selectbox(
                "Linked Phase 6 DCF Model (Recommended baseline source) *",
                options=list(dcf_opts.keys()),
                format_func=lambda k: dcf_opts[k],
                key="scenario_linked_dcf_select",
                help="Selecting a saved DCF model loads its configured terminal value method, bridge items, and linked forecast/WACC cases.",
            )
        else:
            selected_dcf_id = None
            st.info("ℹ️ No saved DCF models found for this project. You can link Forecast and WACC models directly below.")

    with col_nav_btn:
        st.write("")
        st.write("")
        if st.button("🔙 Open DCF Valuation Page", key="btn_nav_to_dcf"):
            st.session_state["app_nav_selection"] = "DCF Valuation"
            st.rerun()

    # Load baseline DCF assumptions if selected
    active_dcf_assumptions: Optional[DcfAssumptions] = None
    selected_fc_id: Optional[int] = None
    selected_wacc_id: Optional[int] = None
    dcf_record_name: Optional[str] = None

    if selected_dcf_id:
        dcf_record = next((m for m in saved_dcf_models if m.id == selected_dcf_id), None)
        if dcf_record:
            dcf_record_name = dcf_record.name
            try:
                active_dcf_assumptions = DcfAssumptions.from_json(dcf_record.assumptions_json)
                selected_fc_id = active_dcf_assumptions.forecast_model_id
                selected_wacc_id = active_dcf_assumptions.wacc_model_id
            except Exception as e:
                st.error(f"Error parsing saved DCF model assumptions: {e}")

    # Fallback or explicit Forecast and WACC selection
    col_fc_link, col_wacc_link = st.columns(2)
    with col_fc_link:
        if saved_fc_models:
            fc_opts = {m.id: f"📈 {m.name} ({m.horizon_years}Y from {m.base_period_label})" for m in saved_fc_models}
            default_fc_idx = list(fc_opts.keys()).index(selected_fc_id) if selected_fc_id in fc_opts else 0
            selected_fc_id = st.selectbox(
                "Linked Forecast Model *",
                options=list(fc_opts.keys()),
                index=default_fc_idx,
                format_func=lambda k: fc_opts[k],
                key="scenario_linked_fc_select",
            )
        else:
            selected_fc_id = None
            st.warning("⚠️ No saved Phase 4 forecast models found for this project.")

    with col_wacc_link:
        if saved_wacc_models:
            wacc_opts = {m.id: f"⚖️ {m.name} (Updated {m.updated_at.strftime('%Y-%m-%d')})" for m in saved_wacc_models}
            default_wacc_idx = list(wacc_opts.keys()).index(selected_wacc_id) if selected_wacc_id in wacc_opts else 0
            selected_wacc_id = st.selectbox(
                "Linked WACC Model *",
                options=list(wacc_opts.keys()),
                index=default_wacc_idx,
                format_func=lambda k: wacc_opts[k],
                key="scenario_linked_wacc_select",
            )
        else:
            selected_wacc_id = None
            st.warning("⚠️ No saved Phase 5 WACC models found for this project.")

    # Parse Forecast and WACC assumptions
    active_fc_assumptions: Optional[ForecastAssumptions] = None
    fc_record_name: Optional[str] = None
    if selected_fc_id:
        fc_rec = next((m for m in saved_fc_models if m.id == selected_fc_id), None)
        if fc_rec:
            fc_record_name = fc_rec.name
            try:
                active_fc_assumptions = ForecastAssumptions.from_dict(json.loads(fc_rec.assumptions_json))
            except Exception as e:
                st.error(f"Error parsing forecast assumptions: {e}")

    active_wacc_assumptions: Optional[WaccAssumptions] = None
    wacc_record_name: Optional[str] = None
    if selected_wacc_id:
        wacc_rec = next((m for m in saved_wacc_models if m.id == selected_wacc_id), None)
        if wacc_rec:
            wacc_record_name = wacc_rec.name
            try:
                active_wacc_assumptions = WaccAssumptions.from_json(wacc_rec.assumptions_json)
            except Exception as e:
                st.error(f"Error parsing WACC assumptions: {e}")

    # If no DCF assumptions loaded from saved DCF model, build default DCF assumptions with linked models
    if active_dcf_assumptions is None:
        from src.dcf.engine import DcfEngine
        active_dcf_assumptions = DcfEngine.create_default_assumptions(
            project_id=selected_project_id,
            forecast_model_id=selected_fc_id,
            wacc_model_id=selected_wacc_id,
            bundle=hist_bundle,
        )
    else:
        active_dcf_assumptions.forecast_model_id = selected_fc_id
        active_dcf_assumptions.wacc_model_id = selected_wacc_id

    st.markdown("---")

    # 4. Scenario Analysis Set Management (Save / Load / Switch)
    st.subheader("📁 Scenario Analysis Set (Save / Load)")

    saved_scenario_sets = ScenarioService.list_scenario_models(selected_project_id)
    set_options = {"new": "➕ Create New Scenario Analysis Set"}
    set_options.update({m.id: f"📂 {m.name} (Updated {m.updated_at.strftime('%Y-%m-%d %H:%M')})" for m in saved_scenario_sets})

    sc_col1, sc_col2 = st.columns([2, 1])
    with sc_col1:
        selected_set_key = st.selectbox(
            "Active Scenario Set",
            options=list(set_options.keys()),
            format_func=lambda k: set_options[k],
            key="saved_scenario_set_select",
        )

    # State keys
    state_key = f"scenario_assumptions_{selected_project_id}"
    loaded_set_id_key = f"scenario_loaded_id_{selected_project_id}"
    current_loaded_set_id = st.session_state.get(loaded_set_id_key)

    # Load from DB if a saved set is chosen
    if selected_set_key != "new" and current_loaded_set_id != selected_set_key:
        db_sc_model = ScenarioService.get_scenario_model(int(selected_set_key))
        if db_sc_model:
            try:
                st.session_state[state_key] = ScenarioAnalysisAssumptions.from_json(db_sc_model.assumptions_json)
                st.session_state[loaded_set_id_key] = selected_set_key
                st.toast(f"Loaded scenario set '{db_sc_model.name}'")
            except Exception as e:
                st.error(f"Error loading saved scenario set: {e}")
    elif selected_set_key == "new" and current_loaded_set_id != "new":
        st.session_state[state_key] = ScenarioAnalysisAssumptions(
            name="Base / Bull / Bear Scenario Set",
            description="Comparative multi-case DCF valuation analysis.",
            project_id=selected_project_id,
            dcf_model_id=selected_dcf_id,
            forecast_model_id=selected_fc_id,
            wacc_model_id=selected_wacc_id,
            bull_overrides=ScenarioOverrides.default_bull(),
            bear_overrides=ScenarioOverrides.default_bear(),
        )
        st.session_state[loaded_set_id_key] = "new"

    if state_key not in st.session_state:
        st.session_state[state_key] = ScenarioAnalysisAssumptions(
            name="Base / Bull / Bear Scenario Set",
            description="Comparative multi-case DCF valuation analysis.",
            project_id=selected_project_id,
            dcf_model_id=selected_dcf_id,
            forecast_model_id=selected_fc_id,
            wacc_model_id=selected_wacc_id,
            bull_overrides=ScenarioOverrides.default_bull(),
            bear_overrides=ScenarioOverrides.default_bear(),
        )

    scenario_assumptions: ScenarioAnalysisAssumptions = st.session_state[state_key]
    scenario_assumptions.project_id = selected_project_id
    scenario_assumptions.dcf_model_id = selected_dcf_id
    scenario_assumptions.forecast_model_id = selected_fc_id
    scenario_assumptions.wacc_model_id = selected_wacc_id

    st.markdown("---")

    # 5. Scenario Override Controls & Guide
    st.subheader("⚙️ Scenario Override Configuration")

    with st.expander("ℹ️ Understanding Scenario Override Units and Direction", expanded=False):
        st.markdown(
            """
            - **Revenue Growth Adjustment (`pp`)**: Expressed in **percentage points** added directly to each forecast year's growth rate.
              *Example:* If the baseline growth is $6.0\\%$, a $+2.0\\text{ pp}$ override yields an $8.0\\%$ growth rate (not a relative $2\\%$ increase).
            - **Operating Margin Adjustment (`pp`)**: Expressed in **percentage points** added to operating profitability (via gross margin) across all forecast periods.
              *Example:* If the baseline operating margin is $16.0\\%$, a $+1.5\\text{ pp}$ override expands operating margin to $17.5\\%$.
            - **WACC Adjustment (`bps`)**: Expressed in **basis points** ($100\\text{ bps} = 1.00\\%$).
              *Example:* A $-50\\text{ bps}$ override reduces an $8.50\\%$ WACC to $8.00\\%$.
            - **Perpetual Growth Rate Adjustment (`bps`)**: Expressed in **basis points** when using Gordon Growth.
              *Example:* A $+25\\text{ bps}$ adjustment raises a $2.50\\%$ perpetual growth rate to $2.75\\%$.
            - **Exit Multiple Adjustment (`x`)**: Expressed as an absolute change in the EV/EBITDA multiple.
              *Example:* A $+1.5\\text{x}$ adjustment increases a $10.0\\text{x}$ multiple to $11.5\\text{x}$.
            - **Illustrative Starting Assumptions**: Defaults are illustrative baseline templates, not market-derived recommendations or investment advice.
            """
        )

    # Determine terminal value method in active DCF assumptions
    term_method = active_dcf_assumptions.terminal_inputs.method
    is_gordon = term_method == TerminalValueMethod.GORDON_GROWTH.value

    col_base_view, col_bull_edit, col_bear_edit = st.columns(3)

    # BASE CASE PANEL (Locked, pure baseline)
    with col_base_view:
        st.markdown("### 🏛️ Base Case")
        st.info("Baseline scenario uses selected saved forecast and WACC inputs **without overrides**.")

        # Display baseline parameters
        base_g_avg = (
            sum(active_fc_assumptions.revenue_growth_rates) / len(active_fc_assumptions.revenue_growth_rates)
            if active_fc_assumptions and active_fc_assumptions.revenue_growth_rates else 5.0
        )
        base_gm_avg = (
            sum(active_fc_assumptions.gross_margin_rates) / len(active_fc_assumptions.gross_margin_rates)
            if active_fc_assumptions and active_fc_assumptions.gross_margin_rates else 40.0
        )
        base_opex_avg = (
            sum(active_fc_assumptions.opex_pct_rates) / len(active_fc_assumptions.opex_pct_rates)
            if active_fc_assumptions and active_fc_assumptions.opex_pct_rates else 20.0
        )
        base_da_avg = (
            sum(active_fc_assumptions.da_pct_rates) / len(active_fc_assumptions.da_pct_rates)
            if active_fc_assumptions and active_fc_assumptions.da_pct_rates else 4.0
        )
        base_margin_est = base_gm_avg - base_opex_avg - base_da_avg

        st.write(f"• **Avg. Revenue Growth:** `{base_g_avg:.2f}%`")
        st.write(f"• **Avg. Operating Margin:** `{base_margin_est:.2f}%`")

        wacc_est_val = "Pending calculation"
        if active_wacc_assumptions:
            from src.wacc.engine import WaccEngine
            w_res = WaccEngine.estimate_wacc(active_wacc_assumptions)
            if w_res.is_complete and w_res.wacc is not None:
                wacc_est_val = f"{w_res.wacc:.2f}%"

        st.write(f"• **Cost of Capital (WACC):** `{wacc_est_val}`")

        if is_gordon:
            g_rate = active_dcf_assumptions.terminal_inputs.perpetual_growth_rate or 2.50
            st.write(f"• **Perpetual Growth Rate ($g$):** `{g_rate:.2f}%`")
        else:
            mult_val = active_dcf_assumptions.terminal_inputs.exit_multiple or 10.0
            st.write(f"• **Exit Multiple (EV/EBITDA):** `{mult_val:.2f}x`")

        st.caption("🔒 Base case is never modified when adjusting Bull/Bear overrides.")

    # BULL CASE PANEL (Editable overrides)
    with col_bull_edit:
        st.markdown("### 🐂 Bull Case Overrides")
        st.caption("Favorable operating performance and lower capital cost.")

        bull_overrides = scenario_assumptions.bull_overrides

        b_rev = st.number_input(
            "Revenue Growth Adjustment (pp) *",
            min_value=-50.0,
            max_value=50.0,
            value=float(bull_overrides.revenue_growth_delta_pp),
            step=0.25,
            format="%.2f",
            key="bull_rev_delta",
            help="Percentage points added to each year's revenue growth rate (+/- pp).",
        )
        bull_overrides.revenue_growth_delta_pp = b_rev

        b_mrg = st.number_input(
            "Operating Margin Adjustment (pp) *",
            min_value=-50.0,
            max_value=50.0,
            value=float(bull_overrides.margin_delta_pp),
            step=0.25,
            format="%.2f",
            key="bull_mrg_delta",
            help="Percentage points added to operating margin (+/- pp).",
        )
        bull_overrides.margin_delta_pp = b_mrg

        b_wacc = st.number_input(
            "WACC Discount Rate Adjustment (bps) *",
            min_value=-1000.0,
            max_value=1000.0,
            value=float(bull_overrides.wacc_delta_bps),
            step=10.0,
            format="%.0f",
            key="bull_wacc_delta",
            help="Basis points added to base WACC (100 bps = 1.00%). E.g., -50 bps reduces WACC by 0.50%.",
        )
        bull_overrides.wacc_delta_bps = b_wacc

        if is_gordon:
            b_pg = st.number_input(
                "Perpetual Growth Rate Adjustment (bps) *",
                min_value=-500.0,
                max_value=500.0,
                value=float(bull_overrides.perpetual_growth_delta_bps),
                step=5.0,
                format="%.0f",
                key="bull_pg_delta",
                help="Basis points added to Gordon Growth rate (100 bps = 1.00%).",
            )
            bull_overrides.perpetual_growth_delta_bps = b_pg
        else:
            b_mult = st.number_input(
                "Exit Multiple Adjustment (x EBITDA) *",
                min_value=-20.0,
                max_value=20.0,
                value=float(bull_overrides.exit_multiple_delta),
                step=0.25,
                format="%.2f",
                key="bull_mult_delta",
                help="Multiple change added to baseline exit multiple (+/- x).",
            )
            bull_overrides.exit_multiple_delta = b_mult

        if st.button("🔄 Reset Bull to Defaults", key="btn_reset_bull"):
            scenario_assumptions.bull_overrides = ScenarioOverrides.default_bull()
            st.rerun()

    # BEAR CASE PANEL (Editable overrides)
    with col_bear_edit:
        st.markdown("### 🐻 Bear Case Overrides")
        st.caption("Challenging operating environment and higher capital cost.")

        bear_overrides = scenario_assumptions.bear_overrides

        bear_rev = st.number_input(
            "Revenue Growth Adjustment (pp) *",
            min_value=-50.0,
            max_value=50.0,
            value=float(bear_overrides.revenue_growth_delta_pp),
            step=0.25,
            format="%.2f",
            key="bear_rev_delta",
            help="Percentage points added to each year's revenue growth rate (+/- pp).",
        )
        bear_overrides.revenue_growth_delta_pp = bear_rev

        bear_mrg = st.number_input(
            "Operating Margin Adjustment (pp) *",
            min_value=-50.0,
            max_value=50.0,
            value=float(bear_overrides.margin_delta_pp),
            step=0.25,
            format="%.2f",
            key="bear_mrg_delta",
            help="Percentage points added to operating margin (+/- pp).",
        )
        bear_overrides.margin_delta_pp = bear_mrg

        bear_wacc = st.number_input(
            "WACC Discount Rate Adjustment (bps) *",
            min_value=-1000.0,
            max_value=1000.0,
            value=float(bear_overrides.wacc_delta_bps),
            step=10.0,
            format="%.0f",
            key="bear_wacc_delta",
            help="Basis points added to base WACC (100 bps = 1.00%). E.g., +50 bps increases WACC by 0.50%.",
        )
        bear_overrides.wacc_delta_bps = bear_wacc

        if is_gordon:
            bear_pg = st.number_input(
                "Perpetual Growth Rate Adjustment (bps) *",
                min_value=-500.0,
                max_value=500.0,
                value=float(bear_overrides.perpetual_growth_delta_bps),
                step=5.0,
                format="%.0f",
                key="bear_pg_delta",
                help="Basis points added to Gordon Growth rate (100 bps = 1.00%).",
            )
            bear_overrides.perpetual_growth_delta_bps = bear_pg
        else:
            bear_mult = st.number_input(
                "Exit Multiple Adjustment (x EBITDA) *",
                min_value=-20.0,
                max_value=20.0,
                value=float(bear_overrides.exit_multiple_delta),
                step=0.25,
                format="%.2f",
                key="bear_mult_delta",
                help="Multiple change added to baseline exit multiple (+/- x).",
            )
            bear_overrides.exit_multiple_delta = bear_mult

        if st.button("🔄 Reset Bear to Defaults", key="btn_reset_bear"):
            scenario_assumptions.bear_overrides = ScenarioOverrides.default_bear()
            st.rerun()

    # 6. Execute Multi-Scenario Calculations
    scenario_result: ScenarioAnalysisResult = ScenarioEngine.run_scenario_analysis(
        assumptions=scenario_assumptions,
        bundle=hist_bundle,
        base_forecast_assumptions=active_fc_assumptions,
        base_wacc_assumptions=active_wacc_assumptions,
        base_dcf_assumptions=active_dcf_assumptions,
        fc_model_name=fc_record_name,
        wacc_model_name=wacc_record_name,
        dcf_model_name=dcf_record_name,
        currency=base_currency,
    )

    st.markdown("---")

    # 7. Headline Comparison Metric Cards
    st.subheader("🏁 Valuation Scenario Comparison Summary")

    base_c = scenario_result.base_case
    bull_c = scenario_result.bull_case
    bear_c = scenario_result.bear_case

    card_bear, card_base, card_bull = st.columns(3)

    with card_bear:
        st.markdown("#### 🐻 Bear Case")
        if bear_c.is_valid and bear_c.implied_value_per_share is not None:
            delta_str = ""
            if base_c.is_valid and base_c.implied_value_per_share:
                delta_pct = (bear_c.implied_value_per_share - base_c.implied_value_per_share) / base_c.implied_value_per_share * 100.0
                delta_str = f" ({delta_pct:+.1f}% vs Base)"
            st.metric(
                label=f"Implied Value / Share{delta_str}",
                value=f"{base_currency} {bear_c.implied_value_per_share:,.2f}",
            )
            st.write(f"• **Equity Value:** `{base_currency} {bear_c.equity_value:,.2f} {hist_bundle.display_unit if hist_bundle else ''}`")
            st.write(f"• **Enterprise Value:** `{base_currency} {bear_c.enterprise_value:,.2f} {hist_bundle.display_unit if hist_bundle else ''}`")
            st.write(f"• **Effective WACC:** `{bear_c.effective_wacc:.2f}%`")
        else:
            st.error("⚠️ Valuation Withheld")
            for reason in bear_c.missing_inputs:
                st.caption(f"• {reason}")
            for warn in bear_c.warnings:
                st.caption(f"• {warn}")

    with card_base:
        st.markdown("#### 🏛️ Base Case (Baseline)")
        if base_c.is_valid and base_c.implied_value_per_share is not None:
            st.metric(
                label="Implied Value / Share (Baseline Target)",
                value=f"{base_currency} {base_c.implied_value_per_share:,.2f}",
            )
            st.write(f"• **Equity Value:** `{base_currency} {base_c.equity_value:,.2f} {hist_bundle.display_unit if hist_bundle else ''}`")
            st.write(f"• **Enterprise Value:** `{base_currency} {base_c.enterprise_value:,.2f} {hist_bundle.display_unit if hist_bundle else ''}`")
            st.write(f"• **Effective WACC:** `{base_c.effective_wacc:.2f}%`")
        else:
            st.error("⚠️ Valuation Withheld")
            for reason in base_c.missing_inputs:
                st.caption(f"• {reason}")

    with card_bull:
        st.markdown("#### 🐂 Bull Case")
        if bull_c.is_valid and bull_c.implied_value_per_share is not None:
            delta_str = ""
            if base_c.is_valid and base_c.implied_value_per_share:
                delta_pct = (bull_c.implied_value_per_share - base_c.implied_value_per_share) / base_c.implied_value_per_share * 100.0
                delta_str = f" ({delta_pct:+.1f}% vs Base)"
            st.metric(
                label=f"Implied Value / Share{delta_str}",
                value=f"{base_currency} {bull_c.implied_value_per_share:,.2f}",
            )
            st.write(f"• **Equity Value:** `{base_currency} {bull_c.equity_value:,.2f} {hist_bundle.display_unit if hist_bundle else ''}`")
            st.write(f"• **Enterprise Value:** `{base_currency} {bull_c.enterprise_value:,.2f} {hist_bundle.display_unit if hist_bundle else ''}`")
            st.write(f"• **Effective WACC:** `{bull_c.effective_wacc:.2f}%`")
        else:
            st.error("⚠️ Valuation Withheld")
            for reason in bull_c.missing_inputs:
                st.caption(f"• {reason}")
            for warn in bull_c.warnings:
                st.caption(f"• {warn}")

    st.markdown("---")

    # 8. Interactive Tabs: Comparative Table, Visual Charts, Audit Table, Persistence
    tab_table, tab_charts, tab_audit, tab_save = st.tabs([
        "📊 Cross-Scenario Valuation Table",
        "📈 Visual Comparison Charts",
        "🔍 Assumptions & Audit Bridge",
        "💾 Save & Manage Scenario Set",
    ])

    # TAB 1: COMPARISON TABLE
    with tab_table:
        st.subheader("Cross-Scenario Valuation Output Matrix")
        st.caption(
            "Side-by-side comparison of operational drivers, cost of capital, cash flow present values, "
            "enterprise value, equity value, and implied intrinsic per-share targets."
        )

        comp_df = build_scenario_comparison_dataframe(
            result=scenario_result,
            currency=base_currency,
            unit=hist_bundle.display_unit if hist_bundle else "millions",
        )
        st.dataframe(comp_df, hide_index=True, use_container_width=True)

        # Download CSV button
        csv_data = comp_df.to_csv(index=False).encode("utf-8")
        st.download_button(
            label="📥 Download Comparison Table (CSV)",
            data=csv_data,
            file_name=f"scenario_comparison_{selected_project_id}.csv",
            mime="text/csv",
            key="dl_scenario_comp_csv",
        )

    # TAB 2: VISUAL COMPARISON CHARTS
    with tab_charts:
        st.subheader("Cross-Scenario Visual Analytics")

        ch_col1, ch_col2 = st.columns(2)

        with ch_col1:
            ev_chart = create_scenario_ev_equity_bar_chart(scenario_result, currency=base_currency)
            if ev_chart:
                st.plotly_chart(ev_chart, use_container_width=True)
            else:
                st.info("Enterprise and Equity value chart unavailable due to incomplete scenarios.")

        with ch_col2:
            sp_chart = create_scenario_share_price_chart(scenario_result, currency=base_currency)
            if sp_chart:
                st.plotly_chart(sp_chart, use_container_width=True)
            else:
                st.info("Implied share price chart unavailable (share count required).")

        ch_col3, ch_col4 = st.columns(2)

        with ch_col3:
            cf_traj_chart = create_scenario_cash_flow_trajectory_chart(scenario_result, currency=base_currency)
            if cf_traj_chart:
                st.plotly_chart(cf_traj_chart, use_container_width=True)
            else:
                st.info("Cash flow trajectory chart unavailable.")

        with ch_col4:
            ev_comp_chart = create_scenario_ev_composition_bar_chart(scenario_result, currency=base_currency)
            if ev_comp_chart:
                st.plotly_chart(ev_comp_chart, use_container_width=True)
            else:
                st.info("Enterprise value composition chart unavailable.")

    # TAB 3: ASSUMPTION AUDIT & DELTA BRIDGE
    with tab_audit:
        st.subheader("Assumption Audit & Provenance Bridge")
        st.caption(
            "Complete audit trail showing baseline parameters, configured overrides, resulting scenario assumptions, "
            "and linked source model provenance."
        )

        audit_df = build_assumption_audit_dataframe(scenario_result)
        st.dataframe(audit_df, hide_index=True, use_container_width=True)

        st.markdown("#### 🔗 Linked Model Provenance")
        prov_col1, prov_col2, prov_col3 = st.columns(3)
        with prov_col1:
            st.write(f"• **Linked Forecast Scenario:** `{fc_record_name or 'Unsaved / In-memory'}`")
            st.write(f"• **Forecast Horizon:** `{active_fc_assumptions.horizon_years if active_fc_assumptions else 'N/A'} years`")
        with prov_col2:
            st.write(f"• **Linked WACC Case:** `{wacc_record_name or 'Unsaved / In-memory'}`")
            st.write(f"• **Baseline WACC:** `{base_c.effective_wacc:.2f}%`" if base_c.effective_wacc else "• **Baseline WACC:** `N/A`")
        with prov_col3:
            st.write(f"• **Linked DCF Case:** `{dcf_record_name or 'Unsaved / In-memory'}`")
            st.write(f"• **Discounting Convention:** `{active_dcf_assumptions.discounting_convention.replace('_', ' ').title()}`")

    # TAB 4: PERSISTENCE (SAVE / UPDATE / DELETE)
    with tab_save:
        st.subheader("💾 Persist Scenario Analysis Configuration")

        col_sn1, col_sn2 = st.columns([2, 1])
        with col_sn1:
            set_name_val = st.text_input(
                "Scenario Analysis Set Name *",
                value=scenario_assumptions.name,
                key="scenario_set_name_input",
                placeholder="e.g. Q3 Base / Bull / Bear Strategic Review",
            )
            scenario_assumptions.name = set_name_val

            set_desc_val = st.text_area(
                "Scenario Set Description & Rationale",
                value=scenario_assumptions.description or "",
                key="scenario_set_desc_input",
                placeholder="Document strategic reasoning, economic assumptions, or stress-test premises...",
            )
            scenario_assumptions.description = set_desc_val

        with col_sn2:
            st.write("")
            st.write("")
            if st.button("💾 Save / Update Scenario Set", type="primary", key="btn_save_scenario_set"):
                try:
                    saved_model = ScenarioService.save_scenario_model(
                        project_id=selected_project_id,
                        name=scenario_assumptions.name,
                        assumptions=scenario_assumptions,
                        description=scenario_assumptions.description,
                    )
                    st.success(f"✅ Successfully saved scenario analysis set '{saved_model.name}' (ID: {saved_model.id})")
                    st.session_state[loaded_set_id_key] = saved_model.id
                    st.rerun()
                except Exception as exc:
                    st.error(f"Error saving scenario analysis set: {exc}")

            if selected_set_key != "new":
                if st.button("🗑️ Delete Selected Scenario Set", key="btn_del_scenario_set"):
                    success = ScenarioService.delete_scenario_model(int(selected_set_key))
                    if success:
                        st.success("Scenario analysis set deleted successfully.")
                        st.session_state[loaded_set_id_key] = "new"
                        st.rerun()
                    else:
                        st.error("Failed to delete scenario set.")

    # 9. Audit Warnings & Diagnostics
    all_warnings = list(dict.fromkeys(base_c.warnings + bull_c.warnings + bear_c.warnings))
    if all_warnings:
        st.markdown("---")
        st.subheader("⚠️ Model Audit & Diagnostics Warnings")
        for warn in all_warnings:
            st.warning(warn)

    st.markdown("---")
    st.caption(f"🔒 {scenario_result.disclaimer}")


if __name__ == "__main__":
    from app.navigation import run_standalone_page
    run_standalone_page("Scenarios", render_scenarios_page)
