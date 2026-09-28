"""Valuation Project management interface.

Allows creating, filtering, editing, archiving, and selecting valuation workspaces.
"""

from __future__ import annotations

import streamlit as st

from src.data.services import CompanyService, ProjectService


def render_projects_page() -> None:
    """Render the Valuation Project Management view."""
    st.header("📁 Valuation Projects")
    st.markdown(
        "A valuation project represents an individual DCF modelling engagement for a company. "
        "A single company can have multiple distinct projects for different reporting dates or scenarios."
    )

    tab_list, tab_create = st.tabs(["📂 Project Registry", "➕ Create Valuation Project"])

    with tab_list:
        companies = CompanyService.list_companies()
        company_options = {c.id: f"{c.name} ({c.ticker or 'No Ticker'})" for c in companies}

        c1, c2, c3 = st.columns([2, 2, 1])
        with c1:
            search_query = st.text_input(
                "🔍 Search Projects",
                placeholder="Search by project name...",
                key="project_search_input",
            )
        with c2:
            filter_company = st.selectbox(
                "Filter by Company",
                options=[None] + list(company_options.keys()),
                format_func=lambda x: "All Companies" if x is None else company_options.get(x, ""),
                key="project_company_filter",
            )
        with c3:
            show_archived = st.checkbox("Include Archived", value=True, key="project_include_archived")

        try:
            projects = ProjectService.list_projects(
                company_id=filter_company,
                include_archived=show_archived,
                search=search_query,
            )
        except Exception as exc:
            st.error(f"Error loading projects: {exc}")
            projects = []

        if not projects:
            st.info("No valuation projects found matching your criteria. Create a new project using the tab above.")
        else:
            st.write(f"Showing **{len(projects)}** valuation projects:")

            for proj in projects:
                status_color = "🟢" if proj.status == "Active" else "⚪"
                comp_name = proj.company.name if proj.company else f"Company ID {proj.company_id}"

                with st.expander(f"{status_color} **{proj.name}** — {comp_name} ({proj.status})"):
                    col_a, col_b, col_c = st.columns(3)
                    with col_a:
                        st.markdown(f"**Associated Company:** {comp_name}")
                        st.markdown(f"**Project Status:** `{proj.status}`")
                    with col_b:
                        st.markdown(f"**Created Date:** `{proj.created_at.strftime('%Y-%m-%d')}`")
                        st.markdown(f"**Last Updated:** `{proj.updated_at.strftime('%Y-%m-%d')}`")
                    with col_c:
                        data_count = len(proj.data_points) if proj.data_points else 0
                        st.markdown(f"**Stored Financial Records:** `{data_count}`")

                    if proj.description:
                        st.markdown(f"**Description:** {proj.description}")

                    st.markdown("---")

                    act1, act2, act3 = st.columns([1.5, 1, 1])

                    with act1:
                        # Quick switch active project
                        if st.button(f"🎯 Set Active Project", key=f"set_active_{proj.id}"):
                            st.session_state["selected_project_id"] = proj.id
                            st.success(f"Active project set to '{proj.name}'.")
                            st.rerun()

                    with act2:
                        with st.popover("✏️ Edit Project"):
                            with st.form(f"edit_proj_form_{proj.id}"):
                                new_name = st.text_input("Project Name", value=proj.name)
                                new_desc = st.text_area("Description", value=proj.description or "")
                                new_status = st.selectbox(
                                    "Project Status",
                                    options=["Active", "Archived"],
                                    index=0 if proj.status == "Active" else 1,
                                )
                                submit_edit = st.form_submit_button("Update Project")
                                if submit_edit:
                                    try:
                                        ProjectService.update_project(
                                            project_id=proj.id,
                                            updates={
                                                "name": new_name.strip(),
                                                "description": new_desc.strip() or None,
                                                "status": new_status,
                                            },
                                        )
                                        st.success("Project updated.")
                                        st.rerun()
                                    except Exception as exc:
                                        st.error(f"Update failed: {exc}")

                    with act3:
                        with st.popover("🗑️ Delete"):
                            st.warning(f"Delete project **{proj.name}** and all its historical financial records?")
                            if st.button("Confirm Delete", key=f"del_proj_{proj.id}", type="primary"):
                                try:
                                    ProjectService.delete_project(proj.id)
                                    if st.session_state.get("selected_project_id") == proj.id:
                                        st.session_state["selected_project_id"] = None
                                    st.success("Project deleted.")
                                    st.rerun()
                                except Exception as exc:
                                    st.error(f"Delete failed: {exc}")

    with tab_create:
        st.subheader("Initialize a Valuation Project")

        companies = CompanyService.list_companies()
        if not companies:
            st.warning("⚠️ No companies found. Please create a company profile first before creating a valuation project.")
        else:
            with st.form("create_project_form", clear_on_submit=True):
                company_map = {c.id: f"{c.name} ({c.ticker or 'No Ticker'})" for c in companies}
                selected_company_id = st.selectbox(
                    "Target Company *",
                    options=list(company_map.keys()),
                    format_func=lambda cid: company_map[cid],
                )

                project_name = st.text_input(
                    "Valuation Project Name *",
                    placeholder="e.g. FY2024 Base DCF Model, Acquisition Valuation Q3",
                )

                project_description = st.text_area(
                    "Project Notes & Scope (Optional)",
                    placeholder="Document the modelling purpose, valuation cutoff date, or analyst notes...",
                )

                submit_proj = st.form_submit_button("Create Project", type="primary")

                if submit_proj:
                    if not project_name.strip():
                        st.error("Project Name is required.")
                    else:
                        try:
                            new_proj = ProjectService.create_project(
                                name=project_name,
                                company_id=selected_company_id,
                                description=project_description,
                                status="Active",
                            )
                            st.session_state["selected_project_id"] = new_proj.id
                            st.success(f"Project '{new_proj.name}' created and set as active!")
                            st.rerun()
                        except Exception as exc:
                            st.error(f"Failed to create project: {exc}")
