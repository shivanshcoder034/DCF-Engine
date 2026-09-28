"""Financial forecasting and multi-year projection engine package.

Provides deterministic multi-period income statement schedules, operating
working capital forecasts, Unlevered Free Cash Flow (UFCF) projections,
and scenario assumption persistence.
"""

from src.forecasting.models import (
    ForecastAssumptions,
    ForecastResult,
    YearForecast,
)
from src.forecasting.engine import FinancialForecastingEngine
from src.forecasting.services import ForecastService
from src.forecasting.formatting import (
    generate_forecast_statement_table,
    generate_ufcf_bridge_table,
)

__all__ = [
    "ForecastAssumptions",
    "YearForecast",
    "ForecastResult",
    "FinancialForecastingEngine",
    "ForecastService",
    "generate_forecast_statement_table",
    "generate_ufcf_bridge_table",
]
