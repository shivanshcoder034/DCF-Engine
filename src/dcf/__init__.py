"""DCF Valuation Engine package.

Provides typed models, deterministic cash flow discounting, terminal value models,
enterprise-to-equity bridges, SQLite scenario persistence, and tabular formatting.
"""

from src.dcf.calculations import (
    calculate_dcf_valuation,
    calculate_discount_factor,
    calculate_equity_bridge,
    calculate_terminal_value_exit_multiple,
    calculate_terminal_value_gordon_growth,
    discount_cash_flow_series,
)
from src.dcf.engine import DcfEngine
from src.dcf.formatting import (
    build_discounting_schedule_dataframe,
    build_equity_bridge_dataframe,
    create_cash_flow_discounting_chart,
    create_ev_composition_donut_chart,
)
from src.dcf.models import (
    DcfAssumptions,
    DcfValuationResult,
    DiscountingConvention,
    EquityBridgeInputs,
    EquityBridgeResult,
    TerminalValueInputs,
    TerminalValueMethod,
    TerminalValueResult,
    YearDiscountingResult,
)
from src.dcf.services import DcfService

__all__ = [
    "DiscountingConvention",
    "TerminalValueMethod",
    "TerminalValueInputs",
    "EquityBridgeInputs",
    "DcfAssumptions",
    "YearDiscountingResult",
    "TerminalValueResult",
    "EquityBridgeResult",
    "DcfValuationResult",
    "calculate_discount_factor",
    "discount_cash_flow_series",
    "calculate_terminal_value_gordon_growth",
    "calculate_terminal_value_exit_multiple",
    "calculate_equity_bridge",
    "calculate_dcf_valuation",
    "DcfEngine",
    "DcfService",
    "build_discounting_schedule_dataframe",
    "build_equity_bridge_dataframe",
    "create_cash_flow_discounting_chart",
    "create_ev_composition_donut_chart",
]
