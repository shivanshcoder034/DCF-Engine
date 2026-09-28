"""Data structures and typed models for financial forecasting.

Defines assumption sets, driver parameters, annual projection line items,
and aggregated multi-year forecast result bundles.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class ForecastAssumptions:
    """Configurable drivers and multi-period assumptions for financial projections."""

    name: str = "Base Case Forecast"
    description: Optional[str] = None
    horizon_years: int = 5

    # Annual rate schedules (percentage values e.g. 5.0 for 5.0%)
    revenue_growth_rates: List[float] = field(default_factory=lambda: [5.0] * 5)
    gross_margin_rates: List[float] = field(default_factory=lambda: [40.0] * 5)
    opex_pct_rates: List[float] = field(default_factory=lambda: [20.0] * 5)
    da_pct_rates: List[float] = field(default_factory=lambda: [4.0] * 5)
    capex_pct_rates: List[float] = field(default_factory=lambda: [5.0] * 5)

    # Working Capital Drivers
    use_working_capital_days: bool = True
    dso_days: List[float] = field(default_factory=lambda: [45.0] * 5)
    dio_days: List[float] = field(default_factory=lambda: [60.0] * 5)
    dpo_days: List[float] = field(default_factory=lambda: [40.0] * 5)
    nwc_pct_revenue: List[float] = field(default_factory=lambda: [10.0] * 5)

    # Tax Rate for NOPAT Calculation (e.g. 25.0 for 25%)
    tax_rate: float = 25.0

    # Source tracking: "historical_baseline", "user_entered", or "application_default"
    driver_sources: Dict[str, str] = field(default_factory=lambda: {
        "revenue_growth": "application_default",
        "gross_margin": "application_default",
        "opex_pct": "application_default",
        "da_pct": "application_default",
        "capex_pct": "application_default",
        "working_capital": "application_default",
        "tax_rate": "application_default",
    })

    def to_dict(self) -> Dict[str, Any]:
        """Serialize assumptions dataclass to dictionary."""
        return asdict(self)

    def to_json(self) -> str:
        """Serialize assumptions to JSON string for database persistence."""
        return json.dumps(self.to_dict())

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> ForecastAssumptions:
        """Construct ForecastAssumptions from dictionary with safe defaults."""
        horizon = int(data.get("horizon_years", 5))

        def pad_or_trim(lst: Optional[List[float]], default_val: float) -> List[float]:
            raw = list(lst) if lst is not None else [default_val] * horizon
            if len(raw) < horizon:
                last_val = raw[-1] if raw else default_val
                raw.extend([last_val] * (horizon - len(raw)))
            return [float(x) for x in raw[:horizon]]

        return cls(
            name=str(data.get("name", "Base Case Forecast")),
            description=data.get("description"),
            horizon_years=horizon,
            revenue_growth_rates=pad_or_trim(data.get("revenue_growth_rates"), 5.0),
            gross_margin_rates=pad_or_trim(data.get("gross_margin_rates"), 40.0),
            opex_pct_rates=pad_or_trim(data.get("opex_pct_rates"), 20.0),
            da_pct_rates=pad_or_trim(data.get("da_pct_rates"), 4.0),
            capex_pct_rates=pad_or_trim(data.get("capex_pct_rates"), 5.0),
            use_working_capital_days=bool(data.get("use_working_capital_days", True)),
            dso_days=pad_or_trim(data.get("dso_days"), 45.0),
            dio_days=pad_or_trim(data.get("dio_days"), 60.0),
            dpo_days=pad_or_trim(data.get("dpo_days"), 40.0),
            nwc_pct_revenue=pad_or_trim(data.get("nwc_pct_revenue"), 10.0),
            tax_rate=float(data.get("tax_rate", 25.0)),
            driver_sources=dict(data.get("driver_sources", {})),
        )

    @classmethod
    def from_json(cls, json_str: str) -> ForecastAssumptions:
        """Construct ForecastAssumptions from JSON string."""
        return cls.from_dict(json.loads(json_str))


@dataclass
class YearForecast:
    """Projected financial statement metrics and cash flows for an individual forecast year."""

    year_index: int  # 1 to N
    period_label: str  # e.g. "FY2024 (F)"

    # Income Statement
    revenue: float
    revenue_growth: float
    cogs: float
    gross_profit: float
    gross_margin: float
    operating_expenses: float
    ebitda: float
    ebitda_margin: float
    depreciation_amortization: float
    ebit: float
    ebit_margin: float
    tax_expense: float
    nopat: float

    # Working Capital Items
    accounts_receivable: Optional[float]
    inventory: Optional[float]
    accounts_payable: Optional[float]
    operating_nwc: float
    delta_operating_nwc: float

    # Cash Flow & UFCF
    capex: float
    capex_pct_revenue: float
    ufcf: float


@dataclass
class ForecastResult:
    """Complete multi-year financial statement and Unlevered Free Cash Flow projection bundle."""

    project_id: int
    company_name: str
    currency: str
    display_unit: str

    # Baseline Period Context (Year 0)
    base_period_label: str
    base_period_year: int
    base_revenue: float
    base_gross_profit: Optional[float]
    base_ebitda: Optional[float]
    base_ebit: Optional[float]
    base_operating_nwc: float
    base_capex: Optional[float]
    base_cfo: Optional[float]

    # Forecast Assumptions & Schedules
    assumptions: ForecastAssumptions
    annual_forecasts: List[YearForecast] = field(default_factory=list)

    # Summary Statistics
    forecast_revenue_cagr: float = 0.0
    avg_gross_margin: float = 0.0
    avg_ebitda_margin: float = 0.0
    avg_ebit_margin: float = 0.0
    total_projected_ufcf: float = 0.0

    warnings: List[str] = field(default_factory=list)
