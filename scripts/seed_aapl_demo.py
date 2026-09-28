# coding: utf-8
"""
seed_aapl_demo.py
=================
Idempotent script to populate the DCF Valuation Engine database with a real-data
demonstration project for Apple Inc. (AAPL) sourced directly from SEC EDGAR XBRL
company-facts API.

Usage:
    python scripts/seed_aapl_demo.py [--force-reimport]

Flags:
    --force-reimport  Re-import financial data even if it already exists
                      (default: skip existing data points).

All historical values are reported actuals from:
  https://data.sec.gov/api/xbrl/companyfacts/CIK0000320193.json
  SEC CIK: 0000320193 | Ticker: AAPL | Company: Apple Inc.

All forecast/WACC/DCF parameters are ILLUSTRATIVE ANALYST ASSUMPTIONS.
They are NOT official Apple guidance or investment advice.
"""
from __future__ import annotations

import logging
import sys
from datetime import date
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Bootstrap sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.config import settings
from src.data.database import get_db_session, init_db
from src.data.models import Company, SecFiling, ValuationProject
from src.data.services import CompanyService, FinancialDataService, ProjectService
from src.dcf.models import DcfAssumptions, EquityBridgeInputs, TerminalValueInputs
from src.dcf.services import DcfService
from src.filings.edgar_client import SecEdgarClient
from src.filings.extractor import StatementExtractor, date_from_str
from src.filings.models import FilingMetadata
from src.forecasting.models import ForecastAssumptions
from src.forecasting.services import ForecastService
from src.wacc.models import (
    CapitalStructureInputs, CostOfDebtInputs, CostOfEquityInputs,
    InputProvenance, SourceCategory, TaxRateInputs, WaccAssumptions,
)
from src.wacc.services import WaccService

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-7s  %(name)s -- %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("seed_aapl_demo")

COMPANY_NAME = "Apple Inc."
COMPANY_TICKER = "AAPL"
COMPANY_CIK = "0000320193"
PROJECT_NAME = "AAPL -- Real Data DCF Demo (FY2022-FY2024)"
PROJECT_DESCRIPTION = (
    "[DEMO PROJECT] Historical financials sourced from SEC EDGAR 10-K XBRL data "
    "(reported actuals). All forecast, WACC, and DCF parameters are illustrative "
    "analyst-consensus-style assumptions only. NOT investment advice or official "
    "Apple guidance."
)

FISCAL_YEAR_ENDS = {
    2022: "2022-09-24",
    2023: "2023-09-30",
    2024: "2024-09-28",
}


def get_or_create_company() -> Company:
    from sqlalchemy import select
    with get_db_session() as session:
        stmt = select(Company).where(Company.ticker == COMPANY_TICKER)
        company = session.scalars(stmt).first()
        if company:
            logger.info("Company exists: %s (ID %d)", company.name, company.id)
            return company
    logger.info("Creating company record for %s ...", COMPANY_NAME)
    company = CompanyService.create_company(
        name=COMPANY_NAME,
        ticker=COMPANY_TICKER,
        exchange="NASDAQ",
        sector="Information Technology",
        industry="Technology Hardware, Storage & Peripherals",
        country="United States",
        currency="USD",
        fiscal_year_end="Late September",
        description=(
            "Apple Inc. designs, manufactures, and markets smartphones, personal computers, "
            "tablets, wearables and accessories, and sells a variety of related services. "
            "SEC CIK: 0000320193. Data source: SEC EDGAR XBRL company facts API."
        ),
    )
    logger.info("Created company ID %d: %s", company.id, company.name)
    return company


def get_or_create_project(company: Company) -> ValuationProject:
    projects = ProjectService.list_projects(company_id=company.id)
    for p in projects:
        if p.name == PROJECT_NAME:
            logger.info("Project exists: '%s' (ID %d)", p.name, p.id)
            return p
    logger.info("Creating project: %s ...", PROJECT_NAME)
    project = ProjectService.create_project(
        name=PROJECT_NAME,
        company_id=company.id,
        description=PROJECT_DESCRIPTION,
        status="Active",
    )
    logger.info("Created project ID %d: %s", project.id, project.name)
    return project


def fetch_aapl_facts(edgar: SecEdgarClient) -> Optional[Dict[str, Any]]:
    logger.info("Fetching AAPL XBRL company facts from SEC EDGAR ...")
    facts = edgar.get_company_facts(COMPANY_CIK)
    if not facts:
        logger.error("Failed to retrieve AAPL company facts.")
        return None
    logger.info("Company facts downloaded successfully.")
    return facts


def build_stub_filing(fiscal_year: int, report_date_str: str) -> FilingMetadata:
    return FilingMetadata(
        ticker=COMPANY_TICKER,
        cik=COMPANY_CIK,
        company_name=COMPANY_NAME,
        form_type="10-K",
        accession_number=f"stub-aapl-10K-{fiscal_year}",
        filing_date=report_date_str,
        report_date=report_date_str,
        fiscal_year=fiscal_year,
        fiscal_period="FY",
        status="Discovered",
    )


def extract_year_items(
    extractor: StatementExtractor,
    facts: Dict[str, Any],
    fiscal_year: int,
    report_date_str: str,
) -> List[Any]:
    stub = build_stub_filing(fiscal_year, report_date_str)
    items = extractor.extract_from_company_facts(facts, stub)
    logger.info("FY%d (%s): extracted %d items", fiscal_year, report_date_str, len(items))
    return items


def persist_year_data(
    project: ValuationProject,
    items: List[Any],
    fiscal_year: int,
    report_date_str: str,
    conflict_resolution: str,
) -> Tuple[int, int]:
    valid_records = []
    for item in items:
        try:
            period_end = date_from_str(item.period_end_date)
            period_start = date_from_str(item.period_start_date)
        except Exception as exc:
            logger.warning("Skipping %s -- bad date: %s", item.line_item_code, exc)
            continue
        valid_records.append({
            "statement_type": item.statement_type,
            "line_item_code": item.line_item_code,
            "display_name": item.display_name,
            "period_start_date": period_start,
            "period_end_date": period_end,
            "period_type": "annual",
            "value": float(item.value),
            "currency": "USD",
            "unit": "units",
            "data_classification": "reported_actual",
            "source_type": "sec_filing",
            "source_reference": (
                f"SEC EDGAR XBRL -- Apple Inc. 10-K FY{fiscal_year} "
                f"(Period ending {report_date_str}). "
                f"CIK: {COMPANY_CIK}. Tag: {item.source_label}."
            ),
            "source_reporting_date": date_from_str(report_date_str),
        })
    if not valid_records:
        logger.warning("FY%d: no valid records.", fiscal_year)
        return 0, 0
    batch, saved, updated = FinancialDataService.save_import_batch(
        project_id=project.id,
        filename=f"SEC_10-K_AAPL_FY{fiscal_year}_{report_date_str}.xbrl",
        valid_records=valid_records,
        rejected_count=0,
        source_description=(
            f"SEC EDGAR XBRL company-facts API -- Apple Inc. (AAPL) FY{fiscal_year} 10-K, "
            f"period ending {report_date_str}. All values are reported actuals in USD."
        ),
        conflict_resolution=conflict_resolution,
    )
    logger.info(
        "FY%d: batch ID %d -- %d saved, %d updated", fiscal_year, batch.id, saved, updated
    )
    return saved, updated


def save_filing_record(company: Company, fiscal_year: int, report_date_str: str) -> None:
    with get_db_session() as session:
        existing = session.query(SecFiling).filter(
            SecFiling.cik == COMPANY_CIK,
            SecFiling.fiscal_year == fiscal_year,
            SecFiling.form_type == "10-K",
        ).first()
        if existing:
            logger.info("SecFiling record exists for FY%d (ID %d).", fiscal_year, existing.id)
            return
        filing = SecFiling(
            company_id=company.id,
            ticker=COMPANY_TICKER,
            cik=COMPANY_CIK,
            company_name=COMPANY_NAME,
            form_type="10-K",
            accession_number=f"demo-aapl-10K-FY{fiscal_year}",
            filing_date=date_from_str(report_date_str),
            report_date=date_from_str(report_date_str),
            fiscal_year=fiscal_year,
            fiscal_period="FY",
            primary_doc_url=(
                f"https://data.sec.gov/api/xbrl/companyfacts/CIK{COMPANY_CIK}.json"
            ),
            status="Analyzed",
            is_amended=0,
        )
        session.add(filing)
        session.flush()
        logger.info("Saved SecFiling record for FY%d (ID %d).", fiscal_year, filing.id)


def create_wacc_model(project: ValuationProject) -> Any:
    wacc_name = "[DEMO] AAPL Base Case WACC -- Illustrative Assumptions"
    for m in WaccService.list_wacc_models(project.id):
        if m.name == wacc_name:
            logger.info("WACC model exists (ID %d).", m.id)
            return m
    assumptions = WaccAssumptions(
        name=wacc_name,
        description=(
            "[ILLUSTRATIVE] CAPM-based WACC for Apple Inc. FY2024 context. "
            "Risk-free rate 4.25% (US 10-yr proxy), Beta 1.24 (5Y monthly proxy), "
            "ERP 5.0% (Damodaran proxy), Cost of debt 3.1% (FY2024 effective rate proxy), "
            "Tax rate 24.1% (FY2024 effective rate). NOT investment advice."
        ),
        equity_inputs=CostOfEquityInputs(
            risk_free_rate=4.25,
            equity_beta=1.24,
            equity_risk_premium=5.00,
            rf_provenance=InputProvenance(
                source_category=SourceCategory.USER_ENTERED.value,
                source_reference="US 10-Year Treasury Yield Q4 2024 Proxy",
                notes="Illustrative. Not a live market rate.",
                is_proxy=True,
            ),
            beta_provenance=InputProvenance(
                source_category=SourceCategory.USER_ENTERED.value,
                source_reference="5-Year Monthly Beta vs S&P 500 Proxy",
                notes="Illustrative AAPL beta. Verify against live data.",
                is_proxy=True,
            ),
            erp_provenance=InputProvenance(
                source_category=SourceCategory.USER_ENTERED.value,
                source_reference="Damodaran Implied ERP January 2024 Proxy",
                notes="Illustrative ERP. See damodaran.com.",
                is_proxy=True,
            ),
        ),
        debt_inputs=CostOfDebtInputs(
            pre_tax_cost_of_debt=3.10,
            provenance=InputProvenance(
                source_category=SourceCategory.USER_ENTERED.value,
                source_reference="AAPL FY2024 Effective Interest Rate Proxy",
                notes="Illustrative cost of debt. Based on FY2024 10-K proxy.",
                is_proxy=True,
            ),
        ),
        capital_inputs=CapitalStructureInputs(
            equity_value=3_500_000_000_000.0,
            equity_value_type="market_value",
            equity_shares_count=15_334_000_000.0,
            equity_share_price=228.0,
            debt_value=108_040_000_000.0,
            debt_value_type="interest_bearing_debt",
            included_debt_items=["short_term_debt", "long_term_debt"],
            equity_provenance=InputProvenance(
                source_category=SourceCategory.USER_ENTERED.value,
                source_reference="AAPL Market Cap Proxy September 2024",
                notes="Illustrative. Not a real-time figure.",
                is_proxy=True,
            ),
            debt_provenance=InputProvenance(
                source_category=SourceCategory.HISTORICAL_DATA.value,
                source_reference="Apple 10-K FY2024 -- Total Interest-Bearing Debt",
                notes="FY2024 10-K: ~$10.95B short-term + ~$97.09B long-term debt.",
                is_proxy=False,
            ),
        ),
        tax_inputs=TaxRateInputs(
            tax_rate=24.1,
            tax_rate_source="historical_effective",
            provenance=InputProvenance(
                source_category=SourceCategory.HISTORICAL_DATA.value,
                source_reference="Apple 10-K FY2024 -- Effective Tax Rate",
                notes="FY2024 effective tax rate proxy.",
            ),
        ),
    )
    model = WaccService.save_wacc_model(
        project_id=project.id,
        name=wacc_name,
        assumptions=assumptions,
        description="Illustrative CAPM WACC for AAPL -- demo only.",
    )
    logger.info("Saved WACC model ID %d", model.id)
    return model


def create_forecast_model(project: ValuationProject) -> Any:
    fname = "[DEMO] AAPL Base Case Forecast FY2025-FY2029 -- Illustrative"
    for m in ForecastService.list_forecast_models(project.id):
        if m.name == fname:
            logger.info("Forecast model exists (ID %d).", m.id)
            return m
    assumptions = ForecastAssumptions(
        name=fname,
        description=(
            "[ILLUSTRATIVE] 5-year Base Case anchored to FY2024 actuals. "
            "Revenue growth and margins are approximate consensus-range estimates. "
            "NOT official Apple guidance."
        ),
        horizon_years=5,
        revenue_growth_rates=[7.0, 6.0, 5.5, 5.0, 5.0],
        gross_margin_rates=[45.5, 45.8, 46.0, 46.2, 46.5],
        opex_pct_rates=[13.5, 13.3, 13.0, 12.8, 12.5],
        da_pct_rates=[3.3, 3.3, 3.2, 3.2, 3.1],
        capex_pct_rates=[3.0, 3.0, 2.8, 2.8, 2.8],
        use_working_capital_days=True,
        dso_days=[21.0, 21.0, 21.0, 21.0, 21.0],
        dio_days=[7.0, 7.0, 7.0, 7.0, 7.0],
        dpo_days=[90.0, 90.0, 90.0, 90.0, 90.0],
        nwc_pct_revenue=[10.0, 10.0, 10.0, 10.0, 10.0],
        tax_rate=24.1,
        driver_sources={
            "revenue_growth": "user_entered",
            "gross_margin": "user_entered",
            "opex_pct": "user_entered",
            "da_pct": "historical_baseline",
            "capex_pct": "historical_baseline",
            "working_capital": "historical_baseline",
            "tax_rate": "historical_baseline",
        },
    )
    model = ForecastService.save_forecast_model(
        project_id=project.id,
        name=fname,
        assumptions=assumptions,
        base_period_label="FY2024 (Reported)",
        description="Illustrative 5-year forecast for AAPL -- demo only.",
    )
    logger.info("Saved Forecast model ID %d", model.id)
    return model


def create_dcf_model(
    project: ValuationProject,
    forecast_model: Any,
    wacc_model: Any,
) -> Any:
    dcf_name = "[DEMO] AAPL Base Case DCF -- Illustrative"
    for m in DcfService.list_dcf_models(project.id):
        if m.name == dcf_name:
            logger.info("DCF model exists (ID %d).", m.id)
            return m
    assumptions = DcfAssumptions(
        name=dcf_name,
        description=(
            "[ILLUSTRATIVE] Base Case DCF for Apple Inc. (AAPL). "
            "Terminal value: Gordon Growth at 3.5% perpetual growth. "
            "Bridge uses FY2024 reported balance sheet. NOT investment advice."
        ),
        project_id=project.id,
        forecast_model_id=forecast_model.id,
        wacc_model_id=wacc_model.id,
        valuation_date="2024-09-28",
        discounting_convention="end_of_year",
        terminal_inputs=TerminalValueInputs(
            method="gordon_growth",
            perpetual_growth_rate=3.5,
        ),
        bridge_inputs=EquityBridgeInputs(
            cash_and_equivalents=29_943_000_000.0,
            debt_value=108_040_000_000.0,
            minority_interest=0.0,
            preferred_equity=0.0,
            other_adjustments=0.0,
        ),
        diluted_shares=15_334_000_000.0,
    )
    model = DcfService.save_dcf_model(
        project_id=project.id,
        name=dcf_name,
        assumptions=assumptions,
        description="Illustrative Base Case DCF for AAPL -- demo only.",
    )
    logger.info("Saved DCF model ID %d", model.id)
    return model


def main(force_reimport: bool = False) -> None:
    conflict_mode = "overwrite" if force_reimport else "skip"
    logger.info("=" * 70)
    logger.info("AAPL Real-Data Demo Seed Script  (conflict_resolution=%s)", conflict_mode)
    logger.info("=" * 70)

    init_db()

    company = get_or_create_company()
    project = get_or_create_project(company)

    edgar = SecEdgarClient()
    facts = fetch_aapl_facts(edgar)

    if facts:
        extractor = StatementExtractor()
        total_saved, total_updated = 0, 0
        for fy, report_date_str in sorted(FISCAL_YEAR_ENDS.items()):
            logger.info("-- FY%d (end: %s) ...", fy, report_date_str)
            try:
                items = extract_year_items(extractor, facts, fy, report_date_str)
                if items:
                    s, u = persist_year_data(project, items, fy, report_date_str, conflict_mode)
                    total_saved += s
                    total_updated += u
                    save_filing_record(company, fy, report_date_str)
                else:
                    logger.warning(
                        "FY%d: no items extracted. Verify report_date '%s' matches EDGAR records.",
                        fy, report_date_str,
                    )
            except Exception as exc:
                logger.error("Error processing FY%d: %s", fy, exc, exc_info=True)
        logger.info("Import complete: %d saved, %d updated.", total_saved, total_updated)
    else:
        logger.warning("No XBRL facts available. Financial data NOT imported.")

    wacc_model = create_wacc_model(project)
    forecast_model = create_forecast_model(project)
    dcf_model = create_dcf_model(project, forecast_model, wacc_model)

    logger.info("=" * 70)
    logger.info("Seed complete:")
    logger.info("  Company  : %s (ID %d)", company.name, company.id)
    logger.info("  Project  : %s (ID %d)", project.name, project.id)
    logger.info("  WACC     : ID %d -- %s", wacc_model.id, wacc_model.name)
    logger.info("  Forecast : ID %d -- %s", forecast_model.id, forecast_model.name)
    logger.info("  DCF      : ID %d -- %s", dcf_model.id, dcf_model.name)
    logger.info("Run: streamlit run app/main.py")
    logger.info("=" * 70)


if __name__ == "__main__":
    force = "--force-reimport" in sys.argv
    main(force_reimport=force)
