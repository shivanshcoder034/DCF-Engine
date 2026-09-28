"""AI-Powered DCF Valuation and Sensitivity Engine - Application Entry Point.

This module serves as the primary Streamlit shell, establishing the centralized
navigation structure, application layout, status indicators, and modular routing
for all valuation phases.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Ensure repository root is in sys.path so app and src packages resolve reliably
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

import streamlit as st

from app.config import settings
from app.components.badges import render_phase_badge
from app.components.cards import render_placeholder_card
from app.pages.companies import render_companies_page
from app.pages.projects import render_projects_page
from app.pages.financial_data import render_financial_data_page
from app.pages.manual_entry import render_manual_entry_page
from app.pages.import_data import render_import_data_page
from app.pages.historical_analysis import render_historical_analysis_page
from app.pages.forecasting import render_forecasting_page
from app.pages.wacc import render_wacc_page
from app.pages.dcf import render_dcf_page
from app.pages.scenarios import render_scenarios_page
from app.pages.sensitivity import render_sensitivity_page
from app.pages.reports import render_reports_page


def setup_page_configuration() -> None:
    """Configure Streamlit page metadata, layout, and initial state."""
    st.set_page_config(
        page_title="AI-Powered DCF Engine",
        page_icon="📊",
        layout="wide",
        initial_sidebar_state="expanded",
    )


def render_sidebar() -> str:
    """Render sidebar branding, project information, and navigation menu."""
    with st.sidebar:
        st.title("💼 DCF Engine")
        st.caption("Valuation & Sensitivity Engine")

        render_phase_badge(phase_text="Phase 9 Active", status="Reporting Engine Ready")

        st.markdown("---")
        st.subheader("Navigation")

        navigation_options = [
            "Home",
            "Company & Financial Data",
            "Historical Analysis",
            "Forecasting",
            "WACC",
            "DCF Valuation",
            "Scenarios",
            "Sensitivity Analysis",
            "Reports & Exports",
        ]

        default_nav_idx = 0
        if "app_nav_selection" in st.session_state and st.session_state["app_nav_selection"] in navigation_options:
            default_nav_idx = navigation_options.index(st.session_state["app_nav_selection"])
            del st.session_state["app_nav_selection"]

        selected_page = st.radio(
            label="Application Sections",
            options=navigation_options,
            index=default_nav_idx,
            label_visibility="collapsed",
        )

        st.markdown("---")
        st.markdown("### Project Environment")
        st.write(f"**Version:** `{settings.app_version}`")
        st.write(f"**Environment:** `{settings.environment}`")
        st.write(f"**Debug Mode:** `{settings.debug}`")

        st.markdown("---")
        st.caption(
            "© Phase 9 • AI-Powered DCF Valuation Engine. "
            "Reporting, presentation & export engine active."
        )

    return selected_page


def render_home_page() -> None:
    """Render the main landing page, project status, and architectural overview."""
    st.title("AI-Powered DCF Valuation and Sensitivity Engine")
    st.markdown(
        "A rigorous, modular financial modelling platform designed for institutional-grade "
        "Discounted Cash Flow (DCF) valuations, scenario planning, multi-variable sensitivity analysis, "
        "and automated presentation-grade exports."
    )

    # Status Banner
    st.markdown("---")
    st.subheader("📌 Project Status: Phase 9 Active")

    status_col1, status_col2 = st.columns([2, 1])

    with status_col1:
        st.success(
            "**Current Status: Reporting, Presentation & Export Engine Active**\n\n"
            "Phase 9 delivers automated report compilation and multi-format export capabilities. "
            "Analysts can configure customized valuation reports selecting underlying historical analyses, "
            "forecasts, WACC estimations, DCF valuation cases, scenario comparisons, and sensitivity simulations. "
            "Export formats include institutional multi-page PDF memorandums, structured multi-tab Excel financial "
            "model workbooks (.xlsx), and modular CSV tables."
        )
        st.info(
            "**Notice:** Phase 10 will deliver advanced interactive financial dashboards and dynamic spreadsheet formula linking. "
            "Valuation reports and exported models represent analytical evaluations based on user-supplied "
            "assumptions and not certified investment advice."
        )

    with status_col2:
        st.markdown("#### System Configuration")
        config_summary = settings.summary()
        for key, value in config_summary.items():
            st.markdown(f"**{key}:** `{value}`")

    st.markdown("---")
    st.subheader("🗺️ 12-Phase Architectural Roadmap")

    roadmap_data = [
        {"Phase": "Phase 1", "Title": "Project Foundation & Architecture", "Focus": "Repository structure, configuration, shell, and docs", "Status": "Complete"},
        {"Phase": "Phase 2", "Title": "Company Profiles & Financial Data", "Focus": "SQLAlchemy persistence, statement records, CSV/Excel imports", "Status": "Complete"},
        {"Phase": "Phase 3", "Title": "Historical Financial Analysis", "Focus": "Growth, margins, working capital cycles, cash flow analysis", "Status": "Complete"},
        {"Phase": "Phase 4", "Title": "Financial Forecasting & Projections", "Focus": "Driver-based revenue models, OpEx schedules, UFCF projections", "Status": "Complete"},
        {"Phase": "Phase 5", "Title": "WACC & Discount Rate Engine", "Focus": "CAPM, Beta estimation, cost of debt, tax shield, capital weighting", "Status": "Complete"},
        {"Phase": "Phase 6", "Title": "DCF Valuation & Terminal Value Engine", "Focus": "Discounting, Gordon Growth, Exit Multiples, Enterprise/Equity value", "Status": "Complete"},
        {"Phase": "Phase 7", "Title": "Scenario Analysis (Base / Bull / Bear)", "Focus": "Bull/Bear scenarios, parameter overrides, cross-scenario comparisons", "Status": "Complete"},
        {"Phase": "Phase 8", "Title": "Sensitivity Analysis & Simulation", "Focus": "2D sensitivity matrices, driver heatmaps, Monte Carlo", "Status": "Complete"},
        {"Phase": "Phase 9 (Current)", "Title": "Reporting, Presentation & Export Engine", "Focus": "Multi-page PDF reports, openpyxl Excel models, CSVs, in-app preview", "Status": "Complete"},
        {"Phase": "Phase 10 (Next)", "Title": "Financial Dashboards & Interactive Visualizations", "Focus": "Interactive Plotly valuation and financial statement dashboards", "Status": "Planned"},
        {"Phase": "Phase 11", "Title": "Dynamic Excel Model Formula Linking", "Focus": "Automated openpyxl workbooks with active spreadsheet formulas", "Status": "Planned"},
        {"Phase": "Phase 12", "Title": "AI-Assisted Document & Filings Analysis", "Focus": "Automated 10-K extraction, footnote parsing, and risk commentary", "Status": "Planned"},
    ]

    for item in roadmap_data:
        cols = st.columns([1.5, 2.8, 3.8, 1.2])
        cols[0].markdown(f"**{item['Phase']}**")
        cols[1].markdown(item["Title"])
        cols[2].caption(item["Focus"])
        if item["Status"] == "Complete":
            cols[3].markdown("🟢 `Complete`")
        else:
            cols[3].markdown("⏳ `Planned`")


def render_company_and_financial_data_section() -> None:
    """Render the functional Company and Financial Data Management hub."""
    sub_section = st.radio(
        label="Data Management Sub-Modules",
        options=[
            "🏢 Companies",
            "📁 Valuation Projects",
            "📊 Historical Financial Records",
            "✍️ Manual Data Entry",
            "📥 Import (CSV / Excel)",
        ],
        horizontal=True,
        key="data_mgmt_sub_nav",
    )

    st.markdown("---")

    if sub_section == "🏢 Companies":
        render_companies_page()
    elif sub_section == "📁 Valuation Projects":
        render_projects_page()
    elif sub_section == "📊 Historical Financial Records":
        render_financial_data_page()
    elif sub_section == "✍️ Manual Data Entry":
        render_manual_entry_page()
    elif sub_section == "📥 Import (CSV / Excel)":
        render_import_data_page()


def main() -> None:
    """Main application dispatcher."""
    setup_page_configuration()
    selected_page = render_sidebar()

    if selected_page == "Home":
        render_home_page()

    elif selected_page == "Company & Financial Data":
        render_company_and_financial_data_section()

    elif selected_page == "Historical Analysis":
        render_historical_analysis_page()

    elif selected_page == "Forecasting":
        render_forecasting_page()

    elif selected_page == "WACC":
        render_wacc_page()

    elif selected_page == "DCF Valuation":
        render_dcf_page()

    elif selected_page == "Scenarios":
        render_scenarios_page()

    elif selected_page == "Sensitivity Analysis":
        render_sensitivity_page()

    elif selected_page == "Reports & Exports":
        render_reports_page()


if __name__ == "__main__":
    import streamlit.runtime
    if not streamlit.runtime.exists():
        from streamlit.web import cli as stcli
        sys.argv = ["streamlit", "run", str(Path(__file__).resolve()), *sys.argv[1:]]
        sys.exit(stcli.main())
    else:
        main()
