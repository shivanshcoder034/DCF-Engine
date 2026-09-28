"""Scenario Analysis Engine coordinating multi-case valuation modeling.

Computes Base, Bull, and Bear cases by applying explicit assumption overrides
to Phase 4 forecast schedules, Phase 5 WACC discount rates, and Phase 6 DCF terminal parameters.
"""

from __future__ import annotations

import copy
import logging
from typing import List, Optional, Tuple

from src.analysis.models import HistoricalAnalysisBundle
from src.dcf.calculations import calculate_dcf_valuation
from src.dcf.models import (
    DcfAssumptions,
    DcfValuationResult,
    TerminalValueInputs,
    TerminalValueMethod,
)
from src.forecasting.engine import FinancialForecastingEngine
from src.forecasting.models import ForecastAssumptions, ForecastResult
from src.scenarios.models import (
    ScenarioAnalysisAssumptions,
    ScenarioAnalysisResult,
    ScenarioCaseResult,
    ScenarioCaseType,
    ScenarioOverrides,
)
from src.wacc.engine import WaccEngine
from src.wacc.models import WaccAssumptions

logger = logging.getLogger(__name__)


class ScenarioEngine:
    """Core analytical orchestrator for Base, Bull, and Bear DCF scenario modeling."""

    @classmethod
    def apply_overrides_to_forecast(
        cls,
        base_assumptions: ForecastAssumptions,
        overrides: ScenarioOverrides,
    ) -> ForecastAssumptions:
        """Create a modified ForecastAssumptions instance applying scenario adjustments.

        - revenue_growth_delta_pp: percentage points added to each year's revenue growth rate.
        - margin_delta_pp: percentage points added to each year's gross margin rate to expand/contract
          operating margin (EBIT margin) by the exact delta.
        """
        data = base_assumptions.to_dict()
        cloned = ForecastAssumptions.from_dict(data)

        # 1. Apply revenue growth adjustment (percentage points)
        if overrides.revenue_growth_delta_pp != 0.0:
            cloned.revenue_growth_rates = [
                round(rate + overrides.revenue_growth_delta_pp, 4)
                for rate in cloned.revenue_growth_rates
            ]

        # 2. Apply operating margin adjustment (percentage points via gross margin)
        if overrides.margin_delta_pp != 0.0:
            cloned.gross_margin_rates = [
                round(gm + overrides.margin_delta_pp, 4)
                for gm in cloned.gross_margin_rates
            ]

        return cloned

    @classmethod
    def apply_overrides_to_wacc(
        cls,
        base_wacc_pct: float,
        overrides: ScenarioOverrides,
    ) -> Tuple[float, List[str]]:
        """Calculate effective WACC by applying basis-point adjustment.

        100 basis points (bps) = 1.00 percentage point (1.0%).
        """
        warnings: List[str] = []
        wacc_adj_pct = overrides.wacc_delta_bps / 100.0
        effective_wacc = base_wacc_pct + wacc_adj_pct

        if effective_wacc <= 0.0:
            warnings.append(
                f"Adjusted WACC is non-positive ({effective_wacc:.2f}%). "
                "Discount rate must be strictly greater than zero."
            )

        return round(effective_wacc, 4), warnings

    @classmethod
    def apply_overrides_to_terminal(
        cls,
        base_terminal: TerminalValueInputs,
        overrides: ScenarioOverrides,
    ) -> Tuple[TerminalValueInputs, Optional[float], List[str]]:
        """Create modified TerminalValueInputs based on method and overrides.

        Returns (modified_inputs, effective_param_value, warnings).
        """
        warnings: List[str] = []
        term_copy = TerminalValueInputs.from_dict(base_terminal.to_dict())
        effective_param: Optional[float] = None

        if term_copy.method == TerminalValueMethod.GORDON_GROWTH.value:
            base_g = term_copy.perpetual_growth_rate or 2.50
            g_adj_pct = overrides.perpetual_growth_delta_bps / 100.0
            new_g = base_g + g_adj_pct
            term_copy.perpetual_growth_rate = round(new_g, 4)
            effective_param = term_copy.perpetual_growth_rate
        elif term_copy.method == TerminalValueMethod.EXIT_MULTIPLE.value:
            base_mult = term_copy.exit_multiple or 10.0
            new_mult = base_mult + overrides.exit_multiple_delta
            if new_mult <= 0.0:
                warnings.append(f"Adjusted exit multiple is non-positive ({new_mult:.2f}x).")
            term_copy.exit_multiple = round(new_mult, 4)
            effective_param = term_copy.exit_multiple
        else:
            effective_param = None

        return term_copy, effective_param, warnings

    @classmethod
    def evaluate_scenario_case(
        cls,
        case_name: str,
        overrides: ScenarioOverrides,
        bundle: Optional[HistoricalAnalysisBundle],
        base_forecast_assumptions: Optional[ForecastAssumptions],
        base_wacc_assumptions: Optional[WaccAssumptions],
        base_dcf_assumptions: Optional[DcfAssumptions],
        fc_model_name: Optional[str] = None,
        wacc_model_name: Optional[str] = None,
        dcf_model_name: Optional[str] = None,
    ) -> ScenarioCaseResult:
        """Evaluate cash flow projections, WACC, and DCF valuation for a single scenario case."""
        missing_inputs: List[str] = []
        warnings: List[str] = []

        # 1. Check prerequisites
        if not bundle or not bundle.periods:
            missing_inputs.append("Historical financial statement actuals (Phase 3 baseline)")
        if not base_forecast_assumptions:
            missing_inputs.append("Linked Phase 4 Forecast scenario")
        if not base_wacc_assumptions:
            missing_inputs.append("Linked Phase 5 WACC scenario")
        if not base_dcf_assumptions:
            missing_inputs.append("Linked Phase 6 DCF configuration")

        if missing_inputs:
            return ScenarioCaseResult(
                case_name=case_name,
                overrides=overrides,
                linked_forecast_name=fc_model_name,
                linked_wacc_name=wacc_model_name,
                linked_dcf_name=dcf_model_name,
                is_valid=False,
                status="incomplete",
                missing_inputs=missing_inputs,
                warnings=warnings,
            )

        assert bundle is not None
        assert base_forecast_assumptions is not None
        assert base_wacc_assumptions is not None
        assert base_dcf_assumptions is not None

        # 2. Base WACC evaluation
        wacc_base_res = WaccEngine.estimate_wacc(base_wacc_assumptions)
        if not wacc_base_res.is_complete or wacc_base_res.wacc is None:
            missing_inputs.append("Valid WACC result from linked WACC case")
            warnings.extend(wacc_base_res.warnings)
            return ScenarioCaseResult(
                case_name=case_name,
                overrides=overrides,
                linked_forecast_name=fc_model_name,
                linked_wacc_name=wacc_model_name,
                linked_dcf_name=dcf_model_name,
                is_valid=False,
                status="incomplete",
                missing_inputs=missing_inputs,
                warnings=warnings,
            )

        base_wacc_val = wacc_base_res.wacc

        # 3. Apply overrides to WACC
        effective_wacc, wacc_warn = cls.apply_overrides_to_wacc(base_wacc_val, overrides)
        warnings.extend(wacc_warn)

        # 4. Apply overrides to forecast assumptions and project cash flows
        fc_case_assumptions = cls.apply_overrides_to_forecast(base_forecast_assumptions, overrides)
        fc_result: Optional[ForecastResult] = None
        ufcf_series: List[Tuple[str, float]] = []
        terminal_ebitda: Optional[float] = None
        avg_rev_growth: Optional[float] = None
        avg_op_margin: Optional[float] = None

        try:
            fc_result = FinancialForecastingEngine.generate_forecast(
                bundle=bundle,
                assumptions=fc_case_assumptions,
            )
            warnings.extend(fc_result.warnings)

            if fc_result.annual_forecasts:
                growths = [yf.revenue_growth for yf in fc_result.annual_forecasts if yf.revenue_growth is not None]
                margins = [yf.ebit_margin for yf in fc_result.annual_forecasts if yf.ebit_margin is not None]
                if growths:
                    avg_rev_growth = round(sum(growths) / len(growths), 2)
                if margins:
                    avg_op_margin = round(sum(margins) / len(margins), 2)

                for yf in fc_result.annual_forecasts:
                    if yf.ufcf is not None:
                        ufcf_series.append((yf.period_label, yf.ufcf))
                    else:
                        missing_inputs.append(f"Projected UFCF for forecast period {yf.period_label}")

                terminal_yf = fc_result.annual_forecasts[-1]
                terminal_ebitda = terminal_yf.ebitda
            else:
                missing_inputs.append("Forecast projection annual schedules")
        except Exception as exc:
            logger.error("Forecast generation failed for scenario case %s: %s", case_name, exc)
            missing_inputs.append(f"Forecast generation failed: {exc}")

        # 5. Apply overrides to Terminal Value inputs
        term_case_inputs, effective_param, term_warn = cls.apply_overrides_to_terminal(
            base_dcf_assumptions.terminal_inputs,
            overrides,
        )
        warnings.extend(term_warn)

        # 6. Check Gordon Growth condition (WACC > g)
        if term_case_inputs.method == TerminalValueMethod.GORDON_GROWTH.value:
            g_val = term_case_inputs.perpetual_growth_rate
            if g_val is not None and effective_wacc is not None and effective_wacc <= g_val:
                warnings.append(
                    f"Invalid Gordon Growth condition in {case_name} case: Adjusted WACC ({effective_wacc:.2f}%) "
                    f"is less than or equal to perpetual growth rate ({g_val:.2f}%). "
                    "Terminal value and Enterprise Value cannot be mathematically computed."
                )

        if missing_inputs:
            return ScenarioCaseResult(
                case_name=case_name,
                overrides=overrides,
                linked_forecast_name=fc_model_name,
                linked_wacc_name=wacc_model_name,
                linked_dcf_name=dcf_model_name,
                effective_revenue_growth_avg=avg_rev_growth,
                effective_operating_margin_avg=avg_op_margin,
                effective_wacc=effective_wacc,
                terminal_method=term_case_inputs.method,
                effective_terminal_param=effective_param,
                forecast_result=fc_result,
                is_valid=False,
                status="incomplete",
                missing_inputs=missing_inputs,
                warnings=warnings,
            )

        # 7. Execute DCF valuation using existing calculation layer
        dcf_result = calculate_dcf_valuation(
            ufcf_series=ufcf_series,
            terminal_ebitda=terminal_ebitda,
            wacc_pct=effective_wacc,
            convention=base_dcf_assumptions.discounting_convention,
            terminal_inputs=term_case_inputs,
            bridge_inputs=base_dcf_assumptions.bridge_inputs,
            diluted_shares=base_dcf_assumptions.diluted_shares,
        )

        warnings.extend(dcf_result.warnings)
        if dcf_result.missing_inputs:
            missing_inputs.extend(dcf_result.missing_inputs)

        is_valid = dcf_result.is_complete and dcf_result.enterprise_value is not None
        status = "complete" if is_valid else ("invalid" if warnings else "incomplete")

        return ScenarioCaseResult(
            case_name=case_name,
            overrides=overrides,
            linked_forecast_name=fc_model_name,
            linked_wacc_name=wacc_model_name,
            linked_dcf_name=dcf_model_name,
            effective_revenue_growth_avg=avg_rev_growth,
            effective_operating_margin_avg=avg_op_margin,
            effective_wacc=effective_wacc,
            terminal_method=term_case_inputs.method,
            effective_terminal_param=effective_param,
            forecast_result=fc_result,
            dcf_result=dcf_result,
            pv_forecast_ufcf=dcf_result.pv_forecast_ufcf,
            pv_terminal_value=dcf_result.pv_terminal_value,
            enterprise_value=dcf_result.enterprise_value,
            equity_value=dcf_result.equity_value,
            implied_value_per_share=dcf_result.implied_value_per_share,
            shares_applied=dcf_result.diluted_shares_applied,
            is_valid=is_valid,
            status=status,
            warnings=warnings,
            missing_inputs=missing_inputs,
        )

    @classmethod
    def run_scenario_analysis(
        cls,
        assumptions: ScenarioAnalysisAssumptions,
        bundle: Optional[HistoricalAnalysisBundle],
        base_forecast_assumptions: Optional[ForecastAssumptions],
        base_wacc_assumptions: Optional[WaccAssumptions],
        base_dcf_assumptions: Optional[DcfAssumptions],
        fc_model_name: Optional[str] = None,
        wacc_model_name: Optional[str] = None,
        dcf_model_name: Optional[str] = None,
        currency: str = "USD",
    ) -> ScenarioAnalysisResult:
        """Run complete 3-case scenario analysis (Base, Bull, Bear).

        Base case uses zero overrides by definition.
        Bull and Bear apply explicit configured overrides.
        """
        base_overrides = ScenarioOverrides.default_base()

        base_res = cls.evaluate_scenario_case(
            case_name=ScenarioCaseType.BASE.value,
            overrides=base_overrides,
            bundle=bundle,
            base_forecast_assumptions=base_forecast_assumptions,
            base_wacc_assumptions=base_wacc_assumptions,
            base_dcf_assumptions=base_dcf_assumptions,
            fc_model_name=fc_model_name,
            wacc_model_name=wacc_model_name,
            dcf_model_name=dcf_model_name,
        )

        bull_res = cls.evaluate_scenario_case(
            case_name=ScenarioCaseType.BULL.value,
            overrides=assumptions.bull_overrides,
            bundle=bundle,
            base_forecast_assumptions=base_forecast_assumptions,
            base_wacc_assumptions=base_wacc_assumptions,
            base_dcf_assumptions=base_dcf_assumptions,
            fc_model_name=fc_model_name,
            wacc_model_name=wacc_model_name,
            dcf_model_name=dcf_model_name,
        )

        bear_res = cls.evaluate_scenario_case(
            case_name=ScenarioCaseType.BEAR.value,
            overrides=assumptions.bear_overrides,
            bundle=bundle,
            base_forecast_assumptions=base_forecast_assumptions,
            base_wacc_assumptions=base_wacc_assumptions,
            base_dcf_assumptions=base_dcf_assumptions,
            fc_model_name=fc_model_name,
            wacc_model_name=wacc_model_name,
            dcf_model_name=dcf_model_name,
        )

        is_complete = base_res.is_valid and bull_res.is_valid and bear_res.is_valid

        return ScenarioAnalysisResult(
            assumptions=assumptions,
            base_case=base_res,
            bull_case=bull_res,
            bear_case=bear_res,
            currency=currency,
            is_complete=is_complete,
        )
