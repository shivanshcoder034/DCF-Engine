"""Typed data models and structures for sensitivity analysis and Monte Carlo simulation.

Defines 2D sensitivity matrix configurations, distribution parameters,
simulation outputs, and summary statistics.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class SensitivityMetric(str, Enum):
    """Supported valuation output metrics for sensitivity matrix evaluation."""
    ENTERPRISE_VALUE = "enterprise_value"
    EQUITY_VALUE = "equity_value"
    IMPLIED_SHARE_PRICE = "implied_share_price"

    @classmethod
    def display_name(cls, value: str) -> str:
        mapping = {
            cls.ENTERPRISE_VALUE: "Enterprise Value (EV)",
            cls.EQUITY_VALUE: "Equity Value",
            cls.IMPLIED_SHARE_PRICE: "Implied Intrinsic Value per Share",
        }
        return mapping.get(value, value.replace("_", " ").title())


class DistributionType(str, Enum):
    """Supported statistical distributions for Monte Carlo simulation."""
    NORMAL = "normal"
    TRIANGULAR = "triangular"
    UNIFORM = "uniform"

    @classmethod
    def display_name(cls, value: str) -> str:
        mapping = {
            cls.NORMAL: "Normal (Mean, Std Dev)",
            cls.TRIANGULAR: "Triangular (Min, Mode, Max)",
            cls.UNIFORM: "Uniform (Min, Max)",
        }
        return mapping.get(value, value.title())


@dataclass
class DistributionConfig:
    """Configurable probability distribution parameters for a simulation variable."""

    dist_type: str = DistributionType.TRIANGULAR.value
    # Normal params
    mean: float = 0.0
    std_dev: float = 1.0
    # Triangular / Uniform params
    min_val: float = -2.0
    mode_val: float = 0.0
    max_val: float = 2.0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> DistributionConfig:
        return cls(
            dist_type=str(data.get("dist_type", DistributionType.TRIANGULAR.value)),
            mean=float(data.get("mean", 0.0)),
            std_dev=float(data.get("std_dev", 1.0)),
            min_val=float(data.get("min_val", -2.0)),
            mode_val=float(data.get("mode_val", 0.0)),
            max_val=float(data.get("max_val", 2.0)),
        )


@dataclass
class AxisRangeConfig:
    """Configurable range and step for a sensitivity matrix axis."""

    base_val: float
    min_val: float
    max_val: float
    step: float

    def generate_values(self) -> List[float]:
        """Generate a sorted, rounded list of axis values guaranteed to include the base value."""
        vals: set[float] = {round(self.base_val, 4)}
        curr = self.min_val
        while curr <= self.max_val + 1e-6:
            vals.add(round(curr, 4))
            curr += self.step
        return sorted(list(vals))

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> AxisRangeConfig:
        return cls(
            base_val=float(data.get("base_val", 8.0)),
            min_val=float(data.get("min_val", 6.0)),
            max_val=float(data.get("max_val", 10.0)),
            step=float(data.get("step", 0.5)),
        )


@dataclass
class SensitivityCellResult:
    """Individual cell in a 2D sensitivity matrix."""

    row_val: float  # e.g. WACC (%)
    col_val: float  # e.g. g (%) or exit multiple (x)
    is_baseline_intersection: bool = False

    enterprise_value: Optional[float] = None
    equity_value: Optional[float] = None
    implied_value_per_share: Optional[float] = None

    is_valid: bool = False
    status: str = "valid"  # "valid", "invalid", "incomplete"
    reason: Optional[str] = None


@dataclass
class SensitivityMatrixResult:
    """Evaluated two-dimensional valuation sensitivity matrix."""

    dcf_model_name: Optional[str]
    terminal_method: str  # Gordon Growth or Exit Multiple
    metric: str  # SensitivityMetric value

    row_param_name: str  # "WACC (%)"
    col_param_name: str  # "Perpetual Growth Rate (g %)" or "Exit Multiple (x)"

    row_values: List[float]
    col_values: List[float]
    baseline_row_val: float
    baseline_col_val: float

    cells: List[List[SensitivityCellResult]]  # Indexed by [row_idx][col_idx]
    fixed_assumptions: Dict[str, Any] = field(default_factory=dict)
    warnings: List[str] = field(default_factory=list)


@dataclass
class MonteCarloSummaryStats:
    """Descriptive statistics for a simulated valuation metric."""

    count: int
    mean: float
    median: float
    std_dev: float
    min: float
    p10: float
    p25: float
    p75: float
    p90: float
    max: float


@dataclass
class MonteCarloSimulationResult:
    """Outputs and statistical distributions from a Monte Carlo simulation run."""

    total_iterations: int
    valid_iterations: int
    invalid_iterations: int
    invalid_reasons: Dict[str, int]
    random_seed: int

    ev_stats: Optional[MonteCarloSummaryStats] = None
    equity_stats: Optional[MonteCarloSummaryStats] = None
    share_price_stats: Optional[MonteCarloSummaryStats] = None

    sampled_evs: List[float] = field(default_factory=list)
    sampled_equities: List[float] = field(default_factory=list)
    sampled_share_prices: List[float] = field(default_factory=list)

    variable_configs: Dict[str, DistributionConfig] = field(default_factory=dict)
    fixed_assumptions: Dict[str, Any] = field(default_factory=dict)
    warnings: List[str] = field(default_factory=list)
    disclaimer: str = (
        "Monte Carlo simulation illustrates valuation sensitivity under user-specified statistical distributions "
        "and random sampling. Percentile statistics are conditional analytical outputs and do not represent "
        "real-world probabilities, confidence intervals, or guaranteed future prices."
    )


@dataclass
class SensitivityConfig:
    """Persisted sensitivity analysis and Monte Carlo configuration bundle."""

    name: str = "Base Sensitivity & Simulation Set"
    description: Optional[str] = None
    project_id: int = 1
    dcf_model_id: Optional[int] = None

    # Matrix configuration
    metric: str = SensitivityMetric.IMPLIED_SHARE_PRICE.value
    wacc_range: Optional[AxisRangeConfig] = None
    terminal_range: Optional[AxisRangeConfig] = None

    # Monte Carlo configuration
    iterations: int = 500
    random_seed: int = 42
    simulate_revenue_growth: bool = True
    simulate_operating_margin: bool = True
    simulate_wacc: bool = True
    simulate_terminal_param: bool = True

    revenue_growth_dist: DistributionConfig = field(
        default_factory=lambda: DistributionConfig(
            dist_type=DistributionType.TRIANGULAR.value,
            min_val=-2.0,
            mode_val=0.0,
            max_val=2.0,
            mean=0.0,
            std_dev=1.0,
        )
    )
    operating_margin_dist: DistributionConfig = field(
        default_factory=lambda: DistributionConfig(
            dist_type=DistributionType.TRIANGULAR.value,
            min_val=-1.5,
            mode_val=0.0,
            max_val=1.5,
            mean=0.0,
            std_dev=0.75,
        )
    )
    wacc_dist: DistributionConfig = field(
        default_factory=lambda: DistributionConfig(
            dist_type=DistributionType.NORMAL.value,
            mean=8.5,
            std_dev=0.5,
            min_val=7.0,
            mode_val=8.5,
            max_val=10.0,
        )
    )
    terminal_param_dist: DistributionConfig = field(
        default_factory=lambda: DistributionConfig(
            dist_type=DistributionType.TRIANGULAR.value,
            min_val=2.0,
            mode_val=2.5,
            max_val=3.0,
            mean=2.5,
            std_dev=0.25,
        )
    )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "project_id": self.project_id,
            "dcf_model_id": self.dcf_model_id,
            "metric": self.metric,
            "wacc_range": self.wacc_range.to_dict() if self.wacc_range else None,
            "terminal_range": self.terminal_range.to_dict() if self.terminal_range else None,
            "iterations": self.iterations,
            "random_seed": self.random_seed,
            "simulate_revenue_growth": self.simulate_revenue_growth,
            "simulate_operating_margin": self.simulate_operating_margin,
            "simulate_wacc": self.simulate_wacc,
            "simulate_terminal_param": self.simulate_terminal_param,
            "revenue_growth_dist": self.revenue_growth_dist.to_dict(),
            "operating_margin_dist": self.operating_margin_dist.to_dict(),
            "wacc_dist": self.wacc_dist.to_dict(),
            "terminal_param_dist": self.terminal_param_dist.to_dict(),
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> SensitivityConfig:
        w_range = AxisRangeConfig.from_dict(data["wacc_range"]) if data.get("wacc_range") else None
        t_range = AxisRangeConfig.from_dict(data["terminal_range"]) if data.get("terminal_range") else None

        return cls(
            name=str(data.get("name", "Base Sensitivity & Simulation Set")),
            description=data.get("description"),
            project_id=int(data.get("project_id", 1)),
            dcf_model_id=data.get("dcf_model_id"),
            metric=str(data.get("metric", SensitivityMetric.IMPLIED_SHARE_PRICE.value)),
            wacc_range=w_range,
            terminal_range=t_range,
            iterations=int(data.get("iterations", 500)),
            random_seed=int(data.get("random_seed", 42)),
            simulate_revenue_growth=bool(data.get("simulate_revenue_growth", True)),
            simulate_operating_margin=bool(data.get("simulate_operating_margin", True)),
            simulate_wacc=bool(data.get("simulate_wacc", True)),
            simulate_terminal_param=bool(data.get("simulate_terminal_param", True)),
            revenue_growth_dist=DistributionConfig.from_dict(data.get("revenue_growth_dist", {})),
            operating_margin_dist=DistributionConfig.from_dict(data.get("operating_margin_dist", {})),
            wacc_dist=DistributionConfig.from_dict(data.get("wacc_dist", {})),
            terminal_param_dist=DistributionConfig.from_dict(data.get("terminal_param_dist", {})),
        )

    @classmethod
    def from_json(cls, json_str: str) -> SensitivityConfig:
        return cls.from_dict(json.loads(json_str))
