"""Centralized navigation, layout configuration, and execution boundaries for DCF Engine.

Provides unified page lifecycle management for both Streamlit multipage routing (pages/*.py)
and centralized in-app dispatching, ensuring consistent layouts, branding, and visible error boundaries.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Callable, Dict, Optional

# Ensure repository root is in sys.path
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

import streamlit as st

from app.config import settings
from app.components.badges import render_phase_badge


PAGE_FILE_MAP: Dict[str, str] = {
    "Home": "main.py",
    "Main": "main.py",
    "Companies": "pages/companies.py",
    "Company Profiles": "pages/companies.py",
    "Company & Financial Data": "pages/companies.py",
    "Valuation Projects": "pages/projects.py",
    "Projects": "pages/projects.py",
    "Historical Financial Records": "pages/financial_data.py",
    "Financial Data": "pages/financial_data.py",
    "Manual Data Entry": "pages/manual_entry.py",
    "Manual Entry": "pages/manual_entry.py",
    "Import (CSV / Excel)": "pages/import_data.py",
    "Import Data": "pages/import_data.py",
    "Document & Filing Analysis": "pages/document_analysis.py",
    "Document Analysis": "pages/document_analysis.py",
    "Historical Analysis": "pages/historical_analysis.py",
    "Forecasting": "pages/forecasting.py",
    "WACC": "pages/wacc.py",
    "DCF Valuation": "pages/dcf.py",
    "DCF": "pages/dcf.py",
    "Scenarios": "pages/scenarios.py",
    "Sensitivity Analysis": "pages/sensitivity.py",
    "Sensitivity": "pages/sensitivity.py",
    "Financial Dashboards": "pages/dashboard.py",
    "Dashboard": "pages/dashboard.py",
    "Reports & Exports": "pages/reports.py",
    "Reports": "pages/reports.py",
}


def setup_page_configuration(page_title: str = "AI-Powered DCF Engine") -> None:
    """Configure Streamlit page metadata, layout, and initial state safely."""
    try:
        st.set_page_config(
            page_title=page_title,
            page_icon="📊",
            layout="wide",
            initial_sidebar_state="expanded",
        )
    except Exception:
        # Ignore if set_page_config was already invoked on this script run
        pass


def render_shared_sidebar(current_page: str = "") -> None:
    """Render consistent sidebar branding, status indicators, and environment metadata."""
    with st.sidebar:
        st.title("💼 DCF Engine")
        st.caption("Valuation & Sensitivity Engine")

        render_phase_badge(phase_text="Phase 12 Complete", status="All 12 Phases Active")

        st.markdown("---")
        st.markdown("### Project Environment")
        st.write(f"**Version:** `{settings.app_version}`")
        st.write(f"**Environment:** `{settings.environment}`")
        st.write(f"**Debug Mode:** `{settings.debug}`")

        st.markdown("---")
        st.caption(
            "© Phase 12 • AI-Powered DCF Valuation Engine. "
            "All 12 engineering phases fully delivered."
        )


def safe_render_page(page_name: str, render_fn: Callable[[], None]) -> None:
    """Render a page function inside a visible, diagnostic error boundary."""
    try:
        render_fn()
    except Exception as exc:
        st.error(
            f"⚠️ An error occurred while rendering the **{page_name}** page: `{exc}`"
        )
        if settings.debug:
            st.exception(exc)
        else:
            st.info(
                "Tip: Enable `DEBUG=true` in your environment or configuration "
                "to view detailed diagnostic tracebacks."
            )


def navigate_to(page_target: str) -> None:
    """Navigate to another page supporting both native MPA routing and custom router."""
    st.session_state["app_nav_selection"] = page_target
    st.session_state["main_nav_radio"] = page_target
    target_file = PAGE_FILE_MAP.get(page_target)
    if target_file:
        try:
            st.switch_page(target_file)
            return
        except Exception:
            pass
    st.rerun()


def run_standalone_page(page_name: str, render_fn: Callable[[], None]) -> None:
    """Entry point for pages executed directly by Streamlit's multipage runner."""
    # Check if a programmatic redirect was queued in session state
    redirect_target = st.session_state.pop("app_nav_selection", None)
    if redirect_target:
        target_file = PAGE_FILE_MAP.get(redirect_target)
        current_script = Path(sys.argv[0]).name if sys.argv else ""
        if target_file and not target_file.endswith(current_script):
            try:
                st.switch_page(target_file)
                return
            except Exception:
                pass

    setup_page_configuration(f"{page_name} - DCF Engine")
    render_shared_sidebar(current_page=page_name)
    safe_render_page(page_name, render_fn)
