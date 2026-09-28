"""Service layer for persisting and retrieving scenario analysis models.

Manages versioned, named scenario valuation configurations associated with specific valuation projects.
"""

from __future__ import annotations

import logging
from typing import List, Optional

from sqlalchemy import select

from src.data.database import get_db_session
from src.data.models import ScenarioModel
from src.scenarios.models import ScenarioAnalysisAssumptions

logger = logging.getLogger(__name__)


class ScenarioService:
    """Business operations for persisting, loading, and managing scenario analysis sets."""

    @staticmethod
    def list_scenario_models(project_id: int) -> List[ScenarioModel]:
        """List all saved scenario analysis models for a project."""
        with get_db_session() as session:
            stmt = (
                select(ScenarioModel)
                .where(ScenarioModel.project_id == project_id)
                .order_by(ScenarioModel.updated_at.desc())
            )
            return list(session.scalars(stmt).all())

    @staticmethod
    def get_scenario_model(model_id: int) -> Optional[ScenarioModel]:
        """Retrieve a specific saved scenario analysis model by ID."""
        with get_db_session() as session:
            stmt = select(ScenarioModel).where(ScenarioModel.id == model_id)
            return session.scalars(stmt).first()

    @staticmethod
    def save_scenario_model(
        project_id: int,
        name: str,
        assumptions: ScenarioAnalysisAssumptions,
        description: Optional[str] = None,
    ) -> ScenarioModel:
        """Persist or update a named scenario analysis assumption set for a project."""
        cleaned_name = name.strip()
        if not cleaned_name:
            raise ValueError("Scenario set name cannot be empty.")

        with get_db_session() as session:
            # Check if matching scenario name already exists for this project
            stmt = select(ScenarioModel).where(
                ScenarioModel.project_id == project_id,
                ScenarioModel.name == cleaned_name,
            )
            existing = session.scalars(stmt).first()

            if existing:
                existing.dcf_model_id = assumptions.dcf_model_id
                existing.forecast_model_id = assumptions.forecast_model_id
                existing.wacc_model_id = assumptions.wacc_model_id
                existing.assumptions_json = assumptions.to_json()
                existing.description = description.strip() if description else existing.description
                session.flush()
                return existing
            else:
                model = ScenarioModel(
                    project_id=project_id,
                    name=cleaned_name,
                    dcf_model_id=assumptions.dcf_model_id,
                    forecast_model_id=assumptions.forecast_model_id,
                    wacc_model_id=assumptions.wacc_model_id,
                    assumptions_json=assumptions.to_json(),
                    description=description.strip() if description else None,
                )
                session.add(model)
                session.flush()
                return model

    @staticmethod
    def delete_scenario_model(model_id: int) -> bool:
        """Delete a saved scenario analysis set."""
        with get_db_session() as session:
            stmt = select(ScenarioModel).where(ScenarioModel.id == model_id)
            model = session.scalars(stmt).first()
            if not model:
                return False
            session.delete(model)
            session.flush()
            return True
