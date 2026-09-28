"""Typed data models and structures for multi-scenario DCF analysis (Base, Bull, Bear).

Defines assumption overrides, case configurations, baseline traceability,
and consolidated scenario comparison outputs.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

from src.dcf.models import DcfValuationResult, TerminalValueMethod
from src.forecasting.models import ForecastResult


class ScenarioCaseType(str, Enum):
    """Standard scenario cases."""
    BASE = "Base"
    BULL = "Bull"
    BEAR = "Bear"


@dataclass
class ScenarioOverrides:
    """Configurable assumption overrides relative to the Base case.

    Units:
    - revenue_growth_delta_pp: Percentage points (e.g. +2.0 pp added to each forecast year's growth rate)
    - margin_delta_pp: Percentage points (e.g. +1.5 pp added to gross margin to expand operating margin)
    - wacc_delta_bps: Basis points (e.g. -50.0 bps = -0.50% added to base WACC)
    - perpetual_growth_delta_bps: Basis points (e.g. +25.0 bps = +0.25% added to Gordon Growth rate)
    - exit_multiple_delta: Multiple change (e.g. +1.5x added to exit multiple)
    """

    revenue_growth_delta_pp: float = 0.0
    margin_delta_pp: float = 0.0
    wacc_delta_bps: float = 0.0
    perpetual_growth_delta_bps: float = 0.0
    exit_multiple_delta: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> ScenarioOverrides:
        return cls(
            revenue_growth_delta_pp=float(data.get("revenue_growth_delta_pp", 0.0)),
            margin_delta_pp=float(data.get("margin_delta_pp", 0.0)),
            wacc_delta_bps=float(data.get("wacc_delta_bps", 0.0)),
            perpetual_growth_delta_bps=float(data.get("perpetual_growth_delta_bps", 0.0)),
            exit_multiple_delta=float(data.get("exit_multiple_delta", 0.0)),
        )

    @classmethod
    def default_bull(cls) -> ScenarioOverrides:
        """Illustrative starting assumptions for Bull case (not recommendations or benchmarks)."""
        return cls(
            revenue_growth_delta_pp=2.0,
            margin_delta_pp=1.5,
            wacc_delta_bps=-50.0,
            perpetual_growth_delta_bps=25.0,
            exit_multiple_delta=1.5,
        )

    @classmethod
    def default_bear(cls) -> ScenarioOverrides:
        """Illustrative starting assumptions for Bear case (not recommendations or benchmarks)."""
        return cls(
            revenue_growth_delta_pp=-2.0,
            margin_delta_pp=-1.5,
            wacc_delta_bps=50.0,
            perpetual_growth_delta_bps=-25.0,
            exit_multiple_delta=-1.5,
        )

    @classmethod
    def default_base(cls) -> ScenarioOverrides:
        """Base case has zero overrides by definition."""
        return cls(
            revenue_growth_delta_pp=0.0,
            margin_delta_pp=0.0,
            wacc_delta_bps=0.0,
            perpetual_growth_delta_bps=0.0,
            exit_multiple_delta=0.0,
        )


@dataclass
class ScenarioAnalysisAssumptions:
    """Configurable assumption bundle for a 3-case scenario analysis set."""

    name: str = "Base / Bull / Bear Scenario Set"
    description: Optional[str] = "Comparative scenario valuation analysis."
    project_id: int = 1

    # Linked Base models
    dcf_model_id: Optional[int] = None
    forecast_model_id: Optional[int] = None
    wacc_model_id: Optional[int] = None

    # Overrides for Bull and Bear cases
    bull_overrides: ScenarioOverrides = field(default_factory=ScenarioOverrides.default_bull)
    bear_overrides: ScenarioOverrides = field(default_factory=ScenarioOverrides.default_bear)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "project_id": self.project_id,
            "dcf_model_id": self.dcf_model_id,
            "forecast_model_id": self.forecast_model_id,
            "wacc_model_id": self.wacc_model_id,
            "bull_overrides": self.bull_overrides.to_dict(),
            "bear_overrides": self.bear_overrides.to_dict(),
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> ScenarioAnalysisAssumptions:
        return cls(
            name=str(data.get("name", "Base / Bull / Bear Scenario Set")),
            description=data.get("description"),
            project_id=int(data.get("project_id", 1)),
            dcf_model_id=data.get("dcf_model_id"),
            forecast_model_id=data.get("forecast_model_id"),
            wacc_model_id=data.get("wacc_model_id"),
            bull_overrides=ScenarioOverrides.from_dict(data.get("bull_overrides", {})),
            bear_overrides=ScenarioOverrides.from_dict(data.get("bear_overrides", {})),
        )

    @classmethod
    def from_json(cls, json_str: str) -> ScenarioAnalysisAssumptions:
        return cls.from_dict(json.loads(json_str))


@dataclass
class ScenarioCaseResult:
    """Valuation and forecast results for a single scenario case."""

    case_name: str  # "Base", "Bull", or "Bear"
    overrides: ScenarioOverrides

    # Provenance tracking
    linked_forecast_name: Optional[str] = None
    linked_wacc_name: Optional[str] = None
    linked_dcf_name: Optional[str] = None

    # Effective assumptions applied
    effective_revenue_growth_avg: Optional[float] = None
    effective_operating_margin_avg: Optional[float] = None
    effective_wacc: Optional[float] = None
    terminal_method: str = TerminalValueMethod.GORDON_GROWTH.value
    effective_terminal_param: Optional[float] = None  # g (%) or multiple (x)

    # Calculation results
    forecast_result: Optional[ForecastResult] = None
    dcf_result: Optional[DcfValuationResult] = None

    # Key valuation outputs
    pv_forecast_ufcf: Optional[float] = None
    pv_terminal_value: Optional[float] = None
    enterprise_value: Optional[float] = None
    equity_value: Optional[float] = None
    implied_value_per_share: Optional[float] = None
    shares_applied: Optional[float] = None

    # Status & diagnostics
    is_valid: bool = False
    status: str = "incomplete"  # "complete", "incomplete", "invalid"
    warnings: List[str] = field(default_factory=list)
    missing_inputs: List[str] = field(default_factory=list)


@dataclass
class ScenarioAnalysisResult:
    """Consolidated 3-case scenario comparison bundle."""

    assumptions: ScenarioAnalysisAssumptions
    base_case: ScenarioCaseResult
    bull_case: ScenarioCaseResult
    bear_case: ScenarioCaseResult
    currency: str = "USD"
    is_complete: bool = False
    disclaimer: str = (
        "Scenario valuation analysis illustrates the mathematical sensitivity of intrinsic value to user-specified "
        "assumption shifts. Scenarios do not represent forecasts, probability distributions, or guarantees of future performance."
    )
