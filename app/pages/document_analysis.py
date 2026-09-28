"""Document & Financial Statement Analysis - Streamlit Interface.

Delivers SEC 10-K and 10-Q filing discovery, document parsing, financial statement line-item
extraction with side-by-side human review, grounded AI footnote disclosure analysis,
and auditable approval into historical project records.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

import streamlit as st
import pandas as pd

from src.data.models import Company, ValuationProject
from src.data.schemas import STANDARD_LINE_ITEMS, StatementType
from src.data.services import CompanyService, ValuationProjectService
from src.filings.models import (
    ExtractedStatementItem,
    FilingAnalysisBundle,
    FilingMetadata,
    FootnoteCategory,
    FootnoteObservationData,
    ObservationReviewStatus,
)
from src.filings.services import FilingService

logger = logging.getLogger(__name__)


def render_document_analysis_page() -> None:
    """Main rendering function for Document and Filing Analysis."""
    st.title("📑 Document & Financial Statement Analysis")
    st.caption(
        "Phase 12 • SEC 10-K/10-Q filing discovery, US-GAAP taxonomy extraction, "
        "and grounded AI footnote disclosure analysis."
    )

    st.markdown("---")

    # Initialize session state for filings workflow
    if "filing_service" not in st.session_state:
        st.session_state["filing_service"] = FilingService()
    if "discovered_filings" not in st.session_state:
        st.session_state["discovered_filings"] = []
    if "selected_filing" not in st.session_state:
        st.session_state["selected_filing"] = None
    if "filing_analysis_bundle" not in st.session_state:
        st.session_state["filing_analysis_bundle"] = None
    if "discovered_entity_info" not in st.session_state:
        st.session_state["discovered_entity_info"] = None

    service: FilingService = st.session_state["filing_service"]

    # 4-stage workflow tabs
    tab_discovery, tab_statements, tab_footnotes, tab_viewer = st.tabs([
        "🔍 1. Filing Discovery & Intake",
        "📊 2. Statement Extraction & Approval",
        "🧠 3. AI Footnote & Disclosure Analysis",
        "📜 4. Document Viewer & Audit Lineage",
    ])

    # =========================================================================
    # TAB 1: FILING DISCOVERY & INTAKE
    # =========================================================================
    with tab_discovery:
        st.subheader("1. Company Identification & SEC Filing Discovery")
        st.markdown(
            "Identify a publicly listed company by stock ticker or SEC Central Index Key (CIK) "
            "to discover official 10-K (Annual) and 10-Q (Quarterly) filings from the SEC EDGAR system."
        )

        col_input, col_config = st.columns([2, 1])

        with col_input:
            input_mode = st.radio(
                "Identification Mode",
                options=["Enter Ticker / CIK", "Select Saved Company Profile"],
                horizontal=True,
            )

            target_identifier = ""
            selected_company_id: Optional[int] = None

            if input_mode == "Enter Ticker / CIK":
                target_identifier = st.text_input(
                    "Public Company Ticker or CIK",
                    value="AAPL",
                    placeholder="e.g. AAPL, MSFT, NVDA, or 0000320193",
                    help="Enter a stock ticker or 10-digit SEC CIK.",
                ).strip()
            else:
                companies = CompanyService.list_companies()
                if not companies:
                    st.info("No saved company profiles found. Please create one in Company Data or use direct ticker input.")
                else:
                    comp_map = {f"{c.name} ({c.ticker or 'No Ticker'})": c for c in companies}
                    selected_label = st.selectbox("Select Company Profile", options=list(comp_map.keys()))
                    chosen = comp_map[selected_label]
                    target_identifier = chosen.ticker or str(chosen.id)
                    selected_company_id = chosen.id

        with col_config:
            st.markdown("#### Filing Filters")
            forms_selected = st.multiselect(
                "Filing Form Types",
                options=["10-K", "10-Q", "10-K/A", "10-Q/A"],
                default=["10-K", "10-Q"],
                help="Select regulatory form types to discover.",
            )
            filing_limit = st.slider("Max Filings to Retrieve", min_value=5, max_value=50, value=20, step=5)

        st.markdown(" ")
        btn_discover = st.button("🔍 Discover Filings on SEC EDGAR", type="primary", use_container_width=True)

        if btn_discover:
            if not target_identifier:
                st.error("Please provide a valid ticker symbol or SEC CIK.")
            else:
                with st.spinner(f"Querying SEC EDGAR registry for '{target_identifier}'..."):
                    try:
                        entity_info, filings = service.discover_filings(
                            ticker_or_cik=target_identifier,
                            forms=forms_selected,
                            limit=filing_limit,
                        )
                        if not entity_info:
                            st.warning(
                                f"No public entity found matching identifier '{target_identifier}'. "
                                f"Please verify the ticker symbol or 10-digit CIK."
                            )
                            st.session_state["discovered_filings"] = []
                            st.session_state["discovered_entity_info"] = None
                        else:
                            st.session_state["discovered_entity_info"] = entity_info
                            st.session_state["discovered_filings"] = filings
                            st.success(
                                f"Discovered entity: **{entity_info['title']}** (CIK: `{entity_info['cik']}`) "
                                f"with **{len(filings)}** recent regulatory filings."
                            )
                    except Exception as exc:
                        st.error(f"SEC EDGAR Discovery Error: {exc}")

        # Display discovered filings table
        discovered_filings: List[FilingMetadata] = st.session_state.get("discovered_filings", [])
        entity_info = st.session_state.get("discovered_entity_info")

        if discovered_filings:
            st.markdown("---")
            st.subheader("Discovered Regulatory Filings")
            if entity_info:
                st.caption(f"**Entity:** {entity_info['title']} | **CIK:** `{entity_info['cik']}` | **Ticker:** `{entity_info.get('ticker', 'N/A')}`")

            # Table presentation
            filing_rows = []
            for idx, f in enumerate(discovered_filings):
                amended_label = "⚠️ Yes (Amended)" if f.is_amended else "No (Original)"
                sec_url = f.primary_doc_url or f"https://www.sec.gov/edgar/browse/?CIK={f.cik}"
                filing_rows.append({
                    "Index": idx + 1,
                    "Form": f.form_type,
                    "Period End Date": f.report_date,
                    "Filing Date": f.filing_date,
                    "Fiscal Period": f"{f.fiscal_period or ''} {f.fiscal_year or ''}".strip(),
                    "Amended": amended_label,
                    "Accession Number": f.accession_number,
                    "Document Link": f"[SEC Document]({sec_url})",
                })

            df_filings = pd.DataFrame(filing_rows)
            st.dataframe(df_filings, use_container_width=True, hide_index=True)

            # Filing selection for retrieval & parsing
            st.markdown("#### Select Filing for Analysis")
            filing_options = {
                f"{f.form_type} • {f.report_date} (Filed: {f.filing_date}) - {f.accession_number}": f
                for f in discovered_filings
            }
            selected_key = st.selectbox("Choose Filing", options=list(filing_options.keys()))
            chosen_filing = filing_options[selected_key]
            st.session_state["selected_filing"] = chosen_filing

            col_btn1, col_btn2 = st.columns([2, 1])
            with col_btn1:
                btn_retrieve = st.button("📥 Retrieve & Parse Selected Filing", type="primary", use_container_width=True)

            if btn_retrieve:
                with st.spinner(f"Retrieving and parsing {chosen_filing.form_type} (Accession: {chosen_filing.accession_number})..."):
                    try:
                        bundle = service.retrieve_and_analyze_filing(chosen_filing)
                        st.session_state["filing_analysis_bundle"] = bundle

                        # Save filing record in SQLite
                        sec_record = service.save_or_update_filing(chosen_filing, company_id=selected_company_id)
                        # Save observations in SQLite
                        service.save_observations(sec_record.id, bundle.observations)

                        st.success(
                            f"Successfully parsed **{chosen_filing.form_type}**! "
                            f"Extracted **{len(bundle.extracted_items)}** US-GAAP statement facts and generated "
                            f"**{len(bundle.observations)}** grounded footnote observations."
                        )
                        st.info("Navigate to Tab 2 to review statement facts, or Tab 3 to inspect AI footnote disclosures.")
                    except Exception as exc:
                        st.error(f"Filing Retrieval & Analysis Failed: {exc}")

        # Offline / Manual document intake sub-section
        with st.expander("📁 Alternative Document Intake (Offline Upload)", expanded=False):
            st.markdown(
                "Upload a regulatory filing or financial statement document (`.htm`, `.html`, `.txt`, `.json`) "
                "from your local machine for offline analysis without querying SEC EDGAR directly."
            )
            uploaded_file = st.file_uploader("Upload Financial Document", type=["htm", "html", "txt", "json"])
            if uploaded_file is not None:
                content_str = uploaded_file.read().decode("utf-8", errors="ignore")
                st.write(f"File uploaded: `{uploaded_file.name}` ({len(content_str):,} characters)")
                if st.button("Parse Uploaded Document"):
                    synthetic_meta = FilingMetadata(
                        ticker=target_identifier or "UPLOAD",
                        cik="0000000000",
                        company_name="Uploaded Entity Document",
                        form_type="10-K",
                        accession_number=f"LOCAL-{uploaded_file.name[:20]}",
                        filing_date="2025-12-31",
                        report_date="2025-12-31",
                        status="Retrieved",
                    )
                    bundle = service.retrieve_and_analyze_filing(synthetic_meta)
                    st.session_state["selected_filing"] = synthetic_meta
                    st.session_state["filing_analysis_bundle"] = bundle
                    st.success(f"Parsed uploaded document with {len(bundle.observations)} observations!")

    # =========================================================================
    # TAB 2: STATEMENT EXTRACTION & APPROVAL
    # =========================================================================
    with tab_statements:
        st.subheader("2. Financial Statement Line-Item Extraction & Human Verification")
        st.markdown(
            "Review candidate line items extracted from official SEC US-GAAP taxonomy tags. "
            "You can verify the candidate mapping, edit figures, and explicitly approve records "
            "for import into your valuation project workspace."
        )

        bundle: Optional[FilingAnalysisBundle] = st.session_state.get("filing_analysis_bundle")
        selected_filing: Optional[FilingMetadata] = st.session_state.get("selected_filing")

        if not bundle or not selected_filing:
            st.info("No filing currently parsed. Please discover and parse a filing in Tab 1 first.")
        else:
            st.markdown(
                f"**Active Filing:** `{selected_filing.form_type}` • Reporting Period: `{selected_filing.report_date}` • "
                f"Entity: `{selected_filing.company_name}`"
            )

            if not bundle.extracted_items:
                st.warning(
                    "No standardized statement line items were detected in this filing. "
                    "This can occur if the filing is an amendment or lacks tagged XBRL facts."
                )
            else:
                # Group by statement type
                stmt_groups = {
                    "income_statement": "📈 Income Statement Items",
                    "balance_sheet": "🏛️ Balance Sheet Items",
                    "cash_flow_statement": "💵 Cash Flow Statement Items",
                }

                all_canonical_codes = list(STANDARD_LINE_ITEMS.keys())

                st.markdown("#### Review Extracted Facts")

                # Build editable table data
                table_rows = []
                for idx, item in enumerate(bundle.extracted_items):
                    table_rows.append({
                        "Include": True,
                        "Statement": StatementType.display_name(item.statement_type),
                        "Canonical Code": item.line_item_code,
                        "Display Name": item.display_name,
                        "Reported Value": item.value,
                        "Source Label": item.source_label,
                        "Period End": item.period_end_date,
                        "Period Type": item.period_type.title(),
                        "Confidence": f"{int(item.confidence_score * 100)}%",
                    })

                df_items = pd.DataFrame(table_rows)

                edited_df = st.data_editor(
                    df_items,
                    column_config={
                        "Include": st.column_config.CheckboxColumn("Import?", default=True),
                        "Canonical Code": st.column_config.SelectboxColumn("Canonical Mapping", options=all_canonical_codes),
                        "Reported Value": st.column_config.NumberColumn("Reported Value ($)", format="$%,.0f"),
                        "Confidence": st.column_config.TextColumn("Confidence"),
                    },
                    disabled=["Statement", "Source Label", "Period End", "Period Type", "Confidence"],
                    hide_index=True,
                    use_container_width=True,
                    key="extracted_items_editor",
                )

                st.markdown("---")
                st.subheader("Target Valuation Project Approval")

                # Select project
                projects = ValuationProjectService.list_projects()
                if not projects:
                    st.warning("No valuation projects found. Please create a valuation project first.")
                else:
                    proj_map = {f"{p.name} (ID: {p.id})": p.id for p in projects}
                    target_proj_id = st.selectbox("Target Valuation Project", options=list(proj_map.keys()))
                    selected_proj_id = proj_map[target_proj_id]

                    col_dup, col_approve = st.columns([1, 2])
                    with col_dup:
                        conflict_policy = st.selectbox(
                            "Duplicate Handling Policy",
                            options=["skip", "overwrite"],
                            format_func=lambda x: "Skip Existing Records" if x == "skip" else "Overwrite Existing Records",
                            help="Determines behavior if a line item already exists for the same period and classification.",
                        )

                    with col_approve:
                        st.markdown("<br>", unsafe_allow_html=True)
                        btn_approve = st.button(
                            "✅ Approve & Import Selected Statement Records",
                            type="primary",
                            use_container_width=True,
                        )

                    if btn_approve:
                        # Filter selected rows
                        selected_indices = [i for i, row in edited_df.iterrows() if row["Include"]]
                        if not selected_indices:
                            st.warning("No line items selected for import. Please check at least one item.")
                        else:
                            items_to_import: List[ExtractedStatementItem] = []
                            for idx in selected_indices:
                                orig = bundle.extracted_items[idx]
                                mapped_code = edited_df.at[idx, "Canonical Code"]
                                edited_val = float(edited_df.at[idx, "Reported Value"])
                                disp_name = STANDARD_LINE_ITEMS.get(mapped_code).display_name if mapped_code in STANDARD_LINE_ITEMS else mapped_code

                                item_copy = ExtractedStatementItem(
                                    statement_type=orig.statement_type,
                                    line_item_code=mapped_code,
                                    display_name=disp_name,
                                    source_label=orig.source_label,
                                    period_start_date=orig.period_start_date,
                                    period_end_date=orig.period_end_date,
                                    period_type=orig.period_type,
                                    value=edited_val,
                                    currency=orig.currency,
                                    unit=orig.unit,
                                    is_derived=orig.is_derived,
                                    confidence_score=orig.confidence_score,
                                    source_location=orig.source_location,
                                    selected=True,
                                )
                                items_to_import.append(item_copy)

                            with st.spinner("Persisting approved financial data points with audit lineage..."):
                                try:
                                    batch, saved_count, updated_count = service.approve_and_import_statements(
                                        project_id=selected_proj_id,
                                        filing=selected_filing,
                                        selected_items=items_to_import,
                                        conflict_resolution=conflict_policy,
                                    )
                                    st.success(
                                        f"🎉 Import Approved! **{saved_count}** new records saved, **{updated_count}** records updated "
                                        f"in Project ID `{selected_proj_id}` under Import Batch #{batch.id}."
                                    )
                                    st.info(
                                        f"Source provenance verified: `SEC {selected_filing.form_type} "
                                        f"(Accession: {selected_filing.accession_number})`. "
                                        f"These records are immediately available in Historical Analysis, Forecasting, WACC, and DCF."
                                    )
                                except Exception as exc:
                                    st.error(f"Import Approval Failed: {exc}")

    # =========================================================================
    # TAB 3: AI FOOTNOTE & DISCLOSURE ANALYSIS
    # =========================================================================
    with tab_footnotes:
        st.subheader("3. Grounded AI Footnote & Disclosure Analysis")
        st.markdown(
            "Institutional analysis of accounting footnotes, debt terms, lease liabilities, "
            "legal contingencies, and tax policies strictly grounded in retrieved filing text. "
            "Each observation traces back to exact disclosure sections and supports human review annotations."
        )

        bundle: Optional[FilingAnalysisBundle] = st.session_state.get("filing_analysis_bundle")
        selected_filing: Optional[FilingMetadata] = st.session_state.get("selected_filing")

        if not bundle or not selected_filing:
            st.info("No parsed filing active. Please retrieve a filing in Tab 1 first.")
        else:
            observations = bundle.observations
            if not observations:
                st.warning("No footnote observations were generated. Ensure the filing document contains standard footnote headings.")
            else:
                # Headline metrics
                kpi1, kpi2, kpi3, kpi4 = st.columns(4)
                total_obs = len(observations)
                pending_count = sum(1 for o in observations if o.review_status == "pending")
                relevant_count = sum(1 for o in observations if o.review_status == "relevant")
                categories_count = len(set(o.category for o in observations))

                kpi1.metric("Total Observations", total_obs)
                kpi2.metric("Categories Analyzed", categories_count)
                kpi3.metric("Pending Review", pending_count)
                kpi4.metric("Flagged Relevant", relevant_count)

                st.markdown("---")

                # Category filter
                cat_options = ["All Categories"] + sorted(list(set(o.category for o in observations)))
                selected_cat = st.selectbox("Filter by Disclosure Category", options=cat_options)

                filtered_obs = observations
                if selected_cat != "All Categories":
                    filtered_obs = [o for o in observations if o.category == selected_cat]

                st.markdown(f"Showing **{len(filtered_obs)}** observations:")

                # Render observation cards
                status_options = [
                    ObservationReviewStatus.PENDING.value,
                    ObservationReviewStatus.REVIEWED.value,
                    ObservationReviewStatus.RELEVANT.value,
                    ObservationReviewStatus.NOT_RELEVANT.value,
                    ObservationReviewStatus.REQUIRES_FOLLOWUP.value,
                ]

                for idx, obs in enumerate(filtered_obs):
                    icon = FootnoteCategory.icon(obs.category)
                    status_badge = {
                        "pending": "⏳ Pending",
                        "reviewed": "✓ Reviewed",
                        "relevant": "⭐ Flagged Relevant",
                        "not_relevant": "✖ Not Relevant",
                        "requires_followup": "⚠️ Follow-up",
                    }.get(obs.review_status, obs.review_status)

                    with st.expander(f"{icon} **{obs.category}** • {obs.source_section} — *[{status_badge}]*", expanded=(idx < 2)):
                        st.markdown(f"**Location:** `{obs.source_location}` • **Confidence:** `{int(obs.confidence_score * 100)}%`")
                        st.markdown(f"**Executive Summary:** {obs.summary}")

                        if obs.source_quote:
                            st.markdown(f"> *\"{obs.source_quote}\"*")

                        col_facts, col_implications = st.columns(2)
                        with col_facts:
                            st.markdown("##### 📌 Explicit Facts Stated in Filing")
                            st.write(obs.explicit_facts or "No specific numerical constraints stated.")
                        with col_implications:
                            st.markdown("##### 💡 Analytical & Valuation Implications")
                            st.write(obs.potential_implications or "Standard accounting compliance profile.")

                        st.markdown("---")
                        col_stat, col_note = st.columns([1, 2])
                        with col_stat:
                            curr_status_idx = status_options.index(obs.review_status) if obs.review_status in status_options else 0
                            new_status = st.selectbox(
                                "Review Status",
                                options=status_options,
                                index=curr_status_idx,
                                format_func=ObservationReviewStatus.display_name,
                                key=f"obs_status_{idx}_{obs.category[:10]}",
                            )
                        with col_note:
                            user_note = st.text_input(
                                "Analyst Audit Notes",
                                value=obs.user_notes or "",
                                placeholder="Add notes on adjustments or audit findings...",
                                key=f"obs_note_{idx}_{obs.category[:10]}",
                            )

                        if st.button("Save Review Status", key=f"btn_save_obs_{idx}"):
                            obs.review_status = new_status
                            obs.user_notes = user_note
                            if obs.id:
                                service.update_observation_status(obs.id, new_status, user_note)
                            st.success("Observation review status updated!")

    # =========================================================================
    # TAB 4: DOCUMENT VIEWER & AUDIT LINEAGE
    # =========================================================================
    with tab_viewer:
        st.subheader("4. Document Viewer & Historical Ingestion Lineage")
        st.markdown(
            "Inspect raw filing content, parsed footnote text sections, "
            "and historical SEC regulatory filing import batches."
        )

        bundle: Optional[FilingAnalysisBundle] = st.session_state.get("filing_analysis_bundle")
        selected_filing: Optional[FilingMetadata] = st.session_state.get("selected_filing")

        if bundle and bundle.footnote_sections:
            with st.expander("📖 Parsed Footnote Sections (Plain Text)", expanded=True):
                sec_titles = list(bundle.footnote_sections.keys())
                chosen_sec = st.selectbox("Select Section to View", options=sec_titles)
                if chosen_sec:
                    sec_text = bundle.footnote_sections[chosen_sec]
                    st.text_area("Footnote Text Content", value=sec_text, height=350, disabled=True)

        st.markdown("---")
        st.subheader("Historical Ingestion Audit Trail")

        saved_filings = service.list_saved_filings()
        if not saved_filings:
            st.info("No filings have been stored in the local repository yet.")
        else:
            audit_rows = []
            for f in saved_filings:
                audit_rows.append({
                    "ID": f.id,
                    "Ticker": f.ticker or "N/A",
                    "Form": f.form_type,
                    "Period End": str(f.report_date),
                    "Filing Date": str(f.filing_date),
                    "Status": f.status,
                    "Accession Number": f.accession_number,
                    "Cached Locally": "Yes" if f.local_cache_path else "No",
                })
            st.dataframe(pd.DataFrame(audit_rows), use_container_width=True, hide_index=True)
