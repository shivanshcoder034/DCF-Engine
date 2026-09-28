"""Historical Financial Data records viewer and inspector.

Displays normalized financial records for a selected valuation project, with statement,
period, and classification filtering, unit scaling, provenance inspection, and record editing.
"""

from __future__ import annotations

import streamlit as st
import pandas as pd

from src.data.schemas import (
    DataClassification,
    FinancialUnit,
    PeriodType,
    StatementType,
)
from src.data.services import FinancialDataService, ProjectService


def render_financial_data_page() -> None:
    """Render the Historical Financial Data Records management view."""
    st.header("📊 Historical Financial Records")
    st.markdown(
        "Inspect, filter, edit, and audit historical financial statements linked to an active valuation project. "
        "Values are presented with explicit reporting currencies, scale units, and provenance tracking."
    )

    # Project Selector
    all_projects = ProjectService.list_projects()
    if not all_projects:
        st.warning("⚠️ No valuation projects found. Please create a company and project first.")
        return

    project_map = {p.id: f"{p.name} ({p.company.name if p.company else 'N/A'})" for p in all_projects}

    default_proj_id = st.session_state.get("selected_project_id")
    if default_proj_id not in project_map:
        default_proj_id = all_projects[0].id

    selected_project_id = st.selectbox(
        "Active Valuation Project *",
        options=list(project_map.keys()),
        index=list(project_map.keys()).index(default_proj_id),
        format_func=lambda pid: project_map[pid],
        key="financial_data_active_project",
    )
    st.session_state["selected_project_id"] = selected_project_id

    current_project = ProjectService.get_project(selected_project_id)
    if not current_project:
        st.error("Project not found.")
        return

    # Project Context Bar
    comp = current_project.company
    st.info(
        f"**Target Company:** {comp.name} {f'({comp.ticker})' if comp and comp.ticker else ''} | "
        f"**Reporting Currency:** `{comp.currency if comp else 'USD'}` | "
        f"**Fiscal Year End:** `{comp.fiscal_year_end if comp else 'Dec 31'}` | "
        f"**Project Status:** `{current_project.status}`"
    )

    tab_records, tab_batches = st.tabs(["📑 Financial Statement Records", "📦 Import Batches & Provenance"])

    with tab_records:
        # Filters
        f1, f2, f3 = st.columns(3)
        with f1:
            statement_filter = st.selectbox(
                "Statement Filter",
                options=["All", StatementType.INCOME_STATEMENT.value, StatementType.BALANCE_SHEET.value, StatementType.CASH_FLOW_STATEMENT.value],
                format_func=lambda x: "All Statements" if x == "All" else StatementType.display_name(x),
            )
        with f2:
            period_filter = st.selectbox(
                "Period Frequency",
                options=["All", PeriodType.ANNUAL.value, PeriodType.QUARTERLY.value],
                format_func=lambda x: "All Frequencies" if x == "All" else PeriodType.display_name(x),
            )
        with f3:
            classification_filter = st.selectbox(
                "Classification Filter",
                options=["All"] + [c.value for c in DataClassification],
                format_func=lambda x: "All Classifications" if x == "All" else DataClassification.display_name(x),
            )

        # Query records
        records = FinancialDataService.list_records(
            project_id=selected_project_id,
            statement_type=None if statement_filter == "All" else statement_filter,
            period_type=None if period_filter == "All" else period_filter,
            classification=None if classification_filter == "All" else classification_filter,
        )

        if not records:
            st.info(
                "No financial records found matching the selected filters. "
                "Use **Manual Entry** or **CSV/Excel Import** to populate historical statements."
            )
        else:
            st.write(f"Showing **{len(records)}** records:")

            # Render Table View
            table_rows = []
            for r in records:
                multiplier = FinancialUnit.multiplier(r.unit)
                unit_label = f"({r.unit.title()})" if r.unit != "units" else ""
                table_rows.append({
                    "ID": r.id,
                    "Statement": StatementType.display_name(r.statement_type),
                    "Line Item": r.display_name,
                    "Code": r.line_item_code,
                    "Period End": r.period_end_date.strftime("%Y-%m-%d"),
                    "Type": r.period_type.capitalize(),
                    "Value": f"{r.value:,.2f}",
                    "Scale & Currency": f"{r.currency} {unit_label}",
                    "Classification": DataClassification.display_name(r.data_classification),
                    "Source": r.source_type.replace("_", " ").title(),
                })

            df_display = pd.DataFrame(table_rows)
            st.dataframe(df_display, use_container_width=True, hide_index=True)

            # Record Detail & Modification
            st.markdown("---")
            st.subheader("🔍 Inspect & Edit Individual Record")
            record_options = {r.id: f"#{r.id} | {r.display_name} ({r.period_end_date}) — {r.currency} {r.value:,.2f}" for r in records}

            target_rec_id = st.selectbox(
                "Select Record to Manage",
                options=list(record_options.keys()),
                format_func=lambda x: record_options[x],
            )

            target_rec = FinancialDataService.get_record(target_rec_id)
            if target_rec:
                with st.expander(f"Record Details (ID: {target_rec.id})", expanded=True):
                    r_col1, r_col2 = st.columns(2)
                    with r_col1:
                        st.markdown(f"**Statement:** {StatementType.display_name(target_rec.statement_type)}")
                        st.markdown(f"**Line Item:** {target_rec.display_name} (`{target_rec.line_item_code}`)")
                        st.markdown(f"**Period Span:** `{target_rec.period_start_date}` to `{target_rec.period_end_date}`")
                        st.markdown(f"**Classification:** `{DataClassification.display_name(target_rec.data_classification)}`")
                    with r_col2:
                        st.markdown(f"**Value:** `{target_rec.value:,.4f}` {target_rec.currency}")
                        st.markdown(f"**Unit Scale:** `{target_rec.unit}`")
                        st.markdown(f"**Source Provenance:** `{target_rec.source_type}` (Batch: `{target_rec.import_batch_id or 'None'}`)")
                        st.markdown(f"**Source Notes:** {target_rec.source_reference or 'None recorded'}")

                    # Modification popovers
                    e_col, d_col = st.columns([1, 1])

                    with e_col:
                        with st.popover("✏️ Edit Value & Metadata"):
                            with st.form(f"edit_rec_form_{target_rec.id}"):
                                new_val = st.number_input("Financial Numeric Value", value=float(target_rec.value), format="%.4f")
                                new_disp = st.text_input("Display Name", value=target_rec.display_name)
                                new_class = st.selectbox(
                                    "Classification",
                                    options=[c.value for c in DataClassification],
                                    index=[c.value for c in DataClassification].index(target_rec.data_classification),
                                    format_func=lambda x: DataClassification.display_name(x),
                                )
                                new_unit = st.selectbox(
                                    "Unit / Scale",
                                    options=[u.value for u in FinancialUnit],
                                    index=[u.value for u in FinancialUnit].index(target_rec.unit),
                                )
                                new_ref = st.text_input("Source Reference Notes", value=target_rec.source_reference or "")

                                submit_rec_edit = st.form_submit_button("Update Record")
                                if submit_rec_edit:
                                    try:
                                        FinancialDataService.update_record(
                                            data_point_id=target_rec.id,
                                            updates={
                                                "value": new_val,
                                                "display_name": new_disp.strip(),
                                                "data_classification": new_class,
                                                "unit": new_unit,
                                                "source_reference": new_ref.strip() or None,
                                            },
                                        )
                                        st.success("Record updated.")
                                        st.rerun()
                                    except Exception as exc:
                                        st.error(f"Update failed: {exc}")

                    with d_col:
                        with st.popover("🗑️ Delete Record"):
                            st.warning(f"Permanently delete record #{target_rec.id} ({target_rec.display_name})?")
                            if st.button("Confirm Delete", key=f"del_rec_{target_rec.id}", type="primary"):
                                try:
                                    FinancialDataService.delete_record(target_rec.id)
                                    st.success("Record deleted.")
                                    st.rerun()
                                except Exception as exc:
                                    st.error(f"Delete failed: {exc}")

    with tab_batches:
        st.subheader("📦 Import Batches & Source Provenance")
        batches = FinancialDataService.list_import_batches(selected_project_id)
        if not batches:
            st.info("No import batches recorded for this valuation project.")
        else:
            st.write(f"Showing **{len(batches)}** historical import batches:")
            for b in batches:
                status_color = "🟢" if b.status == "Completed" else "🟡"
                with st.expander(f"{status_color} Batch #{b.id}: **{b.filename}** ({b.import_timestamp.strftime('%Y-%m-%d %H:%M')})"):
                    st.markdown(f"**Original Filename:** `{b.filename}`")
                    st.markdown(f"**Imported Timestamp:** `{b.import_timestamp.strftime('%Y-%m-%d %H:%M:%S UTC')}`")
                    st.markdown(f"**Records Accepted & Saved:** `{b.records_accepted}`")
                    st.markdown(f"**Records Rejected:** `{b.records_rejected}`")
                    st.markdown(f"**Batch Status:** `{b.status}`")
                    if b.source_description:
                        st.markdown(f"**Source Notes:** {b.source_description}")
                    if b.notes:
                        st.markdown(f"**Audit Notes:** {b.notes}")
