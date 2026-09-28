"""Manual financial data entry interface.

Enables structured input of individual financial statement items with
validation, custom line-item support, and audit trail tagging.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Ensure repository root is in sys.path
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from datetime import date, timedelta
import streamlit as st

from src.data.schemas import (
    DataClassification,
    FinancialUnit,
    PeriodType,
    SourceType,
    StatementType,
    get_standard_items_by_statement,
)
from src.data.services import FinancialDataService, ProjectService


def render_manual_entry_page() -> None:
    """Render the Manual Financial Data Entry interface."""
    st.header("✍️ Manual Financial Statement Data Entry")
    st.markdown(
        "Enter individual historical line items for your active valuation project. "
        "Every record is validated for structural consistency and tagged with audit provenance."
    )

    projects = ProjectService.list_projects()
    if not projects:
        st.warning("⚠️ No valuation projects available. Please create a company and project first.")
        return

    proj_map = {p.id: f"{p.name} ({p.company.name if p.company else 'N/A'})" for p in projects}
    default_proj = st.session_state.get("selected_project_id", projects[0].id)
    if default_proj not in proj_map:
        default_proj = projects[0].id

    selected_project_id = st.selectbox(
        "Target Valuation Project *",
        options=list(proj_map.keys()),
        index=list(proj_map.keys()).index(default_proj),
        format_func=lambda pid: proj_map[pid],
        key="manual_entry_project_select",
    )
    st.session_state["selected_project_id"] = selected_project_id

    current_proj = ProjectService.get_project(selected_project_id)
    comp_currency = current_proj.company.currency if current_proj and current_proj.company else "USD"

    st.markdown("---")

    with st.form("manual_entry_form", clear_on_submit=False):
        c1, c2, c3 = st.columns(3)
        with c1:
            statement_type = st.selectbox(
                "Financial Statement Type *",
                options=[s.value for s in StatementType],
                format_func=lambda s: StatementType.display_name(s),
            )
        with c2:
            period_type = st.selectbox(
                "Period Frequency *",
                options=[p.value for p in PeriodType],
                format_func=lambda p: PeriodType.display_name(p),
            )
        with c3:
            classification = st.selectbox(
                "Data Classification *",
                options=[c.value for c in DataClassification],
                format_func=lambda c: DataClassification.display_name(c),
                help="Distinguish reported actuals from normalized or pro-forma figures.",
            )

        # Dates
        d1, d2 = st.columns(2)
        with d1:
            start_date = st.date_input("Reporting Period Start Date *", value=date(2023, 1, 1))
        with d2:
            end_date = st.date_input("Reporting Period End Date *", value=date(2023, 12, 31))

        # Line item selection
        st.markdown("##### Line Item Selection")
        standard_items = get_standard_items_by_statement(statement_type)
        catalog_options = {"custom": "➕ Custom Line Item..."}
        catalog_options.update({item.code: f"{item.display_name} ({item.code})" for item in standard_items})

        selected_code = st.selectbox(
            "Select Line Item from Catalog",
            options=list(catalog_options.keys()),
            format_func=lambda code: catalog_options[code],
        )

        li_col1, li_col2 = st.columns(2)
        with li_col1:
            if selected_code == "custom":
                line_item_code = st.text_input(
                    "Custom Line Item Code *",
                    placeholder="e.g. stock_based_compensation, restructuring_charges",
                )
            else:
                line_item_code = selected_code
                st.text_input("Standard Line Item Code", value=selected_code, disabled=True)

        with li_col2:
            if selected_code == "custom":
                display_name = st.text_input(
                    "Display Name *",
                    placeholder="e.g. Stock-Based Compensation",
                )
            else:
                matched_item = next((i for i in standard_items if i.code == selected_code), None)
                display_name = matched_item.display_name if matched_item else selected_code.replace("_", " ").title()
                st.text_input("Display Name", value=display_name, disabled=True)

        # Value and Units
        v1, v2, v3 = st.columns(3)
        with v1:
            value = st.number_input(
                "Financial Numeric Value *",
                value=0.0,
                format="%.4f",
                help="Negative figures are supported for expenses, losses, or outflows.",
            )
        with v2:
            currency = st.text_input("Currency Code (ISO 4217) *", value=comp_currency)
        with v3:
            unit = st.selectbox(
                "Unit / Multiplier Scale *",
                options=[u.value for u in FinancialUnit],
                format_func=lambda u: u.capitalize(),
            )

        source_ref = st.text_input(
            "Source Description / Audit Reference",
            placeholder="e.g. FY2023 10-K Item 8, audited footnote 4, management accounts",
        )

        submit_record = st.form_submit_button("Save Financial Record", type="primary")

        if submit_record:
            # Clean custom inputs
            final_code = line_item_code.strip().lower().replace(" ", "_") if line_item_code else ""
            final_display = display_name.strip() if display_name else ""

            record_payload = {
                "project_id": selected_project_id,
                "statement_type": statement_type,
                "period_type": period_type,
                "data_classification": classification,
                "period_start_date": start_date,
                "period_end_date": end_date,
                "line_item_code": final_code,
                "display_name": final_display,
                "value": value,
                "currency": currency.strip().upper(),
                "unit": unit,
                "source_type": SourceType.MANUAL_ENTRY.value,
                "source_reference": source_ref.strip() or None,
            }

            try:
                created = FinancialDataService.create_record(record_payload)
                st.success(
                    f"✅ Record saved successfully! Added **{created.display_name}** "
                    f"({created.currency} {created.value:,.2f}) for period ending {created.period_end_date}."
                )
            except ValueError as val_err:
                st.error(f"❌ Record could not be saved: {val_err}")
            except Exception as exc:
                st.error(f"❌ Unexpected system error: {exc}")


if __name__ == "__main__":
    from app.navigation import run_standalone_page
    run_standalone_page("Manual Entry", render_manual_entry_page)
