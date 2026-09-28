"""CSV and Excel import interface for historical financial statements.

Provides multi-step file ingestion with sheet selection, column auto-mapping,
data preview, rigorous validation, duplicate conflict handling, batch saving,
and sample template generation.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Ensure repository root is in sys.path
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

import streamlit as st
import pandas as pd

from src.data.importers import (
    generate_sample_csv_template,
    get_excel_sheet_names,
    load_file_dataframe,
    process_import_rows,
    suggest_column_mapping,
)
from src.data.schemas import (
    DataClassification,
    FinancialUnit,
    PeriodType,
    StatementType,
)
from src.data.services import FinancialDataService, ProjectService


def render_import_data_page() -> None:
    """Render the CSV and Excel Financial Data Import workflow."""
    st.header("📥 Import Financial Statements (CSV / Excel)")
    st.markdown(
        "Import multi-period historical financial data from spreadsheets into your valuation workspace. "
        "Review column mappings and validation results before confirming persistence."
    )

    # Project Selector
    all_projects = ProjectService.list_projects()
    if not all_projects:
        st.warning("⚠️ No valuation projects found. Please create a company and project first.")
        return

    project_map = {p.id: f"{p.name} ({p.company.name if p.company else 'N/A'})" for p in all_projects}
    default_proj_id = st.session_state.get("selected_project_id", all_projects[0].id)
    if default_proj_id not in project_map:
        default_proj_id = all_projects[0].id

    selected_project_id = st.selectbox(
        "Target Valuation Project *",
        options=list(project_map.keys()),
        index=list(project_map.keys()).index(default_proj_id),
        format_func=lambda pid: project_map[pid],
        key="import_target_project_select",
    )
    st.session_state["selected_project_id"] = selected_project_id

    current_proj = ProjectService.get_project(selected_project_id)
    comp_currency = current_proj.company.currency if current_proj and current_proj.company else "USD"

    # Download Sample Template
    with st.expander("📄 Download Sample Import Template & Schema Guide"):
        st.markdown(
            "Use this standardized CSV template format for seamless column auto-mapping. "
            "Supported fields include `statement_type`, `line_item_code`, `period_start_date`, "
            "`period_end_date`, `value`, `currency`, and `data_classification`."
        )
        sample_csv = generate_sample_csv_template()
        st.download_button(
            label="⬇️ Download CSV Import Template",
            data=sample_csv,
            file_name="dcf_engine_import_template.csv",
            mime="text/csv",
        )

    st.markdown("---")

    # Step 1: File Uploader
    uploaded_file = st.file_uploader(
        "Upload Financial Statement Dataset (.csv, .xlsx)",
        type=["csv", "xlsx"],
        key="financial_statement_uploader",
    )

    if not uploaded_file:
        st.info("Please upload a CSV or Excel file to begin the import workflow.")
        return

    file_bytes = uploaded_file.getvalue()
    filename = uploaded_file.name

    # Step 2: Excel Sheet Selection
    sheet_name = None
    if filename.lower().endswith(".xlsx"):
        try:
            available_sheets = get_excel_sheet_names(file_bytes)
            if len(available_sheets) > 1:
                sheet_name = st.selectbox("Select Excel Sheet", options=available_sheets)
            elif available_sheets:
                sheet_name = available_sheets[0]
        except Exception as exc:
            st.error(f"Failed to inspect Excel workbook sheets: {exc}")
            return

    # Step 3: Load DataFrame
    try:
        raw_df = load_file_dataframe(file_bytes, filename, sheet_name=sheet_name)
    except Exception as exc:
        st.error(f"Error reading file '{filename}': {exc}")
        return

    if raw_df.empty:
        st.warning("The uploaded file contains no data rows.")
        return

    st.write(f"Loaded **{len(raw_df)}** rows from `{filename}` {f'(Sheet: {sheet_name})' if sheet_name else ''}:")
    with st.expander("👀 Raw Data Preview (First 5 Rows)", expanded=False):
        st.dataframe(raw_df.head(), use_container_width=True)

    # Step 4: Column Mapping
    st.markdown("---")
    st.subheader("🛠️ Column Mapping & Defaults")
    st.caption("Map the columns in your file to the required internal financial fields:")

    suggested = suggest_column_mapping(list(raw_df.columns))
    available_cols = ["<Not Mapped>"] + list(raw_df.columns)

    map_c1, map_c2 = st.columns(2)

    with map_c1:
        st.markdown("**Core Categorization**")

        def col_index(suggested_name: str | None) -> int:
            if suggested_name and suggested_name in raw_df.columns:
                return available_cols.index(suggested_name)
            return 0

        stmt_col = st.selectbox(
            "Statement Type Column",
            options=available_cols,
            index=col_index(suggested.get("statement_type")),
        )
        line_code_col = st.selectbox(
            "Line Item Code Column *",
            options=available_cols,
            index=col_index(suggested.get("line_item_code")),
        )
        display_name_col = st.selectbox(
            "Display Name Column",
            options=available_cols,
            index=col_index(suggested.get("display_name")),
        )
        val_col = st.selectbox(
            "Financial Value Column *",
            options=available_cols,
            index=col_index(suggested.get("value")),
        )

    with map_c2:
        st.markdown("**Period & Source Information**")
        p_start_col = st.selectbox(
            "Period Start Date Column",
            options=available_cols,
            index=col_index(suggested.get("period_start_date")),
        )
        p_end_col = st.selectbox(
            "Period End Date Column *",
            options=available_cols,
            index=col_index(suggested.get("period_end_date")),
        )
        p_type_col = st.selectbox(
            "Period Type (Annual/Quarterly) Column",
            options=available_cols,
            index=col_index(suggested.get("period_type")),
        )
        curr_col = st.selectbox(
            "Currency Column",
            options=available_cols,
            index=col_index(suggested.get("currency")),
        )
        unit_col = st.selectbox(
            "Unit / Scale Column",
            options=available_cols,
            index=col_index(suggested.get("unit")),
        )
        class_col = st.selectbox(
            "Data Classification Column",
            options=available_cols,
            index=col_index(suggested.get("data_classification")),
        )

    # Step 5: Fallback Defaults
    st.markdown("##### Fallback Defaults (Applied if column is unmapped or value is missing)")
    d_col1, d_col2, d_col3, d_col4 = st.columns(4)
    with d_col1:
        default_stmt = st.selectbox(
            "Default Statement",
            options=[s.value for s in StatementType],
            format_func=lambda s: StatementType.display_name(s),
        )
    with d_col2:
        default_period_type = st.selectbox(
            "Default Period Type",
            options=[p.value for p in PeriodType],
            format_func=lambda p: PeriodType.display_name(p),
        )
    with d_col3:
        default_currency = st.text_input("Default Currency", value=comp_currency)
    with d_col4:
        default_unit = st.selectbox(
            "Default Scale",
            options=[u.value for u in FinancialUnit],
            format_func=lambda u: u.capitalize(),
        )

    default_class = st.selectbox(
        "Default Data Classification",
        options=[c.value for c in DataClassification],
        format_func=lambda c: DataClassification.display_name(c),
        help="Specify whether unclassified figures represent reported actuals or normalized figures.",
    )

    source_memo = st.text_input(
        "Batch Import Description / Reference Notes",
        value=f"Batch import from {filename}",
    )

    # Build active mapping dictionary
    active_mapping = {}
    if stmt_col != "<Not Mapped>": active_mapping["statement_type"] = stmt_col
    if line_code_col != "<Not Mapped>": active_mapping["line_item_code"] = line_code_col
    if display_name_col != "<Not Mapped>": active_mapping["display_name"] = display_name_col
    if p_start_col != "<Not Mapped>": active_mapping["period_start_date"] = p_start_col
    if p_end_col != "<Not Mapped>": active_mapping["period_end_date"] = p_end_col
    if p_type_col != "<Not Mapped>": active_mapping["period_type"] = p_type_col
    if val_col != "<Not Mapped>": active_mapping["value"] = val_col
    if curr_col != "<Not Mapped>": active_mapping["currency"] = curr_col
    if unit_col != "<Not Mapped>": active_mapping["unit"] = unit_col
    if class_col != "<Not Mapped>": active_mapping["data_classification"] = class_col

    # Step 6: Process and Validate
    st.markdown("---")
    st.subheader("🔍 Validation & Preview")

    # If start date is not mapped, default to end_date - 365 days for annual or 90 days for quarterly
    accepted, rejected = process_import_rows(
        df=raw_df,
        column_mapping=active_mapping,
        project_id=selected_project_id,
        default_currency=default_currency.strip().upper(),
        default_unit=default_unit,
        default_classification=default_class,
        default_period_type=default_period_type,
        source_filename=filename,
    )

    v_col1, v_col2, v_col3 = st.columns(3)
    v_col1.metric("Total Rows in File", len(raw_df))
    v_col2.metric("✅ Accepted for Import", len(accepted))
    v_col3.metric("❌ Rejected (Validation Errors)", len(rejected))

    # Display Rejections if any
    if rejected:
        with st.expander(f"⚠️ View {len(rejected)} Rejected Rows & Failure Reasons", expanded=True):
            for rej in rejected:
                st.markdown(f"**Row {rej['row_number']}:** {'; '.join(rej['errors'])}")
                if rej["warnings"]:
                    st.caption(f"Warnings: {'; '.join(rej['warnings'])}")

    # Display Accepted Preview
    if accepted:
        st.markdown("##### Preview Validated Records to be Saved")
        preview_data = []
        for a in accepted[:10]:
            preview_data.append({
                "Row": a.get("_row_number"),
                "Statement": StatementType.display_name(a["statement_type"]),
                "Line Item": a["display_name"],
                "Period": f"{a['period_start_date']} to {a['period_end_date']}",
                "Value": f"{a['value']:,.2f} {a['currency']}",
                "Scale": a["unit"],
                "Classification": DataClassification.display_name(a["data_classification"]),
                "Warnings": len(a.get("_warnings", [])),
            })
        st.dataframe(pd.DataFrame(preview_data), use_container_width=True, hide_index=True)
        if len(accepted) > 10:
            st.caption(f"Showing first 10 of {len(accepted)} validated records.")

        # Step 7: Duplicate Handling & Confirmation
        st.markdown("---")
        st.subheader("💾 Conflict Resolution & Confirmation")

        conflict_policy = st.radio(
            "Duplicate Conflict Policy",
            options=["skip", "overwrite"],
            format_func=lambda x: "Skip Existing Duplicates (Preserve existing database records)" if x == "skip" else "Overwrite Existing Duplicates (Update with incoming data)",
            help="Defines how to handle records with the same statement type, line item code, period end date, and classification.",
        )

        confirm_save = st.button("🚀 Confirm & Save Validated Records", type="primary")

        if confirm_save:
            try:
                batch, saved_count, updated_count = FinancialDataService.save_import_batch(
                    project_id=selected_project_id,
                    filename=filename,
                    valid_records=accepted,
                    rejected_count=len(rejected),
                    source_description=source_memo,
                    conflict_resolution=conflict_policy,
                )
                st.success(
                    f"🎉 Import Batch #{batch.id} completed! "
                    f"Successfully saved **{saved_count}** new records and updated **{updated_count}** existing records. "
                    f"(Rejected: {len(rejected)})"
                )
                st.balloons()
            except Exception as exc:
                st.error(f"❌ Failed to persist import batch: {exc}")


if __name__ == "__main__":
    from app.navigation import run_standalone_page
    run_standalone_page("Import Data", render_import_data_page)
