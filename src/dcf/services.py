"""Service layer for persisting and retrieving DCF valuation assumption models.

Manages versioned, named DCF valuation scenarios associated with specific valuation projects.
"""

from __future__ import annotations

import logging
from typing import List, Optional

from sqlalchemy import select

from src.data.database import get_db_session
from src.data.models import DcfModel
from src.dcf.models import DcfAssumptions

logger = logging.getLogger(__name__)


class DcfService:
    """Business operations for persisting, loading, and managing DCF valuation models."""

    @staticmethod
    def list_dcf_models(project_id: int) -> List[DcfModel]:
        """List all saved DCF valuation models for a project."""
        with get_db_session() as session:
            stmt = (
                select(DcfModel)
                .where(DcfModel.project_id == project_id)
                .order_by(DcfModel.updated_at.desc())
            )
            return list(session.scalars(stmt).all())

    @staticmethod
    def get_dcf_model(model_id: int) -> Optional[DcfModel]:
        """Retrieve a specific saved DCF model by ID."""
        with get_db_session() as session:
            stmt = select(DcfModel).where(DcfModel.id == model_id)
            return session.scalars(stmt).first()

    @staticmethod
    def save_dcf_model(
        project_id: int,
        name: str,
        assumptions: DcfAssumptions,
        description: Optional[str] = None,
    ) -> DcfModel:
        """Persist or update a named DCF valuation assumption set for a project."""
        cleaned_name = name.strip()
        if not cleaned_name:
            raise ValueError("DCF scenario name cannot be empty.")

        with get_db_session() as session:
            # Check if matching scenario name already exists for this project
            stmt = select(DcfModel).where(
                DcfModel.project_id == project_id,
                DcfModel.name == cleaned_name,
            )
            existing = session.scalars(stmt).first()

            if existing:
                existing.forecast_model_id = assumptions.forecast_model_id
                existing.wacc_model_id = assumptions.wacc_model_id
                existing.assumptions_json = assumptions.to_json()
                existing.description = description.strip() if description else existing.description
                session.flush()
                return existing
            else:
                model = DcfModel(
                    project_id=project_id,
                    name=cleaned_name,
                    forecast_model_id=assumptions.forecast_model_id,
                    wacc_model_id=assumptions.wacc_model_id,
                    assumptions_json=assumptions.to_json(),
                    description=description.strip() if description else None,
                )
                session.add(model)
                session.flush()
                return model

    @staticmethod
    def delete_dcf_model(model_id: int) -> bool:
        """Delete a saved DCF scenario."""
        with get_db_session() as session:
            stmt = select(DcfModel).where(DcfModel.id == model_id)
            model = session.scalars(stmt).first()
            if not model:
                return False
            session.delete(model)
            session.flush()
            return True
