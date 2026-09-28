"""Sensitivity Analysis and Monte Carlo Simulation Streamlit Interface.

Provides two-dimensional sensitivity matrices (WACC vs. Perpetual Growth / Exit Multiple)
and reproducible Monte Carlo probabilistic valuation distributions.
"""

from __future__ import annotations

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
from src.sensitivity.engine import SensitivityEngine
from src.sensitivity.formatting import (
    build_monte_carlo_stats_dataframe,
    build_sensitivity_matrix_dataframe,
    create_monte_carlo_histogram,
    create_sensitivity_heatmap_chart,
)
from src.sensitivity.models import (
    AxisRangeConfig,
    DistributionConfig,
    DistributionType,
    MonteCarloSimulationResult,
    SensitivityConfig,
    SensitivityMatrixResult,
    SensitivityMetric,
)
from src.sensitivity.services import SensitivityService
from src.wacc.engine import WaccEngine
from src.wacc.models import WaccAssumptions
from src.wacc.services import WaccService


def render_sensitivity_page() -> None:
    """Render the Sensitivity Analysis and Monte Carlo Simulation application page."""
    st.header("🎯 Sensitivity Analysis & Simulation Engine")
    st.markdown(
        "Evaluate valuation sensitivity across multidimensional driver shifts. "
        "Explore **Two-Dimensional Sensitivity Matrices** (WACC vs. Terminal Growth or Exit Multiple) "
        "and run **Monte Carlo Probabilistic Simulations** with user-configured statistical distributions. "
        "All outputs reuse the validated Phase 4 forecast, Phase 5 WACC, and Phase 6 DCF calculation engines."
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
            key="sens_project_select",
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

    # 3. Model Dependencies: Select Saved Baseline DCF Model
    st.subheader("🔗 Baseline DCF Model Dependency")

    saved_dcf_models = DcfService.list_dcf_models(selected_project_id)
    col_dcf_sel, col_dcf_btn = st.columns([3, 1])

    with col_dcf_sel:
        if saved_dcf_models:
            dcf_opts = {m.id: f"💰 {m.name} (Updated {m.updated_at.strftime('%Y-%m-%d')})" for m in saved_dcf_models}
            selected_dcf_id = st.selectbox(
                "Baseline DCF Valuation Case *",
                options=list(dcf_opts.keys()),
                format_func=lambda k: dcf_opts[k],
                key="sens_linked_dcf_select",
                help="Sensitivity analysis sensitizes parameters against this saved DCF case.",
            )
        else:
            selected_dcf_id = None
            st.warning("⚠️ No saved Phase 6 DCF models found for this project. Please build and save a DCF case in the **DCF Valuation** section first.")

    with col_dcf_btn:
        st.write("")
        st.write("")
        if st.button("🔙 Open DCF Valuation Page", key="btn_sens_to_dcf"):
            st.session_state["app_nav_selection"] = "DCF Valuation"
            st.rerun()

    if not selected_dcf_id:
        st.stop()

    # Load baseline DCF model and its dependencies
    dcf_record = DcfService.get_dcf_model(selected_dcf_id)
    if not dcf_record:
        st.error("Selected DCF model could not be found.")
        st.stop()

    try:
        base_dcf_assumptions = DcfAssumptions.from_json(dcf_record.assumptions_json)
    except Exception as e:
        st.error(f"Error parsing DCF model assumptions: {e}")
        st.stop()

    # Resolve linked forecast and WACC models
    if not base_dcf_assumptions.forecast_model_id or not base_dcf_assumptions.wacc_model_id:
        st.error(
            "The selected DCF model does not have linked Forecast and WACC models configured. "
            "Please open the DCF page and link valid Forecast and WACC cases."
        )
        st.stop()

    fc_record = ForecastService.get_forecast_model(base_dcf_assumptions.forecast_model_id)
    wacc_record = WaccService.get_wacc_model(base_dcf_assumptions.wacc_model_id)

    if not fc_record or not wacc_record:
        st.error("One or more linked dependency models (Forecast or WACC) have been deleted or cannot be resolved.")
        st.stop()

    try:
        base_fc_assumptions = ForecastAssumptions.from_dict(json.loads(fc_record.assumptions_json))
        base_wacc_assumptions = WaccAssumptions.from_json(wacc_record.assumptions_json)
    except Exception as e:
        st.error(f"Error parsing linked Forecast or WACC assumptions: {e}")
        st.stop()

    # Resolve baseline WACC
    wacc_eval = WaccEngine.estimate_wacc(base_wacc_assumptions)
    if not wacc_eval.is_complete or wacc_eval.wacc is None:
        st.error(f"Linked WACC model '{wacc_record.name}' contains incomplete or invalid parameters.")
        st.stop()
    base_wacc_val = wacc_eval.wacc

    term_method = base_dcf_assumptions.terminal_inputs.method
    is_gordon = term_method == TerminalValueMethod.GORDON_GROWTH.value
    base_term_val = (
        base_dcf_assumptions.terminal_inputs.perpetual_growth_rate or 2.50
        if is_gordon
        else base_dcf_assumptions.terminal_inputs.exit_multiple or 10.0
    )

    st.markdown("---")

    # 4. Sensitivity Configuration Set Management (Save / Load)
    st.subheader("📁 Sensitivity & Simulation Set (Save / Load)")

    saved_sens_configs = SensitivityService.list_sensitivity_models(selected_project_id)
    cfg_options = {"new": "➕ Create New Sensitivity Set"}
    cfg_options.update({m.id: f"📂 {m.name} (Updated {m.updated_at.strftime('%Y-%m-%d %H:%M')})" for m in saved_sens_configs})

    sc_col1, sc_col2 = st.columns([2, 1])
    with sc_col1:
        selected_cfg_key = st.selectbox(
            "Active Sensitivity Configuration Set",
            options=list(cfg_options.keys()),
            format_func=lambda k: cfg_options[k],
            key="saved_sens_set_select",
        )

    state_key = f"sensitivity_config_{selected_project_id}"
    loaded_cfg_id_key = f"sens_loaded_id_{selected_project_id}"
    current_loaded_id = st.session_state.get(loaded_cfg_id_key)

    if selected_cfg_key != "new" and current_loaded_id != selected_cfg_key:
        db_cfg = SensitivityService.get_sensitivity_model(int(selected_cfg_key))
        if db_cfg:
            try:
                st.session_state[state_key] = SensitivityConfig.from_json(db_cfg.config_json)
                st.session_state[loaded_cfg_id_key] = selected_cfg_key
                st.toast(f"Loaded sensitivity configuration '{db_cfg.name}'")
            except Exception as e:
                st.error(f"Error loading saved sensitivity configuration: {e}")
    elif selected_cfg_key == "new" and current_loaded_id != "new":
        # Create default config matching current baseline
        st.session_state[state_key] = SensitivityConfig(
            name=f"{dcf_record.name} - Sensitivity Analysis",
            description="Sensitivity matrix and Monte Carlo simulation configuration.",
            project_id=selected_project_id,
            dcf_model_id=selected_dcf_id,
            wacc_range=AxisRangeConfig(
                base_val=round(base_wacc_val, 2),
                min_val=max(1.0, round(base_wacc_val - 1.5, 1)),
                max_val=round(base_wacc_val + 1.5, 1),
                step=0.5,
            ),
            terminal_range=AxisRangeConfig(
                base_val=round(base_term_val, 2),
                min_val=max(0.5, round(base_term_val - 1.0, 1)) if is_gordon else max(2.0, round(base_term_val - 3.0, 1)),
                max_val=round(base_term_val + 1.0, 1) if is_gordon else round(base_term_val + 3.0, 1),
                step=0.25 if is_gordon else 1.0,
            ),
            wacc_dist=DistributionConfig(
                dist_type=DistributionType.NORMAL.value,
                mean=round(base_wacc_val, 2),
                std_dev=0.5,
            ),
            terminal_param_dist=DistributionConfig(
                dist_type=DistributionType.TRIANGULAR.value,
                min_val=max(0.5, round(base_term_val - 1.0, 1)),
                mode_val=round(base_term_val, 2),
                max_val=round(base_term_val + 1.0, 1),
            ) if is_gordon else DistributionConfig(
                dist_type=DistributionType.TRIANGULAR.value,
                min_val=max(2.0, round(base_term_val - 3.0, 1)),
                mode_val=round(base_term_val, 2),
                max_val=round(base_term_val + 3.0, 1),
            ),
        )
        st.session_state[loaded_cfg_id_key] = "new"

    if state_key not in st.session_state:
        st.session_state[state_key] = SensitivityConfig(
            name=f"{dcf_record.name} - Sensitivity Analysis",
            project_id=selected_project_id,
            dcf_model_id=selected_dcf_id,
            wacc_range=AxisRangeConfig(
                base_val=round(base_wacc_val, 2),
                min_val=max(1.0, round(base_wacc_val - 1.5, 1)),
                max_val=round(base_wacc_val + 1.5, 1),
                step=0.5,
            ),
            terminal_range=AxisRangeConfig(
                base_val=round(base_term_val, 2),
                min_val=max(0.5, round(base_term_val - 1.0, 1)) if is_gordon else max(2.0, round(base_term_val - 3.0, 1)),
                max_val=round(base_term_val + 1.0, 1) if is_gordon else round(base_term_val + 3.0, 1),
                step=0.25 if is_gordon else 1.0,
            ),
            wacc_dist=DistributionConfig(
                dist_type=DistributionType.NORMAL.value,
                mean=round(base_wacc_val, 2),
                std_dev=0.5,
            ),
            terminal_param_dist=DistributionConfig(
                dist_type=DistributionType.TRIANGULAR.value,
                min_val=max(0.5, round(base_term_val - 1.0, 1)),
                mode_val=round(base_term_val, 2),
                max_val=round(base_term_val + 1.0, 1),
            ) if is_gordon else DistributionConfig(
                dist_type=DistributionType.TRIANGULAR.value,
                min_val=max(2.0, round(base_term_val - 3.0, 1)),
                mode_val=round(base_term_val, 2),
                max_val=round(base_term_val + 3.0, 1),
            ),
        )

    sens_cfg: SensitivityConfig = st.session_state[state_key]
    sens_cfg.dcf_model_id = selected_dcf_id
    sens_cfg.project_id = selected_project_id

    st.markdown("---")

    # 5. Core Interface Tabs
    tab_matrix, tab_simulation, tab_audit, tab_save = st.tabs([
        "📊 Two-Dimensional Sensitivity Matrix",
        "🎲 Monte Carlo Simulation",
        "🔍 Assumptions & Audit Bridge",
        "💾 Save & Manage Configuration",
    ])

    # ---------------- TAB 1: 2D SENSITIVITY MATRIX ----------------
    with tab_matrix:
        st.subheader("Two-Dimensional Valuation Sensitivity Matrix")
        st.markdown(
            "Evaluate DCF intrinsic valuation across varying combinations of **Discount Rate (WACC)** "
            f"and **{('Perpetual Growth Rate (g)' if is_gordon else 'Exit Multiple')}**. "
            "All other assumptions (cash flows, timing convention, debt, cash, and share count) are held fixed at baseline."
        )

        col_m1, col_m2, col_m3 = st.columns([2, 2, 2])

        with col_m1:
            metric_choice = st.selectbox(
                "Evaluated Valuation Metric *",
                options=[
                    SensitivityMetric.IMPLIED_SHARE_PRICE.value,
                    SensitivityMetric.EQUITY_VALUE.value,
                    SensitivityMetric.ENTERPRISE_VALUE.value,
                ],
                format_func=lambda v: SensitivityMetric.display_name(v),
                index=0,
                key="sens_metric_select",
            )
            sens_cfg.metric = metric_choice

        # Axis Ranges Configuration
        st.markdown("##### 🎛️ Matrix Axis Ranges & Step Sizes")
        col_ax1, col_ax2 = st.columns(2)

        with col_ax1:
            st.markdown(f"**Row Axis: Discount Rate / WACC (%)** *(Baseline: `{base_wacc_val:.2f}%`)*")
            w_range = sens_cfg.wacc_range or AxisRangeConfig(base_wacc_val, base_wacc_val - 1.5, base_wacc_val + 1.5, 0.5)
            w_range.base_val = round(base_wacc_val, 2)

            sub_w1, sub_w2, sub_w3 = st.columns(3)
            with sub_w1:
                w_min = st.number_input("WACC Min (%)", min_value=0.5, max_value=40.0, value=float(w_range.min_val), step=0.25, format="%.2f", key="sens_w_min")
            with sub_w2:
                w_max = st.number_input("WACC Max (%)", min_value=w_min + 0.25, max_value=50.0, value=max(float(w_range.max_val), float(w_min) + 0.5), step=0.25, format="%.2f", key="sens_w_max")
            with sub_w3:
                w_step = st.number_input("WACC Step (%)", min_value=0.1, max_value=5.0, value=float(w_range.step), step=0.1, format="%.2f", key="sens_w_step")

            w_range.min_val = w_min
            w_range.max_val = w_max
            w_range.step = w_step
            sens_cfg.wacc_range = w_range
            wacc_axis_values = w_range.generate_values()

        with col_ax2:
            term_label = "Perpetual Growth Rate (g %)" if is_gordon else "Exit Multiple (x EBITDA)"
            st.markdown(f"**Column Axis: {term_label}** *(Baseline: `{base_term_val:.2f}{'%' if is_gordon else 'x'}`)*")
            t_range = sens_cfg.terminal_range or AxisRangeConfig(
                base_term_val,
                base_term_val - 1.0 if is_gordon else base_term_val - 3.0,
                base_term_val + 1.0 if is_gordon else base_term_val + 3.0,
                0.25 if is_gordon else 1.0,
            )
            t_range.base_val = round(base_term_val, 2)

            sub_t1, sub_t2, sub_t3 = st.columns(3)
            with sub_t1:
                t_min = st.number_input(f"{'g' if is_gordon else 'Multiple'} Min", min_value=-5.0 if is_gordon else 0.5, max_value=30.0, value=float(t_range.min_val), step=0.1 if is_gordon else 0.5, format="%.2f", key="sens_t_min")
            with sub_t2:
                t_max = st.number_input(f"{'g' if is_gordon else 'Multiple'} Max", min_value=t_min + 0.1, max_value=40.0, value=max(float(t_range.max_val), float(t_min) + 0.5), step=0.1 if is_gordon else 0.5, format="%.2f", key="sens_t_max")
            with sub_t3:
                t_step = st.number_input(f"{'g' if is_gordon else 'Multiple'} Step", min_value=0.05 if is_gordon else 0.25, max_value=10.0, value=float(t_range.step), step=0.05 if is_gordon else 0.25, format="%.2f", key="sens_t_step")

            t_range.min_val = t_min
            t_range.max_val = t_max
            t_range.step = t_step
            sens_cfg.terminal_range = t_range
            term_axis_values = t_range.generate_values()

        # Execute 2D Sensitivity Matrix calculation
        try:
            matrix_result: SensitivityMatrixResult = SensitivityEngine.compute_sensitivity_matrix(
                base_dcf_assumptions=base_dcf_assumptions,
                base_fc_assumptions=base_fc_assumptions,
                base_wacc_val=base_wacc_val,
                bundle=hist_bundle,
                wacc_values=wacc_axis_values,
                terminal_values=term_axis_values,
                metric=metric_choice,
                dcf_model_name=dcf_record.name,
            )
        except Exception as exc:
            st.error(f"Error calculating sensitivity matrix: {exc}")
            matrix_result = None

        if matrix_result:
            st.markdown("---")

            # Heatmap Visual
            heatmap_fig = create_sensitivity_heatmap_chart(matrix_result, currency=base_currency)
            if heatmap_fig:
                st.plotly_chart(heatmap_fig, use_container_width=True)

            # Tabular Matrix
            st.markdown("##### 📋 Tabular Valuation Matrix")
            st.caption("Values marked with **★** indicate the baseline model combination. Invalid cells are clearly labeled.")
            matrix_df = build_sensitivity_matrix_dataframe(
                matrix_result,
                currency=base_currency,
                unit=hist_bundle.display_unit if hist_bundle else "millions",
            )
            st.dataframe(matrix_df, hide_index=True, use_container_width=True)

            # Validity Legend & CSV Download
            col_leg, col_dl = st.columns([3, 1])
            with col_leg:
                st.markdown(
                    """
                    **Legend & Diagnostics:**
                    - `★`: Exact or nearest intersection of the baseline model assumptions.
                    - `[Invalid: WACC <= g]`: Gordon Growth Perpetuity denominator $(WACC - g)$ is non-positive. Outputs are safely withheld.
                    """
                )
            with col_dl:
                csv_bytes = matrix_df.to_csv(index=False).encode("utf-8")
                st.download_button(
                    label="📥 Download Matrix (CSV)",
                    data=csv_bytes,
                    file_name=f"sensitivity_matrix_{selected_project_id}.csv",
                    mime="text/csv",
                    key="dl_matrix_csv",
                )

    # ---------------- TAB 2: MONTE CARLO SIMULATION ----------------
    with tab_simulation:
        st.subheader("Monte Carlo Probabilistic Valuation Simulation")
        st.markdown(
            "Execute random sampling across operational and financial drivers to evaluate the empirical distribution "
            "of implied enterprise value, equity value, and per-share price targets. "
            "All simulations are **100% reproducible** via user-controlled random seeds."
        )

        col_sc1, col_sc2 = st.columns([1, 1])
        with col_sc1:
            iterations_val = st.slider(
                "Simulation Iterations *",
                min_value=50,
                max_value=2000,
                value=int(sens_cfg.iterations),
                step=50,
                key="mc_iter_slider",
                help="Higher iterations yield smoother empirical distributions with a safe upper limit to prevent execution latency.",
            )
            sens_cfg.iterations = iterations_val

        with col_sc2:
            seed_val = st.number_input(
                "Random Number Generator Seed *",
                min_value=0,
                max_value=999999,
                value=int(sens_cfg.random_seed),
                step=1,
                key="mc_seed_input",
                help="A fixed seed guarantees identical, deterministic simulation results.",
            )
            sens_cfg.random_seed = seed_val

        st.markdown("##### 🎲 Input Distribution Calibration")
        st.caption("Select which drivers to randomize. Non-selected variables remain locked at baseline values.")

        dist_types_list = [DistributionType.TRIANGULAR.value, DistributionType.NORMAL.value, DistributionType.UNIFORM.value]

        # 1. Revenue Growth
        col_rg_chk, col_rg_cfg = st.columns([1, 3])
        with col_rg_chk:
            sim_rg = st.checkbox("Simulate Revenue Growth Delta (pp)", value=sens_cfg.simulate_revenue_growth, key="mc_chk_rg")
            sens_cfg.simulate_revenue_growth = sim_rg
        with col_rg_cfg:
            if sim_rg:
                rg_d = sens_cfg.revenue_growth_dist
                c1, c2, c3, c4 = st.columns(4)
                with c1:
                    rg_t = st.selectbox("Distribution Type", options=dist_types_list, index=dist_types_list.index(rg_d.dist_type), format_func=lambda v: DistributionType.display_name(v), key="mc_rg_type")
                    rg_d.dist_type = rg_t
                if rg_t == DistributionType.NORMAL.value:
                    with c2:
                        rg_d.mean = st.number_input("Mean Delta (pp)", value=float(rg_d.mean), step=0.25, format="%.2f", key="mc_rg_mean")
                    with c3:
                        rg_d.std_dev = st.number_input("Std Dev (pp)", min_value=0.01, value=max(0.01, float(rg_d.std_dev)), step=0.25, format="%.2f", key="mc_rg_std")
                else:
                    with c2:
                        rg_d.min_val = st.number_input("Min Delta (pp)", value=float(rg_d.min_val), step=0.25, format="%.2f", key="mc_rg_min")
                    with c3:
                        rg_d.mode_val = st.number_input("Mode Delta (pp)", value=float(rg_d.mode_val), step=0.25, format="%.2f", key="mc_rg_mode") if rg_t == DistributionType.TRIANGULAR.value else rg_d.min_val
                    with c4:
                        rg_d.max_val = st.number_input("Max Delta (pp)", value=float(rg_d.max_val), step=0.25, format="%.2f", key="mc_rg_max")

        # 2. Operating Margin
        col_om_chk, col_om_cfg = st.columns([1, 3])
        with col_om_chk:
            sim_om = st.checkbox("Simulate Operating Margin Delta (pp)", value=sens_cfg.simulate_operating_margin, key="mc_chk_om")
            sens_cfg.simulate_operating_margin = sim_om
        with col_om_cfg:
            if sim_om:
                om_d = sens_cfg.operating_margin_dist
                c1, c2, c3, c4 = st.columns(4)
                with c1:
                    om_t = st.selectbox("Distribution Type", options=dist_types_list, index=dist_types_list.index(om_d.dist_type), format_func=lambda v: DistributionType.display_name(v), key="mc_om_type")
                    om_d.dist_type = om_t
                if om_t == DistributionType.NORMAL.value:
                    with c2:
                        om_d.mean = st.number_input("Mean Delta (pp)", value=float(om_d.mean), step=0.25, format="%.2f", key="mc_om_mean")
                    with c3:
                        om_d.std_dev = st.number_input("Std Dev (pp)", min_value=0.01, value=max(0.01, float(om_d.std_dev)), step=0.25, format="%.2f", key="mc_om_std")
                else:
                    with c2:
                        om_d.min_val = st.number_input("Min Delta (pp)", value=float(om_d.min_val), step=0.25, format="%.2f", key="mc_om_min")
                    with c3:
                        om_d.mode_val = st.number_input("Mode Delta (pp)", value=float(om_d.mode_val), step=0.25, format="%.2f", key="mc_om_mode") if om_t == DistributionType.TRIANGULAR.value else om_d.min_val
                    with c4:
                        om_d.max_val = st.number_input("Max Delta (pp)", value=float(om_d.max_val), step=0.25, format="%.2f", key="mc_om_max")

        # 3. WACC
        col_w_chk, col_w_cfg = st.columns([1, 3])
        with col_w_chk:
            sim_w = st.checkbox("Simulate WACC Discount Rate (%)", value=sens_cfg.simulate_wacc, key="mc_chk_w")
            sens_cfg.simulate_wacc = sim_w
        with col_w_cfg:
            if sim_w:
                w_d = sens_cfg.wacc_dist
                c1, c2, c3, c4 = st.columns(4)
                with c1:
                    w_t = st.selectbox("Distribution Type", options=dist_types_list, index=dist_types_list.index(w_d.dist_type), format_func=lambda v: DistributionType.display_name(v), key="mc_w_type")
                    w_d.dist_type = w_t
                if w_t == DistributionType.NORMAL.value:
                    with c2:
                        w_d.mean = st.number_input("Mean WACC (%)", value=float(w_d.mean or base_wacc_val), step=0.25, format="%.2f", key="mc_w_mean")
                    with c3:
                        w_d.std_dev = st.number_input("Std Dev (pp)", min_value=0.01, value=max(0.01, float(w_d.std_dev)), step=0.1, format="%.2f", key="mc_w_std")
                else:
                    with c2:
                        w_d.min_val = st.number_input("Min WACC (%)", min_value=0.1, value=float(w_d.min_val), step=0.25, format="%.2f", key="mc_w_min")
                    with c3:
                        w_d.mode_val = st.number_input("Mode WACC (%)", min_value=0.1, value=float(w_d.mode_val), step=0.25, format="%.2f", key="mc_w_mode") if w_t == DistributionType.TRIANGULAR.value else w_d.min_val
                    with c4:
                        w_d.max_val = st.number_input("Max WACC (%)", min_value=0.1, value=float(w_d.max_val), step=0.25, format="%.2f", key="mc_w_max")

        # 4. Terminal Assumption
        col_tp_chk, col_tp_cfg = st.columns([1, 3])
        with col_tp_chk:
            sim_tp = st.checkbox(f"Simulate {'Gordon Growth (g %)' if is_gordon else 'Exit Multiple (x)'}", value=sens_cfg.simulate_terminal_param, key="mc_chk_tp")
            sens_cfg.simulate_terminal_param = sim_tp
        with col_tp_cfg:
            if sim_tp:
                tp_d = sens_cfg.terminal_param_dist
                c1, c2, c3, c4 = st.columns(4)
                with c1:
                    tp_t = st.selectbox("Distribution Type", options=dist_types_list, index=dist_types_list.index(tp_d.dist_type), format_func=lambda v: DistributionType.display_name(v), key="mc_tp_type")
                    tp_d.dist_type = tp_t
                if tp_t == DistributionType.NORMAL.value:
                    with c2:
                        tp_d.mean = st.number_input("Mean", value=float(tp_d.mean or base_term_val), step=0.1 if is_gordon else 0.5, format="%.2f", key="mc_tp_mean")
                    with c3:
                        tp_d.std_dev = st.number_input("Std Dev", min_value=0.01, value=max(0.01, float(tp_d.std_dev)), step=0.1, format="%.2f", key="mc_tp_std")
                else:
                    with c2:
                        tp_d.min_val = st.number_input("Min", value=float(tp_d.min_val), step=0.1 if is_gordon else 0.5, format="%.2f", key="mc_tp_min")
                    with c3:
                        tp_d.mode_val = st.number_input("Mode", value=float(tp_d.mode_val), step=0.1 if is_gordon else 0.5, format="%.2f", key="mc_tp_mode") if tp_t == DistributionType.TRIANGULAR.value else tp_d.min_val
                    with c4:
                        tp_d.max_val = st.number_input("Max", value=float(tp_d.max_val), step=0.1 if is_gordon else 0.5, format="%.2f", key="mc_tp_max")

        st.markdown("---")

        # Action: Run Simulation
        sim_run_btn = st.button("🚀 Run Monte Carlo Simulation", type="primary", key="btn_run_mc")

        mc_result_key = f"mc_result_{selected_project_id}"

        if sim_run_btn:
            with st.spinner(f"Executing {sens_cfg.iterations} Monte Carlo iterations with seed {sens_cfg.random_seed}..."):
                try:
                    sim_result: MonteCarloSimulationResult = SensitivityEngine.run_monte_carlo_simulation(
                        base_dcf_assumptions=base_dcf_assumptions,
                        base_fc_assumptions=base_fc_assumptions,
                        base_wacc_assumptions=base_wacc_assumptions,
                        bundle=hist_bundle,
                        config=sens_cfg,
                    )
                    st.session_state[mc_result_key] = sim_result
                    st.toast(f"Completed {sim_result.valid_iterations} valid simulation iterations!")
                except Exception as exc:
                    st.error(f"Simulation failed: {exc}")

        # Display Simulation Results if available
        cached_sim: Optional[MonteCarloSimulationResult] = st.session_state.get(mc_result_key)

        if cached_sim:
            st.markdown("### 📊 Simulation Output & Distribution Analysis")

            # Metrics Banner
            c_iter1, c_iter2, c_iter3, c_iter4 = st.columns(4)
            with c_iter1:
                st.metric("Total Iterations", f"{cached_sim.total_iterations:,}")
            with c_iter2:
                st.metric("Valid Draws", f"{cached_sim.valid_iterations:,}")
            with c_iter3:
                st.metric("Invalid Draws", f"{cached_sim.invalid_iterations:,}")
            with c_iter4:
                rate = (cached_sim.valid_iterations / cached_sim.total_iterations * 100.0) if cached_sim.total_iterations else 0.0
                st.metric("Valid Rate (%)", f"{rate:.1f}%")

            if cached_sim.invalid_iterations > 0:
                with st.expander(f"⚠️ Invalid Draws Breakdown ({cached_sim.invalid_iterations} Draws Excluded)", expanded=False):
                    for reason, cnt in cached_sim.invalid_reasons.items():
                        st.write(f"• `{reason}`: **{cnt} draws** ({cnt / cached_sim.total_iterations * 100.0:.1f}%)")

            # Statistical Summary Table
            st.markdown("##### 📋 Summary Percentile Statistics")
            stats_df = build_monte_carlo_stats_dataframe(
                cached_sim,
                currency=base_currency,
                unit=hist_bundle.display_unit if hist_bundle else "millions",
            )
            st.dataframe(stats_df, hide_index=True, use_container_width=True)

            # Histogram Visual
            st.markdown("##### 📈 Valuation Distribution Histogram")
            hist_metric_choice = st.radio(
                "Display Metric Distribution",
                options=["share_price", "enterprise_value", "equity_value"],
                format_func=lambda k: {
                    "share_price": "Implied Value per Share",
                    "enterprise_value": "Enterprise Value (EV)",
                    "equity_value": "Equity Value",
                }[k],
                horizontal=True,
                key="mc_hist_metric_radio",
            )

            hist_fig = create_monte_carlo_histogram(cached_sim, metric_type=hist_metric_choice, currency=base_currency)
            if hist_fig:
                st.plotly_chart(hist_fig, use_container_width=True)

            st.caption(f"🔒 {cached_sim.disclaimer}")
        else:
            st.info("ℹ️ Click **Run Monte Carlo Simulation** above to sample the configured distributions and generate empirical valuation statistics.")

    # ---------------- TAB 3: ASSUMPTIONS & AUDIT BRIDGE ----------------
    with tab_audit:
        st.subheader("Assumptions Audit & Model Provenance")
        st.markdown(
            "Traceability log disclosing baseline model references, sensitized parameters, "
            "active probability distributions, and held-constant assumptions."
        )

        st.markdown("#### 🔗 Linked Baseline Model Provenance")
        p_c1, p_c2, p_c3 = st.columns(3)
        with p_c1:
            st.write(f"• **DCF Model:** `{dcf_record.name}` (ID: {dcf_record.id})")
            st.write(f"• **Terminal Value Method:** `{term_method.replace('_', ' ').title()}`")
        with p_c2:
            st.write(f"• **Forecast Scenario:** `{fc_record.name}` (ID: {fc_record.id})")
            st.write(f"• **Forecast Horizon:** `{base_fc_assumptions.horizon_years} Years`")
        with p_c3:
            st.write(f"• **WACC Case:** `{wacc_record.name}` (ID: {wacc_record.id})")
            st.write(f"• **Baseline Discount Rate:** `{base_wacc_val:.2f}%`")

        st.markdown("---")
        st.markdown("#### 🔒 Assumptions Held Constant Across Sensitivity & Simulation")
        const_rows = [
            {"Fixed Assumption": "Discounting Timing Convention", "Baseline Value": base_dcf_assumptions.discounting_convention.replace("_", " ").title(), "Treatment": "Invariant across all matrix cells and simulation draws"},
            {"Fixed Assumption": "Diluted Shares Outstanding", "Baseline Value": f"{base_dcf_assumptions.diluted_shares:,.2f}" if base_dcf_assumptions.diluted_shares else "Not Provided", "Treatment": "Fixed across all per-share calculations"},
            {"Fixed Assumption": "Cash & Liquid Equivalents Added", "Baseline Value": f"{base_currency} {base_dcf_assumptions.bridge_inputs.cash_and_equivalents:,.2f}", "Treatment": "Preserved in Enterprise-to-Equity bridge"},
            {"Fixed Assumption": "Interest-Bearing Debt Subtracted", "Baseline Value": f"{base_currency} {base_dcf_assumptions.bridge_inputs.debt_value:,.2f}", "Treatment": "Preserved in Enterprise-to-Equity bridge"},
            {"Fixed Assumption": "Non-Operating Adjustments", "Baseline Value": f"{base_currency} {base_dcf_assumptions.bridge_inputs.other_adjustments:,.2f}", "Treatment": "Preserved in Enterprise-to-Equity bridge"},
        ]
        st.dataframe(pd.DataFrame(const_rows), hide_index=True, use_container_width=True)

        st.markdown("---")
        st.markdown("#### ⚠️ Analytical Scope & Governance Disclaimers")
        st.info(
            "• **Sensitivity Matrix Scope:** Recalculates only the sensitized variables (WACC and Terminal Parameter) while holding operating forecast cash flows fixed.\n"
            "• **Monte Carlo Conditionality:** Simulated statistics are strictly conditional upon the user's selected distributions and parameters. They do not constitute market predictions, investment advice, or guaranteed ranges."
        )

    # ---------------- TAB 4: PERSISTENCE (SAVE / UPDATE / DELETE) ----------------
    with tab_save:
        st.subheader("💾 Persist Sensitivity Analysis & Simulation Settings")
        st.caption("Save named sensitivity matrix ranges and Monte Carlo distribution settings for this valuation project.")

        col_sn1, col_sn2 = st.columns([2, 1])
        with col_sn1:
            cfg_name_input = st.text_input(
                "Configuration Name *",
                value=sens_cfg.name,
                key="sens_cfg_name_input",
                placeholder="e.g. Q3 Strategic Sensitivity & Simulation",
            )
            sens_cfg.name = cfg_name_input

            cfg_desc_input = st.text_area(
                "Configuration Notes / Strategic Rationales",
                value=sens_cfg.description or "",
                key="sens_cfg_desc_input",
                placeholder="Document distribution assumptions, risk scenarios, or analytical premises...",
            )
            sens_cfg.description = cfg_desc_input

        with col_sn2:
            st.write("")
            st.write("")
            if st.button("💾 Save / Update Configuration", type="primary", key="btn_save_sens_cfg"):
                try:
                    saved_cfg_model = SensitivityService.save_sensitivity_model(
                        project_id=selected_project_id,
                        name=sens_cfg.name,
                        config=sens_cfg,
                        description=sens_cfg.description,
                    )
                    st.success(f"✅ Successfully saved configuration '{saved_cfg_model.name}' (ID: {saved_cfg_model.id})")
                    st.session_state[loaded_cfg_id_key] = saved_cfg_model.id
                    st.rerun()
                except Exception as exc:
                    st.error(f"Error saving sensitivity configuration: {exc}")

            if selected_cfg_key != "new":
                if st.button("🗑️ Delete Selected Configuration", key="btn_del_sens_cfg"):
                    ok = SensitivityService.delete_sensitivity_model(int(selected_cfg_key))
                    if ok:
                        st.success("Sensitivity configuration deleted.")
                        st.session_state[loaded_cfg_id_key] = "new"
                        st.rerun()
                    else:
                        st.error("Failed to delete configuration.")

        st.info("ℹ️ **Persistence Note:** Saves input ranges, distribution definitions, iterations count, and random seed. Raw sample iterations are recomputed deterministically on-demand to optimize storage.")
