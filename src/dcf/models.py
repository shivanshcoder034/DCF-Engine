"""Data models and typed structures for DCF valuation.

Defines input assumption structures with provenance tracking, intermediate
calculation results for cash flow discounting, terminal values, and the enterprise-to-equity bridge,
as well as the complete DCF valuation bundle.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

from src.wacc.models import InputProvenance, SourceCategory


class DiscountingConvention(str, Enum):
    """Timing convention for discounting projected cash flows."""
    END_OF_YEAR = "end_of_year"
    MID_YEAR = "mid_year"

    @classmethod
    def display_name(cls, value: str) -> str:
        mapping = {
            cls.END_OF_YEAR: "End-of-Year Convention (t = 1.0, 2.0, ...)",
            cls.MID_YEAR: "Mid-Year Convention (t = 0.5, 1.5, ...)",
        }
        return mapping.get(value, value.replace("_", " ").title())


class TerminalValueMethod(str, Enum):
    """Methodology applied to evaluate terminal enterprise value."""
    GORDON_GROWTH = "gordon_growth"
    EXIT_MULTIPLE = "exit_multiple"

    @classmethod
    def display_name(cls, value: str) -> str:
        mapping = {
            cls.GORDON_GROWTH: "Gordon Growth Perpetuity (Perpetual Growth)",
            cls.EXIT_MULTIPLE: "Exit Multiple Method (Terminal EV/EBITDA)",
        }
        return mapping.get(value, value.replace("_", " ").title())


@dataclass
class TerminalValueInputs:
    """Terminal value methodology inputs and provenance."""
    method: str = TerminalValueMethod.GORDON_GROWTH.value

    # Gordon Growth inputs (percentage e.g. 2.5 for 2.5%)
    perpetual_growth_rate: Optional[float] = 2.50
    growth_provenance: InputProvenance = field(
        default_factory=lambda: InputProvenance(
            source_category=SourceCategory.APPLICATION_DEFAULT.value,
            source_reference="Long-Term GDP / Inflation Expectation Benchmark",
            notes="Default perpetual terminal growth rate assumption (2.50%).",
        )
    )

    # Exit Multiple inputs (e.g. 10.0 for 10.0x EBITDA)
    exit_multiple: Optional[float] = 10.0
    multiple_provenance: InputProvenance = field(
        default_factory=lambda: InputProvenance(
            source_category=SourceCategory.APPLICATION_DEFAULT.value,
            source_reference="Median Industry Peer Terminal EV/EBITDA Multiple",
            notes="Assumed terminal EV/EBITDA multiple placeholder.",
        )
    )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "method": self.method,
            "perpetual_growth_rate": self.perpetual_growth_rate,
            "growth_provenance": self.growth_provenance.to_dict(),
            "exit_multiple": self.exit_multiple,
            "multiple_provenance": self.multiple_provenance.to_dict(),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> TerminalValueInputs:
        return cls(
            method=str(data.get("method", TerminalValueMethod.GORDON_GROWTH.value)),
            perpetual_growth_rate=float(data["perpetual_growth_rate"]) if data.get("perpetual_growth_rate") is not None else None,
            growth_provenance=InputProvenance.from_dict(data.get("growth_provenance")),
            exit_multiple=float(data["exit_multiple"]) if data.get("exit_multiple") is not None else None,
            multiple_provenance=InputProvenance.from_dict(data.get("multiple_provenance")),
        )


@dataclass
class EquityBridgeInputs:
    """Line items for bridging from Enterprise Value to Equity Value."""
    # Added to EV
    cash_and_equivalents: Optional[float] = 0.0
    # Subtracted from EV
    debt_value: Optional[float] = 0.0
    minority_interest: Optional[float] = 0.0
    preferred_equity: Optional[float] = 0.0
    # Signed adjustment added to EV
    other_adjustments: Optional[float] = 0.0
    other_adjustments_description: Optional[str] = None

    # Provenance tracking per line item
    cash_provenance: InputProvenance = field(default_factory=InputProvenance)
    debt_provenance: InputProvenance = field(default_factory=InputProvenance)
    minority_interest_provenance: InputProvenance = field(default_factory=InputProvenance)
    preferred_equity_provenance: InputProvenance = field(default_factory=InputProvenance)
    other_adjustments_provenance: InputProvenance = field(default_factory=InputProvenance)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "cash_and_equivalents": self.cash_and_equivalents,
            "debt_value": self.debt_value,
            "minority_interest": self.minority_interest,
            "preferred_equity": self.preferred_equity,
            "other_adjustments": self.other_adjustments,
            "other_adjustments_description": self.other_adjustments_description,
            "cash_provenance": self.cash_provenance.to_dict(),
            "debt_provenance": self.debt_provenance.to_dict(),
            "minority_interest_provenance": self.minority_interest_provenance.to_dict(),
            "preferred_equity_provenance": self.preferred_equity_provenance.to_dict(),
            "other_adjustments_provenance": self.other_adjustments_provenance.to_dict(),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> EquityBridgeInputs:
        return cls(
            cash_and_equivalents=float(data["cash_and_equivalents"]) if data.get("cash_and_equivalents") is not None else None,
            debt_value=float(data["debt_value"]) if data.get("debt_value") is not None else None,
            minority_interest=float(data["minority_interest"]) if data.get("minority_interest") is not None else 0.0,
            preferred_equity=float(data["preferred_equity"]) if data.get("preferred_equity") is not None else 0.0,
            other_adjustments=float(data["other_adjustments"]) if data.get("other_adjustments") is not None else 0.0,
            other_adjustments_description=data.get("other_adjustments_description"),
            cash_provenance=InputProvenance.from_dict(data.get("cash_provenance")),
            debt_provenance=InputProvenance.from_dict(data.get("debt_provenance")),
            minority_interest_provenance=InputProvenance.from_dict(data.get("minority_interest_provenance")),
            preferred_equity_provenance=InputProvenance.from_dict(data.get("preferred_equity_provenance")),
            other_adjustments_provenance=InputProvenance.from_dict(data.get("other_adjustments_provenance")),
        )


@dataclass
class DcfAssumptions:
    """Configurable parameters and linked models for a DCF valuation scenario."""
    name: str = "Base Case DCF Valuation"
    description: Optional[str] = None
    project_id: int = 1

    # Linked scenarios
    forecast_model_id: Optional[int] = None
    wacc_model_id: Optional[int] = None

    # Timing & Discounting
    valuation_date: Optional[str] = None
    discounting_convention: str = DiscountingConvention.END_OF_YEAR.value

    # Valuation Drivers
    terminal_inputs: TerminalValueInputs = field(default_factory=TerminalValueInputs)
    bridge_inputs: EquityBridgeInputs = field(default_factory=EquityBridgeInputs)

    # Share Count
    diluted_shares: Optional[float] = None
    shares_provenance: InputProvenance = field(
        default_factory=lambda: InputProvenance(
            source_category=SourceCategory.USER_ENTERED.value,
            source_reference="Reported Diluted Common Shares Outstanding",
            notes="Weighted average diluted shares outstanding.",
        )
    )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "project_id": self.project_id,
            "forecast_model_id": self.forecast_model_id,
            "wacc_model_id": self.wacc_model_id,
            "valuation_date": self.valuation_date,
            "discounting_convention": self.discounting_convention,
            "terminal_inputs": self.terminal_inputs.to_dict(),
            "bridge_inputs": self.bridge_inputs.to_dict(),
            "diluted_shares": self.diluted_shares,
            "shares_provenance": self.shares_provenance.to_dict(),
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> DcfAssumptions:
        return cls(
            name=str(data.get("name", "Base Case DCF Valuation")),
            description=data.get("description"),
            project_id=int(data.get("project_id", 1)),
            forecast_model_id=data.get("forecast_model_id"),
            wacc_model_id=data.get("wacc_model_id"),
            valuation_date=data.get("valuation_date"),
            discounting_convention=str(data.get("discounting_convention", DiscountingConvention.END_OF_YEAR.value)),
            terminal_inputs=TerminalValueInputs.from_dict(data.get("terminal_inputs", {})),
            bridge_inputs=EquityBridgeInputs.from_dict(data.get("bridge_inputs", {})),
            diluted_shares=float(data["diluted_shares"]) if data.get("diluted_shares") is not None else None,
            shares_provenance=InputProvenance.from_dict(data.get("shares_provenance")),
        )

    @classmethod
    def from_json(cls, json_str: str) -> DcfAssumptions:
        return cls.from_dict(json.loads(json_str))


# ---------------- Calculation Result Models ----------------

@dataclass
class YearDiscountingResult:
    """Discounting evaluation for an individual forecast year."""
    year_index: int
    period_label: str
    ufcf: float
    discount_period: float
    discount_factor: float
    pv_ufcf: float


@dataclass
class TerminalValueResult:
    """Evaluated terminal enterprise value and present value."""
    method: str
    terminal_value: Optional[float]
    discount_period: float
    discount_factor: float
    pv_terminal_value: Optional[float]
    formula_display: str
    status: str  # "complete", "incomplete", "invalid"
    notes: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    missing_inputs: List[str] = field(default_factory=list)


@dataclass
class EquityBridgeResult:
    """Evaluated enterprise-to-equity value bridge components."""
    enterprise_value: Optional[float]
    cash_added: float
    debt_subtracted: float
    minority_interest_subtracted: float
    preferred_equity_subtracted: float
    other_adjustments_net: float
    net_debt: float  # Debt - Cash
    equity_value: Optional[float]
    status: str
    warnings: List[str] = field(default_factory=list)
    missing_inputs: List[str] = field(default_factory=list)


@dataclass
class DcfValuationResult:
    """Comprehensive DCF valuation summary bundle."""
    enterprise_value: Optional[float]
    equity_value: Optional[float]
    implied_value_per_share: Optional[float]
    diluted_shares_applied: Optional[float]

    pv_forecast_ufcf: Optional[float]
    terminal_value: Optional[float]
    pv_terminal_value: Optional[float]
    terminal_value_pct_ev: Optional[float]
    pv_ufcf_pct_ev: Optional[float]

    wacc_applied: Optional[float]
    discounting_convention_applied: str

    annual_discounting_schedule: List[YearDiscountingResult] = field(default_factory=list)
    terminal_result: Optional[TerminalValueResult] = None
    bridge_result: Optional[EquityBridgeResult] = None

    is_complete: bool = False
    missing_inputs: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    limitations_disclaimer: str = (
        "DCF intrinsic valuation is an analytical calculation highly sensitive to forecast assumptions, "
        "discount rate calibration, and terminal value methodologies. It does not constitute investment advice "
        "or a guarantee of future equity price performance."
    )
