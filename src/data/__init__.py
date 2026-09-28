"""Data management package for companies, valuation projects, and financial records.

Provides SQLAlchemy persistence, schemas, validation, repositories, services,
and multi-format file importers.
"""

from src.data.models import Base, Company, DcfModel, FinancialDataPoint, ForecastModel, ImportBatch, ScenarioModel, ValuationProject, WaccModel
from src.data.database import engine, get_db_session, init_db
from src.data.schemas import (
    DataClassification,
    FinancialUnit,
    LineItemDefinition,
    PeriodType,
    ProjectStatus,
    SourceType,
    StatementType,
    STANDARD_LINE_ITEMS,
    get_standard_items_by_statement,
)
from src.data.services import CompanyService, FinancialDataService, ProjectService
from src.data.validators import validate_financial_record

__all__ = [
    "Base",
    "Company",
    "ValuationProject",
    "ForecastModel",
    "WaccModel",
    "DcfModel",
    "ScenarioModel",
    "ImportBatch",
    "FinancialDataPoint",
    "engine",
    "init_db",
    "get_db_session",
    "StatementType",
    "PeriodType",
    "DataClassification",
    "SourceType",
    "FinancialUnit",
    "ProjectStatus",
    "LineItemDefinition",
    "STANDARD_LINE_ITEMS",
    "get_standard_items_by_statement",
    "CompanyService",
    "ProjectService",
    "FinancialDataService",
    "validate_financial_record",
]
