"""Data models and typed structures for WACC estimation and capital costs.

Defines input assumption structures with provenance tracking, intermediate
calculation results for CAPM, debt costs, and capital structure weights,
and the final WACC valuation bundle.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class SourceCategory(str, Enum):
    """Origin of a WACC parameter or financial assumption."""
    USER_ENTERED = "user_entered"
    HISTORICAL_DATA = "historical_data"
    APPLICATION_DEFAULT = "application_default"

    @classmethod
    def display_name(cls, value: str) -> str:
        mapping = {
            cls.USER_ENTERED: "User Entered",
            cls.HISTORICAL_DATA: "Historical / Company Record",
            cls.APPLICATION_DEFAULT: "Application Default Proxy",
        }
        return mapping.get(value, value.replace("_", " ").title())


@dataclass
class InputProvenance:
    """Audit metadata tracking the source, citation, and overrides for an input."""
    source_category: str = SourceCategory.APPLICATION_DEFAULT.value
    source_reference: Optional[str] = None
    reference_date: Optional[str] = None
    notes: Optional[str] = None
    is_overridden: bool = False
    is_proxy: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Optional[Dict[str, Any]]) -> InputProvenance:
        if not data:
            return cls()
        return cls(
            source_category=str(data.get("source_category", SourceCategory.APPLICATION_DEFAULT.value)),
            source_reference=data.get("source_reference"),
            reference_date=data.get("reference_date"),
            notes=data.get("notes"),
            is_overridden=bool(data.get("is_overridden", False)),
            is_proxy=bool(data.get("is_proxy", False)),
        )


@dataclass
class CostOfEquityInputs:
    """CAPM input parameters and provenance tracking."""
    # Percentage values (e.g. 4.25 for 4.25%) and beta multiple (e.g. 1.15)
    risk_free_rate: Optional[float] = 4.25
    equity_beta: Optional[float] = 1.00
    equity_risk_premium: Optional[float] = 5.00

    # Provenance for each parameter
    rf_provenance: InputProvenance = field(
        default_factory=lambda: InputProvenance(
            source_category=SourceCategory.APPLICATION_DEFAULT.value,
            source_reference="10-Year Benchmark Sovereign Yield Proxy",
            notes="Default risk-free benchmark rate placeholder.",
        )
    )
    beta_provenance: InputProvenance = field(
        default_factory=lambda: InputProvenance(
            source_category=SourceCategory.APPLICATION_DEFAULT.value,
            source_reference="Market-Neutral Assumption",
            notes="Default beta multiple of 1.00.",
        )
    )
    erp_provenance: InputProvenance = field(
        default_factory=lambda: InputProvenance(
            source_category=SourceCategory.APPLICATION_DEFAULT.value,
            source_reference="Consensus Equity Risk Premium Proxy",
            notes="Long-term market risk premium benchmark assumption.",
        )
    )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "risk_free_rate": self.risk_free_rate,
            "equity_beta": self.equity_beta,
            "equity_risk_premium": self.equity_risk_premium,
            "rf_provenance": self.rf_provenance.to_dict(),
            "beta_provenance": self.beta_provenance.to_dict(),
            "erp_provenance": self.erp_provenance.to_dict(),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> CostOfEquityInputs:
        rf = data.get("risk_free_rate")
        beta = data.get("equity_beta")
        erp = data.get("equity_risk_premium")

        return cls(
            risk_free_rate=float(rf) if rf is not None else None,
            equity_beta=float(beta) if beta is not None else None,
            equity_risk_premium=float(erp) if erp is not None else None,
            rf_provenance=InputProvenance.from_dict(data.get("rf_provenance")),
            beta_provenance=InputProvenance.from_dict(data.get("beta_provenance")),
            erp_provenance=InputProvenance.from_dict(data.get("erp_provenance")),
        )


@dataclass
class CostOfDebtInputs:
    """Borrowing cost parameters and estimation configuration."""
    # Percentage value (e.g. 5.50 for 5.50%)
    pre_tax_cost_of_debt: Optional[float] = 5.50
    use_historical_estimate: bool = False

    # Historical estimation context (if derived from financial statements)
    historical_interest_expense: Optional[float] = None
    historical_debt_balance: Optional[float] = None
    historical_period_label: Optional[str] = None
    historical_calculation_notes: Optional[str] = None

    provenance: InputProvenance = field(
        default_factory=lambda: InputProvenance(
            source_category=SourceCategory.APPLICATION_DEFAULT.value,
            source_reference="Benchmark Corporate Borrowing Spread Proxy",
            notes="Default pre-tax borrowing cost assumption.",
        )
    )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "pre_tax_cost_of_debt": self.pre_tax_cost_of_debt,
            "use_historical_estimate": self.use_historical_estimate,
            "historical_interest_expense": self.historical_interest_expense,
            "historical_debt_balance": self.historical_debt_balance,
            "historical_period_label": self.historical_period_label,
            "historical_calculation_notes": self.historical_calculation_notes,
            "provenance": self.provenance.to_dict(),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> CostOfDebtInputs:
        kd = data.get("pre_tax_cost_of_debt")
        return cls(
            pre_tax_cost_of_debt=float(kd) if kd is not None else None,
            use_historical_estimate=bool(data.get("use_historical_estimate", False)),
            historical_interest_expense=data.get("historical_interest_expense"),
            historical_debt_balance=data.get("historical_debt_balance"),
            historical_period_label=data.get("historical_period_label"),
            historical_calculation_notes=data.get("historical_calculation_notes"),
            provenance=InputProvenance.from_dict(data.get("provenance")),
        )


@dataclass
class CapitalStructureInputs:
    """Capital base amounts and weighting configuration."""
    # Equity inputs
    equity_value: Optional[float] = None
    equity_value_type: str = "market_value"  # "market_value" or "book_value_proxy"
    equity_shares_count: Optional[float] = None
    equity_share_price: Optional[float] = None

    # Debt inputs
    debt_value: Optional[float] = None
    debt_value_type: str = "interest_bearing_debt"  # "interest_bearing_debt" or "user_specified"
    included_debt_items: List[str] = field(default_factory=lambda: ["short_term_debt", "long_term_debt"])

    # Provenance
    equity_provenance: InputProvenance = field(
        default_factory=lambda: InputProvenance(
            source_category=SourceCategory.USER_ENTERED.value,
            source_reference="User Entered Market Value",
            notes="Equity capitalization amount.",
        )
    )
    debt_provenance: InputProvenance = field(
        default_factory=lambda: InputProvenance(
            source_category=SourceCategory.HISTORICAL_DATA.value,
            source_reference="Latest Balance Sheet Interest-Bearing Debt",
            notes="Sum of short-term and long-term borrowings.",
        )
    )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "equity_value": self.equity_value,
            "equity_value_type": self.equity_value_type,
            "equity_shares_count": self.equity_shares_count,
            "equity_share_price": self.equity_share_price,
            "debt_value": self.debt_value,
            "debt_value_type": self.debt_value_type,
            "included_debt_items": list(self.included_debt_items),
            "equity_provenance": self.equity_provenance.to_dict(),
            "debt_provenance": self.debt_provenance.to_dict(),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> CapitalStructureInputs:
        eq = data.get("equity_value")
        dt = data.get("debt_value")
        return cls(
            equity_value=float(eq) if eq is not None else None,
            equity_value_type=str(data.get("equity_value_type", "market_value")),
            equity_shares_count=data.get("equity_shares_count"),
            equity_share_price=data.get("equity_share_price"),
            debt_value=float(dt) if dt is not None else None,
            debt_value_type=str(data.get("debt_value_type", "interest_bearing_debt")),
            included_debt_items=list(data.get("included_debt_items", ["short_term_debt", "long_term_debt"])),
            equity_provenance=InputProvenance.from_dict(data.get("equity_provenance")),
            debt_provenance=InputProvenance.from_dict(data.get("debt_provenance")),
        )


@dataclass
class TaxRateInputs:
    """Marginal tax rate configuration for interest tax shield."""
    # Percentage value (e.g. 21.0 for 21.0%)
    tax_rate: Optional[float] = 21.0
    tax_rate_source: str = "user_entered"  # "user_entered", "forecast_scenario", "historical_effective"
    forecast_scenario_name: Optional[str] = None
    forecast_scenario_id: Optional[int] = None

    provenance: InputProvenance = field(
        default_factory=lambda: InputProvenance(
            source_category=SourceCategory.USER_ENTERED.value,
            source_reference="Marginal Statutory Corporate Tax Rate",
            notes="Corporate income tax rate applied to debt interest expense.",
        )
    )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "tax_rate": self.tax_rate,
            "tax_rate_source": self.tax_rate_source,
            "forecast_scenario_name": self.forecast_scenario_name,
            "forecast_scenario_id": self.forecast_scenario_id,
            "provenance": self.provenance.to_dict(),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> TaxRateInputs:
        tr = data.get("tax_rate")
        return cls(
            tax_rate=float(tr) if tr is not None else None,
            tax_rate_source=str(data.get("tax_rate_source", "user_entered")),
            forecast_scenario_name=data.get("forecast_scenario_name"),
            forecast_scenario_id=data.get("forecast_scenario_id"),
            provenance=InputProvenance.from_dict(data.get("provenance")),
        )


@dataclass
class WaccAssumptions:
    """Complete configurable parameter set for a named WACC case."""
    name: str = "Base Case WACC"
    description: Optional[str] = None

    equity_inputs: CostOfEquityInputs = field(default_factory=CostOfEquityInputs)
    debt_inputs: CostOfDebtInputs = field(default_factory=CostOfDebtInputs)
    capital_inputs: CapitalStructureInputs = field(default_factory=CapitalStructureInputs)
    tax_inputs: TaxRateInputs = field(default_factory=TaxRateInputs)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "equity_inputs": self.equity_inputs.to_dict(),
            "debt_inputs": self.debt_inputs.to_dict(),
            "capital_inputs": self.capital_inputs.to_dict(),
            "tax_inputs": self.tax_inputs.to_dict(),
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> WaccAssumptions:
        return cls(
            name=str(data.get("name", "Base Case WACC")),
            description=data.get("description"),
            equity_inputs=CostOfEquityInputs.from_dict(data.get("equity_inputs", {})),
            debt_inputs=CostOfDebtInputs.from_dict(data.get("debt_inputs", {})),
            capital_inputs=CapitalStructureInputs.from_dict(data.get("capital_inputs", {})),
            tax_inputs=TaxRateInputs.from_dict(data.get("tax_inputs", {})),
        )

    @classmethod
    def from_json(cls, json_str: str) -> WaccAssumptions:
        return cls.from_dict(json.loads(json_str))


# ---------------- Calculation Result Models ----------------

@dataclass
class CostOfEquityResult:
    """Evaluated Cost of Equity via CAPM."""
    cost_of_equity: Optional[float]
    risk_free_rate: Optional[float]
    equity_beta: Optional[float]
    equity_risk_premium: Optional[float]
    formula_display: str
    status: str  # "complete", "incomplete", "invalid"
    missing_inputs: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


@dataclass
class CostOfDebtResult:
    """Evaluated Pre-Tax and After-Tax Cost of Debt."""
    pre_tax_cost_of_debt: Optional[float]
    after_tax_cost_of_debt: Optional[float]
    tax_rate_applied: Optional[float]
    tax_shield_benefit: Optional[float]
    formula_display: str
    status: str  # "complete", "incomplete", "invalid"
    missing_inputs: List[str] = field(default_factory=list)
    notes: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


@dataclass
class CapitalStructureResult:
    """Evaluated enterprise capital structure and weighting."""
    equity_value: Optional[float]
    debt_value: Optional[float]
    total_capital: Optional[float]
    equity_weight: Optional[float]  # 0.0 to 1.0 (e.g. 0.70 for 70%)
    debt_weight: Optional[float]    # 0.0 to 1.0 (e.g. 0.30 for 30%)
    equity_weight_pct: Optional[float]  # e.g. 70.0 for 70.0%
    debt_weight_pct: Optional[float]    # e.g. 30.0 for 30.0%
    is_book_value_proxy: bool
    formula_display: str
    status: str  # "complete", "incomplete", "invalid"
    missing_inputs: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


@dataclass
class WaccResult:
    """Full WACC estimation bundle with breakdown, formula bridge, and audit trail."""
    wacc: Optional[float]  # Percentage e.g. 8.58 for 8.58%
    is_complete: bool
    cost_of_equity: CostOfEquityResult
    cost_of_debt: CostOfDebtResult
    capital_structure: CapitalStructureResult
    formula_breakdown: str
    equity_contribution: Optional[float]
    debt_contribution: Optional[float]
    missing_inputs: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    limitations_disclaimer: str = (
        "WACC is a forward-looking discount rate estimate derived from user assumptions "
        "and available historical proxies. It does not constitute investment advice, a credit rating, "
        "or guaranteed commercial cost of financing."
    )
