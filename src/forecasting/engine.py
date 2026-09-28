"""Deterministic financial statement forecasting and cash flow projection engine.

Projects multi-year income statement schedules, operating working capital dynamics,
and Unlevered Free Cash Flows (UFCF) from historical baselines and user assumptions.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from src.analysis.models import HistoricalAnalysisBundle
from src.forecasting.models import (
    ForecastAssumptions,
    ForecastResult,
    YearForecast,
)


class FinancialForecastingEngine:
    """Core projection engine generating multi-period financial forecasts."""

    @classmethod
    def extract_historical_baselines(
        cls,
        bundle: HistoricalAnalysisBundle,
    ) -> Dict[str, Any]:
        """Extract baseline operating ratios and drivers from historical analysis."""
        if not bundle.periods:
            return {}

        latest_p = bundle.periods[-1]
        p_label = latest_p.label
        latest_metrics = bundle.metrics_by_period.get(p_label, {})
        latest_wc = bundle.working_capital.get(p_label)
        latest_cf = bundle.cash_flow_metrics.get(p_label)
        raw_items = bundle.raw_line_items_by_period.get(p_label, {})

        rev = latest_metrics.get("revenue").value if "revenue" in latest_metrics else raw_items.get("revenue")
        growth_m = latest_metrics.get("revenue_growth")
        gp_m = latest_metrics.get("gross_margin")
        ebitda_m = latest_metrics.get("ebitda_margin")
        ebit_m = latest_metrics.get("ebit_margin")
        da_pct_m = latest_metrics.get("da_pct_revenue")
        opex_pct_m = latest_metrics.get("opex_pct_revenue")

        # Multi-year revenue CAGR if available
        cagr_m = bundle.cagr_results.get("revenue_cagr")

        return {
            "base_period": latest_p,
            "base_period_label": p_label,
            "base_period_year": latest_p.end_date.year,
            "base_revenue": rev or 0.0,
            "base_cogs": raw_items.get("cogs"),
            "base_gross_profit": latest_metrics.get("gross_profit").value if "gross_profit" in latest_metrics else None,
            "base_gross_margin": gp_m.value if gp_m and gp_m.value is not None else None,
            "base_ebitda": latest_metrics.get("ebitda").value if "ebitda" in latest_metrics else None,
            "base_ebitda_margin": ebitda_m.value if ebitda_m and ebitda_m.value is not None else None,
            "base_ebit": latest_metrics.get("ebit").value if "ebit" in latest_metrics else None,
            "base_ebit_margin": ebit_m.value if ebit_m and ebit_m.value is not None else None,
            "base_operating_nwc": latest_wc.operating_nwc if latest_wc and latest_wc.operating_nwc is not None else 0.0,
            "base_cfo": latest_cf.operating_cash_flow if latest_cf else None,
            "base_capex": latest_cf.capex_magnitude if latest_cf else None,
            # Baseline Driver Suggestions
            "suggested_growth": cagr_m.value if cagr_m and cagr_m.value is not None else (growth_m.value if growth_m and growth_m.value is not None else 5.0),
            "suggested_gross_margin": gp_m.value if gp_m and gp_m.value is not None else 40.0,
            "suggested_opex_pct": opex_pct_m.value if opex_pct_m and opex_pct_m.value is not None else 20.0,
            "suggested_da_pct": da_pct_m.value if da_pct_m and da_pct_m.value is not None else 4.0,
            "suggested_capex_pct": latest_cf.capex_pct_revenue if latest_cf and latest_cf.capex_pct_revenue is not None else 5.0,
            "suggested_dso": latest_wc.dso if latest_wc and latest_wc.dso is not None else 45.0,
            "suggested_dio": latest_wc.dio if latest_wc and latest_wc.dio is not None else 60.0,
            "suggested_dpo": latest_wc.dpo if latest_wc and latest_wc.dpo is not None else 40.0,
            "suggested_tax_rate": latest_cf.effective_tax_rate if latest_cf and latest_cf.effective_tax_rate is not None and 10.0 <= latest_cf.effective_tax_rate <= 40.0 else 25.0,
            "has_wc_days": bool(latest_wc and latest_wc.dso is not None and latest_wc.dio is not None and latest_wc.dpo is not None),
        }

    @classmethod
    def create_default_assumptions(
        cls,
        bundle: HistoricalAnalysisBundle,
        horizon_years: int = 5,
        name: str = "Base Case Forecast",
    ) -> ForecastAssumptions:
        """Create baseline forecast assumptions pre-populated from historical analysis."""
        baselines = cls.extract_historical_baselines(bundle)

        growth = float(baselines.get("suggested_growth", 5.0))
        gm = float(baselines.get("suggested_gross_margin", 40.0))
        opex_pct = float(baselines.get("suggested_opex_pct", 20.0))
        da_pct = float(baselines.get("suggested_da_pct", 4.0))
        capex_pct = float(baselines.get("suggested_capex_pct", 5.0))
        tax_rate = float(baselines.get("suggested_tax_rate", 25.0))

        has_wc_days = baselines.get("has_wc_days", False)
        dso = float(baselines.get("suggested_dso", 45.0))
        dio = float(baselines.get("suggested_dio", 60.0))
        dpo = float(baselines.get("suggested_dpo", 40.0))

        # Calculate NWC % of revenue fallback
        base_rev = baselines.get("base_revenue", 0.0)
        base_op_nwc = baselines.get("base_operating_nwc", 0.0)
        nwc_pct = (base_op_nwc / base_rev * 100.0) if base_rev > 0 else 10.0

        driver_sources = {
            "revenue_growth": "historical_baseline" if baselines.get("suggested_growth") is not None else "application_default",
            "gross_margin": "historical_baseline" if baselines.get("base_gross_margin") is not None else "application_default",
            "opex_pct": "historical_baseline" if baselines.get("suggested_opex_pct") is not None else "application_default",
            "da_pct": "historical_baseline" if baselines.get("suggested_da_pct") is not None else "application_default",
            "capex_pct": "historical_baseline" if baselines.get("suggested_capex_pct") is not None else "application_default",
            "working_capital": "historical_baseline" if has_wc_days else "application_default",
            "tax_rate": "historical_baseline" if baselines.get("suggested_tax_rate") is not None else "application_default",
        }

        return ForecastAssumptions(
            name=name,
            horizon_years=horizon_years,
            revenue_growth_rates=[growth] * horizon_years,
            gross_margin_rates=[gm] * horizon_years,
            opex_pct_rates=[opex_pct] * horizon_years,
            da_pct_rates=[da_pct] * horizon_years,
            capex_pct_rates=[capex_pct] * horizon_years,
            use_working_capital_days=has_wc_days,
            dso_days=[dso] * horizon_years,
            dio_days=[dio] * horizon_years,
            dpo_days=[dpo] * horizon_years,
            nwc_pct_revenue=[nwc_pct] * horizon_years,
            tax_rate=tax_rate,
            driver_sources=driver_sources,
        )

    @classmethod
    def project_financials(
        cls,
        bundle: HistoricalAnalysisBundle,
        assumptions: ForecastAssumptions,
    ) -> ForecastResult:
        """Execute deterministic multi-year projections based on assumptions."""
        warnings: List[str] = []

        if not bundle.periods:
            raise ValueError("Cannot project without historical periods. Please ingest historical records first.")

        baselines = cls.extract_historical_baselines(bundle)
        base_revenue = float(baselines.get("base_revenue", 0.0))
        base_op_nwc = float(baselines.get("base_operating_nwc", 0.0))
        base_year = int(baselines.get("base_period_year", 2023))
        base_label = str(baselines.get("base_period_label", "FY2023"))

        if base_revenue <= 0.0:
            warnings.append(
                f"Baseline revenue for {base_label} is non-positive ({base_revenue:,.2f}). "
                "Projections may yield zero or atypical figures."
            )

        horizon = assumptions.horizon_years
        annual_forecasts: List[YearForecast] = []

        prev_revenue = base_revenue
        prev_op_nwc = base_op_nwc

        tax_rate_mult = max(0.0, assumptions.tax_rate / 100.0)

        for year_idx in range(1, horizon + 1):
            forecast_year = base_year + year_idx
            period_label = f"FY{forecast_year} (F)"

            # Index into schedules safely
            growth_rate = assumptions.revenue_growth_rates[year_idx - 1] if year_idx - 1 < len(assumptions.revenue_growth_rates) else 5.0
            gm_rate = assumptions.gross_margin_rates[year_idx - 1] if year_idx - 1 < len(assumptions.gross_margin_rates) else 40.0
            opex_pct = assumptions.opex_pct_rates[year_idx - 1] if year_idx - 1 < len(assumptions.opex_pct_rates) else 20.0
            da_pct = assumptions.da_pct_rates[year_idx - 1] if year_idx - 1 < len(assumptions.da_pct_rates) else 4.0
            capex_pct = assumptions.capex_pct_rates[year_idx - 1] if year_idx - 1 < len(assumptions.capex_pct_rates) else 5.0

            # 1. Revenue
            rev = prev_revenue * (1.0 + (growth_rate / 100.0))

            # 2. COGS & Gross Profit
            gm_fraction = gm_rate / 100.0
            cogs = rev * (1.0 - gm_fraction)
            gp = rev - cogs

            # 3. Operating Expenses & EBITDA
            opex = rev * (opex_pct / 100.0)
            ebitda = gp - opex
            ebitda_margin = (ebitda / rev * 100.0) if rev > 0 else 0.0

            # 4. Depreciation & Amortization
            da = rev * (da_pct / 100.0)

            # 5. EBIT (Operating Profit)
            ebit = ebitda - da
            ebit_margin = (ebit / rev * 100.0) if rev > 0 else 0.0

            # 6. Taxes & NOPAT
            # NOPAT = EBIT * (1 - T)
            tax_expense = max(0.0, ebit * tax_rate_mult) if ebit > 0 else 0.0
            nopat = ebit * (1.0 - tax_rate_mult)

            # 7. Working Capital Projections
            ar_proj: Optional[float] = None
            inv_proj: Optional[float] = None
            ap_proj: Optional[float] = None

            if assumptions.use_working_capital_days:
                dso = assumptions.dso_days[year_idx - 1] if year_idx - 1 < len(assumptions.dso_days) else 45.0
                dio = assumptions.dio_days[year_idx - 1] if year_idx - 1 < len(assumptions.dio_days) else 60.0
                dpo = assumptions.dpo_days[year_idx - 1] if year_idx - 1 < len(assumptions.dpo_days) else 40.0

                ar_proj = (rev * dso) / 365.0
                inv_proj = (cogs * dio) / 365.0
                ap_proj = (cogs * dpo) / 365.0
                op_nwc = ar_proj + inv_proj - ap_proj
            else:
                nwc_pct = assumptions.nwc_pct_revenue[year_idx - 1] if year_idx - 1 < len(assumptions.nwc_pct_revenue) else 10.0
                op_nwc = rev * (nwc_pct / 100.0)

            delta_op_nwc = op_nwc - prev_op_nwc

            # 8. CapEx & UFCF
            capex = rev * (capex_pct / 100.0)
            # UFCF = NOPAT + D&A - CapEx - Delta_Operating_NWC
            ufcf = nopat + da - capex - delta_op_nwc

            annual_forecasts.append(
                YearForecast(
                    year_index=year_idx,
                    period_label=period_label,
                    revenue=rev,
                    revenue_growth=growth_rate,
                    cogs=cogs,
                    gross_profit=gp,
                    gross_margin=gm_rate,
                    operating_expenses=opex,
                    ebitda=ebitda,
                    ebitda_margin=ebitda_margin,
                    depreciation_amortization=da,
                    ebit=ebit,
                    ebit_margin=ebit_margin,
                    tax_expense=tax_expense,
                    nopat=nopat,
                    accounts_receivable=ar_proj,
                    inventory=inv_proj,
                    accounts_payable=ap_proj,
                    operating_nwc=op_nwc,
                    delta_operating_nwc=delta_op_nwc,
                    capex=capex,
                    capex_pct_revenue=capex_pct,
                    ufcf=ufcf,
                )
            )

            prev_revenue = rev
            prev_op_nwc = op_nwc

        # Summary Metrics
        last_forecast_rev = annual_forecasts[-1].revenue if annual_forecasts else base_revenue
        forecast_cagr = (
            ((last_forecast_rev / base_revenue) ** (1.0 / horizon) - 1.0) * 100.0
            if (base_revenue > 0 and horizon > 0 and last_forecast_rev > 0)
            else 0.0
        )
        avg_gm = sum(f.gross_margin for f in annual_forecasts) / horizon if horizon > 0 else 0.0
        avg_ebitda_m = sum(f.ebitda_margin for f in annual_forecasts) / horizon if horizon > 0 else 0.0
        avg_ebit_m = sum(f.ebit_margin for f in annual_forecasts) / horizon if horizon > 0 else 0.0
        total_ufcf = sum(f.ufcf for f in annual_forecasts)

        return ForecastResult(
            project_id=bundle.project_id,
            company_name=bundle.company_name,
            currency=bundle.reporting_currency,
            display_unit=bundle.display_unit,
            base_period_label=base_label,
            base_period_year=base_year,
            base_revenue=base_revenue,
            base_gross_profit=baselines.get("base_gross_profit"),
            base_ebitda=baselines.get("base_ebitda"),
            base_ebit=baselines.get("base_ebit"),
            base_operating_nwc=base_op_nwc,
            base_capex=baselines.get("base_capex"),
            base_cfo=baselines.get("base_cfo"),
            assumptions=assumptions,
            annual_forecasts=annual_forecasts,
            forecast_revenue_cagr=forecast_cagr,
            avg_gross_margin=avg_gm,
            avg_ebitda_margin=avg_ebitda_m,
            avg_ebit_margin=avg_ebit_m,
            total_projected_ufcf=total_ufcf,
            warnings=warnings,
        )
