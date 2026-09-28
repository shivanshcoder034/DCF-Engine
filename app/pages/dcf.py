"""DCF Valuation Engine Streamlit Interface.

Provides interactive configuration of forecast cash flow discounting,
terminal value models (Gordon Growth vs. Exit Multiple), enterprise-to-equity bridges,
and implied per-share intrinsic valuation.
"""

from __future__ import annotations

import json
from typing import Dict, List, Optional

import streamlit as st
import pandas as pd

from src.analysis.engine import HistoricalAnalysisEngine
from src.data.services import ProjectService
from src.dcf.engine import DcfEngine
from src.dcf.formatting import (
    build_discounting_schedule_dataframe,
    build_equity_bridge_dataframe,
    create_cash_flow_discounting_chart,
    create_ev_composition_donut_chart,
)
from src.dcf.models import (
    DcfAssumptions,
    DiscountingConvention,
    EquityBridgeInputs,
    TerminalValueInputs,
    TerminalValueMethod,
)
from src.dcf.services import DcfService
from src.forecasting.models import ForecastAssumptions
from src.forecasting.services import ForecastService
from src.wacc.models import InputProvenance, SourceCategory, WaccAssumptions
from src.wacc.services import WaccService


def render_dcf_page() -> None:
    """Render the DCF Valuation Engine application page."""
    st.header("💰 Discounted Cash Flow (DCF) Valuation Engine")
    st.markdown(
        "Determine enterprise intrinsic value and implied share price by discounting projected **Unlevered Free Cash Flows (UFCF)** "
        "at the **Weighted Average Cost of Capital (WACC)**, adding discounted terminal value, and applying the enterprise-to-equity bridge."
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
            key="dcf_project_select",
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

    # 3. Model Linking: Select Forecast Model and WACC Model
    st.subheader("🔗 Linked Engine Model Dependencies")

    # Available saved forecast models
    saved_forecast_models = ForecastService.list_forecast_models(selected_project_id)
    # Available saved WACC models
    saved_wacc_models = WaccService.list_wacc_models(selected_project_id)

    col_link_fc, col_link_wacc = st.columns(2)

    with col_link_fc:
        if saved_forecast_models:
            fc_opts = {m.id: f"📈 {m.name} ({m.horizon_years}Y from {m.base_period_label})" for m in saved_forecast_models}
            selected_fc_id = st.selectbox(
                "Linked Phase 4 Forecast Scenario *",
                options=list(fc_opts.keys()),
                format_func=lambda k: fc_opts[k],
                key="dcf_linked_forecast_select",
            )
        else:
            selected_fc_id = None
            st.warning("⚠️ No saved Phase 4 forecast models found for this project. Please build and save a forecast in the **Forecasting** section.")

    with col_link_wacc:
        if saved_wacc_models:
            wacc_opts = {m.id: f"⚖️ {m.name} (Updated {m.updated_at.strftime('%Y-%m-%d')})" for m in saved_wacc_models}
            selected_wacc_id = st.selectbox(
                "Linked Phase 5 WACC Case *",
                options=list(wacc_opts.keys()),
                format_func=lambda k: wacc_opts[k],
                key="dcf_linked_wacc_select",
            )
        else:
            selected_wacc_id = None
            st.warning("⚠️ No saved Phase 5 WACC cases found for this project. Please configure and save a WACC case in the **WACC** section.")

    # Parse linked model assumptions
    active_fc_assumptions: Optional[ForecastAssumptions] = None
    if selected_fc_id:
        fc_record = next((m for m in saved_forecast_models if m.id == selected_fc_id), None)
        if fc_record:
            try:
                active_fc_assumptions = ForecastAssumptions.from_dict(json.loads(fc_record.assumptions_json))
            except Exception as e:
                st.error(f"Error parsing forecast scenario assumptions: {e}")

    active_wacc_assumptions: Optional[WaccAssumptions] = None
    if selected_wacc_id:
        wacc_record = next((m for m in saved_wacc_models if m.id == selected_wacc_id), None)
        if wacc_record:
            try:
                active_wacc_assumptions = WaccAssumptions.from_json(wacc_record.assumptions_json)
            except Exception as e:
                st.error(f"Error parsing WACC case assumptions: {e}")

    st.markdown("---")

    # 4. DCF Valuation Case Management (Save / Load / Case Selector)
    st.subheader("📁 DCF Valuation Scenario Case")

    saved_dcf_cases = DcfService.list_dcf_models(selected_project_id)
    case_options = {"new": "➕ Create New DCF Case"}
    case_options.update({m.id: f"📂 {m.name} (Updated {m.updated_at.strftime('%Y-%m-%d %H:%M')})" for m in saved_dcf_cases})

    sc_col1, sc_col2 = st.columns([2, 1])
    with sc_col1:
        selected_dcf_key = st.selectbox(
            "Active DCF Valuation Scenario",
            options=list(case_options.keys()),
            format_func=lambda k: case_options[k],
            key="saved_dcf_case_select",
        )

    # State key for DCF assumptions
    state_key = f"dcf_assumptions_{selected_project_id}"
    loaded_case_id_key = f"dcf_loaded_case_id_{selected_project_id}"
    current_loaded_id = st.session_state.get(loaded_case_id_key)

    # Load from database if a saved case is selected
    if selected_dcf_key != "new" and current_loaded_id != selected_dcf_key:
        db_model = DcfService.get_dcf_model(int(selected_dcf_key))
        if db_model:
            try:
                st.session_state[state_key] = DcfAssumptions.from_json(db_model.assumptions_json)
                st.session_state[loaded_case_id_key] = selected_dcf_key
                st.toast(f"Loaded DCF scenario '{db_model.name}'")
            except Exception as e:
                st.error(f"Error loading saved DCF scenario: {e}")
    elif selected_dcf_key == "new" and current_loaded_id != "new":
        st.session_state[state_key] = DcfEngine.create_default_assumptions(
            project_id=selected_project_id,
            forecast_model_id=selected_fc_id,
            wacc_model_id=selected_wacc_id,
            bundle=hist_bundle,
        )
        st.session_state[loaded_case_id_key] = "new"

    # Ensure state initialized
    if state_key not in st.session_state:
        st.session_state[state_key] = DcfEngine.create_default_assumptions(
            project_id=selected_project_id,
            forecast_model_id=selected_fc_id,
            wacc_model_id=selected_wacc_id,
            bundle=hist_bundle,
        )

    assumptions: DcfAssumptions = st.session_state[state_key]
    assumptions.forecast_model_id = selected_fc_id
    assumptions.wacc_model_id = selected_wacc_id

    with sc_col2:
        case_name_input = st.text_input(
            "DCF Scenario Name",
            value=assumptions.name,
            key="dcf_case_name_input",
        )
        assumptions.name = case_name_input.strip() or "Base Case DCF Valuation"

    # Save and Delete controls
    save_col1, save_col2, save_col3 = st.columns([1, 1, 2])
    with save_col1:
        if st.button("💾 Save DCF Case", type="primary", use_container_width=True):
            try:
                saved = DcfService.save_dcf_model(
                    project_id=selected_project_id,
                    name=assumptions.name,
                    assumptions=assumptions,
                    description=assumptions.description,
                )
                st.session_state[loaded_case_id_key] = saved.id
                st.success(f"DCF valuation scenario '{saved.name}' saved successfully!")
                st.rerun()
            except Exception as e:
                st.error(f"Failed to save DCF scenario: {e}")

    with save_col2:
        if selected_dcf_key != "new":
            if st.button("🗑️ Delete Case", type="secondary", use_container_width=True):
                if DcfService.delete_dcf_model(int(selected_dcf_key)):
                    st.session_state[loaded_case_id_key] = "new"
                    st.session_state[state_key] = DcfEngine.create_default_assumptions(
                        project_id=selected_project_id,
                        forecast_model_id=selected_fc_id,
                        wacc_model_id=selected_wacc_id,
                        bundle=hist_bundle,
                    )
                    st.success("DCF scenario deleted.")
                    st.rerun()

    with save_col3:
        if st.button("🔄 Reset Bridge to Balance Sheet Defaults", use_container_width=True):
            assumptions.bridge_inputs = DcfEngine.extract_bridge_defaults(hist_bundle)
            st.rerun()

    st.markdown("---")

    # 5. Preliminary Execution to Populate Headline Metrics
    current_result = DcfEngine.evaluate_dcf(
        assumptions=assumptions,
        forecast_assumptions=active_fc_assumptions,
        wacc_assumptions=active_wacc_assumptions,
        bundle=hist_bundle,
    )

    # 6. Headline Metric Cards
    m1, m2, m3, m4, m5, m6 = st.columns(6)
    with m1:
        share_disp = f"{base_currency} {current_result.implied_value_per_share:,.2f}" if current_result.implied_value_per_share is not None else "[Withheld]"
        st.metric("Implied Value / Share", share_disp, help="Equity Value / Diluted Common Shares Outstanding")
    with m2:
        eq_disp = f"{current_result.equity_value:,.1f}" if current_result.equity_value is not None else "[Withheld]"
        st.metric(f"Equity Value ({base_currency})", eq_disp, help="Enterprise Value + Cash - Debt - Senior Claims")
    with m3:
        ev_disp = f"{current_result.enterprise_value:,.1f}" if current_result.enterprise_value is not None else "[Withheld]"
        st.metric(f"Enterprise Value ({base_currency})", ev_disp, help="PV of Forecast Cash Flows + PV of Terminal Value")
    with m4:
        pv_fc_disp = f"{current_result.pv_forecast_ufcf:,.1f}" if current_result.pv_forecast_ufcf is not None else "[Withheld]"
        st.metric("PV of Forecast UFCF", pv_fc_disp, help="Sum of discounted explicit forecast cash flows")
    with m5:
        pv_tv_disp = f"{current_result.pv_terminal_value:,.1f}" if current_result.pv_terminal_value is not None else "[Withheld]"
        st.metric("PV of Terminal Value", pv_tv_disp, help="Present value of enterprise value beyond the forecast horizon")
    with m6:
        tv_share_disp = f"{current_result.terminal_value_pct_ev:.1f}%" if current_result.terminal_value_pct_ev is not None else "—"
        st.metric("Terminal Value Share", tv_share_disp, help="Percentage of total enterprise value represented by terminal value")

    # 7. Interactive Assumption Tabs
    st.markdown("### 🛠️ Valuation Drivers & Bridge Inputs")

    tab_timing, tab_tv, tab_bridge, tab_schedule = st.tabs([
        "1. Timing & Discounting Convention",
        "2. Terminal Value Methodology",
        "3. Enterprise-to-Equity Bridge",
        "4. Valuation Schedules & Visualizations",
    ])

    # ---------------- TAB 1: TIMING & DISCOUNTING ----------------
    with tab_timing:
        st.subheader("Valuation Anchor & Cash Flow Timing Convention")
        st.caption("Discount Factor = 1 / (1 + WACC)^t")

        col_time1, col_time2 = st.columns(2)

        with col_time1:
            st.markdown("##### Discounting Timing Convention")
            conv_options = [DiscountingConvention.END_OF_YEAR.value, DiscountingConvention.MID_YEAR.value]
            selected_conv = st.radio(
                "Cash Flow Realization Assumption",
                options=conv_options,
                index=conv_options.index(assumptions.discounting_convention) if assumptions.discounting_convention in conv_options else 0,
                format_func=lambda c: DiscountingConvention.display_name(c),
                key="dcf_convention_radio",
                help="End-of-year assumes cash flows materialize at period end; mid-year assumes uniform cash generation throughout the year.",
            )
            assumptions.discounting_convention = selected_conv

            val_date_input = st.text_input(
                "Valuation Anchor Date",
                value=assumptions.valuation_date or "Latest Fiscal Period End",
                key="dcf_valuation_date_input",
                help="Reference date for discounting schedule calibration.",
            )
            assumptions.valuation_date = val_date_input.strip()

        with col_time2:
            st.markdown("##### Discount Rate (WACC) Verification")
            if current_result.wacc_applied is not None:
                st.success(f"**Applied Discount Rate (WACC):** `{current_result.wacc_applied:.2f}%`")
                if active_wacc_assumptions:
                    st.caption(
                        f"Linked Scenario: **{active_wacc_assumptions.name}** | "
                        f"Cost of Equity: `{active_wacc_assumptions.equity_inputs.risk_free_rate or 0 + (active_wacc_assumptions.equity_inputs.equity_beta or 1) * (active_wacc_assumptions.equity_inputs.equity_risk_premium or 5):.2f}%` | "
                        f"Pre-Tax Kd: `{active_wacc_assumptions.debt_inputs.pre_tax_cost_of_debt or 0:.2f}%`"
                    )
            else:
                st.error("⚠️ Discount rate WACC is currently missing or incomplete.")

    # ---------------- TAB 2: TERMINAL VALUE METHODOLOGY ----------------
    with tab_tv:
        st.subheader("Terminal Enterprise Value Methodology")
        st.caption("Captures value generation extending perpetually beyond the explicit forecast horizon.")

        tv_in = assumptions.terminal_inputs

        method_options = [TerminalValueMethod.GORDON_GROWTH.value, TerminalValueMethod.EXIT_MULTIPLE.value]
        selected_tv_method = st.radio(
            "Select Terminal Value Method *",
            options=method_options,
            index=method_options.index(tv_in.method) if tv_in.method in method_options else 0,
            format_func=lambda m: TerminalValueMethod.display_name(m),
            key="dcf_tv_method_radio",
        )
        tv_in.method = selected_tv_method

        col_tv1, col_tv2 = st.columns(2)

        if selected_tv_method == TerminalValueMethod.GORDON_GROWTH.value:
            with col_tv1:
                st.markdown("##### Perpetual Growth Model Inputs")
                g_val = st.number_input(
                    "Perpetual Growth Rate (g, %) *",
                    min_value=-5.0,
                    max_value=10.0,
                    value=float(tv_in.perpetual_growth_rate) if tv_in.perpetual_growth_rate is not None else 2.50,
                    step=0.25,
                    format="%.2f",
                    key="dcf_gordon_g_input",
                    help="Sustainable long-term growth rate in perpetuity. Must be strictly less than WACC.",
                )
                tv_in.perpetual_growth_rate = g_val

                g_prov = st.text_input(
                    "Growth Rate Citation / Benchmark Note",
                    value=tv_in.growth_provenance.source_reference or "",
                    placeholder="e.g. Long-term Sovereign GDP Growth Benchmark",
                    key="dcf_g_note",
                )
                tv_in.growth_provenance.source_reference = g_prov

            with col_tv2:
                st.markdown("##### Gordon Growth Formulation")
                st.latex(r"\text{Terminal Value} = \frac{\text{UFCF}_N \times (1 + g)}{\text{WACC} - g}")
                if current_result.terminal_result and current_result.terminal_result.formula_display:
                    st.info(f"**Calculation Bridge:** `{current_result.terminal_result.formula_display}`")

        else:
            with col_tv1:
                st.markdown("##### Exit Multiple Inputs")
                mult_val = st.number_input(
                    "Terminal EV / EBITDA Multiple (x) *",
                    min_value=0.0,
                    max_value=50.0,
                    value=float(tv_in.exit_multiple) if tv_in.exit_multiple is not None else 10.0,
                    step=0.5,
                    format="%.1f",
                    key="dcf_exit_mult_input",
                    help="Implied exit enterprise multiple applied to final explicit forecast year EBITDA.",
                )
                tv_in.exit_multiple = mult_val

                mult_prov = st.text_input(
                    "Exit Multiple Citation / Peer Group Note",
                    value=tv_in.multiple_provenance.source_reference or "",
                    placeholder="e.g. Median Peer Group Forward EV/EBITDA Multiple",
                    key="dcf_mult_note",
                )
                tv_in.multiple_provenance.source_reference = mult_prov

            with col_tv2:
                st.markdown("##### Exit Multiple Formulation")
                st.latex(r"\text{Terminal Value} = \text{Terminal EBITDA}_N \times \text{Exit Multiple}")
                if current_result.terminal_result and current_result.terminal_result.formula_display:
                    st.info(f"**Calculation Bridge:** `{current_result.terminal_result.formula_display}`")

    # ---------------- TAB 3: ENTERPRISE-TO-EQUITY BRIDGE ----------------
    with tab_bridge:
        st.subheader("Enterprise Value to Equity Value Bridge")
        st.caption("Equity Value = Enterprise Value + Cash - Debt - Minority Interest - Preferred Equity + Other Adjustments")

        b_in = assumptions.bridge_inputs

        col_b1, col_b2 = st.columns(2)

        with col_b1:
            st.markdown(f"##### (+) Cash & (-) Debt Claims [{base_currency}]")

            cash_val = st.number_input(
                f"Cash and Cash Equivalents (+ Add) *",
                min_value=0.0,
                max_value=1e12,
                value=float(b_in.cash_and_equivalents) if b_in.cash_and_equivalents is not None else 0.0,
                step=10.0,
                format="%.2f",
                key="dcf_cash_input",
                help="Unrestricted cash and liquid short-term investments available to common shareholders.",
            )
            b_in.cash_and_equivalents = cash_val

            debt_val = st.number_input(
                f"Interest-Bearing Debt Balance (- Deduct) *",
                min_value=0.0,
                max_value=1e12,
                value=float(b_in.debt_value) if b_in.debt_value is not None else 0.0,
                step=10.0,
                format="%.2f",
                key="dcf_debt_input",
                help="Total short-term and long-term borrowings. Excludes non-interest operating liabilities.",
            )
            b_in.debt_value = debt_val

            net_debt_disp = debt_val - cash_val
            st.info(f"**Implied Net Debt Impact (Debt - Cash):** `{net_debt_disp:,.2f} {base_currency}`")

        with col_b2:
            st.markdown(f"##### Senior Claims & Non-Operating Adjustments [{base_currency}]")

            mi_val = st.number_input(
                "Minority Interest / Non-Controlling Claims (- Deduct)",
                min_value=0.0,
                max_value=1e12,
                value=float(b_in.minority_interest) if b_in.minority_interest is not None else 0.0,
                step=5.0,
                format="%.2f",
                key="dcf_mi_input",
            )
            b_in.minority_interest = mi_val

            pe_val = st.number_input(
                "Preferred Stock / Equity Claims (- Deduct)",
                min_value=0.0,
                max_value=1e12,
                value=float(b_in.preferred_equity) if b_in.preferred_equity is not None else 0.0,
                step=5.0,
                format="%.2f",
                key="dcf_pe_input",
            )
            b_in.preferred_equity = pe_val

            adj_val = st.number_input(
                "Other Non-Operating Adjustments (+/- Signed Amount)",
                min_value=-1e12,
                max_value=1e12,
                value=float(b_in.other_adjustments) if b_in.other_adjustments is not None else 0.0,
                step=5.0,
                format="%.2f",
                key="dcf_adj_input",
                help="Associates, non-operating assets, pension deficits, litigation reserves.",
            )
            b_in.other_adjustments = adj_val

        st.markdown("---")
        st.markdown("##### Diluted Common Shares Outstanding")
        col_sh1, col_sh2 = st.columns([1, 1])
        with col_sh1:
            shares_val = st.number_input(
                f"Diluted Shares Outstanding ({hist_bundle.display_unit if hist_bundle else 'units'}) *",
                min_value=0.0,
                max_value=1e12,
                value=float(assumptions.diluted_shares) if assumptions.diluted_shares is not None else 100.0,
                step=1.0,
                format="%.2f",
                key="dcf_shares_input",
                help="Diluted common shares outstanding used to compute intrinsic per-share value.",
            )
            assumptions.diluted_shares = shares_val

        with col_sh2:
            shares_prov = st.text_input(
                "Share Count Provenance / SEC Filing Reference",
                value=assumptions.shares_provenance.source_reference or "",
                placeholder="e.g. 10-K Weighted Average Diluted Common Shares",
                key="dcf_shares_note",
            )
            assumptions.shares_provenance.source_reference = shares_prov

    # ---------------- TAB 4: VALUATION TABLES & CHARTS ----------------
    with tab_schedule:
        st.subheader("Valuation Schedules & Visual Breakdown")

        if current_result.is_complete:
            # Visual Charts
            ch_col1, ch_col2 = st.columns([3, 2])
            with ch_col1:
                cf_chart = create_cash_flow_discounting_chart(current_result, currency=base_currency)
                if cf_chart:
                    st.plotly_chart(cf_chart, use_container_width=True)

            with ch_col2:
                ev_donut = create_ev_composition_donut_chart(current_result)
                if ev_donut:
                    st.plotly_chart(ev_donut, use_container_width=True)

            # Cash Flow Discounting Schedule Table
            st.markdown("#### 📅 Projected Cash Flow Discounting Schedule")
            schedule_df = build_discounting_schedule_dataframe(
                current_result,
                currency=base_currency,
                unit=hist_bundle.display_unit if hist_bundle else "units",
            )
            st.dataframe(schedule_df, hide_index=True, use_container_width=True)

            # Enterprise-to-Equity Bridge Table
            st.markdown("#### 🌉 Enterprise Value to Equity Value Bridge")
            bridge_df = build_equity_bridge_dataframe(
                current_result,
                currency=base_currency,
                unit=hist_bundle.display_unit if hist_bundle else "units",
            )
            st.dataframe(bridge_df, hide_index=True, use_container_width=True)

        else:
            st.error("⚠️ DCF Valuation is currently withheld due to missing or invalid inputs.")
            st.markdown("**Missing / Incomplete Requirements:**")
            for item in current_result.missing_inputs:
                st.markdown(f"- ❌ `{item}`")

    # 8. Model Audit Warnings Area
    if current_result.warnings:
        st.markdown("---")
        st.subheader("⚠️ Model Audit & Diagnostics Warnings")
        for warn in current_result.warnings:
            st.warning(warn)

    st.markdown("---")
    st.caption(f"🔒 {current_result.limitations_disclaimer}")
