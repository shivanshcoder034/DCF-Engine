"""Scenario Analysis (Base, Bull, Bear) Engine Package.

Provides deterministic multi-case DCF valuation, assumption override modeling,
persistence, cross-scenario comparisons, and auditability.
"""

from src.scenarios.engine import ScenarioEngine
from src.scenarios.formatting import (
    build_assumption_audit_dataframe,
    build_scenario_comparison_dataframe,
    create_scenario_cash_flow_trajectory_chart,
    create_scenario_ev_composition_bar_chart,
    create_scenario_ev_equity_bar_chart,
    create_scenario_share_price_chart,
)
from src.scenarios.models import (
    ScenarioAnalysisAssumptions,
    ScenarioAnalysisResult,
    ScenarioCaseResult,
    ScenarioCaseType,
    ScenarioOverrides,
)
from src.scenarios.services import ScenarioService

__all__ = [
    "ScenarioOverrides",
    "ScenarioAnalysisAssumptions",
    "ScenarioCaseResult",
    "ScenarioAnalysisResult",
    "ScenarioCaseType",
    "ScenarioEngine",
    "ScenarioService",
    "build_scenario_comparison_dataframe",
    "build_assumption_audit_dataframe",
    "create_scenario_ev_equity_bar_chart",
    "create_scenario_share_price_chart",
    "create_scenario_cash_flow_trajectory_chart",
    "create_scenario_ev_composition_bar_chart",
]
