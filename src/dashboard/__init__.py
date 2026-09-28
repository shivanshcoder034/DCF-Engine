"""Financial Dashboards & Interactive Visualizations package.

Provides high-performance, presentation-grade Plotly chart generators
and analytical visualizers for historical trends, forecast projections,
DCF valuation bridges, scenario comparisons, and sensitivity simulations.
"""

from __future__ import annotations

from src.dashboard.charts import (
    create_historical_trend_chart,
    create_margin_evolution_chart,
    create_cash_flow_capex_chart,
    create_working_capital_cycle_chart,
    create_revenue_actual_vs_projected_chart,
    create_forecast_driver_margins_chart,
    create_ufcf_trajectory_breakdown_chart,
    create_valuation_waterfall_chart,
    create_terminal_value_share_donut_chart,
    create_cash_flow_discounting_comparison_chart,
    create_scenario_comparison_chart,
    create_sensitivity_contour_chart,
    create_monte_carlo_distribution_chart,
)

__all__ = [
    "create_historical_trend_chart",
    "create_margin_evolution_chart",
    "create_cash_flow_capex_chart",
    "create_working_capital_cycle_chart",
    "create_revenue_actual_vs_projected_chart",
    "create_forecast_driver_margins_chart",
    "create_ufcf_trajectory_breakdown_chart",
    "create_valuation_waterfall_chart",
    "create_terminal_value_share_donut_chart",
    "create_cash_flow_discounting_comparison_chart",
    "create_scenario_comparison_chart",
    "create_sensitivity_contour_chart",
    "create_monte_carlo_distribution_chart",
]
