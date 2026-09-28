"""Domain models and data structures for report generation, presentation, and exports.

Defines section configurations, metadata, model reference links, and complete
compiled report bundles.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import date
from enum import Enum
import json
from typing import Any, Dict, List, Optional

from src.analysis.models import HistoricalAnalysisBundle
from src.dcf.models import DcfAssumptions, DcfValuationResult
from src.forecasting.models import ForecastAssumptions, ForecastResult
from src.scenarios.models import ScenarioAnalysisResult
from src.sensitivity.models import MonteCarloSimulationResult, SensitivityConfig, SensitivityMatrixResult
from src.wacc.models import WaccAssumptions, WaccResult


class ReportSection(str, Enum):
    """Supported valuation report chapters/sections."""

    OVERVIEW = "overview"
    EXECUTIVE_SUMMARY = "executive_summary"
    HISTORICAL_ANALYSIS = "historical_analysis"
    FORECAST_PROJECTIONS = "forecast_projections"
    WACC_ANALYSIS = "wacc_analysis"
    DCF_VALUATION = "dcf_valuation"
    SCENARIO_ANALYSIS = "scenario_analysis"
    SENSITIVITY_SIMULATION = "sensitivity_simulation"
    DISCLOSURES_LIMITATIONS = "disclosures_limitations"
    APPENDIX = "appendix"

    @classmethod
    def display_name(cls, section: str | ReportSection) -> str:
        """User-friendly title for the report section."""
        mapping = {
            cls.OVERVIEW: "1. Report Overview & Metadata",
            cls.EXECUTIVE_SUMMARY: "2. Executive Valuation Summary",
            cls.HISTORICAL_ANALYSIS: "3. Historical Financial Analysis",
            cls.FORECAST_PROJECTIONS: "4. Forecast Assumptions & Projections",
            cls.WACC_ANALYSIS: "5. WACC & Cost of Capital",
            cls.DCF_VALUATION: "6. DCF Valuation & Equity Bridge",
            cls.SCENARIO_ANALYSIS: "7. Scenario Analysis (Base / Bull / Bear)",
            cls.SENSITIVITY_SIMULATION: "8. Sensitivity Analysis & Simulation",
            cls.DISCLOSURES_LIMITATIONS: "9. Data Quality, Limitations & Disclosures",
            cls.APPENDIX: "10. Appendix & Methodology",
        }
        val = cls(section) if isinstance(section, str) else section
        return mapping.get(val, str(section))


@dataclass
class ReportSectionConfig:
    """Toggles for selecting which sections are included in the generated report."""

    include_overview: bool = True
    include_executive_summary: bool = True
    include_historical_analysis: bool = True
    include_forecast_projections: bool = True
    include_wacc_analysis: bool = True
    include_dcf_valuation: bool = True
    include_scenario_analysis: bool = True
    include_sensitivity_simulation: bool = True
    include_disclosures_limitations: bool = True
    include_appendix: bool = True

    def to_dict(self) -> Dict[str, bool]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> ReportSectionConfig:
        return cls(
            include_overview=bool(data.get("include_overview", True)),
            include_executive_summary=bool(data.get("include_executive_summary", True)),
            include_historical_analysis=bool(data.get("include_historical_analysis", True)),
            include_forecast_projections=bool(data.get("include_forecast_projections", True)),
            include_wacc_analysis=bool(data.get("include_wacc_analysis", True)),
            include_dcf_valuation=bool(data.get("include_dcf_valuation", True)),
            include_scenario_analysis=bool(data.get("include_scenario_analysis", True)),
            include_sensitivity_simulation=bool(data.get("include_sensitivity_simulation", True)),
            include_disclosures_limitations=bool(data.get("include_disclosures_limitations", True)),
            include_appendix=bool(data.get("include_appendix", True)),
        )


@dataclass
class ReportMetadata:
    """Descriptive metadata and narrative headers for the report."""

    title: str = "Valuation & DCF Analysis Report"
    subtitle: Optional[str] = "Intrinsic Valuation, Scenario Sensitivity & Risk Assessment"
    company_name: str = ""
    ticker: Optional[str] = None
    project_name: str = ""
    project_id: int = 0
    reporting_currency: str = "USD"
    fiscal_year_end: str = "Dec 31"
    report_date: str = field(default_factory=lambda: date.today().isoformat())
    prepared_by: Optional[str] = None
    narrative_summary: Optional[str] = None
    valuation_notes: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> ReportMetadata:
        return cls(
            title=str(data.get("title") or "Valuation & DCF Analysis Report"),
            subtitle=data.get("subtitle"),
            company_name=str(data.get("company_name") or ""),
            ticker=data.get("ticker"),
            project_name=str(data.get("project_name") or ""),
            project_id=int(data.get("project_id", 0)),
            reporting_currency=str(data.get("reporting_currency") or "USD"),
            fiscal_year_end=str(data.get("fiscal_year_end") or "Dec 31"),
            report_date=str(data.get("report_date") or date.today().isoformat()),
            prepared_by=data.get("prepared_by"),
            narrative_summary=data.get("narrative_summary"),
            valuation_notes=data.get("valuation_notes"),
        )


@dataclass
class ReportModelReferences:
    """References to saved underlying models linked to this report."""

    historical_frequency: str = "annual"
    historical_classification: str = "reported_actual"
    forecast_model_id: Optional[int] = None
    forecast_model_name: Optional[str] = None
    wacc_model_id: Optional[int] = None
    wacc_model_name: Optional[str] = None
    dcf_model_id: Optional[int] = None
    dcf_model_name: Optional[str] = None
    scenario_model_id: Optional[int] = None
    scenario_model_name: Optional[str] = None
    sensitivity_model_id: Optional[int] = None
    sensitivity_model_name: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> ReportModelReferences:
        return cls(
            historical_frequency=str(data.get("historical_frequency", "annual")),
            historical_classification=str(data.get("historical_classification", "reported_actual")),
            forecast_model_id=int(data["forecast_model_id"]) if data.get("forecast_model_id") is not None else None,
            forecast_model_name=data.get("forecast_model_name"),
            wacc_model_id=int(data["wacc_model_id"]) if data.get("wacc_model_id") is not None else None,
            wacc_model_name=data.get("wacc_model_name"),
            dcf_model_id=int(data["dcf_model_id"]) if data.get("dcf_model_id") is not None else None,
            dcf_model_name=data.get("dcf_model_name"),
            scenario_model_id=int(data["scenario_model_id"]) if data.get("scenario_model_id") is not None else None,
            scenario_model_name=data.get("scenario_model_name"),
            sensitivity_model_id=int(data["sensitivity_model_id"]) if data.get("sensitivity_model_id") is not None else None,
            sensitivity_model_name=data.get("sensitivity_model_name"),
        )


@dataclass
class ReportConfig:
    """Complete configuration specification for a reproducible valuation report."""

    metadata: ReportMetadata = field(default_factory=ReportMetadata)
    references: ReportModelReferences = field(default_factory=ReportModelReferences)
    sections: ReportSectionConfig = field(default_factory=ReportSectionConfig)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "metadata": self.metadata.to_dict(),
            "references": self.references.to_dict(),
            "sections": self.sections.to_dict(),
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> ReportConfig:
        return cls(
            metadata=ReportMetadata.from_dict(data.get("metadata", {})),
            references=ReportModelReferences.from_dict(data.get("references", {})),
            sections=ReportSectionConfig.from_dict(data.get("sections", {})),
        )

    @classmethod
    def from_json(cls, json_str: str) -> ReportConfig:
        return cls.from_dict(json.loads(json_str))


@dataclass
class ReportBundle:
    """Compiled domain bundle containing all resolved calculations, models, and diagnostics."""

    config: ReportConfig
    project_id: int
    company_name: str
    ticker: Optional[str] = None
    historical_bundle: Optional[HistoricalAnalysisBundle] = None
    forecast_assumptions: Optional[ForecastAssumptions] = None
    forecast_result: Optional[ForecastResult] = None
    wacc_assumptions: Optional[WaccAssumptions] = None
    wacc_result: Optional[WaccResult] = None
    dcf_assumptions: Optional[DcfAssumptions] = None
    dcf_result: Optional[DcfValuationResult] = None
    scenario_model_name: Optional[str] = None
    scenario_result: Optional[ScenarioAnalysisResult] = None
    sensitivity_model_name: Optional[str] = None
    sensitivity_config: Optional[SensitivityConfig] = None
    sensitivity_matrix_result: Optional[SensitivityMatrixResult] = None
    monte_carlo_result: Optional[MonteCarloSimulationResult] = None
    missing_models_diagnostics: List[str] = field(default_factory=list)
    validation_warnings: List[str] = field(default_factory=list)
    data_quality_issues: List[str] = field(default_factory=list)
