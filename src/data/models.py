"""SQLAlchemy ORM models for companies, valuation projects, and financial statements.

Defines persistence schema for company profiles, valuation project workspaces,
normalized financial data points, and traceable import batches.
"""

from __future__ import annotations

from datetime import datetime, date
from typing import List, Optional

from sqlalchemy import (
    Column,
    Integer,
    String,
    Float,
    Text,
    Date,
    DateTime,
    ForeignKey,
    Index,
)
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


class Company(Base):
    """Company profile representing a publicly traded or private target entity."""

    __tablename__ = "companies"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False, index=True)
    ticker = Column(String(32), nullable=True, index=True)
    exchange = Column(String(32), nullable=True)
    sector = Column(String(100), nullable=True)
    industry = Column(String(100), nullable=True)
    country = Column(String(100), nullable=False, default="United States")
    currency = Column(String(10), nullable=False, default="USD")
    fiscal_year_end = Column(String(50), nullable=True)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    projects = relationship(
        "ValuationProject",
        back_populates="company",
        cascade="all, delete-orphan",
        passive_deletes=False,
    )

    def __repr__(self) -> str:
        ticker_str = f" ({self.ticker})" if self.ticker else ""
        return f"<Company id={self.id} name='{self.name}'{ticker_str}>"


class ValuationProject(Base):
    """Valuation modelling workspace associated with a specific company."""

    __tablename__ = "valuation_projects"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False, index=True)
    company_id = Column(Integer, ForeignKey("companies.id", ondelete="RESTRICT"), nullable=False, index=True)
    description = Column(Text, nullable=True)
    status = Column(String(50), nullable=False, default="Active")  # Active, Archived
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    company = relationship("Company", back_populates="projects")
    data_points = relationship(
        "FinancialDataPoint",
        back_populates="project",
        cascade="all, delete-orphan",
    )
    import_batches = relationship(
        "ImportBatch",
        back_populates="project",
        cascade="all, delete-orphan",
    )
    forecast_models = relationship(
        "ForecastModel",
        back_populates="project",
        cascade="all, delete-orphan",
    )
    wacc_models = relationship(
        "WaccModel",
        back_populates="project",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<ValuationProject id={self.id} name='{self.name}' company_id={self.company_id} status='{self.status}'>"


class ImportBatch(Base):
    """Traceable audit record of an imported dataset."""

    __tablename__ = "import_batches"

    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(Integer, ForeignKey("valuation_projects.id", ondelete="CASCADE"), nullable=False, index=True)
    filename = Column(String(255), nullable=False)
    import_timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)
    source_description = Column(Text, nullable=True)
    records_accepted = Column(Integer, default=0, nullable=False)
    records_rejected = Column(Integer, default=0, nullable=False)
    status = Column(String(50), default="Completed", nullable=False)  # Completed, Partial, Failed
    notes = Column(Text, nullable=True)

    # Relationships
    project = relationship("ValuationProject", back_populates="import_batches")
    data_points = relationship("FinancialDataPoint", back_populates="import_batch")

    def __repr__(self) -> str:
        return f"<ImportBatch id={self.id} file='{self.filename}' accepted={self.records_accepted}>"


class FinancialDataPoint(Base):
    """Normalized atomic historical financial record."""

    __tablename__ = "financial_data_points"

    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(Integer, ForeignKey("valuation_projects.id", ondelete="CASCADE"), nullable=False, index=True)

    # Statement categorization
    statement_type = Column(String(50), nullable=False, index=True)  # income_statement, balance_sheet, cash_flow_statement
    line_item_code = Column(String(100), nullable=False, index=True)
    display_name = Column(String(255), nullable=False)

    # Reporting period
    period_start_date = Column(Date, nullable=False)
    period_end_date = Column(Date, nullable=False, index=True)
    period_type = Column(String(50), nullable=False, index=True)  # annual, quarterly

    # Value & Scale
    value = Column(Float, nullable=False)
    currency = Column(String(10), nullable=False, default="USD")
    unit = Column(String(50), nullable=False, default="units")  # units, thousands, millions, billions

    # Classification & Provenance
    data_classification = Column(String(50), nullable=False, default="reported_actual", index=True)
    source_type = Column(String(50), nullable=False, default="manual_entry")  # manual_entry, csv_import, excel_import
    source_reference = Column(String(255), nullable=True)
    source_reporting_date = Column(Date, nullable=True)
    import_batch_id = Column(Integer, ForeignKey("import_batches.id", ondelete="SET NULL"), nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    project = relationship("ValuationProject", back_populates="data_points")
    import_batch = relationship("ImportBatch", back_populates="data_points")

    __table_args__ = (
        Index(
            "ix_project_statement_item_period",
            "project_id",
            "statement_type",
            "line_item_code",
            "period_end_date",
            "data_classification",
        ),
    )

    def __repr__(self) -> str:
        return (
            f"<FinancialDataPoint id={self.id} item='{self.line_item_code}' "
            f"period={self.period_end_date} val={self.value} {self.currency}>"
        )


class ForecastModel(Base):
    """Persisted forecast assumption set and model configuration."""

    __tablename__ = "forecast_models"

    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(Integer, ForeignKey("valuation_projects.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    horizon_years = Column(Integer, nullable=False, default=5)
    base_period_label = Column(String(50), nullable=False)
    assumptions_json = Column(Text, nullable=False)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    project = relationship("ValuationProject", back_populates="forecast_models")

    def __repr__(self) -> str:
        return f"<ForecastModel id={self.id} name='{self.name}' project_id={self.project_id} horizon={self.horizon_years}>"


class WaccModel(Base):
    """Persisted WACC assumption set and capital cost configuration."""

    __tablename__ = "wacc_models"

    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(Integer, ForeignKey("valuation_projects.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    assumptions_json = Column(Text, nullable=False)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    project = relationship("ValuationProject", back_populates="wacc_models")

    def __repr__(self) -> str:
        return f"<WaccModel id={self.id} name='{self.name}' project_id={self.project_id}>"

