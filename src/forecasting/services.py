"""Service layer for persisting and retrieving forecast assumption models.

Manages versioned forecast assumption sets scoped to specific valuation projects.
"""

from __future__ import annotations

import logging
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.data.database import get_db_session
from src.data.models import ForecastModel
from src.forecasting.models import ForecastAssumptions

logger = logging.getLogger(__name__)


class ForecastService:
    """Business operations for persisting, loading, and managing forecast models."""

    @staticmethod
    def list_forecast_models(project_id: int) -> List[ForecastModel]:
        """List all saved forecast assumption models for a project."""
        with get_db_session() as session:
            stmt = (
                select(ForecastModel)
                .where(ForecastModel.project_id == project_id)
                .order_by(ForecastModel.updated_at.desc())
            )
            return list(session.scalars(stmt).all())

    @staticmethod
    def get_forecast_model(model_id: int) -> Optional[ForecastModel]:
        """Retrieve a specific saved forecast model by ID."""
        with get_db_session() as session:
            stmt = select(ForecastModel).where(ForecastModel.id == model_id)
            return session.scalars(stmt).first()

    @staticmethod
    def save_forecast_model(
        project_id: int,
        name: str,
        assumptions: ForecastAssumptions,
        base_period_label: str,
        description: Optional[str] = None,
    ) -> ForecastModel:
        """Persist or update a forecast assumption set for a project."""
        cleaned_name = name.strip()
        if not cleaned_name:
            raise ValueError("Forecast scenario name cannot be empty.")

        with get_db_session() as session:
            # Check if matching scenario name already exists for this project
            stmt = select(ForecastModel).where(
                ForecastModel.project_id == project_id,
                ForecastModel.name == cleaned_name,
            )
            existing = session.scalars(stmt).first()

            if existing:
                existing.horizon_years = assumptions.horizon_years
                existing.base_period_label = base_period_label
                existing.assumptions_json = assumptions.to_json()
                existing.description = description.strip() if description else existing.description
                session.flush()
                return existing
            else:
                model = ForecastModel(
                    project_id=project_id,
                    name=cleaned_name,
                    horizon_years=assumptions.horizon_years,
                    base_period_label=base_period_label,
                    assumptions_json=assumptions.to_json(),
                    description=description.strip() if description else None,
                )
                session.add(model)
                session.flush()
                return model

    @staticmethod
    def delete_forecast_model(model_id: int) -> bool:
        """Delete a saved forecast scenario."""
        with get_db_session() as session:
            stmt = select(ForecastModel).where(ForecastModel.id == model_id)
            model = session.scalars(stmt).first()
            if not model:
                return False
            session.delete(model)
            session.flush()
            return True
