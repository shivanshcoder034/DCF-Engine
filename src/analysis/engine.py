"""Historical financial analysis engine coordinating record ingestion, alignment, and metrics.

Processes stored FinancialDataPoint records, harmonizes scales and currencies,
detects duplicate conflicts, calculates multi-period metrics, and produces an auditable bundle.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import date
from typing import Any, Dict, List, Optional, Set, Tuple

import pandas as pd

from src.analysis.cash_flow import calculate_period_cash_flow_metrics
from src.analysis.metrics import (
    calculate_cagr,
    calculate_ebit_and_margin,
    calculate_ebitda_and_margin,
    calculate_effective_tax_rate,
    calculate_gross_profit_and_margin,
    calculate_growth,
    calculate_net_income_and_margin,
)
from src.analysis.models import (
    DataQualityIssue,
    FinancialPeriod,
    HistoricalAnalysisBundle,
    MetricResult,
)
from src.analysis.working_capital import calculate_period_working_capital
from src.data.models import FinancialDataPoint
from src.data.schemas import FinancialUnit
from src.data.services import FinancialDataService, ProjectService


class HistoricalAnalysisEngine:
    """Core analytical processor evaluating multi-period financial statements."""

    @classmethod
    def analyze_project(
        cls,
        project_id: int,
        period_type: str = "annual",
        data_classification: str = "reported_actual",
        selected_currency: Optional[str] = None,
    ) -> HistoricalAnalysisBundle:
        """Execute comprehensive historical financial analysis for a valuation project."""
        quality_issues: List[DataQualityIssue] = []

        project = ProjectService.get_project(project_id)
        if not project:
            raise ValueError(f"Valuation project with ID {project_id} not found.")

        comp_name = project.company.name if project.company else "Unknown Company"
        ticker = project.company.ticker if project.company else None
        base_currency = project.company.currency if project.company else "USD"

        # 1. Retrieve records through existing service layer
        raw_records = FinancialDataService.list_records(
            project_id=project_id,
            period_type=period_type,
            classification=data_classification,
        )

        if not raw_records:
            quality_issues.append(
                DataQualityIssue(
                    severity="info",
                    category="missing_data",
                    message=(
                        f"No {period_type} financial records found for classification '{data_classification}'. "
                        "Please enter or import financial statements to generate historical analysis."
                    ),
                )
            )
            return HistoricalAnalysisBundle(
                project_id=project_id,
                project_name=project.name,
                company_name=comp_name,
                ticker=ticker,
                reporting_currency=selected_currency or base_currency,
                display_unit="units",
                data_classification=data_classification,
                period_type=period_type,
                quality_issues=quality_issues,
            )

        # 2. Currency Validation and Consistency
        currencies_found = {r.currency.upper() for r in raw_records if r.currency}
        target_currency = selected_currency.upper() if selected_currency else None

        if not target_currency:
            # Pick dominant currency
            curr_counts = defaultdict(int)
            for r in raw_records:
                curr_counts[r.currency.upper()] += 1
            target_currency = max(curr_counts, key=curr_counts.get) if curr_counts else base_currency

        if len(currencies_found) > 1:
            quality_issues.append(
                DataQualityIssue(
                    severity="warning",
                    category="currency_inconsistency",
                    message=(
                        f"Multiple reporting currencies detected ({', '.join(currencies_found)}). "
                        f"Analysis is filtered strictly to '{target_currency}' to prevent invalid currency aggregation."
                    ),
                )
            )

        filtered_records = [r for r in raw_records if r.currency.upper() == target_currency]

        # 3. Unit Scale Harmonization (Normalize to base numerical units)
        # value * unit_multiplier
        normalized_data_points: List[Tuple[FinancialDataPoint, float]] = []
        for r in filtered_records:
            multiplier = FinancialUnit.multiplier(r.unit)
            base_value = r.value * multiplier
            normalized_data_points.append((r, base_value))

        # 4. Group by Reporting Period End Date
        periods_map: Dict[date, List[Tuple[FinancialDataPoint, float]]] = defaultdict(list)
        for r, val in normalized_data_points:
            periods_map[r.period_end_date].append((r, val))

        sorted_end_dates = sorted(periods_map.keys())

        # Construct FinancialPeriod objects
        financial_periods: List[FinancialPeriod] = []
        raw_items_by_period: Dict[str, Dict[str, float]] = {}

        for end_dt in sorted_end_dates:
            group = periods_map[end_dt]
            start_dt = min(r.period_start_date for r, _ in group)

            if period_type == "annual":
                label = f"FY{end_dt.year}"
            else:
                quarter_num = (end_dt.month - 1) // 3 + 1
                label = f"Q{quarter_num} {end_dt.year}"

            period_obj = FinancialPeriod(
                start_date=start_dt,
                end_date=end_dt,
                period_type=period_type,
                label=label,
            )
            financial_periods.append(period_obj)

            # Extract line items, handling potential conflicts
            items_dict: Dict[str, float] = {}
            conflicts_found: Dict[str, List[int]] = defaultdict(list)

            for r, val in group:
                if r.line_item_code in items_dict:
                    conflicts_found[r.line_item_code].append(r.id)
                items_dict[r.line_item_code] = val  # Latest record wins

            for code, ids in conflicts_found.items():
                quality_issues.append(
                    DataQualityIssue(
                        severity="warning",
                        category="conflict",
                        message=(
                            f"Multiple records for '{code}' in period ending {end_dt}. "
                            f"Resolved using most recently updated record. Duplicate IDs: {ids}."
                        ),
                        affected_periods=[label],
                        affected_items=[code],
                    )
                )

            raw_items_by_period[label] = items_dict

        # 5. Check for Period Gaps in Annual Data
        if period_type == "annual" and len(financial_periods) > 1:
            for idx in range(1, len(financial_periods)):
                prev_yr = financial_periods[idx - 1].end_date.year
                curr_yr = financial_periods[idx].end_date.year
                if curr_yr - prev_yr > 1:
                    quality_issues.append(
                        DataQualityIssue(
                            severity="warning",
                            category="period_alignment",
                            message=f"Gap detected in historical sequence between FY{prev_yr} and FY{curr_yr}.",
                            affected_periods=[financial_periods[idx - 1].label, financial_periods[idx].label],
                        )
                    )

        # 6. Check Accounting Balance Sheet Equilibrium
        for p in financial_periods:
            items = raw_items_by_period[p.label]
            total_assets = items.get("total_assets")
            total_liab = items.get("total_liabilities")
            total_eq = items.get("total_equity")

            if total_assets is not None and total_liab is not None and total_eq is not None:
                diff = total_assets - (total_liab + total_eq)
                if abs(diff) > 0.01 * abs(total_assets):
                    quality_issues.append(
                        DataQualityIssue(
                            severity="warning",
                            category="accounting_balance",
                            message=(
                                f"Balance Sheet does not balance for {p.label}: "
                                f"Assets ({total_assets:,.0f}) != Liabilities + Equity ({total_liab + total_eq:,.0f}). "
                                f"Difference: {diff:,.0f}."
                            ),
                            affected_periods=[p.label],
                        )
                    )

        # 7. Compute Historical Metrics across Periods
        metrics_by_period: Dict[str, Dict[str, MetricResult]] = {}
        working_capital_by_period = {}
        cash_flow_by_period = {}

        for idx, period in enumerate(financial_periods):
            p_label = period.label
            items = raw_items_by_period[p_label]
            p_metrics: Dict[str, MetricResult] = {}

            # Prior period data if available
            prior_period = financial_periods[idx - 1] if idx > 0 else None
            prior_items = raw_items_by_period[prior_period.label] if prior_period else None

            # Revenue & Revenue Growth
            rev = items.get("revenue")
            prior_rev = prior_items.get("revenue") if prior_items else None
            p_metrics["revenue"] = MetricResult(
                metric_code="revenue",
                metric_name="Revenue",
                value=rev,
                unit_or_type="currency",
                period_label=p_label,
                is_reported=True,
                source_line_items=["revenue"],
                status="reported" if rev is not None else "unavailable",
            )
            p_metrics["revenue_growth"] = calculate_growth(
                current=rev,
                previous=prior_rev,
                metric_code="revenue_growth",
                metric_name="Revenue Growth Rate",
                period_label=p_label,
            )

            # Gross Profit & Margin
            cogs = items.get("cogs")
            reported_gp = items.get("gross_profit")
            gp_m, gp_pct = calculate_gross_profit_and_margin(
                revenue=rev, cogs=cogs, reported_gp=reported_gp, period_label=p_label
            )
            p_metrics["gross_profit"] = gp_m
            p_metrics["gross_margin"] = gp_pct

            # EBITDA & Margin
            ebit = items.get("ebit")
            da = items.get("depreciation_amortization")
            reported_ebitda = items.get("ebitda")
            ebitda_m, ebitda_pct = calculate_ebitda_and_margin(
                revenue=rev, ebit=ebit, da=da, reported_ebitda=reported_ebitda, period_label=p_label
            )
            p_metrics["ebitda"] = ebitda_m
            p_metrics["ebitda_margin"] = ebitda_pct

            # EBIT & Margin
            ebit_m, ebit_pct = calculate_ebit_and_margin(revenue=rev, reported_ebit=ebit, period_label=p_label)
            p_metrics["ebit"] = ebit_m
            p_metrics["ebit_margin"] = ebit_pct

            # Net Income & Margin
            reported_ni = items.get("net_income")
            ni_m, ni_pct = calculate_net_income_and_margin(
                revenue=rev, reported_net_income=reported_ni, period_label=p_label
            )
            p_metrics["net_income"] = ni_m
            p_metrics["net_margin"] = ni_pct

            # Effective Tax Rate
            pbt = items.get("profit_before_tax")
            tax_exp = items.get("income_tax_expense")
            p_metrics["effective_tax_rate"] = calculate_effective_tax_rate(
                pbt=pbt, tax_expense=tax_exp, period_label=p_label
            )

            # Operating Expenses Analysis
            opex = items.get("operating_expenses")
            p_metrics["operating_expenses"] = MetricResult(
                metric_code="operating_expenses",
                metric_name="Operating Expenses",
                value=opex,
                unit_or_type="currency",
                period_label=p_label,
                is_reported=True,
                source_line_items=["operating_expenses"],
                status="reported" if opex is not None else "unavailable",
            )
            if opex is not None and rev is not None and rev > 0:
                p_metrics["opex_pct_revenue"] = MetricResult(
                    metric_code="opex_pct_revenue",
                    metric_name="OpEx % Revenue",
                    value=(opex / rev) * 100.0,
                    unit_or_type="percentage",
                    period_label=p_label,
                    status="calculated",
                )

            # D&A Analysis
            if da is not None and rev is not None and rev > 0:
                p_metrics["da_pct_revenue"] = MetricResult(
                    metric_code="da_pct_revenue",
                    metric_name="D&A % Revenue",
                    value=(abs(da) / rev) * 100.0,
                    unit_or_type="percentage",
                    period_label=p_label,
                    status="calculated",
                )

            # 8. Working Capital & Efficiency
            wc_metrics = calculate_period_working_capital(
                current_period=period,
                current_items=items,
                prior_period=prior_period,
                prior_items=prior_items,
            )
            working_capital_by_period[p_label] = wc_metrics

            # 9. Cash Flow & UFCF
            cf_metrics = calculate_period_cash_flow_metrics(
                current_period=period,
                current_items=items,
                delta_nwc=wc_metrics.delta_nwc,
            )
            cash_flow_by_period[p_label] = cf_metrics

            metrics_by_period[p_label] = p_metrics

        # 10. Multi-year CAGR Calculations (When at least 2 full periods exist)
        cagr_results: Dict[str, MetricResult] = {}
        if len(financial_periods) >= 2 and period_type == "annual":
            first_p = financial_periods[0]
            last_p = financial_periods[-1]
            num_years = (last_p.end_date - first_p.end_date).days / 365.25

            first_rev = raw_items_by_period[first_p.label].get("revenue")
            last_rev = raw_items_by_period[last_p.label].get("revenue")
            cagr_results["revenue_cagr"] = calculate_cagr(
                start_val=first_rev,
                end_val=last_rev,
                num_years=num_years,
                metric_code="revenue_cagr",
                metric_name=f"Revenue CAGR ({first_p.label} to {last_p.label})",
                period_label=f"{first_p.label} - {last_p.label}",
            )

            first_ebit = raw_items_by_period[first_p.label].get("ebit")
            last_ebit = raw_items_by_period[last_p.label].get("ebit")
            cagr_results["ebit_cagr"] = calculate_cagr(
                start_val=first_ebit,
                end_val=last_ebit,
                num_years=num_years,
                metric_code="ebit_cagr",
                metric_name=f"EBIT CAGR ({first_p.label} to {last_p.label})",
                period_label=f"{first_p.label} - {last_p.label}",
            )

        return HistoricalAnalysisBundle(
            project_id=project_id,
            project_name=project.name,
            company_name=comp_name,
            ticker=ticker,
            reporting_currency=target_currency,
            display_unit="units",
            data_classification=data_classification,
            period_type=period_type,
            periods=financial_periods,
            metrics_by_period=metrics_by_period,
            working_capital=working_capital_by_period,
            cash_flow_metrics=cash_flow_by_period,
            cagr_results=cagr_results,
            raw_line_items_by_period=raw_items_by_period,
            quality_issues=quality_issues,
        )
