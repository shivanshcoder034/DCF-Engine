"""Service layer for persisting and retrieving sensitivity and simulation configurations.

Manages versioned, named sensitivity configurations associated with specific valuation projects.
"""

from __future__ import annotations

import logging
from typing import List, Optional

from sqlalchemy import select

from src.data.database import get_db_session
from src.data.models import SensitivityModel
from src.sensitivity.models import SensitivityConfig

logger = logging.getLogger(__name__)


class SensitivityService:
    """Business operations for persisting, loading, and managing sensitivity analysis models."""

    @staticmethod
    def list_sensitivity_models(project_id: int) -> List[SensitivityModel]:
        """List all saved sensitivity analysis configurations for a project."""
        with get_db_session() as session:
            stmt = (
                select(SensitivityModel)
                .where(SensitivityModel.project_id == project_id)
                .order_by(SensitivityModel.updated_at.desc())
            )
            return list(session.scalars(stmt).all())

    @staticmethod
    def get_sensitivity_model(model_id: int) -> Optional[SensitivityModel]:
        """Retrieve a specific saved sensitivity model by ID."""
        with get_db_session() as session:
            stmt = select(SensitivityModel).where(SensitivityModel.id == model_id)
            return session.scalars(stmt).first()

    @staticmethod
    def save_sensitivity_model(
        project_id: int,
        name: str,
        config: SensitivityConfig,
        description: Optional[str] = None,
    ) -> SensitivityModel:
        """Persist or update a named sensitivity configuration for a project."""
        cleaned_name = name.strip()
        if not cleaned_name:
            raise ValueError("Sensitivity configuration name cannot be empty.")

        with get_db_session() as session:
            stmt = select(SensitivityModel).where(
                SensitivityModel.project_id == project_id,
                SensitivityModel.name == cleaned_name,
            )
            existing = session.scalars(stmt).first()

            if existing:
                existing.dcf_model_id = config.dcf_model_id
                existing.config_json = config.to_json()
                existing.description = description.strip() if description else existing.description
                session.flush()
                return existing
            else:
                model = SensitivityModel(
                    project_id=project_id,
                    name=cleaned_name,
                    dcf_model_id=config.dcf_model_id,
                    config_json=config.to_json(),
                    description=description.strip() if description else None,
                )
                session.add(model)
                session.flush()
                return model

    @staticmethod
    def delete_sensitivity_model(model_id: int) -> bool:
        """Delete a saved sensitivity configuration."""
        with get_db_session() as session:
            stmt = select(SensitivityModel).where(SensitivityModel.id == model_id)
            model = session.scalars(stmt).first()
            if not model:
                return False
            session.delete(model)
            session.flush()
            return True
