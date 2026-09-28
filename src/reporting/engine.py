"""Analytical reporting engine compiling valuation models, statements, and diagnostics.

Coordinates underlying analysis bundles, forecasts, WACC estimations, DCF models,
scenarios, and sensitivity simulations into a unified ReportBundle.
"""

from __future__ import annotations

import logging
from typing import List, Optional

from src.analysis.engine import HistoricalAnalysisEngine
from src.analysis.models import HistoricalAnalysisBundle
from src.data.services import ProjectService
from src.dcf.engine import DcfEngine
from src.dcf.models import DcfAssumptions
from src.dcf.services import DcfService
from src.forecasting.engine import FinancialForecastingEngine
from src.forecasting.models import ForecastAssumptions
from src.forecasting.services import ForecastService
from src.reporting.models import ReportBundle, ReportConfig
from src.scenarios.engine import ScenarioAnalysisEngine
from src.scenarios.models import ScenarioAssumptionsSet
from src.scenarios.services import ScenarioService
from src.sensitivity.engine import SensitivityEngine
from src.sensitivity.models import SensitivityConfig
from src.sensitivity.services import SensitivityService
from src.wacc.engine import WaccEngine
from src.wacc.models import WaccAssumptions
from src.wacc.services import WaccService

logger = logging.getLogger(__name__)


class ReportEngine:
    """Core analytical reporting coordinator."""

    @classmethod
    def compile_report_bundle(cls, config: ReportConfig) -> ReportBundle:
        """Compile a complete, validated ReportBundle from project models and engines."""
        project = ProjectService.get_project(config.metadata.project_id)
        if not project:
            bundle = ReportBundle(
                config=config,
                project_id=config.metadata.project_id,
                company_name=config.metadata.company_name or "Unknown Company",
                ticker=config.metadata.ticker,
            )
            bundle.missing_models_diagnostics.append(
                f"Valuation Project ID {config.metadata.project_id} was not found."
            )
            return bundle

        comp = project.company
        company_name = config.metadata.company_name or (comp.name if comp else "Unknown Company")
        ticker = config.metadata.ticker or (comp.ticker if comp else None)

        bundle = ReportBundle(
            config=config,
            project_id=project.id,
            company_name=company_name,
            ticker=ticker,
        )

        # 1. Historical Financial Analysis
        try:
            hist_bundle = HistoricalAnalysisEngine.analyze_project(
                project_id=project.id,
                period_type=config.references.historical_frequency,
                data_classification=config.references.historical_classification,
                selected_currency=config.metadata.reporting_currency,
            )
            bundle.historical_bundle = hist_bundle
            if hist_bundle.data_quality_issues:
                for issue in hist_bundle.data_quality_issues:
                    bundle.data_quality_issues.append(
                        f"[{issue.severity.upper()}] {issue.category}: {issue.message}"
                    )
        except Exception as exc:
            logger.warning(f"Error compiling historical analysis for report: {exc}")
            bundle.missing_models_diagnostics.append(f"Historical analysis could not be evaluated: {exc}")

        # 2. Forecast Projections
        if config.references.forecast_model_id:
            fc_model = ForecastService.get_forecast_model(config.references.forecast_model_id)
            if not fc_model:
                bundle.missing_models_diagnostics.append(
                    f"Selected Forecast model ID {config.references.forecast_model_id} was not found or has been deleted."
                )
            else:
                try:
                    fc_assumptions = ForecastAssumptions.from_json(fc_model.assumptions_json)
                    bundle.forecast_assumptions = fc_assumptions
                    if bundle.historical_bundle and bundle.historical_bundle.periods:
                        fc_result = FinancialForecastingEngine.generate_forecast(
                            bundle.historical_bundle, fc_assumptions
                        )
                        bundle.forecast_result = fc_result
                    else:
                        bundle.missing_models_diagnostics.append(
                            "Cannot evaluate forecast projections: historical financial statements are missing."
                        )
                except Exception as exc:
                    logger.warning(f"Error evaluating forecast for report: {exc}")
                    bundle.missing_models_diagnostics.append(f"Forecast evaluation error: {exc}")

        # 3. WACC Model
        if config.references.wacc_model_id:
            wacc_model = WaccService.get_wacc_model(config.references.wacc_model_id)
            if not wacc_model:
                bundle.missing_models_diagnostics.append(
                    f"Selected WACC model ID {config.references.wacc_model_id} was not found or has been deleted."
                )
            else:
                try:
                    wacc_assumptions = WaccAssumptions.from_json(wacc_model.assumptions_json)
                    bundle.wacc_assumptions = wacc_assumptions
                    wacc_res = WaccEngine.estimate_wacc(wacc_assumptions)
                    bundle.wacc_result = wacc_res
                    if wacc_res.validation_warnings:
                        bundle.validation_warnings.extend(wacc_res.validation_warnings)
                except Exception as exc:
                    logger.warning(f"Error evaluating WACC for report: {exc}")
                    bundle.missing_models_diagnostics.append(f"WACC estimation error: {exc}")

        # 4. DCF Valuation Model
        if config.references.dcf_model_id:
            dcf_model = DcfService.get_dcf_model(config.references.dcf_model_id)
            if not dcf_model:
                bundle.missing_models_diagnostics.append(
                    f"Selected DCF model ID {config.references.dcf_model_id} was not found or has been deleted."
                )
            else:
                try:
                    dcf_assumptions = DcfAssumptions.from_json(dcf_model.assumptions_json)
                    bundle.dcf_assumptions = dcf_assumptions

                    # Ensure forecast and WACC are resolved (from linked models or DCF model relationships)
                    active_fc = bundle.forecast_assumptions
                    if not active_fc and dcf_model.forecast_model:
                        active_fc = ForecastAssumptions.from_json(dcf_model.forecast_model.assumptions_json)
                        bundle.forecast_assumptions = active_fc
                        if bundle.historical_bundle and bundle.historical_bundle.periods:
                            bundle.forecast_result = FinancialForecastingEngine.generate_forecast(
                                bundle.historical_bundle, active_fc
                            )

                    active_wacc = bundle.wacc_assumptions
                    if not active_wacc and dcf_model.wacc_model:
                        active_wacc = WaccAssumptions.from_json(dcf_model.wacc_model.assumptions_json)
                        bundle.wacc_assumptions = active_wacc
                        bundle.wacc_result = WaccEngine.estimate_wacc(active_wacc)

                    dcf_res = DcfEngine.evaluate_dcf(
                        assumptions=dcf_assumptions,
                        forecast_assumptions=active_fc,
                        wacc_assumptions=active_wacc,
                        bundle=bundle.historical_bundle,
                    )
                    bundle.dcf_result = dcf_res
                    if dcf_res.warnings:
                        bundle.validation_warnings.extend(dcf_res.warnings)
                except Exception as exc:
                    logger.warning(f"Error evaluating DCF for report: {exc}")
                    bundle.missing_models_diagnostics.append(f"DCF valuation error: {exc}")

        # 5. Scenario Analysis
        if config.references.scenario_model_id:
            sc_model = ScenarioService.get_scenario_model(config.references.scenario_model_id)
            if not sc_model:
                bundle.missing_models_diagnostics.append(
                    f"Selected Scenario model ID {config.references.scenario_model_id} was not found or has been deleted."
                )
            else:
                try:
                    bundle.scenario_model_name = sc_model.name
                    sc_assumptions = ScenarioAssumptionsSet.from_json(sc_model.assumptions_json)

                    # Resolve baseline models
                    base_dcf = bundle.dcf_assumptions
                    if not base_dcf and sc_model.dcf_model:
                        base_dcf = DcfAssumptions.from_json(sc_model.dcf_model.assumptions_json)
                    base_fc = bundle.forecast_assumptions
                    if not base_fc and sc_model.forecast_model:
                        base_fc = ForecastAssumptions.from_json(sc_model.forecast_model.assumptions_json)
                    base_wacc = bundle.wacc_assumptions
                    if not base_wacc and sc_model.wacc_model:
                        base_wacc = WaccAssumptions.from_json(sc_model.wacc_model.assumptions_json)

                    if base_dcf and base_fc and base_wacc and bundle.historical_bundle:
                        sc_res = ScenarioAnalysisEngine.evaluate_scenarios(
                            dcf_assumptions=base_dcf,
                            base_fc_assumptions=base_fc,
                            base_wacc_assumptions=base_wacc,
                            bundle=bundle.historical_bundle,
                            scenario_set=sc_assumptions,
                        )
                        bundle.scenario_result = sc_res
                    else:
                        bundle.missing_models_diagnostics.append(
                            "Scenario analysis could not be fully calculated: one or more baseline models (DCF, Forecast, WACC, or Historicals) are missing."
                        )
                except Exception as exc:
                    logger.warning(f"Error evaluating scenario analysis for report: {exc}")
                    bundle.missing_models_diagnostics.append(f"Scenario analysis error: {exc}")

        # 6. Sensitivity Analysis & Monte Carlo Simulation
        if config.references.sensitivity_model_id:
            sens_model = SensitivityService.get_sensitivity_model(config.references.sensitivity_model_id)
            if not sens_model:
                bundle.missing_models_diagnostics.append(
                    f"Selected Sensitivity model ID {config.references.sensitivity_model_id} was not found or has been deleted."
                )
            else:
                try:
                    bundle.sensitivity_model_name = sens_model.name
                    sens_cfg = SensitivityConfig.from_json(sens_model.config_json)
                    bundle.sensitivity_config = sens_cfg

                    base_dcf = bundle.dcf_assumptions
                    if not base_dcf and sens_model.dcf_model:
                        base_dcf = DcfAssumptions.from_json(sens_model.dcf_model.assumptions_json)
                    base_fc = bundle.forecast_assumptions
                    base_wacc = bundle.wacc_assumptions

                    if base_dcf and base_fc and base_wacc and bundle.historical_bundle:
                        matrix_res = SensitivityEngine.compute_sensitivity_matrix(
                            dcf_assumptions=base_dcf,
                            base_fc_assumptions=base_fc,
                            base_wacc_assumptions=base_wacc,
                            bundle=bundle.historical_bundle,
                            axis_row_config=sens_cfg.axis_row,
                            axis_col_config=sens_cfg.axis_col,
                            metric=sens_cfg.metric,
                        )
                        bundle.sensitivity_matrix_result = matrix_res

                        if sens_cfg.run_monte_carlo:
                            mc_res = SensitivityEngine.run_monte_carlo_simulation(
                                dcf_assumptions=base_dcf,
                                base_fc_assumptions=base_fc,
                                base_wacc_assumptions=base_wacc,
                                bundle=bundle.historical_bundle,
                                config=sens_cfg,
                            )
                            bundle.monte_carlo_result = mc_res
                    else:
                        bundle.missing_models_diagnostics.append(
                            "Sensitivity analysis could not be calculated: baseline DCF, forecast, or WACC models are missing."
                        )
                except Exception as exc:
                    logger.warning(f"Error evaluating sensitivity analysis for report: {exc}")
                    bundle.missing_models_diagnostics.append(f"Sensitivity analysis error: {exc}")

        return bundle
