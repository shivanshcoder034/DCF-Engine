"""UI Page modules package for the DCF Valuation application."""

from app.pages.companies import render_companies_page
from app.pages.dashboard import render_dashboard_page
from app.pages.dcf import render_dcf_page
from app.pages.document_analysis import render_document_analysis_page
from app.pages.financial_data import render_financial_data_page
from app.pages.forecasting import render_forecasting_page
from app.pages.historical_analysis import render_historical_analysis_page
from app.pages.import_data import render_import_data_page
from app.pages.manual_entry import render_manual_entry_page
from app.pages.projects import render_projects_page
from app.pages.reports import render_reports_page
from app.pages.scenarios import render_scenarios_page
from app.pages.sensitivity import render_sensitivity_page
from app.pages.wacc import render_wacc_page

__all__ = [
    "render_companies_page",
    "render_dashboard_page",
    "render_dcf_page",
    "render_document_analysis_page",
    "render_financial_data_page",
    "render_forecasting_page",
    "render_historical_analysis_page",
    "render_import_data_page",
    "render_manual_entry_page",
    "render_projects_page",
    "render_reports_page",
    "render_scenarios_page",
    "render_sensitivity_page",
    "render_wacc_page",
]
