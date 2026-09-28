"""Historical Financial Analysis page.

Visualizes multi-period income statements, balance sheets, cash flows, profitability margins,
working capital cycles, and cash flow indicators with interactive Plotly charts and audit diagnostics.
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
from src.analysis.formatting import (
    generate_balance_sheet_table,
    generate_cash_flow_table,
    generate_efficiency_table,
    generate_income_statement_table,
)
from src.data.schemas import DataClassification, PeriodType
from src.data.services import ProjectService


def render_historical_analysis_page() -> None:
    """Render the Historical Financial Analysis interface."""
    st.header("📈 Historical Financial Analysis")
    st.markdown(
        "Analyze historical financial performance, margin evolution, working capital efficiency, "
        "and cash flow dynamics. All metrics are computed deterministically from verified stored records."
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
            key="hist_analysis_project_select",
        )
        st.session_state["selected_project_id"] = selected_project_id

    current_proj = ProjectService.get_project(selected_project_id)
    comp = current_proj.company if current_proj else None
    base_currency = comp.currency if comp else "USD"

    with col_curr:
        st.write(f"**Reporting Currency:** `{base_currency}`")
        st.write(f"**Fiscal Year End:** `{comp.fiscal_year_end if comp else 'Dec 31'}`")

    # 2. Scope & Filters
    st.markdown("---")
    f1, f2, f3 = st.columns(3)
    with f1:
        frequency = st.selectbox(
            "Reporting Frequency",
            options=[PeriodType.ANNUAL.value, PeriodType.QUARTERLY.value],
            format_func=lambda x: PeriodType.display_name(x),
            key="hist_freq_select",
        )
    with f2:
        classification = st.selectbox(
            "Data Classification",
            options=[c.value for c in DataClassification],
            format_func=lambda x: DataClassification.display_name(x),
            key="hist_class_select",
        )
    with f3:
        scale_option = st.selectbox(
            "Table Display Scale",
            options=["Millions (M)", "Thousands (K)", "Exact Units"],
            index=0,
            key="hist_scale_select",
        )

    scale_divisor = 1_000_000.0 if "Millions" in scale_option else (1_000.0 if "Thousands" in scale_option else 1.0)
    scale_label = "Millions" if "Millions" in scale_option else ("Thousands" if "Thousands" in scale_option else "Units")

    # 3. Execute Analysis Engine
    try:
        bundle = HistoricalAnalysisEngine.analyze_project(
            project_id=selected_project_id,
            period_type=frequency,
            data_classification=classification,
            selected_currency=base_currency,
        )
    except Exception as exc:
        st.error(f"Error computing historical analysis: {exc}")
        return

    # Check if records exist
    if not bundle.periods:
        st.info(
            f"ℹ️ No {PeriodType.display_name(frequency)} records found for classification '{DataClassification.display_name(classification)}'. "
            "Please go to **Company & Financial Data** to enter or import historical statements."
        )
        return

    # 4. Executive Performance Cards (Latest Period)
    latest_period = bundle.periods[-1]
    latest_metrics = bundle.metrics_by_period.get(latest_period.label, {})
    latest_wc = bundle.working_capital.get(latest_period.label)
    latest_cf = bundle.cash_flow_metrics.get(latest_period.label)

    st.markdown(f"### 📊 Key Performance Indicators ({latest_period.label})")
    kpi_c1, kpi_c2, kpi_c3, kpi_c4, kpi_c5 = st.columns(5)

    with kpi_c1:
        rev_m = latest_metrics.get("revenue")
        growth_m = latest_metrics.get("revenue_growth")
        rev_str = f"{bundle.reporting_currency} {rev_m.value / scale_divisor:,.1f} {scale_label[0]}" if rev_m and rev_m.value is not None else "—"
        growth_str = f"{growth_m.value:+.1f}% YoY" if growth_m and growth_m.value is not None else "—"
        st.metric("Revenue", rev_str, delta=growth_str if growth_m and growth_m.value is not None else None)

    with kpi_c2:
        gm = latest_metrics.get("gross_margin")
        gm_str = f"{gm.value:.1f}%" if gm and gm.value is not None else "—"
        st.metric("Gross Margin", gm_str)

    with kpi_c3:
        ebitda_m = latest_metrics.get("ebitda_margin")
        ebitda_str = f"{ebitda_m.value:.1f}%" if ebitda_m and ebitda_m.value is not None else "—"
        st.metric("EBITDA Margin", ebitda_str)

    with kpi_c4:
        nm = latest_metrics.get("net_margin")
        nm_str = f"{nm.value:.1f}%" if nm and nm.value is not None else "—"
        st.metric("Net Profit Margin", nm_str)

    with kpi_c5:
        cfo_val = latest_cf.operating_cash_flow if latest_cf else None
        cfo_str = f"{bundle.reporting_currency} {cfo_val / scale_divisor:,.1f} {scale_label[0]}" if cfo_val is not None else "—"
        st.metric("Operating Cash Flow", cfo_str)

    # Multi-year CAGR pill if available
    if bundle.cagr_results:
        cagr_cols = st.columns(len(bundle.cagr_results))
        for idx, (code, res) in enumerate(bundle.cagr_results.items()):
            with cagr_cols[idx]:
                if res.value is not None:
                    st.info(f"**{res.metric_name}:** `{res.value:+.1f}%` ({res.explanation})")

    st.markdown("---")

    # 5. Tabbed Interface for Charts, Tables, and Diagnostics
    tab_charts, tab_tables, tab_audit = st.tabs([
        "📈 Interactive Charts",
        "📑 Financial Statement Tables",
        "🔍 Data Quality & Audit Diagnostics",
    ])

    with tab_charts:
        chart_p_labels = [p.label for p in bundle.periods]

        # Chart 1: Revenue & YoY Growth
        st.subheader("1. Revenue Trend and YoY Growth Rate")
        rev_values = [bundle.metrics_by_period[p]["revenue"].value for p in chart_p_labels]
        growth_values = [bundle.metrics_by_period[p]["revenue_growth"].value for p in chart_p_labels]

        scaled_rev = [(v / scale_divisor) if v is not None else None for v in rev_values]

        fig_rev = make_subplots(specs=[[{"secondary_y": True}]])
        fig_rev.add_trace(
            go.Bar(
                x=chart_p_labels,
                y=scaled_rev,
                name=f"Revenue ({bundle.reporting_currency} {scale_label})",
                marker_color="#1E3A8A",
            ),
            secondary_y=False,
        )
        fig_rev.add_trace(
            go.Scatter(
                x=chart_p_labels,
                y=growth_values,
                name="YoY Growth Rate (%)",
                mode="lines+markers",
                line=dict(color="#10B981", width=3),
                marker=dict(size=8),
            ),
            secondary_y=True,
        )
        fig_rev.update_layout(
            height=380,
            margin=dict(l=40, r=40, t=30, b=40),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            hovermode="x unified",
        )
        fig_rev.update_yaxes(title_text=f"Revenue ({bundle.reporting_currency} {scale_label})", secondary_y=False)
        fig_rev.update_yaxes(title_text="YoY Growth (%)", secondary_y=True)
        st.plotly_chart(fig_rev, use_container_width=True)

        st.markdown("---")

        # Chart 2: Profitability Margins Evolution
        st.subheader("2. Profitability Margins Evolution")
        gm_vals = [bundle.metrics_by_period[p]["gross_margin"].value for p in chart_p_labels]
        ebitda_m_vals = [bundle.metrics_by_period[p]["ebitda_margin"].value for p in chart_p_labels]
        ebit_m_vals = [bundle.metrics_by_period[p]["ebit_margin"].value for p in chart_p_labels]
        net_m_vals = [bundle.metrics_by_period[p]["net_margin"].value for p in chart_p_labels]

        fig_margins = go.Figure()
        fig_margins.add_trace(go.Scatter(x=chart_p_labels, y=gm_vals, name="Gross Margin %", mode="lines+markers", line=dict(color="#2563EB", width=2)))
        fig_margins.add_trace(go.Scatter(x=chart_p_labels, y=ebitda_m_vals, name="EBITDA Margin %", mode="lines+markers", line=dict(color="#7C3AED", width=2)))
        fig_margins.add_trace(go.Scatter(x=chart_p_labels, y=ebit_m_vals, name="EBIT Margin %", mode="lines+markers", line=dict(color="#F59E0B", width=2)))
        fig_margins.add_trace(go.Scatter(x=chart_p_labels, y=net_m_vals, name="Net Profit Margin %", mode="lines+markers", line=dict(color="#10B981", width=2)))

        fig_margins.update_layout(
            height=380,
            margin=dict(l=40, r=40, t=30, b=40),
            yaxis_title="Margin (%)",
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            hovermode="x unified",
        )
        st.plotly_chart(fig_margins, use_container_width=True)

        st.markdown("---")

        # Chart 3: Cash Flow from Operations vs CapEx
        st.subheader("3. Operating Cash Flow vs. Capital Expenditure")
        cfo_vals = [(bundle.cash_flow_metrics[p].operating_cash_flow / scale_divisor) if bundle.cash_flow_metrics[p].operating_cash_flow is not None else None for p in chart_p_labels]
        capex_vals = [(bundle.cash_flow_metrics[p].capex_magnitude / scale_divisor) if bundle.cash_flow_metrics[p].capex_magnitude is not None else None for p in chart_p_labels]
        fcf_vals = [(bundle.cash_flow_metrics[p].cfo_less_capex / scale_divisor) if bundle.cash_flow_metrics[p].cfo_less_capex is not None else None for p in chart_p_labels]

        fig_cf = go.Figure()
        fig_cf.add_trace(go.Bar(x=chart_p_labels, y=cfo_vals, name=f"Operating Cash Flow (CFO)", marker_color="#0284C7"))
        fig_cf.add_trace(go.Bar(x=chart_p_labels, y=capex_vals, name=f"CapEx Magnitude", marker_color="#DC2626"))
        fig_cf.add_trace(go.Scatter(x=chart_p_labels, y=fcf_vals, name="CFO Less CapEx", mode="lines+markers", line=dict(color="#16A34A", width=3)))

        fig_cf.update_layout(
            height=380,
            barmode="group",
            margin=dict(l=40, r=40, t=30, b=40),
            yaxis_title=f"Amount ({bundle.reporting_currency} {scale_label})",
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            hovermode="x unified",
        )
        st.plotly_chart(fig_cf, use_container_width=True)

        st.markdown("---")

        # Chart 4: Working Capital Efficiency & Cash Conversion Cycle
        st.subheader("4. Working Capital Efficiency (DSO, DIO, DPO, CCC)")
        dso_vals = [bundle.working_capital[p].dso for p in chart_p_labels]
        dio_vals = [bundle.working_capital[p].dio for p in chart_p_labels]
        dpo_vals = [bundle.working_capital[p].dpo for p in chart_p_labels]
        ccc_vals = [bundle.working_capital[p].cash_conversion_cycle for p in chart_p_labels]

        has_efficiency_data = any(v is not None for v in ccc_vals)
        if has_efficiency_data:
            fig_eff = go.Figure()
            fig_eff.add_trace(go.Bar(x=chart_p_labels, y=dso_vals, name="DSO (Receivables)", marker_color="#3B82F6"))
            fig_eff.add_trace(go.Bar(x=chart_p_labels, y=dio_vals, name="DIO (Inventory)", marker_color="#F59E0B"))
            fig_eff.add_trace(go.Bar(x=chart_p_labels, y=dpo_vals, name="DPO (Payables)", marker_color="#EF4444"))
            fig_eff.add_trace(go.Scatter(x=chart_p_labels, y=ccc_vals, name="Cash Conversion Cycle (CCC)", mode="lines+markers", line=dict(color="#0F172A", width=3)))

            fig_eff.update_layout(
                height=380,
                barmode="group",
                margin=dict(l=40, r=40, t=30, b=40),
                yaxis_title="Days",
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                hovermode="x unified",
            )
            st.plotly_chart(fig_eff, use_container_width=True)
        else:
            st.info("Working capital efficiency metrics (DSO/DIO/DPO) require Accounts Receivable, Inventory, Payables, and COGS line items.")

    with tab_tables:
        st.caption(f"All monetary figures presented in **{bundle.reporting_currency} {scale_label}**. Derived figures are explicitly identified.")

        # Income Statement
        st.subheader("📑 Historical Income Statement & Margins")
        df_is = generate_income_statement_table(bundle, scale_divisor=scale_divisor)
        st.dataframe(df_is, use_container_width=True, hide_index=True)

        st.markdown("---")

        # Balance Sheet & NWC
        st.subheader("🏛️ Historical Balance Sheet & Working Capital")
        df_bs = generate_balance_sheet_table(bundle, scale_divisor=scale_divisor)
        st.dataframe(df_bs, use_container_width=True, hide_index=True)

        st.markdown("---")

        # Cash Flow & Free Cash Flow
        st.subheader("💵 Historical Cash Flow & Free Cash Flow Estimates")
        st.caption(
            "Note: UFCF represents a historical analytical estimate [EBIT*(1-T) + D&A - CapEx - ΔNWC] "
            "based purely on historical records, not a future cash flow projection."
        )
        df_cf = generate_cash_flow_table(bundle, scale_divisor=scale_divisor)
        st.dataframe(df_cf, use_container_width=True, hide_index=True)

        st.markdown("---")

        # Efficiency Indicators
        st.subheader("⏱️ Working Capital Efficiency Diagnostics")
        df_eff = generate_efficiency_table(bundle)
        st.dataframe(df_eff, use_container_width=True, hide_index=True)

    with tab_audit:
        st.subheader("🔍 Data Quality, Consistency & Integrity Audit")
        st.markdown(
            "The historical analysis engine performs automated audits on reporting period continuity, "
            "accounting balance sheet equilibrium, currency consistency, and missing input items."
        )

        if not bundle.quality_issues:
            st.success("✅ **Audit Clean:** No accounting discrepancies, currency conflicts, or period gaps detected.")
        else:
            for issue in bundle.quality_issues:
                icon = "⚠️" if issue.severity == "warning" else ("ℹ️" if issue.severity == "info" else "❌")
                category_label = issue.category.replace("_", " ").title()
                st.warning(f"**{icon} {category_label}:** {issue.message}")

        # Summary of Available Periods and Records
        st.markdown("---")
        st.markdown("#### Audit Metadata")
        st.write(f"**Target Company:** {bundle.company_name} ({bundle.ticker or 'No Ticker'})")
        st.write(f"**Valuation Project:** {bundle.project_name} (ID: {bundle.project_id})")
        st.write(f"**Data Classification Analyzed:** `{bundle.data_classification}`")
        st.write(f"**Reporting Frequency:** `{bundle.period_type}`")
        st.write(f"**Chronological Periods Processed ({len(bundle.periods)}):** {', '.join(p.label for p in bundle.periods)}")


if __name__ == "__main__":
    from app.navigation import run_standalone_page
    run_standalone_page("Historical Analysis", render_historical_analysis_page)
