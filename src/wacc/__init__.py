"""WACC Estimation and Capital Cost Engine.

Provides models, pure calculations, parameter extraction engine, persistence services,
and presentation formatting for Weighted Average Cost of Capital analysis.
"""

from src.wacc.calculations import (
    calculate_capital_structure,
    calculate_cost_of_debt,
    calculate_cost_of_equity,
    calculate_wacc,
)
from src.wacc.engine import WaccEngine
from src.wacc.formatting import (
    build_capital_structure_dataframe,
    build_cost_of_capital_dataframe,
    create_capital_structure_donut_chart,
    create_wacc_contribution_bar_chart,
)
from src.wacc.models import (
    CapitalStructureInputs,
    CapitalStructureResult,
    CostOfDebtInputs,
    CostOfDebtResult,
    CostOfEquityInputs,
    CostOfEquityResult,
    InputProvenance,
    SourceCategory,
    TaxRateInputs,
    WaccAssumptions,
    WaccResult,
)
from src.wacc.services import WaccService

__all__ = [
    "SourceCategory",
    "InputProvenance",
    "CostOfEquityInputs",
    "CostOfDebtInputs",
    "CapitalStructureInputs",
    "TaxRateInputs",
    "WaccAssumptions",
    "CostOfEquityResult",
    "CostOfDebtResult",
    "CapitalStructureResult",
    "WaccResult",
    "calculate_cost_of_equity",
    "calculate_cost_of_debt",
    "calculate_capital_structure",
    "calculate_wacc",
    "WaccEngine",
    "WaccService",
    "build_capital_structure_dataframe",
    "build_cost_of_capital_dataframe",
    "create_capital_structure_donut_chart",
    "create_wacc_contribution_bar_chart",
]
