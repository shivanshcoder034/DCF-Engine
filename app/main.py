"""AI-Powered DCF Valuation and Sensitivity Engine - Application Entry Point.

This module serves as the primary Streamlit shell, establishing the centralized
navigation structure, application layout, status indicators, and modular routing
for all valuation phases.
"""

from __future__ import annotations

import streamlit as st

from app.config import settings
from app.components.badges import render_phase_badge
from app.components.cards import render_placeholder_card
from app.pages.companies import render_companies_page
from app.pages.projects import render_projects_page
from app.pages.financial_data import render_financial_data_page
from app.pages.manual_entry import render_manual_entry_page
from app.pages.import_data import render_import_data_page


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

        render_phase_badge(phase_text="Phase 2 Active", status="Data Layer Ready")

        st.markdown("---")
        st.subheader("Navigation")

        navigation_options = [
            "Home",
            "Company & Financial Data",
            "Historical Analysis",
            "DCF Valuation",
            "WACC",
            "Forecasting",
            "Scenarios",
            "Sensitivity Analysis",
            "Reports & Exports",
        ]

        selected_page = st.radio(
            label="Application Sections",
            options=navigation_options,
            index=0,
            label_visibility="collapsed",
        )

        st.markdown("---")
        st.markdown("### Project Environment")
        st.write(f"**Version:** `{settings.app_version}`")
        st.write(f"**Environment:** `{settings.environment}`")
        st.write(f"**Debug Mode:** `{settings.debug}`")

        st.markdown("---")
        st.caption(
            "© Phase 2 • AI-Powered DCF Valuation Engine. "
            "Financial calculations and analysis models scheduled in subsequent phases."
        )

    return selected_page


def render_home_page() -> None:
    """Render the main landing page, project status, and architectural overview."""
    st.title("AI-Powered DCF Valuation and Sensitivity Engine")
    st.markdown(
        "A rigorous, modular financial modelling platform designed for institutional-grade "
        "Discounted Cash Flow (DCF) valuations, scenario planning, and multi-variable sensitivity analysis."
    )

    # Status Banner
    st.markdown("---")
    st.subheader("📌 Project Status: Phase 2 Active")

    status_col1, status_col2 = st.columns([2, 1])

    with status_col1:
        st.success(
            "**Current Status: Financial Data Management Layer Active**\n\n"
            "Phase 2 establishes persistent company profile management, valuation project workspaces, "
            "atomic historical financial statement storage in SQLite, manual record entry, and multi-period "
            "CSV/Excel file ingestion with automated column mapping, verification, and audit provenance."
        )
        st.warning(
            "**Notice:** Financial ratio calculations, forecasting engines, and DCF calculations are "
            "scheduled for subsequent phases (Phases 3-6). Stored financial figures remain unmutated."
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
        {"Phase": "Phase 2 (Current)", "Title": "Company Profiles & Financial Data", "Focus": "SQLAlchemy persistence, statement records, CSV/Excel imports", "Status": "Complete"},
        {"Phase": "Phase 3", "Title": "Historical Financial Analysis", "Focus": "Ratios, margins, growth trends, working capital cycles", "Status": "Planned"},
        {"Phase": "Phase 4", "Title": "Financial Forecasting & Projections", "Focus": "Driver-based revenue models, OpEx schedules, UFCF projections", "Status": "Planned"},
        {"Phase": "Phase 5", "Title": "WACC & Discount Rate Engine", "Focus": "CAPM, Beta estimation, cost of debt, tax shield, capital weighting", "Status": "Planned"},
        {"Phase": "Phase 6", "Title": "DCF Valuation & Terminal Value Engine", "Focus": "Discounting, Gordon Growth, Exit Multiples, Enterprise/Equity value", "Status": "Planned"},
        {"Phase": "Phase 7", "Title": "Scenario Analysis", "Focus": "Bull/Bear scenarios, parameter overrides, cross-scenario comparisons", "Status": "Planned"},
        {"Phase": "Phase 8", "Title": "Sensitivity Analysis & Simulation", "Focus": "2D sensitivity matrices, driver tornado charts, Monte Carlo", "Status": "Planned"},
        {"Phase": "Phase 9", "Title": "Financial Dashboards & Visualizations", "Focus": "Interactive Plotly valuation and financial statement dashboards", "Status": "Planned"},
        {"Phase": "Phase 10", "Title": "Dynamic Excel Model Exports", "Focus": "Automated openpyxl workbooks with active spreadsheet formulas", "Status": "Planned"},
        {"Phase": "Phase 11", "Title": "Valuation Reports & Memos", "Focus": "Institutional PDF/Markdown summary memos and audit trails", "Status": "Planned"},
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
        render_placeholder_card(
            title="📊 Historical Financial Analysis",
            phase="Phase 3",
            target_module="src.analysis",
            description=(
                "Diagnostic tooling for reviewing historical operational performance, "
                "cost structure dynamics, profitability trends, and balance sheet efficiency."
            ),
            planned_capabilities=[
                "Compound Annual Growth Rate (CAGR) calculations for revenue, gross profit, and EBIT.",
                "Margin evolution tracking (Gross, EBITDA, Operating, and Net margins).",
                "Working capital cycle metrics (DSO, DIO, DPO, and Cash Conversion Cycle).",
                "Return metrics including ROIC, ROCE, and ROE.",
            ],
            prerequisites=[
                "Phase 2 Financial statement storage and normalization (Ready)",
            ],
        )

    elif selected_page == "DCF Valuation":
        render_placeholder_card(
            title="💰 DCF Valuation Engine",
            phase="Phase 6",
            target_module="src.valuation",
            description=(
                "Core valuation engine computing Enterprise Value, Net Debt bridges, "
                "and Equity Value per share based on discounted Unlevered Free Cash Flows."
            ),
            planned_capabilities=[
                "Present value computation of projected explicit forecast period cash flows.",
                "Perpetual Growth (Gordon Growth Model) terminal value formulation.",
                "Exit Multiple Method terminal value formulation (e.g. EV/EBITDA).",
                "Bridge from Enterprise Value to Equity Value (Cash, Debt, Minority Interest, Non-operating assets).",
                "Implied per-share intrinsic value vs. current market pricing.",
            ],
            prerequisites=[
                "Phase 4 Unlevered Free Cash Flow projections",
                "Phase 5 Weighted Average Cost of Capital (WACC)",
            ],
        )

    elif selected_page == "WACC":
        render_placeholder_card(
            title="⚖️ WACC Estimation & Discount Rate",
            phase="Phase 5",
            target_module="src.valuation",
            description=(
                "Estimation of the Weighted Average Cost of Capital (WACC) to establish "
                "the appropriate discount rate reflecting enterprise operating and financial risk."
            ),
            planned_capabilities=[
                "Cost of Equity calculation via Capital Asset Pricing Model (CAPM).",
                "Beta estimation (raw beta, adjusted beta, unlevered and relevered industry beta).",
                "Pre-tax and effective after-tax Cost of Debt calculation.",
                "Target capital structure weighting based on market values of equity and debt.",
            ],
            prerequisites=[
                "Phase 2 Company balance sheet and capital structure records (Ready)",
            ],
        )

    elif selected_page == "Forecasting":
        render_placeholder_card(
            title="📈 Forecasting & Free Cash Flow Projections",
            phase="Phase 4",
            target_module="src.forecasting",
            description=(
                "Driver-based multi-year financial forecasting generating explicit "
                "Unlevered Free Cash Flow (UFCF) schedules."
            ),
            planned_capabilities=[
                "Revenue projections driven by growth rate schedules and segment models.",
                "Operating expense forecasting and EBITDA/EBIT bridge modeling.",
                "Depreciation, Amortization, and Capital Expenditure (CapEx) schedules.",
                "Net Working Capital (NWC) projections and annual cash flow adjustments.",
                "Formulaic derivation of Unlevered Free Cash Flow: NOPAT + D&A - CapEx - ΔNWC.",
            ],
            prerequisites=[
                "Phase 3 Historical financial analysis and baseline ratios",
            ],
        )

    elif selected_page == "Scenarios":
        render_placeholder_card(
            title="🔀 Scenario Modelling",
            phase="Phase 7",
            target_module="src.scenarios",
            description=(
                "Multi-scenario framework allowing users to define, compare, and stress-test "
                "different operational and economic environments."
            ),
            planned_capabilities=[
                "Preset scenario profiles: Base Case, Bull Case, Bear Case.",
                "Custom scenario parameter overrides (revenue growth delta, margin expansion/contraction, WACC shifts).",
                "Comparative visualization of key financial metrics across scenarios.",
            ],
            prerequisites=[
                "Phase 4 Projection engine",
                "Phase 6 DCF valuation module",
            ],
        )

    elif selected_page == "Sensitivity Analysis":
        render_placeholder_card(
            title="🎯 Sensitivity Analysis & Simulation",
            phase="Phase 8",
            target_module="src.sensitivity",
            description=(
                "Rigorous multi-dimensional sensitivity matrices evaluating valuation volatility "
                "in response to shifts in foundational assumptions."
            ),
            planned_capabilities=[
                "Two-dimensional sensitivity tables (e.g., WACC vs. Long-Term Terminal Growth Rate).",
                "Exit Multiple sensitivity matrices (e.g., WACC vs. Terminal EV/EBITDA Multiple).",
                "Driver impact ranking and tornado charts.",
                "Monte Carlo valuation distribution simulation.",
            ],
            prerequisites=[
                "Phase 6 DCF valuation engine",
            ],
        )

    elif selected_page == "Reports & Exports":
        render_placeholder_card(
            title="📑 Reports & Financial Model Exports",
            phase="Phase 10 & 11",
            target_module="src.exports",
            description=(
                "Institutional-quality financial model exports to Excel and comprehensive "
                "executive summary documentation."
            ),
            planned_capabilities=[
                "Automated Excel financial model generation with active formulas via openpyxl.",
                "Executive valuation memo generation with charts and tables.",
                "Audit trail export of all input assumptions and valuation bridges.",
            ],
            prerequisites=[
                "Phase 6 DCF valuation engine",
                "Phase 7 & 8 Scenario and sensitivity outputs",
            ],
        )


if __name__ == "__main__":
    main()
