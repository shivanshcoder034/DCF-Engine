"""Persistence service layer for saving, loading, and managing report configurations.

Provides database operations scoped to ValuationProject entities in SQLite.
"""

from __future__ import annotations

import logging
from typing import List, Optional

from sqlalchemy import select

from src.data.database import get_db_session
from src.data.models import ReportModel
from src.reporting.models import ReportConfig

logger = logging.getLogger(__name__)


class ReportService:
    """Service handling CRUD operations for saved valuation reports."""

    @staticmethod
    def list_reports(project_id: int) -> List[ReportModel]:
        """List all saved report configurations for a valuation project."""
        with get_db_session() as session:
            stmt = (
                select(ReportModel)
                .where(ReportModel.project_id == project_id)
                .order_by(ReportModel.updated_at.desc())
            )
            return list(session.scalars(stmt).all())

    @staticmethod
    def get_report(report_id: int) -> Optional[ReportModel]:
        """Retrieve a specific saved report model by ID."""
        with get_db_session() as session:
            stmt = select(ReportModel).where(ReportModel.id == report_id)
            return session.scalars(stmt).first()

    @staticmethod
    def save_report(
        project_id: int,
        name: str,
        config: ReportConfig,
        description: Optional[str] = None,
    ) -> ReportModel:
        """Persist or update a report configuration for a valuation project."""
        clean_name = name.strip()
        if not clean_name:
            raise ValueError("Report configuration name cannot be empty.")

        with get_db_session() as session:
            stmt = select(ReportModel).where(
                ReportModel.project_id == project_id,
                ReportModel.name == clean_name,
            )
            existing = session.scalars(stmt).first()

            if existing:
                existing.title = config.metadata.title
                existing.subtitle = config.metadata.subtitle
                existing.config_json = config.to_json()
                if description is not None:
                    existing.description = description.strip()
                session.flush()
                return existing
            else:
                model = ReportModel(
                    project_id=project_id,
                    name=clean_name,
                    title=config.metadata.title,
                    subtitle=config.metadata.subtitle,
                    config_json=config.to_json(),
                    description=description.strip() if description else None,
                )
                session.add(model)
                session.flush()
                return model

    @staticmethod
    def delete_report(report_id: int) -> bool:
        """Delete a saved report configuration."""
        with get_db_session() as session:
            stmt = select(ReportModel).where(ReportModel.id == report_id)
            model = session.scalars(stmt).first()
            if not model:
                return False
            session.delete(model)
            session.flush()
            return True
