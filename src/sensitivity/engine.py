"""Sensitivity Analysis and Monte Carlo Simulation Engine.

Provides deterministic two-dimensional sensitivity matrices (WACC vs. Perpetual Growth / Exit Multiple)
and reproducible Monte Carlo probabilistic valuation distributions.
"""

from __future__ import annotations

import logging
from collections import defaultdict
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

from src.analysis.models import HistoricalAnalysisBundle
from src.dcf.calculations import calculate_dcf_valuation
from src.dcf.models import (
    DcfAssumptions,
    DcfValuationResult,
    TerminalValueInputs,
    TerminalValueMethod,
)
from src.forecasting.engine import FinancialForecastingEngine
from src.forecasting.models import ForecastAssumptions
from src.sensitivity.models import (
    DistributionConfig,
    DistributionType,
    MonteCarloSimulationResult,
    MonteCarloSummaryStats,
    SensitivityCellResult,
    SensitivityConfig,
    SensitivityMatrixResult,
    SensitivityMetric,
)
from src.wacc.engine import WaccEngine
from src.wacc.models import WaccAssumptions

logger = logging.getLogger(__name__)


class SensitivityEngine:
    """Core analytical orchestrator for 2D sensitivity matrices and Monte Carlo simulations."""

    @classmethod
    def compute_sensitivity_matrix(
        cls,
        base_dcf_assumptions: DcfAssumptions,
        base_fc_assumptions: ForecastAssumptions,
        base_wacc_val: float,
        bundle: HistoricalAnalysisBundle,
        wacc_values: List[float],
        terminal_values: List[float],
        metric: str = SensitivityMetric.IMPLIED_SHARE_PRICE.value,
        dcf_model_name: Optional[str] = None,
    ) -> SensitivityMatrixResult:
        """Evaluate a deterministic 2D sensitivity matrix.

        Sensitizes WACC (rows) against the terminal value assumption (columns: Gordon Growth rate or Exit Multiple).
        All other DCF drivers (UFCF projections, timing convention, cash, debt, shares) remain fixed at baseline.
        """
        warnings: List[str] = []

        # 1. Generate baseline forecast projections once (fixed across all matrix cells)
        fc_res = FinancialForecastingEngine.generate_forecast(bundle, base_fc_assumptions)
        if not fc_res.is_complete or not fc_res.annual_forecasts:
            raise ValueError("Baseline forecast projections are incomplete or failed to generate.")

        ufcf_series: List[Tuple[str, float]] = [
            (yf.period_label, yf.ufcf) for yf in fc_res.annual_forecasts if yf.ufcf is not None
        ]
        terminal_ebitda: Optional[float] = fc_res.annual_forecasts[-1].ebitda

        # 2. Identify method and baseline values
        term_method = base_dcf_assumptions.terminal_inputs.method
        is_gordon = term_method == TerminalValueMethod.GORDON_GROWTH.value

        base_row_val = round(base_wacc_val, 4)
        if is_gordon:
            col_param_name = "Perpetual Growth Rate (g %)"
            base_col_val = round(base_dcf_assumptions.terminal_inputs.perpetual_growth_rate or 2.50, 4)
        else:
            col_param_name = "Exit Multiple (EV/EBITDA x)"
            base_col_val = round(base_dcf_assumptions.terminal_inputs.exit_multiple or 10.0, 4)

        # 3. Disclose fixed assumptions held constant
        fixed_assumptions: Dict[str, Any] = {
            "Discounting Convention": base_dcf_assumptions.discounting_convention.replace("_", " ").title(),
            "Diluted Shares Outstanding": f"{base_dcf_assumptions.diluted_shares:,.2f}" if base_dcf_assumptions.diluted_shares else "Not Provided",
            "Cash & Equivalents Added": f"{base_dcf_assumptions.bridge_inputs.cash_and_equivalents:,.2f}",
            "Interest-Bearing Debt Subtracted": f"{base_dcf_assumptions.bridge_inputs.debt_value:,.2f}",
            "Forecast Horizon": f"{len(ufcf_series)} Years",
            "Base WACC": f"{base_row_val:.2f}%",
            "Base Terminal Assumption": f"{base_col_val:.2f}%" if is_gordon else f"{base_col_val:.2f}x",
        }

        # 4. Construct 2D grid
        grid_cells: List[List[SensitivityCellResult]] = []

        for row_wacc in wacc_values:
            row_cells: List[SensitivityCellResult] = []
            for col_term in terminal_values:
                # Check baseline intersection (closest match within 1e-4)
                is_intersect = (abs(row_wacc - base_row_val) < 1e-4) and (abs(col_term - base_col_val) < 1e-4)

                # Validity checks
                if row_wacc <= 0.0:
                    row_cells.append(
                        SensitivityCellResult(
                            row_val=row_wacc,
                            col_val=col_term,
                            is_baseline_intersection=is_intersect,
                            is_valid=False,
                            status="invalid",
                            reason="WACC must be strictly positive",
                        )
                    )
                    continue

                if is_gordon:
                    if row_wacc <= col_term:
                        row_cells.append(
                            SensitivityCellResult(
                                row_val=row_wacc,
                                col_val=col_term,
                                is_baseline_intersection=is_intersect,
                                is_valid=False,
                                status="invalid",
                                reason=f"Invalid: WACC ({row_wacc:.2f}%) <= g ({col_term:.2f}%)",
                            )
                        )
                        continue
                else:
                    if col_term <= 0.0:
                        row_cells.append(
                            SensitivityCellResult(
                                row_val=row_wacc,
                                col_val=col_term,
                                is_baseline_intersection=is_intersect,
                                is_valid=False,
                                status="invalid",
                                reason=f"Invalid: Exit multiple ({col_term:.2f}x) <= 0",
                            )
                        )
                        continue

                # Clone terminal inputs for this specific cell
                cell_term_inputs = TerminalValueInputs(
                    method=term_method,
                    perpetual_growth_rate=col_term if is_gordon else None,
                    exit_multiple=col_term if not is_gordon else None,
                )

                # Execute DCF calculation using Phase 6 layer
                dcf_res = calculate_dcf_valuation(
                    ufcf_series=ufcf_series,
                    terminal_ebitda=terminal_ebitda,
                    wacc_pct=row_wacc,
                    convention=base_dcf_assumptions.discounting_convention,
                    terminal_inputs=cell_term_inputs,
                    bridge_inputs=base_dcf_assumptions.bridge_inputs,
                    diluted_shares=base_dcf_assumptions.diluted_shares,
                )

                if dcf_res.is_complete and dcf_res.enterprise_value is not None:
                    row_cells.append(
                        SensitivityCellResult(
                            row_val=row_wacc,
                            col_val=col_term,
                            is_baseline_intersection=is_intersect,
                            enterprise_value=dcf_res.enterprise_value,
                            equity_value=dcf_res.equity_value,
                            implied_value_per_share=dcf_res.implied_value_per_share,
                            is_valid=True,
                            status="valid",
                        )
                    )
                else:
                    reason = "; ".join(dcf_res.warnings or dcf_res.missing_inputs) or "Incomplete DCF calculation"
                    row_cells.append(
                        SensitivityCellResult(
                            row_val=row_wacc,
                            col_val=col_term,
                            is_baseline_intersection=is_intersect,
                            is_valid=False,
                            status="invalid",
                            reason=reason,
                        )
                    )

            grid_cells.append(row_cells)

        return SensitivityMatrixResult(
            dcf_model_name=dcf_model_name,
            terminal_method=term_method,
            metric=metric,
            row_param_name="WACC (%)",
            col_param_name=col_param_name,
            row_values=wacc_values,
            col_values=terminal_values,
            baseline_row_val=base_row_val,
            baseline_col_val=base_col_val,
            cells=grid_cells,
            fixed_assumptions=fixed_assumptions,
            warnings=warnings,
        )

    @classmethod
    def _sample_from_dist(cls, rng: np.random.Generator, dist: DistributionConfig) -> float:
        """Draw a single random sample from the specified distribution configuration."""
        dtype = dist.dist_type
        if dtype == DistributionType.NORMAL.value:
            sigma = max(1e-4, abs(dist.std_dev))
            return float(rng.normal(dist.mean, sigma))
        elif dtype == DistributionType.TRIANGULAR.value:
            low = min(dist.min_val, dist.mode_val, dist.max_val)
            high = max(dist.min_val, dist.mode_val, dist.max_val)
            if high <= low:
                high = low + 1e-4
            mode = min(max(dist.mode_val, low), high)
            return float(rng.triangular(left=low, mode=mode, right=high))
        elif dtype == DistributionType.UNIFORM.value:
            low = min(dist.min_val, dist.max_val)
            high = max(dist.min_val, dist.max_val)
            if high <= low:
                high = low + 1e-4
            return float(rng.uniform(low=low, high=high))
        else:
            return float(dist.mean)

    @classmethod
    def _calculate_stats(cls, values: List[float]) -> Optional[MonteCarloSummaryStats]:
        """Compute descriptive percentile statistics for an array of simulated values."""
        if not values or len(values) < 5:
            return None

        arr = np.array(values, dtype=float)
        return MonteCarloSummaryStats(
            count=len(arr),
            mean=round(float(np.mean(arr)), 4),
            median=round(float(np.median(arr)), 4),
            std_dev=round(float(np.std(arr)), 4),
            min=round(float(np.min(arr)), 4),
            p10=round(float(np.percentile(arr, 10)), 4),
            p25=round(float(np.percentile(arr, 25)), 4),
            p75=round(float(np.percentile(arr, 75)), 4),
            p90=round(float(np.percentile(arr, 90)), 4),
            max=round(float(np.max(arr)), 4),
        )

    @classmethod
    def run_monte_carlo_simulation(
        cls,
        base_dcf_assumptions: DcfAssumptions,
        base_fc_assumptions: ForecastAssumptions,
        base_wacc_assumptions: WaccAssumptions,
        bundle: HistoricalAnalysisBundle,
        config: SensitivityConfig,
    ) -> MonteCarloSimulationResult:
        """Execute a reproducible, deterministic Monte Carlo simulation across selected drivers."""
        warnings: List[str] = []
        safe_iterations = max(10, min(config.iterations, 5000))
        rng = np.random.default_rng(abs(config.random_seed))

        # Resolve baseline WACC
        wacc_base_res = WaccEngine.estimate_wacc(base_wacc_assumptions)
        if not wacc_base_res.is_complete or wacc_base_res.wacc is None:
            raise ValueError("Baseline WACC calculation is incomplete or invalid.")
        base_wacc_val = wacc_base_res.wacc

        term_method = base_dcf_assumptions.terminal_inputs.method
        is_gordon = term_method == TerminalValueMethod.GORDON_GROWTH.value
        base_term_val = (
            base_dcf_assumptions.terminal_inputs.perpetual_growth_rate or 2.50
            if is_gordon
            else base_dcf_assumptions.terminal_inputs.exit_multiple or 10.0
        )

        # Baseline forecast cash flows
        fc_base_res = FinancialForecastingEngine.generate_forecast(bundle, base_fc_assumptions)
        if not fc_base_res.is_complete or not fc_base_res.annual_forecasts:
            raise ValueError("Baseline forecast generation is incomplete.")

        base_ufcf_series: List[Tuple[str, float]] = [
            (yf.period_label, yf.ufcf) for yf in fc_base_res.annual_forecasts if yf.ufcf is not None
        ]
        base_terminal_ebitda: Optional[float] = fc_base_res.annual_forecasts[-1].ebitda

        # Identify which distributions are active
        active_dists: Dict[str, DistributionConfig] = {}
        if config.simulate_revenue_growth:
            active_dists["Revenue Growth Delta (pp)"] = config.revenue_growth_dist
        if config.simulate_operating_margin:
            active_dists["Operating Margin Delta (pp)"] = config.operating_margin_dist
        if config.simulate_wacc:
            active_dists["Cost of Capital / WACC (%)"] = config.wacc_dist
        if config.simulate_terminal_param:
            lbl = "Perpetual Growth Rate (g %)" if is_gordon else "Exit Multiple (x EBITDA)"
            active_dists[lbl] = config.terminal_param_dist

        fixed_assumptions: Dict[str, Any] = {
            "Simulated Iterations Requested": safe_iterations,
            "Random Seed": config.random_seed,
            "Discounting Convention": base_dcf_assumptions.discounting_convention.replace("_", " ").title(),
            "Diluted Shares Outstanding": f"{base_dcf_assumptions.diluted_shares:,.2f}" if base_dcf_assumptions.diluted_shares else "Not Provided",
            "Cash & Equivalents Added": f"{base_dcf_assumptions.bridge_inputs.cash_and_equivalents:,.2f}",
            "Interest-Bearing Debt Subtracted": f"{base_dcf_assumptions.bridge_inputs.debt_value:,.2f}",
            "Forecast Horizon": f"{len(base_ufcf_series)} Years",
            "Baseline WACC": f"{base_wacc_val:.2f}%",
            "Baseline Terminal Value Assumption": f"{base_term_val:.2f}%" if is_gordon else f"{base_term_val:.2f}x",
        }

        sampled_evs: List[float] = []
        sampled_equities: List[float] = []
        sampled_share_prices: List[float] = []
        invalid_reasons: Dict[str, int] = defaultdict(int)

        # Simulation loop
        for _ in range(safe_iterations):
            # 1. Sample operational drivers (if active)
            delta_rev = cls._sample_from_dist(rng, config.revenue_growth_dist) if config.simulate_revenue_growth else 0.0
            delta_mrg = cls._sample_from_dist(rng, config.operating_margin_dist) if config.simulate_operating_margin else 0.0

            # 2. Sample financial / terminal drivers (if active)
            sampled_wacc = cls._sample_from_dist(rng, config.wacc_dist) if config.simulate_wacc else base_wacc_val
            sampled_term = cls._sample_from_dist(rng, config.terminal_param_dist) if config.simulate_terminal_param else base_term_val

            # 3. Enforce mathematical validity boundaries
            if sampled_wacc <= 0.0:
                invalid_reasons["Sampled WACC <= 0%"] += 1
                continue

            if is_gordon:
                if sampled_wacc <= sampled_term:
                    invalid_reasons["WACC <= Perpetual Growth Rate (g)"] += 1
                    continue
            else:
                if sampled_term <= 0.0:
                    invalid_reasons["Sampled Exit Multiple <= 0x"] += 1
                    continue

            # 4. Resolve forecast cash flows
            if config.simulate_revenue_growth or config.simulate_operating_margin:
                # Modify forecast assumptions
                cloned_fc = ForecastAssumptions.from_dict(base_fc_assumptions.to_dict())
                cloned_fc.revenue_growth_rates = [r + delta_rev for r in cloned_fc.revenue_growth_rates]
                cloned_fc.gross_margin_rates = [gm + delta_mrg for gm in cloned_fc.gross_margin_rates]

                try:
                    iter_fc = FinancialForecastingEngine.generate_forecast(bundle, cloned_fc)
                    if not iter_fc.is_complete or not iter_fc.annual_forecasts:
                        invalid_reasons["Forecast projection calculation failure"] += 1
                        continue
                    iter_ufcf = [(yf.period_label, yf.ufcf) for yf in iter_fc.annual_forecasts if yf.ufcf is not None]
                    iter_ebitda = iter_fc.annual_forecasts[-1].ebitda
                except Exception as exc:
                    invalid_reasons[f"Forecast generation exception: {exc}"] += 1
                    continue
            else:
                iter_ufcf = base_ufcf_series
                iter_ebitda = base_terminal_ebitda

            # 5. Execute DCF valuation
            cell_term = TerminalValueInputs(
                method=term_method,
                perpetual_growth_rate=sampled_term if is_gordon else None,
                exit_multiple=sampled_term if not is_gordon else None,
            )

            dcf_res = calculate_dcf_valuation(
                ufcf_series=iter_ufcf,
                terminal_ebitda=iter_ebitda,
                wacc_pct=sampled_wacc,
                convention=base_dcf_assumptions.discounting_convention,
                terminal_inputs=cell_term,
                bridge_inputs=base_dcf_assumptions.bridge_inputs,
                diluted_shares=base_dcf_assumptions.diluted_shares,
            )

            if dcf_res.is_complete and dcf_res.enterprise_value is not None:
                sampled_evs.append(dcf_res.enterprise_value)
                if dcf_res.equity_value is not None:
                    sampled_equities.append(dcf_res.equity_value)
                if dcf_res.implied_value_per_share is not None:
                    sampled_share_prices.append(dcf_res.implied_value_per_share)
            else:
                invalid_reasons["DCF valuation incomplete or withheld"] += 1

        valid_count = len(sampled_evs)
        invalid_count = safe_iterations - valid_count

        if valid_count < 10:
            warnings.append(
                f"Too few valid iterations ({valid_count}/{safe_iterations}) to produce meaningful distribution statistics. "
                "Review distribution parameters to avoid invalid combinations (e.g., WACC <= g)."
            )

        ev_stats = cls._calculate_stats(sampled_evs)
        equity_stats = cls._calculate_stats(sampled_equities)
        share_stats = cls._calculate_stats(sampled_share_prices)

        return MonteCarloSimulationResult(
            total_iterations=safe_iterations,
            valid_iterations=valid_count,
            invalid_iterations=invalid_count,
            invalid_reasons=dict(invalid_reasons),
            random_seed=config.random_seed,
            ev_stats=ev_stats,
            equity_stats=equity_stats,
            share_price_stats=share_stats,
            sampled_evs=sampled_evs,
            sampled_equities=sampled_equities,
            sampled_share_prices=sampled_share_prices,
            variable_configs=active_dists,
            fixed_assumptions=fixed_assumptions,
            warnings=warnings,
        )
