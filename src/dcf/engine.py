"""DCF Valuation Engine coordinating cash flow projections, WACC integration, and equity bridges.

Orchestrates Phase 4 forecast outputs and Phase 5 WACC parameters to compute
enterprise value, equity value, and intrinsic share price.
"""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Optional, Tuple

from src.analysis.models import HistoricalAnalysisBundle
from src.dcf.calculations import calculate_dcf_valuation
from src.dcf.models import (
    DcfAssumptions,
    DcfValuationResult,
    DiscountingConvention,
    EquityBridgeInputs,
    TerminalValueInputs,
    TerminalValueMethod,
)
from src.forecasting.engine import FinancialForecastingEngine
from src.forecasting.models import ForecastAssumptions
from src.wacc.engine import WaccEngine
from src.wacc.models import InputProvenance, SourceCategory, WaccAssumptions

logger = logging.getLogger(__name__)


class DcfEngine:
    """Core analytical engine orchestrating DCF intrinsic enterprise and equity valuations."""

    @classmethod
    def extract_bridge_defaults(
        cls,
        bundle: Optional[HistoricalAnalysisBundle],
    ) -> EquityBridgeInputs:
        """Extract latest balance sheet cash and debt balances to initialize the equity bridge."""
        bridge = EquityBridgeInputs(
            cash_and_equivalents=0.0,
            debt_value=0.0,
            minority_interest=0.0,
            preferred_equity=0.0,
            other_adjustments=0.0,
            cash_provenance=InputProvenance(
                source_category=SourceCategory.APPLICATION_DEFAULT.value,
                source_reference="Explicit Placeholder (Set to 0.0)",
                notes="Cash balance placeholder.",
            ),
            debt_provenance=InputProvenance(
                source_category=SourceCategory.APPLICATION_DEFAULT.value,
                source_reference="Explicit Placeholder (Set to 0.0)",
                notes="Interest-bearing debt placeholder.",
            ),
            minority_interest_provenance=InputProvenance(
                source_category=SourceCategory.APPLICATION_DEFAULT.value,
                source_reference="Explicit Zero / Not Applicable",
                notes="Non-controlling interests placeholder.",
            ),
            preferred_equity_provenance=InputProvenance(
                source_category=SourceCategory.APPLICATION_DEFAULT.value,
                source_reference="Explicit Zero / Not Applicable",
                notes="Preferred stock claims placeholder.",
            ),
            other_adjustments_provenance=InputProvenance(
                source_category=SourceCategory.APPLICATION_DEFAULT.value,
                source_reference="No Net Non-Operating Adjustments",
                notes="Non-operating assets or liabilities.",
            ),
        )

        if not bundle or not bundle.periods:
            return bridge

        latest_p = bundle.periods[-1]
        p_label = latest_p.label
        line_items = bundle.raw_line_items_by_period.get(p_label, {})

        cash_val = line_items.get("cash_and_equivalents")
        if cash_val is not None:
            bridge.cash_and_equivalents = float(cash_val)
            bridge.cash_provenance = InputProvenance(
                source_category=SourceCategory.HISTORICAL_DATA.value,
                source_reference=f"Balance Sheet Cash ({p_label})",
                reference_date=str(latest_p.end_date),
                notes=f"Reported Cash and Cash Equivalents from {p_label} balance sheet.",
            )

        st_debt = line_items.get("short_term_debt") or 0.0
        lt_debt = line_items.get("long_term_debt") or 0.0
        total_debt = float(st_debt) + float(lt_debt)

        if total_debt > 0.0:
            bridge.debt_value = total_debt
            bridge.debt_provenance = InputProvenance(
                source_category=SourceCategory.HISTORICAL_DATA.value,
                source_reference=f"Balance Sheet Borrowings ({p_label})",
                reference_date=str(latest_p.end_date),
                notes=f"Interest-bearing borrowings from {p_label} balance sheet (Short-Term + Long-Term Debt).",
            )

        return bridge

    @classmethod
    def create_default_assumptions(
        cls,
        project_id: int,
        forecast_model_id: Optional[int] = None,
        wacc_model_id: Optional[int] = None,
        bundle: Optional[HistoricalAnalysisBundle] = None,
    ) -> DcfAssumptions:
        """Create baseline DCF valuation assumptions with populated bridge defaults."""
        bridge = cls.extract_bridge_defaults(bundle)

        return DcfAssumptions(
            name="Base Case DCF Valuation",
            description="Initial DCF valuation scenario calibrated with linked forecast and WACC parameters.",
            project_id=project_id,
            forecast_model_id=forecast_model_id,
            wacc_model_id=wacc_model_id,
            discounting_convention=DiscountingConvention.END_OF_YEAR.value,
            terminal_inputs=TerminalValueInputs(
                method=TerminalValueMethod.GORDON_GROWTH.value,
                perpetual_growth_rate=2.50,
                exit_multiple=10.0,
            ),
            bridge_inputs=bridge,
            diluted_shares=100.0,
            shares_provenance=InputProvenance(
                source_category=SourceCategory.APPLICATION_DEFAULT.value,
                source_reference="Benchmark Share Count Placeholder",
                notes="Diluted common shares outstanding (in millions or matching reporting units).",
            ),
        )

    @classmethod
    def evaluate_dcf(
        cls,
        assumptions: DcfAssumptions,
        forecast_assumptions: Optional[ForecastAssumptions],
        wacc_assumptions: Optional[WaccAssumptions],
        bundle: Optional[HistoricalAnalysisBundle],
    ) -> DcfValuationResult:
        """Execute end-to-end DCF valuation by combining forecast cash flows and WACC discount rate."""
        missing_inputs: List[str] = []
        warnings: List[str] = []

        # 1. Resolve WACC
        wacc_val: Optional[float] = None
        if wacc_assumptions:
            wacc_res = WaccEngine.estimate_wacc(wacc_assumptions)
            if wacc_res.is_complete and wacc_res.wacc is not None:
                wacc_val = wacc_res.wacc
            else:
                missing_inputs.append("Complete, valid WACC calculation from linked WACC case")
                warnings.extend(wacc_res.warnings)
        else:
            missing_inputs.append("Linked WACC Case (Please select or create a WACC scenario)")

        # 2. Resolve Forecast Cash Flows (UFCF) and Terminal EBITDA
        ufcf_series: List[Tuple[str, float]] = []
        terminal_ebitda: Optional[float] = None

        if forecast_assumptions and bundle and bundle.periods:
            try:
                fc_result = FinancialForecastingEngine.generate_forecast(
                    bundle=bundle,
                    assumptions=forecast_assumptions,
                )
                if fc_result.is_complete and fc_result.annual_forecasts:
                    for yf in fc_result.annual_forecasts:
                        if yf.ufcf is not None:
                            ufcf_series.append((yf.period_label, yf.ufcf))
                        else:
                            missing_inputs.append(f"Projected UFCF for forecast year {yf.period_label}")

                    terminal_yf = fc_result.annual_forecasts[-1]
                    terminal_ebitda = terminal_yf.ebitda
                else:
                    missing_inputs.append("Valid forecast projection outputs from linked forecast scenario")
            except Exception as exc:
                logger.error("Error generating linked forecast projections: %s", exc)
                missing_inputs.append(f"Forecast generation failed: {exc}")
        else:
            missing_inputs.append("Linked Forecast Scenario (Please select or create a forecast model with historical actuals)")

        if missing_inputs:
            return DcfValuationResult(
                enterprise_value=None,
                equity_value=None,
                implied_value_per_share=None,
                diluted_shares_applied=assumptions.diluted_shares,
                pv_forecast_ufcf=None,
                terminal_value=None,
                pv_terminal_value=None,
                terminal_value_pct_ev=None,
                pv_ufcf_pct_ev=None,
                wacc_applied=wacc_val,
                discounting_convention_applied=assumptions.discounting_convention,
                is_complete=False,
                missing_inputs=missing_inputs,
                warnings=warnings,
            )

        # 3. Execute calculations
        return calculate_dcf_valuation(
            ufcf_series=ufcf_series,
            terminal_ebitda=terminal_ebitda,
            wacc_pct=wacc_val,
            convention=assumptions.discounting_convention,
            terminal_inputs=assumptions.terminal_inputs,
            bridge_inputs=assumptions.bridge_inputs,
            diluted_shares=assumptions.diluted_shares,
        )
