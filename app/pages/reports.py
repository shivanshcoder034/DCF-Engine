"""Reporting, Presentation and Export Engine Streamlit Interface.

Coordinates report configuration, in-app executive previews, model provenance tracking,
multi-format institutional exports (PDF, Excel, CSV), and saved report management.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Ensure repository root is in sys.path
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from datetime import date
import io
import re
from typing import Dict, List, Optional

import pandas as pd
import streamlit as st

from src.data.services import ProjectService
from src.dcf.services import DcfService
from src.forecasting.services import ForecastService
from src.reporting.csv_export import CsvReportGenerator
from src.reporting.engine import ReportEngine
from src.reporting.dynamic_excel_export import DynamicExcelModelGenerator
from src.reporting.excel_export import ExcelReportGenerator
from src.reporting.models import (
    ReportBundle,
    ReportConfig,
    ReportMetadata,
    ReportModelReferences,
    ReportSection,
    ReportSectionConfig,
)
from src.reporting.pdf_export import PdfReportGenerator
from src.reporting.services import ReportService
from src.scenarios.services import ScenarioService
from src.sensitivity.services import SensitivityService
from src.wacc.services import WaccService


def _sanitize_filename(name: str) -> str:
    """Remove invalid filename characters for cross-platform file saving."""
    clean = re.sub(r'[\\/*?:"<>| ]', "_", name)
    return re.sub(r"_+", "_", clean).strip("_")


def render_reports_page() -> None:
    """Render the main Reports, Presentation & Export Engine interface."""
    st.header("📑 Valuation Reports & Model Exports")
    st.markdown(
        "Assemble professional, auditable valuation reports and financial model workbooks. "
        "Select which analytical modules to include, review the in-app preview, and export in "
        "practical formats: **Institutional PDF Report**, **Multi-Tab Excel Financial Model**, and **Structured CSVs**. "
        "All calculations strictly reuse the verified domain engines from Phases 3–8."
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
            key="report_proj_select",
        )
        st.session_state["selected_project_id"] = selected_project_id

    current_proj = ProjectService.get_project(selected_project_id)
    company = current_proj.company if current_proj else None
    base_currency = company.currency if company else "USD"
    company_name = company.name if company else "Valuation Target"
    company_ticker = company.ticker if company else ""

    with col_curr:
        st.write(f"**Reporting Currency:** `{base_currency}`")
        st.write(f"**Fiscal Year End:** `{company.fiscal_year_end if company else 'Dec 31'}`")

    # Available Saved Models for this project
    saved_forecasts = ForecastService.list_forecast_models(selected_project_id)
    saved_waccs = WaccService.list_wacc_models(selected_project_id)
    saved_dcfs = DcfService.list_dcf_models(selected_project_id)
    saved_scenarios = ScenarioService.list_scenario_models(selected_project_id)
    saved_sensitivities = SensitivityService.list_sensitivity_models(selected_project_id)

    # Manage Active Report Config in Session State
    if "active_report_config" not in st.session_state or st.session_state.get("report_config_project_id") != selected_project_id:
        default_meta = ReportMetadata(
            title=f"{company_name} — DCF Valuation & Sensitivity Memorandum",
            subtitle="Intrinsic Valuation, Scenario Sensitivity & Risk Assessment",
            company_name=company_name,
            ticker=company_ticker,
            project_name=current_proj.name if current_proj else "",
            project_id=selected_project_id,
            reporting_currency=base_currency,
            fiscal_year_end=company.fiscal_year_end if company else "Dec 31",
            report_date=date.today().isoformat(),
            prepared_by="Valuation Analyst",
            narrative_summary=f"Comprehensive discounted cash flow valuation for {company_name}.",
            valuation_notes="Valuation results are conditional on user-supplied assumptions and historical statements.",
        )
        default_refs = ReportModelReferences(
            historical_frequency="annual",
            historical_classification="reported_actual",
            forecast_model_id=saved_forecasts[0].id if saved_forecasts else None,
            forecast_model_name=saved_forecasts[0].name if saved_forecasts else None,
            wacc_model_id=saved_waccs[0].id if saved_waccs else None,
            wacc_model_name=saved_waccs[0].name if saved_waccs else None,
            dcf_model_id=saved_dcfs[0].id if saved_dcfs else None,
            dcf_model_name=saved_dcfs[0].name if saved_dcfs else None,
            scenario_model_id=saved_scenarios[0].id if saved_scenarios else None,
            scenario_model_name=saved_scenarios[0].name if saved_scenarios else None,
            sensitivity_model_id=saved_sensitivities[0].id if saved_sensitivities else None,
            sensitivity_model_name=saved_sensitivities[0].name if saved_sensitivities else None,
        )
        st.session_state["active_report_config"] = ReportConfig(
            metadata=default_meta,
            references=default_refs,
            sections=ReportSectionConfig(),
        )
        st.session_state["report_config_project_id"] = selected_project_id

    active_config: ReportConfig = st.session_state["active_report_config"]

    # 4 Modular Application Tabs
    tab_cfg, tab_preview, tab_export, tab_saved = st.tabs([
        "⚙️ Report Configuration",
        "👁️ In-App Preview",
        "📥 Export Center (PDF, Excel, CSV)",
        "💾 Saved Configurations",
    ])

    # =========================================================================
    # TAB 1: REPORT CONFIGURATION
    # =========================================================================
    with tab_cfg:
        st.subheader("1. General Information & Metadata")
        c1, c2 = st.columns(2)
        with c1:
            active_config.metadata.title = st.text_input(
                "Report Title *",
                value=active_config.metadata.title,
                key="rep_cfg_title",
            )
            active_config.metadata.company_name = st.text_input(
                "Company Name",
                value=active_config.metadata.company_name,
                key="rep_cfg_company",
            )
            active_config.metadata.prepared_by = st.text_input(
                "Prepared By (Analyst / Firm)",
                value=active_config.metadata.prepared_by or "",
                key="rep_cfg_prepared_by",
            )
        with c2:
            active_config.metadata.subtitle = st.text_input(
                "Report Subtitle",
                value=active_config.metadata.subtitle or "",
                key="rep_cfg_subtitle",
            )
            active_config.metadata.ticker = st.text_input(
                "Ticker Symbol",
                value=active_config.metadata.ticker or "",
                key="rep_cfg_ticker",
            )
            active_config.metadata.report_date = st.text_input(
                "Report Generation Date (YYYY-MM-DD)",
                value=active_config.metadata.report_date,
                key="rep_cfg_date",
                help="Date shown on the exported report and running headers.",
            )

        st.markdown("---")
        st.subheader("2. Linked Models & Source References")
        st.caption(
            "Select which saved models from previous phases to bind to this report. "
            "Underlying models are never modified during report generation."
        )

        r1, r2 = st.columns(2)
        with r1:
            # Historical frequency & classification
            hf1, hf2 = st.columns(2)
            with hf1:
                active_config.references.historical_frequency = st.selectbox(
                    "Historical Frequency",
                    options=["annual", "quarterly"],
                    index=0 if active_config.references.historical_frequency == "annual" else 1,
                    format_func=lambda x: x.title(),
                    key="rep_ref_freq",
                )
            with hf2:
                active_config.references.historical_classification = st.selectbox(
                    "Historical Classification",
                    options=["reported_actual", "normalized", "restated"],
                    index=0,
                    format_func=lambda x: x.replace("_", " ").title(),
                    key="rep_ref_class",
                )

            # Forecast Model selector
            fc_options = {None: "None / Exclude"}
            for f in saved_forecasts:
                fc_options[f.id] = f"{f.name} ({f.horizon_years}Y, Base: {f.base_period_label})"
            current_fc_idx = list(fc_options.keys()).index(active_config.references.forecast_model_id) if active_config.references.forecast_model_id in fc_options else 0
            sel_fc_id = st.selectbox(
                "Linked Forecast Model",
                options=list(fc_options.keys()),
                index=current_fc_idx,
                format_func=lambda x: fc_options[x],
                key="rep_ref_fc",
            )
            active_config.references.forecast_model_id = sel_fc_id
            active_config.references.forecast_model_name = fc_options[sel_fc_id] if sel_fc_id else None

            # WACC Model selector
            wacc_options = {None: "None / Exclude"}
            for w in saved_waccs:
                wacc_options[w.id] = w.name
            current_wacc_idx = list(wacc_options.keys()).index(active_config.references.wacc_model_id) if active_config.references.wacc_model_id in wacc_options else 0
            sel_wacc_id = st.selectbox(
                "Linked WACC Model",
                options=list(wacc_options.keys()),
                index=current_wacc_idx,
                format_func=lambda x: wacc_options[x],
                key="rep_ref_wacc",
            )
            active_config.references.wacc_model_id = sel_wacc_id
            active_config.references.wacc_model_name = wacc_options[sel_wacc_id] if sel_wacc_id else None

        with r2:
            # DCF Model selector
            dcf_options = {None: "None / Exclude"}
            for d in saved_dcfs:
                dcf_options[d.id] = d.name
            current_dcf_idx = list(dcf_options.keys()).index(active_config.references.dcf_model_id) if active_config.references.dcf_model_id in dcf_options else 0
            sel_dcf_id = st.selectbox(
                "Linked DCF Valuation Case *",
                options=list(dcf_options.keys()),
                index=current_dcf_idx,
                format_func=lambda x: dcf_options[x],
                key="rep_ref_dcf",
            )
            active_config.references.dcf_model_id = sel_dcf_id
            active_config.references.dcf_model_name = dcf_options[sel_dcf_id] if sel_dcf_id else None

            # Scenario Model selector
            sc_options = {None: "None / Exclude"}
            for s in saved_scenarios:
                sc_options[s.id] = s.name
            current_sc_idx = list(sc_options.keys()).index(active_config.references.scenario_model_id) if active_config.references.scenario_model_id in sc_options else 0
            sel_sc_id = st.selectbox(
                "Linked Scenario Set (Base/Bull/Bear)",
                options=list(sc_options.keys()),
                index=current_sc_idx,
                format_func=lambda x: sc_options[x],
                key="rep_ref_sc",
            )
            active_config.references.scenario_model_id = sel_sc_id
            active_config.references.scenario_model_name = sc_options[sel_sc_id] if sel_sc_id else None

            # Sensitivity Model selector
            sens_options = {None: "None / Exclude"}
            for sn in saved_sensitivities:
                sens_options[sn.id] = sn.name
            current_sens_idx = list(sens_options.keys()).index(active_config.references.sensitivity_model_id) if active_config.references.sensitivity_model_id in sens_options else 0
            sel_sens_id = st.selectbox(
                "Linked Sensitivity & Simulation Config",
                options=list(sens_options.keys()),
                index=current_sens_idx,
                format_func=lambda x: sens_options[x],
                key="rep_ref_sens",
            )
            active_config.references.sensitivity_model_id = sel_sens_id
            active_config.references.sensitivity_model_name = sens_options[sel_sens_id] if sel_sens_id else None

        st.markdown("---")
        st.subheader("3. Section Inclusion Controls")
        st.caption("Toggle which chapters appear in the exported report and preview:")

        sec = active_config.sections
        s_col1, s_col2 = st.columns(2)
        with s_col1:
            sec.include_overview = st.checkbox("1. Report Overview & Metadata", value=sec.include_overview, key="sec_inc_over")
            sec.include_executive_summary = st.checkbox("2. Executive Valuation Summary", value=sec.include_executive_summary, key="sec_inc_exec")
            sec.include_historical_analysis = st.checkbox("3. Historical Financial Analysis", value=sec.include_historical_analysis, key="sec_inc_hist")
            sec.include_forecast_projections = st.checkbox("4. Forecast Assumptions & Projections", value=sec.include_forecast_projections, key="sec_inc_fc")
            sec.include_wacc_analysis = st.checkbox("5. WACC & Cost of Capital", value=sec.include_wacc_analysis, key="sec_inc_wacc")
        with s_col2:
            sec.include_dcf_valuation = st.checkbox("6. DCF Valuation & Equity Bridge", value=sec.include_dcf_valuation, key="sec_inc_dcf")
            sec.include_scenario_analysis = st.checkbox("7. Scenario Analysis (Base / Bull / Bear)", value=sec.include_scenario_analysis, key="sec_inc_scen")
            sec.include_sensitivity_simulation = st.checkbox("8. Sensitivity Analysis & Simulation", value=sec.include_sensitivity_simulation, key="sec_inc_sens")
            sec.include_disclosures_limitations = st.checkbox("9. Data Quality, Limitations & Disclosures", value=sec.include_disclosures_limitations, key="sec_inc_disc")
            sec.include_appendix = st.checkbox("10. Appendix & Methodology", value=sec.include_appendix, key="sec_inc_app")

        st.markdown("---")
        st.subheader("4. Narrative Notes & Valuation Commentary")
        active_config.metadata.narrative_summary = st.text_area(
            "Executive Narrative Summary (Optional)",
            value=active_config.metadata.narrative_summary or "",
            placeholder="Add high-level context on company positioning, thesis, or principal valuation drivers...",
            height=90,
            key="rep_cfg_narrative",
        )
        active_config.metadata.valuation_notes = st.text_area(
            "Valuation Methodology & Risk Notes (Optional)",
            value=active_config.metadata.valuation_notes or "",
            placeholder="Document key terminal growth rationale, cost of debt assumptions, or sensitivity caveats...",
            height=90,
            key="rep_cfg_val_notes",
        )

        st.success("✅ Report configuration updated. Proceed to **In-App Preview** or **Export Center**.")

    # Compile the ReportBundle
    with st.spinner("Compiling valuation models and analytical outputs..."):
        report_bundle = ReportEngine.compile_report_bundle(active_config)

    # =========================================================================
    # TAB 2: IN-APP PREVIEW
    # =========================================================================
    with tab_preview:
        st.subheader("👁️ Live Report Preview")

        # Warnings / Missing Dependencies Banner
        if report_bundle.missing_models_diagnostics:
            for diag in report_bundle.missing_models_diagnostics:
                st.warning(f"⚠️ **Model Dependency Notice:** {diag}")

        # 1. Title Banner
        st.markdown(
            f"""
            <div style="background: linear-gradient(135deg, #1E3A8A 0%, #172554 100%); padding: 24px; border-radius: 8px; color: white; margin-bottom: 20px;">
                <h2 style="margin: 0; color: white; font-size: 26px;">{active_config.metadata.title}</h2>
                <p style="margin: 6px 0 16px 0; color: #93C5FD; font-size: 14px;">{active_config.metadata.subtitle or ''}</p>
                <div style="display: flex; gap: 20px; font-size: 13px; color: #E0E7FF; flex-wrap: wrap;">
                    <span><b>Company:</b> {report_bundle.company_name} {f'({report_bundle.ticker})' if report_bundle.ticker else ''}</span>
                    <span><b>Project:</b> {active_config.metadata.project_name}</span>
                    <span><b>Currency:</b> {active_config.metadata.reporting_currency}</span>
                    <span><b>Date:</b> {active_config.metadata.report_date}</span>
                    <span><b>Prepared By:</b> {active_config.metadata.prepared_by or 'N/A'}</span>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        sec = active_config.sections

        # 2. Executive Summary
        if sec.include_executive_summary:
            st.markdown("### 1. Executive Valuation Summary")
            dcf = report_bundle.dcf_result
            if dcf and dcf.is_complete:
                k1, k2, k3, k4 = st.columns(4)
                k1.metric("Enterprise Value", f"${dcf.enterprise_value:,.1f}M", help="Present Value of forecast cash flows + Present Value of terminal value")
                k2.metric("Equity Value", f"${dcf.equity_value:,.1f}M" if dcf.equity_value else "N/A", help="Enterprise Value adjusted for net debt, cash, and non-operating claims")
                k3.metric("Implied Value / Share", f"${dcf.implied_share_price:,.2f}" if dcf.implied_share_price else "N/A", help="Equity Value divided by diluted common shares")
                k4.metric("Discount Rate (WACC)", f"{dcf.wacc * 100.0:.2f}%" if dcf.wacc else "N/A", help="Weighted Average Cost of Capital")

                if active_config.metadata.narrative_summary:
                    st.info(f"**Executive Notes:** {active_config.metadata.narrative_summary}")
            else:
                st.info("ℹ️ DCF Valuation is incomplete or unselected. Select a DCF Valuation Case in the Configuration tab.")

            st.markdown("---")

        # 3. Historical Financial Analysis
        if sec.include_historical_analysis and report_bundle.historical_bundle and report_bundle.historical_bundle.periods:
            st.markdown("### 2. Historical Financial Analysis")
            hb = report_bundle.historical_bundle
            periods = [p.label for p in hb.periods[-5:]]

            hist_data = []
            for code, label, is_pct in [
                ("revenue", "Revenue ($M)", False),
                ("revenue_growth_yoy", "Revenue Growth YoY (%)", True),
                ("gross_profit", "Gross Profit ($M)", False),
                ("gross_margin", "Gross Margin (%)", True),
                ("ebitda", "EBITDA ($M)", False),
                ("ebitda_margin", "EBITDA Margin (%)", True),
                ("operating_income", "Operating Income (EBIT) ($M)", False),
                ("operating_cash_flow", "Operating Cash Flow ($M)", False),
                ("capital_expenditures", "CapEx ($M)", False),
                ("ufcf_estimate", "UFCF Analytical Estimate ($M)", False),
            ]:
                row = {"Financial Metric": label}
                for p in periods:
                    val = None
                    p_m = hb.metrics_by_period.get(p, {})
                    if code in p_m:
                        val = p_m[code].value
                    elif code in ("operating_cash_flow", "capital_expenditures", "ufcf_estimate"):
                        cf = hb.cash_flow_metrics.get(p)
                        if cf:
                            val = cf.capex_magnitude if code == "capital_expenditures" else getattr(cf, code, None)

                    if val is not None:
                        row[p] = f"{val:.1f}%" if is_pct else f"${val:,.1f}M"
                    else:
                        row[p] = "-"
                hist_data.append(row)

            st.dataframe(pd.DataFrame(hist_data), use_container_width=True, hide_index=True)
            st.markdown("---")

        # 4. Forecast Assumptions & Projections
        if sec.include_forecast_projections and report_bundle.forecast_result:
            st.markdown("### 3. Forecast Projections & UFCF Derivations")
            fc = report_bundle.forecast_result
            fc_data = []
            lines = [
                ("Revenue ($M)", [f"${v:,.1f}M" for v in fc.revenue]),
                ("Revenue Growth Rate (%)", [f"{v:.1f}%" for v in fc.revenue_growth_rate]),
                ("Gross Profit ($M)", [f"${v:,.1f}M" for v in fc.gross_profit]),
                ("EBITDA ($M)", [f"${v:,.1f}M" for v in fc.ebitda]),
                ("Operating Income (EBIT) ($M)", [f"${v:,.1f}M" for v in fc.ebit]),
                ("Effective Tax Rate (%)", [f"{v:.1f}%" for v in fc.effective_tax_rate]),
                ("NOPAT (EBIT x (1 - t)) ($M)", [f"${v:,.1f}M" for v in fc.nopat]),
                ("(+) D&A ($M)", [f"${v:,.1f}M" for v in fc.depreciation_and_amortization]),
                ("(-) Capital Expenditures ($M)", [f"-${v:,.1f}M" for v in fc.capex]),
                ("(-) Change in Operating NWC ($M)", [f"-${v:,.1f}M" for v in fc.delta_operating_nwc]),
                ("(=) Unlevered Free Cash Flow (UFCF) ($M)", [f"${v:,.1f}M" for v in fc.ufcf]),
            ]
            for label, vals in lines:
                row = {"Projection Step": label}
                for i, yr in enumerate(fc.projected_years):
                    row[yr] = vals[i]
                fc_data.append(row)

            st.dataframe(pd.DataFrame(fc_data), use_container_width=True, hide_index=True)
            st.markdown("---")

        # 5. WACC & Cost of Capital
        if sec.include_wacc_analysis and report_bundle.wacc_result:
            st.markdown("### 4. WACC & Cost of Capital Breakdown")
            w = report_bundle.wacc_result
            wc1, wc2 = st.columns(2)
            with wc1:
                st.markdown("**Cost of Equity & Debt (CAPM)**")
                eq = w.cost_of_equity
                debt = w.cost_of_debt
                st.write(f"- **Risk-Free Rate (Rf):** `{eq.risk_free_rate:.2f}%`")
                st.write(f"- **Beta:** `{eq.beta:.2f}x` | **Equity Risk Premium:** `{eq.equity_risk_premium:.2f}%`")
                st.write(f"- **Cost of Equity (Ke):** `{eq.cost_of_equity:.2f}%`")
                st.write(f"- **Pre-tax Cost of Debt (Kd):** `{debt.pre_tax_cost_of_debt:.2f}%`")
                st.write(f"- **Marginal Tax Rate:** `{debt.effective_tax_rate:.2f}%`")
                st.write(f"- **After-tax Cost of Debt (Kd x (1 - t)):** `{debt.after_tax_cost_of_debt:.2f}%`")
            with wc2:
                st.markdown("**Capital Structure Weights & Blended WACC**")
                cs = w.capital_structure
                st.write(f"- **Equity Value (E):** `${cs.equity_value:,.1f}M` ({cs.weight_equity * 100.0:.1f}%)")
                st.write(f"- **Total Debt (D):** `${cs.total_debt:,.1f}M` ({cs.weight_debt * 100.0:.1f}%)")
                st.write(f"- **Total Capital (E + D):** `${cs.total_capital:,.1f}M`")
                st.success(f"**Resulting WACC:** `{w.wacc * 100.0:.2f}%`")

            st.markdown("---")

        # 6. DCF Valuation & Equity Bridge
        if sec.include_dcf_valuation and report_bundle.dcf_result:
            st.markdown("### 5. DCF Valuation & Equity Bridge")
            dcf = report_bundle.dcf_result
            d1, d2 = st.columns(2)
            with d1:
                st.markdown("**Cash Flow Discounting Schedule**")
                cf_data = []
                for item in dcf.cash_flow_schedule:
                    cf_data.append({
                        "Period": item.period_label,
                        "Year (t)": f"{item.period_index:.1f}",
                        "Discount Factor": f"{item.discount_factor:.4f}",
                        "Forecast UFCF": f"${item.ufcf:,.1f}M",
                        "Present Value": f"${item.present_value:,.1f}M",
                    })
                st.dataframe(pd.DataFrame(cf_data), use_container_width=True, hide_index=True)
                st.write(f"**PV of Forecast Cash Flows:** `${dcf.pv_forecast_cash_flows:,.1f}M`")
                st.write(f"**PV of Terminal Value ({dcf.terminal_value_pct_of_ev:.1f}% of EV):** `${dcf.pv_terminal_value:,.1f}M`")
                st.write(f"**ENTERPRISE VALUE (EV):** `${dcf.enterprise_value:,.1f}M`")

            with d2:
                st.markdown("**Enterprise-to-Equity Value Bridge**")
                b = dcf.bridge_inputs
                bridge_data = [
                    {"Component": "Enterprise Value (EV)", "Value": f"${dcf.enterprise_value:,.1f}M"},
                    {"Component": "(+) Cash & Cash Equivalents", "Value": f"+${b.cash_and_equivalents:,.1f}M"},
                    {"Component": "(-) Total Debt Claims", "Value": f"-${b.debt_value:,.1f}M"},
                    {"Component": "(-) Minority Interest", "Value": f"-${b.minority_interest:,.1f}M"},
                    {"Component": "(-) Preferred Stock Equity", "Value": f"-${b.preferred_equity:,.1f}M"},
                    {"Component": "(+/-) Other Net Adjustments", "Value": f"{b.other_adjustments:+,.1f}M"},
                    {"Component": "(=) IMPLIED EQUITY VALUE", "Value": f"${dcf.equity_value:,.1f}M" if dcf.equity_value else "N/A"},
                    {"Component": "(/) Diluted Common Shares", "Value": f"{dcf.diluted_shares:,.1f}M"},
                    {"Component": "(=) INTRINSIC VALUE / SHARE", "Value": f"${dcf.implied_share_price:,.2f}" if dcf.implied_share_price else "N/A"},
                ]
                st.dataframe(pd.DataFrame(bridge_data), use_container_width=True, hide_index=True)

            st.markdown("---")

        # 7. Scenario Analysis
        if sec.include_scenario_analysis and report_bundle.scenario_result:
            st.markdown("### 6. Scenario Analysis (Base / Bull / Bear)")
            sc = report_bundle.scenario_result
            b, u, d = sc.base_case, sc.bull_case, sc.bear_case
            u_pct = ((u.implied_value_per_share - b.implied_value_per_share) / b.implied_value_per_share * 100.0) if (u.implied_value_per_share and b.implied_value_per_share) else None
            d_pct = ((d.implied_value_per_share - b.implied_value_per_share) / b.implied_value_per_share * 100.0) if (d.implied_value_per_share and b.implied_value_per_share) else None

            sc_table = [
                {"Driver / Metric": "Revenue Growth Override", "Base Case": f"{b.overrides.revenue_growth_delta_pp:+.1f} pp", "Bull Case": f"{u.overrides.revenue_growth_delta_pp:+.1f} pp", "Bear Case": f"{d.overrides.revenue_growth_delta_pp:+.1f} pp"},
                {"Driver / Metric": "Operating Margin Override", "Base Case": f"{b.overrides.margin_delta_pp:+.1f} pp", "Bull Case": f"{u.overrides.margin_delta_pp:+.1f} pp", "Bear Case": f"{d.overrides.margin_delta_pp:+.1f} pp"},
                {"Driver / Metric": "WACC Adjustment", "Base Case": f"{b.overrides.wacc_delta_bps:+.0f} bps", "Bull Case": f"{u.overrides.wacc_delta_bps:+.0f} bps", "Bear Case": f"{d.overrides.wacc_delta_bps:+.0f} bps"},
                {"Driver / Metric": "Effective WACC", "Base Case": f"{b.effective_wacc:.2f}%", "Bull Case": f"{u.effective_wacc:.2f}%", "Bear Case": f"{d.effective_wacc:.2f}%"},
                {"Driver / Metric": "Enterprise Value ($M)", "Base Case": f"${b.enterprise_value:,.1f}" if b.enterprise_value else "N/A", "Bull Case": f"${u.enterprise_value:,.1f}" if u.enterprise_value else "N/A", "Bear Case": f"${d.enterprise_value:,.1f}" if d.enterprise_value else "N/A"},
                {"Driver / Metric": "Equity Value ($M)", "Base Case": f"${b.equity_value:,.1f}" if b.equity_value else "N/A", "Bull Case": f"${u.equity_value:,.1f}" if u.equity_value else "N/A", "Bear Case": f"${d.equity_value:,.1f}" if d.equity_value else "N/A"},
                {"Driver / Metric": "Implied Share Price", "Base Case": f"${b.implied_value_per_share:,.2f}" if b.implied_value_per_share else "N/A", "Bull Case": f"${u.implied_value_per_share:,.2f}" if u.implied_value_per_share else "N/A", "Bear Case": f"${d.implied_value_per_share:,.2f}" if d.implied_value_per_share else "N/A"},
                {"Driver / Metric": "Upside / Downside vs. Base", "Base Case": "0.0%", "Bull Case": f"{u_pct:+.1f}%" if u_pct is not None else "N/A", "Bear Case": f"{d_pct:+.1f}%" if d_pct is not None else "N/A"},
            ]
            st.dataframe(pd.DataFrame(sc_table), use_container_width=True, hide_index=True)
            st.markdown("---")

        # 8. Sensitivity Analysis & Simulation
        if sec.include_sensitivity_simulation and (report_bundle.sensitivity_matrix_result or report_bundle.monte_carlo_result):
            st.markdown("### 7. Sensitivity Analysis & Monte Carlo Simulation")
            m = report_bundle.sensitivity_matrix_result
            if m:
                st.markdown(f"**Two-Dimensional Sensitivity Matrix ({m.metric_label})**")
                mat_rows = []
                col_headers = [f"{c:.2f}%" if "%" in m.col_label else f"{c:.1f}x" for c in m.col_values]
                for r_idx, r_val in enumerate(m.row_values):
                    row_dict = {f"WACC \\ {m.col_label}": f"{r_val:.2f}%"}
                    for c_idx, ch in enumerate(col_headers):
                        cell = m.cells[r_idx][c_idx]
                        if cell.is_valid and cell.output_value is not None:
                            val_str = f"${cell.output_value:,.2f}" if "Share" in m.metric_label else f"${cell.output_value:,.1f}M"
                            if cell.is_baseline:
                                val_str += " ★"
                            row_dict[ch] = val_str
                        else:
                            row_dict[ch] = "INVALID"
                    mat_rows.append(row_dict)
                st.dataframe(pd.DataFrame(mat_rows), use_container_width=True, hide_index=True)

            mc = report_bundle.monte_carlo_result
            if mc and mc.summary_stats:
                st.markdown(f"**Monte Carlo Simulation Summary ({mc.total_iterations} Iterations | Seed: {mc.config.random_seed})**")
                mc_table = []
                ev_s = mc.summary_stats.get("enterprise_value")
                eq_s = mc.summary_stats.get("equity_value")
                sp_s = mc.summary_stats.get("implied_share_price")
                for label, attr, is_sp in [
                    ("Mean", "mean", False),
                    ("Median (P50)", "median", False),
                    ("Std Deviation", "std_dev", False),
                    ("10th Percentile (P10)", "p10", False),
                    ("90th Percentile (P90)", "p90", False),
                ]:
                    mc_table.append({
                        "Statistic": label,
                        "Enterprise Value ($M)": f"${getattr(ev_s, attr):,.1f}M" if ev_s else "-",
                        "Equity Value ($M)": f"${getattr(eq_s, attr):,.1f}M" if eq_s else "-",
                        "Implied Share Price": f"${getattr(sp_s, attr):,.2f}" if sp_s else "-",
                    })
                st.dataframe(pd.DataFrame(mc_table), use_container_width=True, hide_index=True)

            st.markdown("---")

        # 9. Disclosures & Disclaimers
        if sec.include_disclosures_limitations:
            st.markdown("### 8. Data Quality, Disclosures & Important Notices")
            if report_bundle.data_quality_issues:
                st.markdown("**Data Quality Findings:**")
                for issue in report_bundle.data_quality_issues:
                    st.write(f"- {issue}")

            st.info(
                "**Analytical & Regulatory Disclaimers:**\n\n"
                "1. **Not Investment Advice:** This report is compiled for analytical, educational, and financial modeling purposes only. "
                "It does not constitute investment advice, a trade recommendation, or an endorsement of any security.\n"
                "2. **User Input Contingency:** Intrinsic valuation results and forecast projections are strictly conditional on user-supplied "
                "assumptions and historical statements entered into the system.\n"
                "3. **Simulation Limitations:** Monte Carlo iterations and sensitivity matrices describe mathematical variance under specified "
                "parameters and do not represent empirical market return probabilities or guarantees."
            )

    # =========================================================================
    # TAB 3: EXPORT CENTER
    # =========================================================================
    with tab_export:
        st.subheader("📥 Export Center")
        st.markdown(
            "Download institutional-grade report assets and spreadsheets. "
            "All exports accurately reflect the current report configuration and selected model outputs."
        )

        clean_slug = _sanitize_filename(report_bundle.company_name or "Company")
        date_str = active_config.metadata.report_date

        e_col1, e_col2, e_col3 = st.columns(3)

        # 1. PDF Export
        with e_col1:
            st.markdown("#### 📄 Institutional PDF Report")
            st.caption(
                "Printable, multi-page publication document with running headers/footers, "
                "KPI highlight cards, structured financial tables, and disclaimers."
            )
            with st.spinner("Generating printable PDF..."):
                pdf_bytes = PdfReportGenerator.generate_pdf(report_bundle)

            pdf_filename = f"{clean_slug}_Valuation_Report_{date_str}.pdf"
            st.download_button(
                label="📄 Download PDF Report",
                data=pdf_bytes,
                file_name=pdf_filename,
                mime="application/pdf",
                key="btn_download_pdf",
                use_container_width=True,
            )
            st.caption(f"File: `{pdf_filename}` ({len(pdf_bytes) / 1024:.1f} KB)")

        # 2. Dynamic Formula-Linked Excel Model Export
        with e_col2:
            st.markdown("#### ⚡ Dynamic Financial Model (.xlsx)")
            st.caption(
                "Multi-tab spreadsheet with live Excel formulas linking Assumptions to Forecast, "
                "WACC, DCF valuation, and Equity bridge. Supports real-time driver editing in spreadsheet software."
            )
            with st.spinner("Generating dynamic formula-linked model..."):
                dyn_excel_bytes = DynamicExcelModelGenerator.generate_workbook(report_bundle)

            dyn_filename = f"{clean_slug}_Dynamic_DCF_Model_{date_str}.xlsx"
            st.download_button(
                label="⚡ Download Dynamic Model (.xlsx)",
                data=dyn_excel_bytes,
                file_name=dyn_filename,
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                key="btn_download_dyn_excel",
                use_container_width=True,
            )
            st.caption(f"File: `{dyn_filename}` ({len(dyn_excel_bytes) / 1024:.1f} KB)")

        # 3. Static Excel Report & CSV Exports
        with e_col3:
            st.markdown("#### 📊 Static Excel & CSV Exports")
            st.caption("Snapshot tabular workbook and standardized CSV data tables.")

            with st.spinner("Generating static Excel workbook..."):
                excel_bytes = ExcelReportGenerator.generate_workbook(report_bundle)

            excel_filename = f"{clean_slug}_DCF_Financial_Report_{date_str}.xlsx"
            st.download_button(
                label="📊 Download Static Excel (.xlsx)",
                data=excel_bytes,
                file_name=excel_filename,
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                key="btn_download_excel",
                use_container_width=True,
            )
            st.caption(f"File: `{excel_filename}` ({len(excel_bytes) / 1024:.1f} KB)")

            csv_summary = CsvReportGenerator.generate_valuation_summary_csv(report_bundle)
            st.download_button(
                label="📥 Valuation Summary CSV",
                data=csv_summary,
                file_name=f"{clean_slug}_Valuation_Summary_{date_str}.csv",
                mime="text/csv",
                key="btn_download_csv_sum",
                use_container_width=True,
            )

            if report_bundle.forecast_result:
                csv_fc = CsvReportGenerator.generate_forecast_schedule_csv(report_bundle)
                st.download_button(
                    label="📥 Forecast Schedule CSV",
                    data=csv_fc,
                    file_name=f"{clean_slug}_Forecast_Schedule_{date_str}.csv",
                    mime="text/csv",
                    key="btn_download_csv_fc",
                    use_container_width=True,
                )

            if report_bundle.sensitivity_matrix_result:
                csv_sens = CsvReportGenerator.generate_sensitivity_matrix_csv(report_bundle)
                st.download_button(
                    label="📥 Sensitivity Matrix CSV",
                    data=csv_sens,
                    file_name=f"{clean_slug}_Sensitivity_Matrix_{date_str}.csv",
                    mime="text/csv",
                    key="btn_download_csv_sens",
                    use_container_width=True,
                )

        st.markdown("---")
        st.info(
            "💡 **Formula Linking Note:** The **Dynamic Financial Model (.xlsx)** contains active cell formulas "
            "(`=SUM`, `=NPV`, `=IF`, etc.) that automatically recalculate when opened in Microsoft Excel, LibreOffice Calc, "
            "or Google Sheets. Users can adjust highlighted assumption cells directly in their spreadsheet application."
        )

    # =========================================================================
    # TAB 4: SAVED CONFIGURATIONS
    # =========================================================================
    with tab_saved:
        st.subheader("💾 Manage Saved Report Configurations")
        st.markdown(
            "Save named report configurations scoped to this valuation project. "
            "Reloading a configuration restores your metadata, linked model selections, and section choices."
        )

        with st.form("save_report_form"):
            save_name = st.text_input("Configuration Name *", placeholder="e.g. FY2024 Institutional DCF Presentation", key="save_rep_name")
            save_desc = st.text_area("Description (Optional)", placeholder="Notes on audience, scenario selections, or distribution bounds...", key="save_rep_desc")
            btn_save = st.form_submit_button("💾 Save Report Configuration")

            if btn_save:
                if not save_name.strip():
                    st.error("Please provide a name for this report configuration.")
                else:
                    try:
                        ReportService.save_report(
                            project_id=selected_project_id,
                            name=save_name.strip(),
                            config=active_config,
                            description=save_desc.strip() if save_desc else None,
                        )
                        st.success(f"Report configuration '{save_name.strip()}' saved successfully!")
                        st.rerun()
                    except Exception as exc:
                        st.error(f"Error saving report configuration: {exc}")

        st.markdown("---")
        st.subheader("Saved Reports for this Project")
        saved_reports = ReportService.list_reports(selected_project_id)
        if not saved_reports:
            st.info("ℹ️ No saved report configurations for this valuation project.")
        else:
            for rep in saved_reports:
                with st.expander(f"📑 {rep.name} — Title: {rep.title} (Updated: {rep.updated_at.strftime('%Y-%m-%d %H:%M')})", expanded=False):
                    if rep.description:
                        st.markdown(f"**Description:** {rep.description}")
                    st.caption(f"Created: {rep.created_at.strftime('%Y-%m-%d %H:%M')}")

                    act_col1, act_col2 = st.columns([1, 1])
                    with act_col1:
                        if st.button("🔄 Reload This Configuration", key=f"reload_rep_{rep.id}"):
                            try:
                                loaded_cfg = ReportConfig.from_json(rep.config_json)
                                st.session_state["active_report_config"] = loaded_cfg
                                st.session_state["report_config_project_id"] = selected_project_id
                                st.success(f"Reloaded '{rep.name}'. Switch to Configuration or Preview tab.")
                                st.rerun()
                            except Exception as exc:
                                st.error(f"Error loading report configuration: {exc}")
                    with act_col2:
                        if st.button("🗑️ Delete Configuration", key=f"del_rep_{rep.id}"):
                            ReportService.delete_report(rep.id)
                            st.success(f"Deleted report configuration '{rep.name}'.")
                            st.rerun()


if __name__ == "__main__":
    from app.navigation import run_standalone_page
    run_standalone_page("Reports", render_reports_page)
