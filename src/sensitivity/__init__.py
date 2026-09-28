"""Sensitivity Analysis and Simulation Engine Package.

Provides two-dimensional valuation sensitivity matrices, Monte Carlo probabilistic simulations,
persistence, and visualization components.
"""

from src.sensitivity.engine import SensitivityEngine
from src.sensitivity.formatting import (
    build_monte_carlo_stats_dataframe,
    build_sensitivity_matrix_dataframe,
    create_monte_carlo_histogram,
    create_sensitivity_heatmap_chart,
)
from src.sensitivity.models import (
    AxisRangeConfig,
    DistributionConfig,
    DistributionType,
    MonteCarloSimulationResult,
    MonteCarloSummaryStats,
    SensitivityCellResult,
    SensitivityConfig,
    SensitivityMatrixResult,
    SensitivityMetric,
)
from src.sensitivity.services import SensitivityService

__all__ = [
    "SensitivityEngine",
    "SensitivityService",
    "SensitivityMetric",
    "DistributionType",
    "DistributionConfig",
    "AxisRangeConfig",
    "SensitivityCellResult",
    "SensitivityMatrixResult",
    "MonteCarloSummaryStats",
    "MonteCarloSimulationResult",
    "SensitivityConfig",
    "build_sensitivity_matrix_dataframe",
    "create_sensitivity_heatmap_chart",
    "build_monte_carlo_stats_dataframe",
    "create_monte_carlo_histogram",
]
