"""Company profile management interface.

Allows creating, viewing, searching, editing, and safely deleting target companies.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Ensure repository root is in sys.path
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

import streamlit as st

from src.data.services import CompanyService, ProjectService


def render_companies_page() -> None:
    """Render the Company Management view."""
    st.header("🏢 Company Profiles")
    st.markdown(
        "Manage publicly traded and privately held target entities. "
        "Each company can hold multiple valuation projects."
    )

    tab_list, tab_create = st.tabs(["📋 Company Directory", "➕ Add New Company"])

    with tab_list:
        search_query = st.text_input(
            "🔍 Search Companies",
            placeholder="Search by company name or ticker symbol...",
            key="company_search_input",
        )

        try:
            companies = CompanyService.list_companies(search=search_query)
        except Exception as exc:
            st.error(f"Error loading companies: {exc}")
            companies = []

        if not companies:
            st.info("No companies found. Use the **Add New Company** tab above to create your first company profile.")
        else:
            st.write(f"Showing **{len(companies)}** company profiles:")

            for comp in companies:
                with st.expander(f"**{comp.name}** {f'({comp.ticker})' if comp.ticker else ''} — {comp.country} | {comp.currency}"):
                    c1, c2, c3 = st.columns(3)
                    with c1:
                        st.markdown(f"**Ticker Symbol:** `{comp.ticker or 'N/A'}`")
                        st.markdown(f"**Exchange:** `{comp.exchange or 'N/A'}`")
                        st.markdown(f"**Country:** `{comp.country}`")
                    with c2:
                        st.markdown(f"**Sector:** `{comp.sector or 'N/A'}`")
                        st.markdown(f"**Industry:** `{comp.industry or 'N/A'}`")
                        st.markdown(f"**Reporting Currency:** `{comp.currency}`")
                    with c3:
                        st.markdown(f"**Fiscal Year End:** `{comp.fiscal_year_end or 'December 31'}`")
                        st.markdown(f"**Created:** `{comp.created_at.strftime('%Y-%m-%d')}`")
                        project_count = len(comp.projects) if comp.projects else 0
                        st.markdown(f"**Valuation Projects:** `{project_count}`")

                    if comp.description:
                        st.markdown(f"**Description:** {comp.description}")

                    st.markdown("---")

                    # Edit & Delete Sub-actions
                    edit_col, delete_col = st.columns([1, 1])

                    with edit_col:
                        with st.popover("✏️ Edit Profile"):
                            with st.form(f"edit_company_form_{comp.id}"):
                                new_name = st.text_input("Company Name *", value=comp.name)
                                new_ticker = st.text_input("Ticker", value=comp.ticker or "")
                                new_exchange = st.text_input("Exchange", value=comp.exchange or "")
                                new_country = st.text_input("Country", value=comp.country)
                                new_currency = st.text_input("Reporting Currency (ISO 4217)", value=comp.currency)
                                new_sector = st.text_input("Sector", value=comp.sector or "")
                                new_industry = st.text_input("Industry", value=comp.industry or "")
                                new_fye = st.text_input("Fiscal Year End", value=comp.fiscal_year_end or "")
                                new_desc = st.text_area("Description", value=comp.description or "")

                                submit_edit = st.form_submit_button("Save Changes")
                                if submit_edit:
                                    try:
                                        CompanyService.update_company(
                                            company_id=comp.id,
                                            updates={
                                                "name": new_name.strip(),
                                                "ticker": new_ticker.strip().upper() or None,
                                                "exchange": new_exchange.strip().upper() or None,
                                                "country": new_country.strip() or "United States",
                                                "currency": new_currency.strip().upper() or "USD",
                                                "sector": new_sector.strip() or None,
                                                "industry": new_industry.strip() or None,
                                                "fiscal_year_end": new_fye.strip() or None,
                                                "description": new_desc.strip() or None,
                                            },
                                        )
                                        st.success("Company profile updated successfully!")
                                        st.rerun()
                                    except Exception as exc:
                                        st.error(f"Update failed: {exc}")

                    with delete_col:
                        with st.popover("🗑️ Delete Company"):
                            st.warning(
                                f"Are you sure you want to delete **{comp.name}**? "
                                "Companies with associated valuation projects cannot be deleted without first removing those projects."
                            )
                            confirm_delete = st.button("Confirm Delete", key=f"del_comp_{comp.id}", type="primary")
                            if confirm_delete:
                                try:
                                    CompanyService.delete_company(comp.id, force=False)
                                    st.success(f"Company '{comp.name}' deleted.")
                                    st.rerun()
                                except ValueError as val_err:
                                    st.error(str(val_err))
                                except Exception as exc:
                                    st.error(f"Deletion failed: {exc}")

    with tab_create:
        st.subheader("Register a New Company")
        with st.form("create_company_form", clear_on_submit=True):
            f1, f2 = st.columns(2)
            with f1:
                name = st.text_input("Company Legal / Trading Name *", placeholder="e.g. Acme Financial Group")
                ticker = st.text_input("Ticker Symbol (Optional)", placeholder="e.g. AFG")
                exchange = st.text_input("Primary Exchange (Optional)", placeholder="e.g. NYSE, NASDAQ, LSE, NSE")
                country = st.text_input("Country of Domicile *", value="United States")

            with f2:
                currency = st.text_input("Reporting Currency (3-letter code) *", value="USD")
                sector = st.text_input("Economic Sector", placeholder="e.g. Technology, Industrials, Healthcare")
                industry = st.text_input("Industry Classification", placeholder="e.g. Enterprise Software, Semiconductors")
                fiscal_year_end = st.text_input("Fiscal Year End", value="December 31")

            description = st.text_area(
                "Company Business Description (Optional)",
                placeholder="Brief overview of operational segments and core revenue drivers...",
            )

            submit_create = st.form_submit_button("Create Company Profile", type="primary")

            if submit_create:
                if not name.strip():
                    st.error("Company Name is required.")
                else:
                    try:
                        new_comp = CompanyService.create_company(
                            name=name,
                            country=country,
                            currency=currency,
                            ticker=ticker,
                            exchange=exchange,
                            sector=sector,
                            industry=industry,
                            fiscal_year_end=fiscal_year_end,
                            description=description,
                        )
                        st.success(f"Company '{new_comp.name}' created successfully with ID {new_comp.id}!")
                        st.rerun()
                    except ValueError as val_err:
                        st.error(str(val_err))
                    except Exception as exc:
                        st.error(f"Failed to create company: {exc}")


if __name__ == "__main__":
    from app.navigation import run_standalone_page
    run_standalone_page("Companies", render_companies_page)
