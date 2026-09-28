"""Repository layer managing direct database interactions for financial entities.

Provides typed CRUD operations and query helpers adhering to SQLAlchemy 2.0 standards.
"""

from __future__ import annotations

from datetime import date
from typing import Any, Dict, List, Optional

from sqlalchemy import or_, select
from sqlalchemy.orm import Session, joinedload

from src.data.models import Company, FinancialDataPoint, ImportBatch, ValuationProject


class CompanyRepository:
    """Data access repository for Company entities."""

    def __init__(self, session: Session):
        self.session = session

    def get_all(self, search: Optional[str] = None) -> List[Company]:
        stmt = select(Company).order_by(Company.name.asc())
        if search and search.strip():
            term = f"%{search.strip()}%"
            stmt = stmt.where(or_(Company.name.ilike(term), Company.ticker.ilike(term)))
        return list(self.session.scalars(stmt).all())

    def get_by_id(self, company_id: int) -> Optional[Company]:
        stmt = (
            select(Company)
            .where(Company.id == company_id)
            .options(joinedload(Company.projects))
        )
        return self.session.scalars(stmt).unique().first()

    def create(self, **kwargs: Any) -> Company:
        company = Company(**kwargs)
        self.session.add(company)
        self.session.flush()
        return company

    def update(self, company_id: int, updates: Dict[str, Any]) -> Optional[Company]:
        company = self.get_by_id(company_id)
        if not company:
            return None
        for key, value in updates.items():
            if hasattr(company, key) and key not in ("id", "created_at"):
                setattr(company, key, value)
        self.session.flush()
        return company

    def count_projects(self, company_id: int) -> int:
        stmt = select(ValuationProject).where(ValuationProject.company_id == company_id)
        return len(list(self.session.scalars(stmt).all()))

    def delete(self, company_id: int) -> bool:
        company = self.get_by_id(company_id)
        if not company:
            return False
        self.session.delete(company)
        self.session.flush()
        return True


class ValuationProjectRepository:
    """Data access repository for ValuationProject entities."""

    def __init__(self, session: Session):
        self.session = session

    def get_all(
        self,
        company_id: Optional[int] = None,
        include_archived: bool = True,
        search: Optional[str] = None,
    ) -> List[ValuationProject]:
        stmt = (
            select(ValuationProject)
            .options(joinedload(ValuationProject.company))
            .order_by(ValuationProject.created_at.desc())
        )
        if company_id is not None:
            stmt = stmt.where(ValuationProject.company_id == company_id)
        if not include_archived:
            stmt = stmt.where(ValuationProject.status == "Active")
        if search and search.strip():
            term = f"%{search.strip()}%"
            stmt = stmt.where(ValuationProject.name.ilike(term))
        return list(self.session.scalars(stmt).unique().all())

    def get_by_id(self, project_id: int) -> Optional[ValuationProject]:
        stmt = (
            select(ValuationProject)
            .where(ValuationProject.id == project_id)
            .options(joinedload(ValuationProject.company))
        )
        return self.session.scalars(stmt).unique().first()

    def create(self, **kwargs: Any) -> ValuationProject:
        project = ValuationProject(**kwargs)
        self.session.add(project)
        self.session.flush()
        return project

    def update(self, project_id: int, updates: Dict[str, Any]) -> Optional[ValuationProject]:
        project = self.get_by_id(project_id)
        if not project:
            return None
        for key, value in updates.items():
            if hasattr(project, key) and key not in ("id", "created_at"):
                setattr(project, key, value)
        self.session.flush()
        return project

    def delete(self, project_id: int) -> bool:
        project = self.get_by_id(project_id)
        if not project:
            return False
        self.session.delete(project)
        self.session.flush()
        return True


class FinancialDataRepository:
    """Data access repository for FinancialDataPoint records."""

    def __init__(self, session: Session):
        self.session = session

    def get_by_project(
        self,
        project_id: int,
        statement_type: Optional[str] = None,
        period_type: Optional[str] = None,
        classification: Optional[str] = None,
    ) -> List[FinancialDataPoint]:
        stmt = (
            select(FinancialDataPoint)
            .where(FinancialDataPoint.project_id == project_id)
            .order_by(
                FinancialDataPoint.period_end_date.asc(),
                FinancialDataPoint.statement_type.asc(),
                FinancialDataPoint.line_item_code.asc(),
            )
        )
        if statement_type:
            stmt = stmt.where(FinancialDataPoint.statement_type == statement_type)
        if period_type:
            stmt = stmt.where(FinancialDataPoint.period_type == period_type)
        if classification:
            stmt = stmt.where(FinancialDataPoint.data_classification == classification)

        return list(self.session.scalars(stmt).all())

    def get_by_id(self, data_point_id: int) -> Optional[FinancialDataPoint]:
        stmt = select(FinancialDataPoint).where(FinancialDataPoint.id == data_point_id)
        return self.session.scalars(stmt).first()

    def find_duplicate(
        self,
        project_id: int,
        statement_type: str,
        line_item_code: str,
        period_end_date: date,
        data_classification: str,
    ) -> Optional[FinancialDataPoint]:
        stmt = select(FinancialDataPoint).where(
            FinancialDataPoint.project_id == project_id,
            FinancialDataPoint.statement_type == statement_type,
            FinancialDataPoint.line_item_code == line_item_code,
            FinancialDataPoint.period_end_date == period_end_date,
            FinancialDataPoint.data_classification == data_classification,
        )
        return self.session.scalars(stmt).first()

    def create(self, **kwargs: Any) -> FinancialDataPoint:
        data_point = FinancialDataPoint(**kwargs)
        self.session.add(data_point)
        self.session.flush()
        return data_point

    def update(self, data_point_id: int, updates: Dict[str, Any]) -> Optional[FinancialDataPoint]:
        point = self.get_by_id(data_point_id)
        if not point:
            return None
        for key, value in updates.items():
            if hasattr(point, key) and key not in ("id", "created_at"):
                setattr(point, key, value)
        self.session.flush()
        return point

    def delete(self, data_point_id: int) -> bool:
        point = self.get_by_id(data_point_id)
        if not point:
            return False
        self.session.delete(point)
        self.session.flush()
        return True


class ImportBatchRepository:
    """Data access repository for ImportBatch provenance records."""

    def __init__(self, session: Session):
        self.session = session

    def create(self, **kwargs: Any) -> ImportBatch:
        batch = ImportBatch(**kwargs)
        self.session.add(batch)
        self.session.flush()
        return batch

    def get_by_project(self, project_id: int) -> List[ImportBatch]:
        stmt = (
            select(ImportBatch)
            .where(ImportBatch.project_id == project_id)
            .order_by(ImportBatch.import_timestamp.desc())
        )
        return list(self.session.scalars(stmt).all())

    def get_by_id(self, batch_id: int) -> Optional[ImportBatch]:
        stmt = select(ImportBatch).where(ImportBatch.id == batch_id)
        return self.session.scalars(stmt).first()
