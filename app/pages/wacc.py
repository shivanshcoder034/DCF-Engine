"""Weighted Average Cost of Capital (WACC) Estimation Interface.

Provides interactive configuration of CAPM equity cost, pre-tax and after-tax
borrowing rates, capital structure weights, and scenario persistence.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Ensure repository root is in sys.path
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from typing import Dict, List, Optional

import streamlit as st
import pandas as pd

from src.analysis.engine import HistoricalAnalysisEngine
from src.data.services import ProjectService
from src.forecasting.services import ForecastService
from src.wacc.engine import WaccEngine
from src.wacc.formatting import (
    build_capital_structure_dataframe,
    build_cost_of_capital_dataframe,
    create_capital_structure_donut_chart,
    create_wacc_contribution_bar_chart,
)
from src.wacc.models import (
    CapitalStructureInputs,
    CostOfDebtInputs,
    CostOfEquityInputs,
    InputProvenance,
    SourceCategory,
    TaxRateInputs,
    WaccAssumptions,
)
from src.wacc.services import WaccService


def render_wacc_page() -> None:
    """Render the WACC Estimation & Discount Rate engine page."""
    st.header("⚖️ Weighted Average Cost of Capital (WACC) Estimation Engine")
    st.markdown(
        "Estimate the enterprise hurdle and discount rate by blending the **Cost of Equity (CAPM)** "
        "and **After-Tax Cost of Debt** weighted by capital structure. "
        "Assumptions maintain complete provenance tracking across historical actuals, forecast scenarios, and user inputs."
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
            key="wacc_project_select",
        )
        st.session_state["selected_project_id"] = selected_project_id

    current_proj = ProjectService.get_project(selected_project_id)
    comp = current_proj.company if current_proj else None
    base_currency = comp.currency if comp else "USD"

    with col_curr:
        st.write(f"**Reporting Currency:** `{base_currency}`")
        st.write(f"**Fiscal Year End:** `{comp.fiscal_year_end if comp else 'Dec 31'}`")

    # 2. Retrieve Historical Analysis & Forecast Scenarios
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

    saved_forecast_models = ForecastService.list_forecast_models(selected_project_id)

    st.markdown("---")

    # 3. WACC Scenario Management (Save / Load / Case Selector)
    st.subheader("📁 WACC Scenario & Assumption Case")

    saved_wacc_cases = WaccService.list_wacc_models(selected_project_id)
    case_options = {"new": "➕ Create New WACC Case"}
    case_options.update({m.id: f"📂 {m.name} (Updated {m.updated_at.strftime('%Y-%m-%d %H:%M')})" for m in saved_wacc_cases})

    sc_col1, sc_col2 = st.columns([2, 1])
    with sc_col1:
        selected_case_key = st.selectbox(
            "Active WACC Scenario Case",
            options=list(case_options.keys()),
            format_func=lambda k: case_options[k],
            key="saved_wacc_case_select",
        )

    # State key for WACC assumptions
    state_key = f"wacc_assumptions_{selected_project_id}"

    # Load from database if a saved case is picked and not yet loaded into state
    loaded_case_id_key = f"wacc_loaded_case_id_{selected_project_id}"
    current_loaded_id = st.session_state.get(loaded_case_id_key)

    if selected_case_key != "new" and current_loaded_id != selected_case_key:
        db_model = WaccService.get_wacc_model(int(selected_case_key))
        if db_model:
            try:
                st.session_state[state_key] = WaccAssumptions.from_json(db_model.assumptions_json)
                st.session_state[loaded_case_id_key] = selected_case_key
                st.toast(f"Loaded WACC scenario '{db_model.name}'")
            except Exception as e:
                st.error(f"Error loading saved scenario: {e}")
    elif selected_case_key == "new" and current_loaded_id != "new":
        st.session_state[state_key] = WaccEngine.create_default_assumptions(selected_project_id, hist_bundle)
        st.session_state[loaded_case_id_key] = "new"

    # Ensure state is initialized
    if state_key not in st.session_state:
        st.session_state[state_key] = WaccEngine.create_default_assumptions(selected_project_id, hist_bundle)

    assumptions: WaccAssumptions = st.session_state[state_key]

    with sc_col2:
        case_name_input = st.text_input(
            "Scenario Name",
            value=assumptions.name,
            key="wacc_case_name_input",
        )
        assumptions.name = case_name_input.strip() or "Base Case WACC"

    # Save and Delete controls
    save_col1, save_col2, save_col3 = st.columns([1, 1, 2])
    with save_col1:
        if st.button("💾 Save WACC Case", type="primary", use_container_width=True):
            try:
                saved = WaccService.save_wacc_model(
                    project_id=selected_project_id,
                    name=assumptions.name,
                    assumptions=assumptions,
                    description=assumptions.description,
                )
                st.session_state[loaded_case_id_key] = saved.id
                st.success(f"WACC case '{saved.name}' saved successfully!")
                st.rerun()
            except Exception as e:
                st.error(f"Failed to save WACC case: {e}")

    with save_col2:
        if selected_case_key != "new":
            if st.button("🗑️ Delete Case", type="secondary", use_container_width=True):
                if WaccService.delete_wacc_model(int(selected_case_key)):
                    st.session_state[loaded_case_id_key] = "new"
                    st.session_state[state_key] = WaccEngine.create_default_assumptions(selected_project_id, hist_bundle)
                    st.success("WACC scenario deleted.")
                    st.rerun()

    with save_col3:
        if st.button("🔄 Reset to Default Baselines", use_container_width=True):
            st.session_state[state_key] = WaccEngine.create_default_assumptions(selected_project_id, hist_bundle)
            st.rerun()

    st.markdown("---")

    # 4. Preliminary Execution to Populate Headline Metrics
    current_result = WaccEngine.estimate_wacc(assumptions)

    # 5. Headline Metric Cards
    m1, m2, m3, m4, m5, m6 = st.columns(6)
    with m1:
        wacc_disp = f"{current_result.wacc:.2f}%" if current_result.wacc is not None else "Incomplete"
        st.metric("Estimated WACC", wacc_disp, help="Blended enterprise hurdle rate: (We × Ke) + (Wd × Kd_after)")
    with m2:
        ke_disp = f"{current_result.cost_of_equity.cost_of_equity:.2f}%" if current_result.cost_of_equity.cost_of_equity is not None else "Incomplete"
        st.metric("Cost of Equity (Ke)", ke_disp, help="CAPM: Rf + (Beta × ERP)")
    with m3:
        kd_pre_disp = f"{current_result.cost_of_debt.pre_tax_cost_of_debt:.2f}%" if current_result.cost_of_debt.pre_tax_cost_of_debt is not None else "Incomplete"
        st.metric("Pre-Tax Kd", kd_pre_disp, help="Unadjusted borrowing cost before interest tax shield")
    with m4:
        kd_post_disp = f"{current_result.cost_of_debt.after_tax_cost_of_debt:.2f}%" if current_result.cost_of_debt.after_tax_cost_of_debt is not None else "Incomplete"
        st.metric("After-Tax Kd", kd_post_disp, help="Effective borrowing rate: Pre-Tax Kd × (1 - Tax Rate)")
    with m5:
        we_disp = f"{current_result.capital_structure.equity_weight_pct:.1f}%" if current_result.capital_structure.equity_weight_pct is not None else "—"
        st.metric("Equity Weight (We)", we_disp, help="Equity Value / (Equity Value + Debt Balance)")
    with m6:
        wd_disp = f"{current_result.capital_structure.debt_weight_pct:.1f}%" if current_result.capital_structure.debt_weight_pct is not None else "—"
        st.metric("Debt Weight (Wd)", wd_disp, help="Debt Balance / (Equity Value + Debt Balance)")

    # 6. Assumption Configuration Sections
    st.markdown("### 🛠️ Cost of Capital Inputs & Provenance Tracking")

    tab_equity, tab_debt, tab_capital, tab_bridge = st.tabs([
        "1. Cost of Equity (CAPM)",
        "2. Cost of Debt & Tax Shield",
        "3. Capital Structure & Weights",
        "4. Bridge, Breakdown & Charts",
    ])

    # ---------------- TAB 1: COST OF EQUITY (CAPM) ----------------
    with tab_equity:
        st.subheader("Cost of Equity — Capital Asset Pricing Model (CAPM)")
        st.caption("Ke = Risk-Free Rate (Rf) + [Equity Beta (β) × Equity Risk Premium (ERP)]")

        eq_in = assumptions.equity_inputs

        col_rf, col_beta, col_erp = st.columns(3)

        with col_rf:
            st.markdown("##### 1. Risk-Free Rate ($R_f$)")
            rf_val = st.number_input(
                "Risk-Free Rate (%) *",
                min_value=-5.0,
                max_value=25.0,
                value=float(eq_in.risk_free_rate) if eq_in.risk_free_rate is not None else 4.25,
                step=0.05,
                format="%.2f",
                key="wacc_rf_input",
                help="Yield on benchmark sovereign bonds matching the forecast horizon (e.g. 10-Year US Treasury yield).",
            )
            eq_in.risk_free_rate = rf_val

            rf_source = st.selectbox(
                "Source Category",
                options=[s.value for s in SourceCategory],
                index=[s.value for s in SourceCategory].index(eq_in.rf_provenance.source_category),
                format_func=lambda s: SourceCategory.display_name(s),
                key="wacc_rf_source",
            )
            eq_in.rf_provenance.source_category = rf_source

            rf_note = st.text_input(
                "Citation / Benchmark Note",
                value=eq_in.rf_provenance.source_reference or "",
                placeholder="e.g. 10-Year US Treasury Yield (4.25%)",
                key="wacc_rf_note",
            )
            eq_in.rf_provenance.source_reference = rf_note

        with col_beta:
            st.markdown("##### 2. Equity Beta ($\beta$)")
            beta_val = st.number_input(
                "Equity Beta Multiple *",
                min_value=-2.0,
                max_value=5.0,
                value=float(eq_in.equity_beta) if eq_in.equity_beta is not None else 1.00,
                step=0.05,
                format="%.2f",
                key="wacc_beta_input",
                help="Systematic market risk sensitivity. 1.00 equals market risk.",
            )
            eq_in.equity_beta = beta_val

            beta_source = st.selectbox(
                "Source Category",
                options=[s.value for s in SourceCategory],
                index=[s.value for s in SourceCategory].index(eq_in.beta_provenance.source_category),
                format_func=lambda s: SourceCategory.display_name(s),
                key="wacc_beta_source",
            )
            eq_in.beta_provenance.source_category = beta_source

            beta_note = st.text_input(
                "Citation / Benchmark Note",
                value=eq_in.beta_provenance.source_reference or "",
                placeholder="e.g. Raw 2Y Weekly Beta / Industry Peer Proxy",
                key="wacc_beta_note",
            )
            eq_in.beta_provenance.source_reference = beta_note

        with col_erp:
            st.markdown("##### 3. Equity Risk Premium (ERP)")
            erp_val = st.number_input(
                "Equity Risk Premium (%) *",
                min_value=0.0,
                max_value=20.0,
                value=float(eq_in.equity_risk_premium) if eq_in.equity_risk_premium is not None else 5.00,
                step=0.25,
                format="%.2f",
                key="wacc_erp_input",
                help="Expected excess return of equities over the risk-free rate.",
            )
            eq_in.equity_risk_premium = erp_val

            erp_source = st.selectbox(
                "Source Category",
                options=[s.value for s in SourceCategory],
                index=[s.value for s in SourceCategory].index(eq_in.erp_provenance.source_category),
                format_func=lambda s: SourceCategory.display_name(s),
                key="wacc_erp_source",
            )
            eq_in.erp_provenance.source_category = erp_source

            erp_note = st.text_input(
                "Citation / Benchmark Note",
                value=eq_in.erp_provenance.source_reference or "",
                placeholder="e.g. Damodaran US ERP Survey / Long-Term Geometric ERP",
                key="wacc_erp_note",
            )
            eq_in.erp_provenance.source_reference = erp_note

        # Live calculation status
        ke_eval = current_result.cost_of_equity
        st.info(f"**Cost of Equity Formula:** `{ke_eval.formula_display}`")
        if ke_eval.warnings:
            for w in ke_eval.warnings:
                st.warning(f"⚠️ {w}")

    # ---------------- TAB 2: COST OF DEBT & TAX SHIELD ----------------
    with tab_debt:
        st.subheader("Cost of Debt & Marginal Corporate Tax Shield")
        st.caption("After-Tax Kd = Pre-Tax Cost of Debt × (1 - Marginal Tax Rate)")

        debt_in = assumptions.debt_inputs
        tax_in = assumptions.tax_inputs

        col_debt_cfg, col_tax_cfg = st.columns(2)

        with col_debt_cfg:
            st.markdown("##### Pre-Tax Cost of Debt ($K_d$)")

            hist_debt_est = WaccEngine.extract_historical_cost_of_debt(hist_bundle) if hist_bundle else {"is_available": False}

            debt_method = st.radio(
                "Cost of Debt Source Method",
                options=["manual", "historical_estimate"],
                index=1 if (debt_in.use_historical_estimate and hist_debt_est["is_available"]) else 0,
                format_func=lambda m: "Historical Accounting Interest Estimate" if m == "historical_estimate" else "User Entered Market Borrowing Spread",
                key="wacc_debt_method_select",
            )

            if debt_method == "historical_estimate":
                debt_in.use_historical_estimate = True
                if hist_debt_est["is_available"]:
                    st.success(
                        f"**Historical Derived Rate:** `{hist_debt_est['pre_tax_kd_estimate']:.2f}%` "
                        f"(FY: `{hist_debt_est['period_label']}`)"
                    )
                    st.caption(f"ℹ️ {hist_debt_est['notes']}")
                    debt_in.pre_tax_cost_of_debt = hist_debt_est["pre_tax_kd_estimate"]
                    debt_in.historical_interest_expense = hist_debt_est["interest_expense"]
                    debt_in.historical_debt_balance = hist_debt_est["debt_balance"]
                    debt_in.historical_period_label = hist_debt_est["period_label"]
                    debt_in.historical_calculation_notes = hist_debt_est["notes"]
                    debt_in.provenance.source_category = SourceCategory.HISTORICAL_DATA.value
                    debt_in.provenance.source_reference = f"FY{hist_debt_est['period_label']} Interest Expense / Debt"
                else:
                    st.warning("⚠️ Historical interest and debt data not available. Please enter rate manually.")
                    debt_in.use_historical_estimate = False
            else:
                debt_in.use_historical_estimate = False

            kd_val = st.number_input(
                "Pre-Tax Borrowing Rate (%) *",
                min_value=0.0,
                max_value=30.0,
                value=float(debt_in.pre_tax_cost_of_debt) if debt_in.pre_tax_cost_of_debt is not None else 5.50,
                step=0.10,
                format="%.2f",
                key="wacc_kd_input",
                help="Yield-to-maturity on long-term bonds or current commercial borrowing spread.",
            )
            debt_in.pre_tax_cost_of_debt = kd_val

            debt_note = st.text_input(
                "Borrowing Cost Citation / Credit Note",
                value=debt_in.provenance.source_reference or "",
                placeholder="e.g. Yield on Senior Notes / Commercial Loan Spread",
                key="wacc_debt_note",
            )
            debt_in.provenance.source_reference = debt_note

        with col_tax_cfg:
            st.markdown("##### Marginal Corporate Tax Rate ($t$)")

            tax_source_mode = st.radio(
                "Tax Rate Source",
                options=["user_entered", "forecast_scenario", "historical_effective"],
                index=["user_entered", "forecast_scenario", "historical_effective"].index(tax_in.tax_rate_source) if tax_in.tax_rate_source in ["user_entered", "forecast_scenario", "historical_effective"] else 0,
                format_func=lambda s: {
                    "user_entered": "User Entered Marginal Statutory Rate",
                    "forecast_scenario": "Phase 4 Forecast Scenario Tax Assumption",
                    "historical_effective": "Historical Effective Tax Rate Actual",
                }.get(s, s),
                key="wacc_tax_source_mode",
            )
            tax_in.tax_rate_source = tax_source_mode

            if tax_source_mode == "forecast_scenario":
                if saved_forecast_models:
                    fc_map = {m.id: f"{m.name} ({m.horizon_years}Y)" for m in saved_forecast_models}
                    selected_fc_id = st.selectbox(
                        "Select Forecast Scenario",
                        options=list(fc_map.keys()),
                        format_func=lambda k: fc_map[k],
                        key="wacc_forecast_tax_select",
                    )
                    tax_in.forecast_scenario_id = selected_fc_id
                    tax_in.forecast_scenario_name = fc_map[selected_fc_id]

                    chosen_fc = next((m for m in saved_forecast_models if m.id == selected_fc_id), None)
                    if chosen_fc:
                        try:
                            fc_dict = json.loads(chosen_fc.assumptions_json)
                            fc_rate = float(fc_dict.get("tax_rate", 21.0))
                            tax_in.tax_rate = fc_rate
                            tax_in.provenance.source_category = SourceCategory.APPLICATION_DEFAULT.value
                            tax_in.provenance.source_reference = f"Phase 4 Scenario: {chosen_fc.name}"
                            st.success(f"Inherited Tax Rate from '{chosen_fc.name}': `{fc_rate:.2f}%`")
                        except Exception:
                            st.warning("Could not read tax rate from forecast scenario.")
                else:
                    st.info("No Phase 4 forecast scenarios found for this project. Enter tax rate manually.")

            elif tax_source_mode == "historical_effective":
                hist_tax = WaccEngine.extract_historical_effective_tax_rate(hist_bundle) if hist_bundle else {"is_available": False}
                if hist_tax["is_available"] and hist_tax["effective_tax_rate"] is not None:
                    tax_in.tax_rate = hist_tax["effective_tax_rate"]
                    tax_in.provenance.source_category = SourceCategory.HISTORICAL_DATA.value
                    tax_in.provenance.source_reference = f"FY{hist_tax['period_label']} Effective Tax Rate"
                    st.success(f"Loaded Historical Tax Rate: `{hist_tax['effective_tax_rate']:.2f}%` ({hist_tax['period_label']})")
                else:
                    st.warning("No valid historical effective tax rate found.")

            # Editable tax rate field
            tax_val = st.number_input(
                "Corporate Tax Rate Applied to Debt (%) *",
                min_value=0.0,
                max_value=60.0,
                value=float(tax_in.tax_rate) if tax_in.tax_rate is not None else 21.0,
                step=0.5,
                format="%.2f",
                key="wacc_tax_input",
                help="Statutory corporate income tax rate providing the interest deductibility tax shield.",
            )
            tax_in.tax_rate = tax_val

            tax_note = st.text_input(
                "Tax Rate Citation / Authority",
                value=tax_in.provenance.source_reference or "",
                placeholder="e.g. US Federal Statutory Corporate Tax Rate (21.0%)",
                key="wacc_tax_note",
            )
            tax_in.provenance.source_reference = tax_note

        kd_eval = current_result.cost_of_debt
        st.info(f"**After-Tax Cost of Debt Formula:** `{kd_eval.formula_display}` (Tax Shield Benefit: `{kd_eval.tax_shield_benefit or 0:.2f}%`)")

    # ---------------- TAB 3: CAPITAL STRUCTURE & WEIGHTS ----------------
    with tab_capital:
        st.subheader("Capital Structure Determination & Weighting")
        st.caption("We = Equity / (Equity + Debt) | Wd = Debt / (Equity + Debt)")

        cap_in = assumptions.capital_inputs
        hist_cap = WaccEngine.extract_historical_debt_and_equity(hist_bundle) if hist_bundle else {}

        col_eq_cap, col_dt_cap = st.columns(2)

        with col_eq_cap:
            st.markdown(f"##### Equity Component (E) [{base_currency}]")

            eq_mode = st.radio(
                "Equity Valuation Basis",
                options=["market_value", "book_value_proxy"],
                index=0 if cap_in.equity_value_type == "market_value" else 1,
                format_func=lambda m: "Market Capitalization / Market Value" if m == "market_value" else "Balance Sheet Book Value Proxy",
                key="wacc_eq_mode_select",
            )
            cap_in.equity_value_type = eq_mode

            if eq_mode == "book_value_proxy":
                if hist_cap.get("book_value_of_equity") is not None:
                    book_eq = float(hist_cap["book_value_of_equity"])
                    st.warning(
                        f"⚠️ **Proxy Selected:** Using Book Value of Equity (`{book_eq:,.2f}` {base_currency}). "
                        "Book equity may diverge substantially from market capitalization."
                    )
                    cap_in.equity_value = book_eq
                    cap_in.equity_provenance.source_category = SourceCategory.HISTORICAL_DATA.value
                    cap_in.equity_provenance.is_proxy = True
                else:
                    st.info("No historical book equity record found.")
            else:
                cap_in.equity_provenance.is_proxy = False

            eq_val_input = st.number_input(
                f"Equity Capital Amount ({base_currency} {hist_bundle.display_unit if hist_bundle else 'units'}) *",
                min_value=0.0,
                max_value=1e12,
                value=float(cap_in.equity_value) if cap_in.equity_value is not None else 1000.0,
                step=10.0,
                format="%.2f",
                key="wacc_eq_amount_input",
                help="Market capitalization (Shares Outstanding × Current Share Price) or proxy equity capital base.",
            )
            cap_in.equity_value = eq_val_input

            eq_prov_note = st.text_input(
                "Equity Citation / Source Reference",
                value=cap_in.equity_provenance.source_reference or "",
                placeholder="e.g. Market Cap as of 2026-09-28 ($150.00/share × 10M shares)",
                key="wacc_eq_prov_note",
            )
            cap_in.equity_provenance.source_reference = eq_prov_note

        with col_dt_cap:
            st.markdown(f"##### Interest-Bearing Debt Component (D) [{base_currency}]")

            dt_mode = st.radio(
                "Debt Balance Basis",
                options=["interest_bearing_debt", "user_specified"],
                index=0 if cap_in.debt_value_type == "interest_bearing_debt" else 1,
                format_func=lambda m: "Latest Balance Sheet Interest-Bearing Borrowings" if m == "interest_bearing_debt" else "User Specified Total Debt Balance",
                key="wacc_dt_mode_select",
            )
            cap_in.debt_value_type = dt_mode

            if dt_mode == "interest_bearing_debt":
                if hist_cap.get("total_interest_bearing_debt") is not None:
                    tot_dt = float(hist_cap["total_interest_bearing_debt"])
                    st.success(
                        f"Reported Interest-Bearing Debt: `{tot_dt:,.2f}` {base_currency} "
                        f"({hist_cap.get('period_label', 'Latest')})"
                    )
                    st.caption("ℹ️ Non-interest-bearing liabilities (Accounts Payable, Accruals) are excluded.")
                    cap_in.debt_value = tot_dt
                    cap_in.debt_provenance.source_category = SourceCategory.HISTORICAL_DATA.value
                else:
                    st.info("No balance sheet interest-bearing debt found.")

            dt_val_input = st.number_input(
                f"Debt Balance Amount ({base_currency} {hist_bundle.display_unit if hist_bundle else 'units'}) *",
                min_value=0.0,
                max_value=1e12,
                value=float(cap_in.debt_value) if cap_in.debt_value is not None else 300.0,
                step=10.0,
                format="%.2f",
                key="wacc_dt_amount_input",
                help="Sum of short-term borrowings, commercial paper, and long-term notes payable.",
            )
            cap_in.debt_value = dt_val_input

            dt_prov_note = st.text_input(
                "Debt Citation / Source Reference",
                value=cap_in.debt_provenance.source_reference or "",
                placeholder="e.g. Latest SEC 10-K / Balance Sheet Reported Debt",
                key="wacc_dt_prov_note",
            )
            cap_in.debt_provenance.source_reference = dt_prov_note

        cap_eval = current_result.capital_structure
        st.info(f"**Capital Structure Evaluation:** `{cap_eval.formula_display}`")

    # ---------------- TAB 4: BRIDGE, BREAKDOWN & CHARTS ----------------
    with tab_bridge:
        st.subheader("WACC Derivation Bridge & Visual Breakdown")

        if current_result.is_complete:
            st.success(f"### Final Blended WACC: `{current_result.wacc:.2f}%`")
            st.caption(f"Formula: `{current_result.formula_breakdown}`")

            # Charts
            c_col1, c_col2 = st.columns([1, 1])
            with c_col1:
                donut = create_capital_structure_donut_chart(current_result)
                if donut:
                    st.plotly_chart(donut, use_container_width=True)
            with c_col2:
                bar = create_wacc_contribution_bar_chart(current_result)
                if bar:
                    st.plotly_chart(bar, use_container_width=True)

            # Detailed Cost of Capital Summary Table
            st.markdown("#### Cost of Capital Component Matrix")
            cost_df = build_cost_of_capital_dataframe(current_result, assumptions)
            st.dataframe(cost_df, hide_index=True, use_container_width=True)

            # Capital Structure Breakdown Table
            st.markdown("#### Enterprise Capital Base")
            cap_df = build_capital_structure_dataframe(
                current_result,
                currency=base_currency,
                unit=hist_bundle.display_unit if hist_bundle else "units",
            )
            st.dataframe(cap_df, hide_index=True, use_container_width=True)

        else:
            st.error("⚠️ Final WACC calculation is currently withheld because required inputs are missing or invalid.")
            st.markdown("**Incomplete Input Items:**")
            for item in current_result.missing_inputs:
                st.markdown(f"- ❌ `{item}`")

    # 7. Audit Warnings & Diagnostics Area
    if current_result.warnings:
        st.markdown("---")
        st.subheader("⚠️ Model Audit & Diagnostics Warnings")
        for warn in current_result.warnings:
            st.warning(warn)

    st.markdown("---")
    st.caption(f"🔒 {current_result.limitations_disclaimer}")


if __name__ == "__main__":
    from app.navigation import run_standalone_page
    run_standalone_page("WACC", render_wacc_page)
