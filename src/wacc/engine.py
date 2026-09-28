"""WACC Estimation Engine coordinating historical data extraction and capital cost models.

Inspects historical financial statement records, extracts baseline debt balances,
accounting interest rates, and effective tax rates, and produces calibrated WACC estimates.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Tuple

from src.analysis.models import HistoricalAnalysisBundle
from src.wacc.calculations import calculate_wacc
from src.wacc.models import (
    CapitalStructureInputs,
    CostOfDebtInputs,
    CostOfEquityInputs,
    InputProvenance,
    SourceCategory,
    TaxRateInputs,
    WaccAssumptions,
    WaccResult,
)

logger = logging.getLogger(__name__)


class WaccEngine:
    """Core analytical orchestrator for WACC estimation and parameter extraction."""

    @classmethod
    def extract_historical_debt_and_equity(
        cls,
        bundle: HistoricalAnalysisBundle,
    ) -> Dict[str, Any]:
        """Extract latest balance sheet debt balances and book equity from historical analysis.

        Excludes non-interest-bearing operating liabilities such as accounts payable and accruals.
        """
        result: Dict[str, Any] = {
            "period_label": None,
            "period_end_date": None,
            "short_term_debt": None,
            "long_term_debt": None,
            "total_interest_bearing_debt": None,
            "book_value_of_equity": None,
            "included_debt_items": [],
            "notes": [],
        }

        if not bundle or not bundle.periods:
            return result

        # Chronologically latest period
        latest_period = bundle.periods[-1]
        p_label = latest_period.label
        result["period_label"] = p_label
        result["period_end_date"] = str(latest_period.end_date)

        line_items = bundle.raw_line_items_by_period.get(p_label, {})

        st_debt = line_items.get("short_term_debt")
        lt_debt = line_items.get("long_term_debt")
        book_equity = line_items.get("total_equity")

        result["short_term_debt"] = st_debt
        result["long_term_debt"] = lt_debt
        result["book_value_of_equity"] = book_equity

        debt_components: List[str] = []
        total_debt = 0.0
        has_debt_data = False

        if st_debt is not None:
            total_debt += float(st_debt)
            debt_components.append("short_term_debt")
            has_debt_data = True

        if lt_debt is not None:
            total_debt += float(lt_debt)
            debt_components.append("long_term_debt")
            has_debt_data = True

        if has_debt_data:
            result["total_interest_bearing_debt"] = total_debt
            result["included_debt_items"] = debt_components
            comp_str = " + ".join(debt_components)
            result["notes"].append(
                f"Interest-bearing debt for {p_label} calculated from: {comp_str} = {total_debt:,.2f} {bundle.display_unit}."
            )
        else:
            result["notes"].append(
                f"No specific short-term or long-term debt line items found for {p_label}."
            )

        if book_equity is not None:
            result["notes"].append(
                f"Reported total book equity for {p_label} is {book_equity:,.2f} {bundle.display_unit}."
            )

        return result

    @classmethod
    def extract_historical_cost_of_debt(
        cls,
        bundle: HistoricalAnalysisBundle,
    ) -> Dict[str, Any]:
        """Estimate accounting-based cost of debt from historical interest expense and debt balances.

        Limitations:
            Accounting interest expense reflects historical coupon rates, amortized fees, and lease interest,
            and does not necessarily reflect current marginal market borrowing rates for new debt.
        """
        result: Dict[str, Any] = {
            "pre_tax_kd_estimate": None,
            "period_label": None,
            "interest_expense": None,
            "debt_balance": None,
            "notes": "",
            "is_available": False,
        }

        if not bundle or not bundle.periods:
            result["notes"] = "No historical financial periods available for borrowing cost estimation."
            return result

        # Look for the latest period that has interest expense
        for period in reversed(bundle.periods):
            p_label = period.label
            line_items = bundle.raw_line_items_by_period.get(p_label, {})
            interest = line_items.get("interest_expense")

            if interest is not None and abs(interest) > 0.0:
                # Find debt balance for this period
                st_debt = line_items.get("short_term_debt") or 0.0
                lt_debt = line_items.get("long_term_debt") or 0.0
                debt_bal = float(st_debt) + float(lt_debt)

                if debt_bal > 0.0:
                    # Positive interest magnitude
                    interest_mag = abs(float(interest))
                    implied_kd = (interest_mag / debt_bal) * 100.0

                    result["pre_tax_kd_estimate"] = round(implied_kd, 2)
                    result["period_label"] = p_label
                    result["interest_expense"] = interest_mag
                    result["debt_balance"] = debt_bal
                    result["is_available"] = True
                    result["notes"] = (
                        f"Estimated from {p_label} reported interest expense ({interest_mag:,.2f} {bundle.display_unit}) "
                        f"divided by reported interest-bearing debt ({debt_bal:,.2f} {bundle.display_unit}). "
                        f"Limitations: Historical accounting interest may include amortized debt discounts, capitalized interest, "
                        f"or legacy coupon rates that differ from current market borrowing spreads."
                    )
                    return result
                else:
                    result["notes"] = (
                        f"Period {p_label} has reported interest expense of {abs(interest):,.2f}, "
                        f"but interest-bearing debt is zero or unrecorded. Cannot divide by zero."
                    )
                    return result

        result["notes"] = "No historical period with both non-zero interest expense and debt balances was found."
        return result

    @classmethod
    def extract_historical_effective_tax_rate(
        cls,
        bundle: HistoricalAnalysisBundle,
    ) -> Dict[str, Any]:
        """Extract the most recent historical effective corporate tax rate from analysis bundle."""
        result: Dict[str, Any] = {
            "effective_tax_rate": None,
            "period_label": None,
            "notes": "",
            "is_available": False,
        }

        if not bundle or not bundle.periods:
            return result

        for period in reversed(bundle.periods):
            p_label = period.label
            cf_metric = bundle.cash_flow_metrics.get(p_label)
            if cf_metric and cf_metric.effective_tax_rate is not None and cf_metric.effective_tax_rate > 0.0:
                result["effective_tax_rate"] = round(cf_metric.effective_tax_rate, 2)
                result["period_label"] = p_label
                result["is_available"] = True
                result["notes"] = f"Historical effective tax rate from {p_label} reported income statement."
                return result

            # Fallback to metrics_by_period
            period_metrics = bundle.metrics_by_period.get(p_label, {})
            tax_metric = period_metrics.get("effective_tax_rate")
            if tax_metric and tax_metric.value is not None and tax_metric.value > 0.0:
                result["effective_tax_rate"] = round(tax_metric.value, 2)
                result["period_label"] = p_label
                result["is_available"] = True
                result["notes"] = f"Historical effective tax rate from {p_label} financial records."
                return result

        result["notes"] = "No positive historical effective tax rate could be derived from reporting periods."
        return result

    @classmethod
    def create_default_assumptions(
        cls,
        project_id: int,
        bundle: Optional[HistoricalAnalysisBundle] = None,
    ) -> WaccAssumptions:
        """Construct an initial calibrated WaccAssumptions set with explicit source tracking.

        Uses historical company records when available, or transparent application defaults.
        """
        # 1. Cost of Equity CAPM (Defaults)
        equity_inputs = CostOfEquityInputs(
            risk_free_rate=4.25,
            equity_beta=1.00,
            equity_risk_premium=5.00,
            rf_provenance=InputProvenance(
                source_category=SourceCategory.APPLICATION_DEFAULT.value,
                source_reference="10-Year Benchmark Sovereign Yield Proxy",
                notes="Standard baseline risk-free sovereign bond rate.",
            ),
            beta_provenance=InputProvenance(
                source_category=SourceCategory.APPLICATION_DEFAULT.value,
                source_reference="Market-Neutral Benchmark",
                notes="Baseline equity beta of 1.00.",
            ),
            erp_provenance=InputProvenance(
                source_category=SourceCategory.APPLICATION_DEFAULT.value,
                source_reference="US Consensus Long-Term ERP Proxy",
                notes="Expected excess market equity risk premium.",
            ),
        )

        # 2. Cost of Debt
        debt_inputs = CostOfDebtInputs(
            pre_tax_cost_of_debt=5.50,
            use_historical_estimate=False,
            provenance=InputProvenance(
                source_category=SourceCategory.APPLICATION_DEFAULT.value,
                source_reference="Investment-Grade Borrowing Spread Proxy",
                notes="Default pre-tax cost of debt benchmark.",
            ),
        )

        # 3. Capital Structure
        capital_inputs = CapitalStructureInputs(
            equity_value=1000.0,
            equity_value_type="market_value",
            debt_value=300.0,
            debt_value_type="interest_bearing_debt",
            included_debt_items=["short_term_debt", "long_term_debt"],
            equity_provenance=InputProvenance(
                source_category=SourceCategory.APPLICATION_DEFAULT.value,
                source_reference="Default Model Capitalization Placeholder",
                notes="Baseline equity capital base placeholder.",
            ),
            debt_provenance=InputProvenance(
                source_category=SourceCategory.APPLICATION_DEFAULT.value,
                source_reference="Default Model Debt Placeholder",
                notes="Baseline interest-bearing debt placeholder.",
            ),
        )

        # 4. Tax Rate
        tax_inputs = TaxRateInputs(
            tax_rate=21.0,
            tax_rate_source="user_entered",
            provenance=InputProvenance(
                source_category=SourceCategory.USER_ENTERED.value,
                source_reference="US Federal Statutory Corporate Tax Rate (21.0%)",
                notes="Marginal corporate income tax rate for debt interest deductibility.",
            ),
        )

        # If historical analysis bundle is supplied, enrich inputs with verifiable actuals
        if bundle and bundle.periods:
            # Capital structure historical extraction
            cap_data = cls.extract_historical_debt_and_equity(bundle)
            if cap_data["total_interest_bearing_debt"] is not None:
                capital_inputs.debt_value = cap_data["total_interest_bearing_debt"]
                capital_inputs.included_debt_items = cap_data["included_debt_items"]
                capital_inputs.debt_provenance = InputProvenance(
                    source_category=SourceCategory.HISTORICAL_DATA.value,
                    source_reference=f"Balance Sheet ({cap_data['period_label']})",
                    reference_date=cap_data["period_end_date"],
                    notes=f"Interest-bearing debt from {cap_data['period_label']} balance sheet actuals.",
                )

            if cap_data["book_value_of_equity"] is not None and cap_data["book_value_of_equity"] > 0:
                capital_inputs.equity_value = cap_data["book_value_of_equity"]
                capital_inputs.equity_value_type = "book_value_proxy"
                capital_inputs.equity_provenance = InputProvenance(
                    source_category=SourceCategory.HISTORICAL_DATA.value,
                    source_reference=f"Balance Sheet Book Equity ({cap_data['period_label']})",
                    reference_date=cap_data["period_end_date"],
                    notes=(
                        f"Book value of equity from {cap_data['period_label']} balance sheet. "
                        f"Proxy warning: Book equity may differ significantly from current market valuation."
                    ),
                    is_proxy=True,
                )

            # Historical borrowing cost extraction
            debt_hist = cls.extract_historical_cost_of_debt(bundle)
            if debt_hist["is_available"] and debt_hist["pre_tax_kd_estimate"] is not None:
                debt_inputs.pre_tax_cost_of_debt = debt_hist["pre_tax_kd_estimate"]
                debt_inputs.use_historical_estimate = True
                debt_inputs.historical_interest_expense = debt_hist["interest_expense"]
                debt_inputs.historical_debt_balance = debt_hist["debt_balance"]
                debt_inputs.historical_period_label = debt_hist["period_label"]
                debt_inputs.historical_calculation_notes = debt_hist["notes"]
                debt_inputs.provenance = InputProvenance(
                    source_category=SourceCategory.HISTORICAL_DATA.value,
                    source_reference=f"Historical Interest / Debt ({debt_hist['period_label']})",
                    notes=debt_hist["notes"],
                )

            # Historical effective tax rate extraction
            tax_hist = cls.extract_historical_effective_tax_rate(bundle)
            if tax_hist["is_available"] and tax_hist["effective_tax_rate"] is not None:
                tax_inputs.tax_rate = tax_hist["effective_tax_rate"]
                tax_inputs.tax_rate_source = "historical_effective"
                tax_inputs.provenance = InputProvenance(
                    source_category=SourceCategory.HISTORICAL_DATA.value,
                    source_reference=f"Historical Effective Tax Rate ({tax_hist['period_label']})",
                    notes=tax_hist["notes"],
                )

        return WaccAssumptions(
            name="Base Case WACC",
            description="Initial baseline WACC assumption set calibrated with historical and benchmark inputs.",
            equity_inputs=equity_inputs,
            debt_inputs=debt_inputs,
            capital_inputs=capital_inputs,
            tax_inputs=tax_inputs,
        )

    @classmethod
    def estimate_wacc(cls, assumptions: WaccAssumptions) -> WaccResult:
        """Execute end-to-end WACC estimation based on current assumptions."""
        return calculate_wacc(assumptions)
