"""Service layer coordinating business logic, validation, and database transactions.

Ensures strict separation between UI actions, domain rules, and atomic database persistence.
"""

from __future__ import annotations

import logging
from datetime import date
from typing import Any, Dict, List, Optional, Tuple

from src.data.database import get_db_session, init_db
from src.data.models import Company, FinancialDataPoint, ImportBatch, ValuationProject
from src.data.repository import (
    CompanyRepository,
    FinancialDataRepository,
    ImportBatchRepository,
    ValuationProjectRepository,
)
from src.data.validators import validate_financial_record

logger = logging.getLogger(__name__)

# Ensure database tables exist upon loading the service layer
init_db()


class CompanyService:
    """Business operations for company profiles."""

    @staticmethod
    def list_companies(search: Optional[str] = None) -> List[Company]:
        with get_db_session() as session:
            repo = CompanyRepository(session)
            return repo.get_all(search=search)

    @staticmethod
    def get_company(company_id: int) -> Optional[Company]:
        with get_db_session() as session:
            repo = CompanyRepository(session)
            return repo.get_by_id(company_id)

    @staticmethod
    def create_company(
        name: str,
        country: str = "United States",
        currency: str = "USD",
        ticker: Optional[str] = None,
        exchange: Optional[str] = None,
        sector: Optional[str] = None,
        industry: Optional[str] = None,
        fiscal_year_end: Optional[str] = None,
        description: Optional[str] = None,
    ) -> Company:
        cleaned_name = name.strip()
        if not cleaned_name:
            raise ValueError("Company name is required and cannot be whitespace only.")

        cleaned_ticker = ticker.strip().upper() if ticker and ticker.strip() else None
        cleaned_exchange = exchange.strip().upper() if exchange and exchange.strip() else None

        with get_db_session() as session:
            repo = CompanyRepository(session)

            # Check potential duplicate: same name or same ticker & exchange
            existing = repo.get_all(search=cleaned_name)
            for c in existing:
                if c.name.lower() == cleaned_name.lower():
                    raise ValueError(f"A company named '{cleaned_name}' already exists (ID: {c.id}).")
                if cleaned_ticker and c.ticker == cleaned_ticker and c.exchange == cleaned_exchange:
                    raise ValueError(
                        f"A company with ticker '{cleaned_ticker}' on exchange '{cleaned_exchange or 'Unspecified'}' already exists."
                    )

            return repo.create(
                name=cleaned_name,
                country=country.strip() or "United States",
                currency=currency.strip().upper() or "USD",
                ticker=cleaned_ticker,
                exchange=cleaned_exchange,
                sector=sector.strip() if sector and sector.strip() else None,
                industry=industry.strip() if industry and industry.strip() else None,
                fiscal_year_end=fiscal_year_end.strip() if fiscal_year_end and fiscal_year_end.strip() else None,
                description=description.strip() if description and description.strip() else None,
            )

    @staticmethod
    def update_company(company_id: int, updates: Dict[str, Any]) -> Optional[Company]:
        if "name" in updates and not str(updates["name"]).strip():
            raise ValueError("Company name cannot be empty.")

        with get_db_session() as session:
            repo = CompanyRepository(session)
            return repo.update(company_id, updates)

    @staticmethod
    def delete_company(company_id: int, force: bool = False) -> bool:
        """Safely delete a company profile, blocking deletion if valuation projects exist unless forced."""
        with get_db_session() as session:
            repo = CompanyRepository(session)
            project_count = repo.count_projects(company_id)
            if project_count > 0 and not force:
                raise ValueError(
                    f"Cannot delete company. It has {project_count} associated valuation project(s). "
                    "Archive or delete the associated projects first to prevent unintended loss of financial data."
                )
            return repo.delete(company_id)


class ProjectService:
    """Business operations for valuation projects."""

    @staticmethod
    def list_projects(
        company_id: Optional[int] = None,
        include_archived: bool = True,
        search: Optional[str] = None,
    ) -> List[ValuationProject]:
        with get_db_session() as session:
            repo = ValuationProjectRepository(session)
            return repo.get_all(company_id=company_id, include_archived=include_archived, search=search)

    @staticmethod
    def get_project(project_id: int) -> Optional[ValuationProject]:
        with get_db_session() as session:
            repo = ValuationProjectRepository(session)
            return repo.get_by_id(project_id)

    @staticmethod
    def create_project(
        name: str,
        company_id: int,
        description: Optional[str] = None,
        status: str = "Active",
    ) -> ValuationProject:
        cleaned_name = name.strip()
        if not cleaned_name:
            raise ValueError("Project name is required.")

        with get_db_session() as session:
            company_repo = CompanyRepository(session)
            if not company_repo.get_by_id(company_id):
                raise ValueError(f"Cannot create project: Company with ID {company_id} does not exist.")

            repo = ValuationProjectRepository(session)
            return repo.create(
                name=cleaned_name,
                company_id=company_id,
                description=description.strip() if description and description.strip() else None,
                status=status,
            )

    @staticmethod
    def update_project(project_id: int, updates: Dict[str, Any]) -> Optional[ValuationProject]:
        if "name" in updates and not str(updates["name"]).strip():
            raise ValueError("Project name cannot be empty.")

        with get_db_session() as session:
            repo = ValuationProjectRepository(session)
            return repo.update(project_id, updates)

    @staticmethod
    def delete_project(project_id: int) -> bool:
        with get_db_session() as session:
            repo = ValuationProjectRepository(session)
            return repo.delete(project_id)


# Alias for backward and cross-module compatibility
ValuationProjectService = ProjectService


class FinancialDataService:
    """Business operations for historical financial data points and import batches."""

    @staticmethod
    def list_records(
        project_id: int,
        statement_type: Optional[str] = None,
        period_type: Optional[str] = None,
        classification: Optional[str] = None,
    ) -> List[FinancialDataPoint]:
        with get_db_session() as session:
            repo = FinancialDataRepository(session)
            return repo.get_by_project(
                project_id=project_id,
                statement_type=statement_type,
                period_type=period_type,
                classification=classification,
            )

    @staticmethod
    def get_record(data_point_id: int) -> Optional[FinancialDataPoint]:
        with get_db_session() as session:
            repo = FinancialDataRepository(session)
            return repo.get_by_id(data_point_id)

    @staticmethod
    def create_record(record_data: Dict[str, Any]) -> FinancialDataPoint:
        validation_result = validate_financial_record(record_data)
        if not validation_result.is_valid:
            err_msgs = [e.message for e in validation_result.errors]
            raise ValueError(f"Record validation failed: {'; '.join(err_msgs)}")

        clean = validation_result.data
        assert clean is not None

        with get_db_session() as session:
            repo = FinancialDataRepository(session)

            # Check potential duplicate
            duplicate = repo.find_duplicate(
                project_id=clean["project_id"],
                statement_type=clean["statement_type"],
                line_item_code=clean["line_item_code"],
                period_end_date=clean["period_end_date"],
                data_classification=clean["data_classification"],
            )
            if duplicate:
                raise ValueError(
                    f"A duplicate record already exists for line item '{clean['line_item_code']}' "
                    f"ending on {clean['period_end_date']} under classification '{clean['data_classification']}'."
                )

            return repo.create(**clean)

    @staticmethod
    def update_record(data_point_id: int, updates: Dict[str, Any]) -> Optional[FinancialDataPoint]:
        with get_db_session() as session:
            repo = FinancialDataRepository(session)
            existing = repo.get_by_id(data_point_id)
            if not existing:
                raise ValueError(f"Financial record with ID {data_point_id} not found.")

            # Merge current and updates for validation
            merged = {
                "project_id": existing.project_id,
                "statement_type": updates.get("statement_type", existing.statement_type),
                "line_item_code": updates.get("line_item_code", existing.line_item_code),
                "display_name": updates.get("display_name", existing.display_name),
                "period_start_date": updates.get("period_start_date", existing.period_start_date),
                "period_end_date": updates.get("period_end_date", existing.period_end_date),
                "period_type": updates.get("period_type", existing.period_type),
                "value": updates.get("value", existing.value),
                "currency": updates.get("currency", existing.currency),
                "unit": updates.get("unit", existing.unit),
                "data_classification": updates.get("data_classification", existing.data_classification),
                "source_type": updates.get("source_type", existing.source_type),
                "source_reference": updates.get("source_reference", existing.source_reference),
                "source_reporting_date": updates.get("source_reporting_date", existing.source_reporting_date),
                "import_batch_id": existing.import_batch_id,
            }

            validation = validate_financial_record(merged)
            if not validation.is_valid:
                raise ValueError("; ".join(e.message for e in validation.errors))

            return repo.update(data_point_id, validation.data or {})

    @staticmethod
    def delete_record(data_point_id: int) -> bool:
        with get_db_session() as session:
            repo = FinancialDataRepository(session)
            return repo.delete(data_point_id)

    @staticmethod
    def save_import_batch(
        project_id: int,
        filename: str,
        valid_records: List[Dict[str, Any]],
        rejected_count: int,
        source_description: Optional[str] = None,
        conflict_resolution: str = "skip",  # "skip" or "overwrite"
    ) -> Tuple[ImportBatch, int, int]:
        """Atomically persist an import batch and its valid data points with duplicate resolution.

        Returns (batch_record, count_saved, count_updated).
        """
        with get_db_session() as session:
            data_repo = FinancialDataRepository(session)
            batch_repo = ImportBatchRepository(session)

            batch = batch_repo.create(
                project_id=project_id,
                filename=filename,
                source_description=source_description,
                records_accepted=0,
                records_rejected=rejected_count,
                status="Processing",
            )

            count_saved = 0
            count_updated = 0

            for rec in valid_records:
                duplicate = data_repo.find_duplicate(
                    project_id=project_id,
                    statement_type=rec["statement_type"],
                    line_item_code=rec["line_item_code"],
                    period_end_date=rec["period_end_date"],
                    data_classification=rec["data_classification"],
                )

                if duplicate:
                    if conflict_resolution == "overwrite":
                        rec_payload = dict(rec)
                        rec_payload["import_batch_id"] = batch.id
                        data_repo.update(duplicate.id, rec_payload)
                        count_updated += 1
                    elif conflict_resolution == "skip":
                        continue
                else:
                    rec_payload = dict(rec)
                    rec_payload["project_id"] = project_id
                    rec_payload["import_batch_id"] = batch.id
                    data_repo.create(**rec_payload)
                    count_saved += 1

            batch.records_accepted = count_saved + count_updated
            batch.status = "Completed" if rejected_count == 0 else "Partial"
            session.flush()

            return batch, count_saved, count_updated

    @staticmethod
    def list_import_batches(project_id: int) -> List[ImportBatch]:
        with get_db_session() as session:
            repo = ImportBatchRepository(session)
            return repo.get_by_project(project_id)
