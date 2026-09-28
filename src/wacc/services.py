"""Service layer for persisting and retrieving WACC assumption models.

Manages versioned, named WACC assumption scenarios associated with specific valuation projects.
"""

from __future__ import annotations

import logging
from typing import List, Optional

from sqlalchemy import select

from src.data.database import get_db_session
from src.data.models import WaccModel
from src.wacc.models import WaccAssumptions

logger = logging.getLogger(__name__)


class WaccService:
    """Business operations for persisting, loading, and managing WACC models."""

    @staticmethod
    def list_wacc_models(project_id: int) -> List[WaccModel]:
        """List all saved WACC assumption models for a project."""
        with get_db_session() as session:
            stmt = (
                select(WaccModel)
                .where(WaccModel.project_id == project_id)
                .order_by(WaccModel.updated_at.desc())
            )
            return list(session.scalars(stmt).all())

    @staticmethod
    def get_wacc_model(model_id: int) -> Optional[WaccModel]:
        """Retrieve a specific saved WACC model by ID."""
        with get_db_session() as session:
            stmt = select(WaccModel).where(WaccModel.id == model_id)
            return session.scalars(stmt).first()

    @staticmethod
    def save_wacc_model(
        project_id: int,
        name: str,
        assumptions: WaccAssumptions,
        description: Optional[str] = None,
    ) -> WaccModel:
        """Persist or update a named WACC assumption set for a project."""
        cleaned_name = name.strip()
        if not cleaned_name:
            raise ValueError("WACC scenario name cannot be empty.")

        with get_db_session() as session:
            # Check if matching scenario name already exists for this project
            stmt = select(WaccModel).where(
                WaccModel.project_id == project_id,
                WaccModel.name == cleaned_name,
            )
            existing = session.scalars(stmt).first()

            if existing:
                existing.assumptions_json = assumptions.to_json()
                existing.description = description.strip() if description else existing.description
                session.flush()
                return existing
            else:
                model = WaccModel(
                    project_id=project_id,
                    name=cleaned_name,
                    assumptions_json=assumptions.to_json(),
                    description=description.strip() if description else None,
                )
                session.add(model)
                session.flush()
                return model

    @staticmethod
    def delete_wacc_model(model_id: int) -> bool:
        """Delete a saved WACC scenario."""
        with get_db_session() as session:
            stmt = select(WaccModel).where(WaccModel.id == model_id)
            model = session.scalars(stmt).first()
            if not model:
                return False
            session.delete(model)
            session.flush()
            return True
