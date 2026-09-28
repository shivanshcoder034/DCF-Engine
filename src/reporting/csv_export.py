"""CSV export generators for tabular financial data and valuation outputs.

Provides standardized, unambiguous CSV export routines for valuation summaries,
forecast schedules, historical financial statements, sensitivity matrices, and scenarios.
"""

from __future__ import annotations

import csv
import io
import logging
from typing import Optional

from src.reporting.models import ReportBundle

logger = logging.getLogger(__name__)


class CsvReportGenerator:
    """Generates structured CSV files for distinct valuation tables."""

    @classmethod
    def generate_valuation_summary_csv(cls, bundle: ReportBundle) -> str:
        """Export executive valuation summary and equity bridge as CSV."""
        buf = io.StringIO()
        writer = csv.writer(buf)

        meta = bundle.config.metadata
        writer.writerow(["REPORT / VALUATION SUMMARY"])
        writer.writerow(["Title", meta.title])
        writer.writerow(["Subtitle", meta.subtitle or ""])
        writer.writerow(["Company", bundle.company_name])
        writer.writerow(["Ticker", bundle.ticker or ""])
        writer.writerow(["Reporting Currency", meta.reporting_currency])
        writer.writerow(["Report Date", meta.report_date])
        writer.writerow(["Prepared By", meta.prepared_by or ""])
        writer.writerow([])

        dcf = bundle.dcf_result
        if dcf and dcf.is_complete:
            writer.writerow(["METRIC", "VALUE", "UNIT", "NOTES"])
            writer.writerow(["Enterprise Value", f"{dcf.enterprise_value:.2f}", f"{meta.reporting_currency} Millions", "PV Forecast UFCF + PV Terminal Value"])
            writer.writerow(["Less: Total Debt", f"{-dcf.bridge_inputs.debt_value:.2f}", f"{meta.reporting_currency} Millions", "Interest-bearing debt claim"])
            writer.writerow(["Plus: Cash & Equivalents", f"{dcf.bridge_inputs.cash_and_equivalents:.2f}", f"{meta.reporting_currency} Millions", "Liquid balance sheet cash"])
            writer.writerow(["Less: Minority Interest", f"{-dcf.bridge_inputs.minority_interest:.2f}", f"{meta.reporting_currency} Millions", "Non-controlling claims"])
            writer.writerow(["Less: Preferred Stock", f"{-dcf.bridge_inputs.preferred_equity:.2f}", f"{meta.reporting_currency} Millions", "Preferred equity claims"])
            writer.writerow(["Plus/Minus: Other Net Adjustments", f"{dcf.bridge_inputs.other_adjustments:.2f}", f"{meta.reporting_currency} Millions", "Other non-operating claims"])
            writer.writerow(["Equity Value", f"{dcf.equity_value:.2f}" if dcf.equity_value is not None else "N/A", f"{meta.reporting_currency} Millions", "Residual equity claim"])
            writer.writerow(["Diluted Common Shares", f"{dcf.diluted_shares:.2f}", "Millions of shares", "Share count divisor"])
            writer.writerow(["Implied Value per Share", f"{dcf.implied_share_price:.2f}" if dcf.implied_share_price is not None else "N/A", f"{meta.reporting_currency} / share", "Equity Value / Diluted Shares"])
            writer.writerow(["WACC (Discount Rate)", f"{dcf.wacc * 100.0:.2f}%" if dcf.wacc else "N/A", "Percentage", "Cost of Capital"])
            writer.writerow(["Terminal Value Method", dcf.terminal_inputs.method, "Method", ""])
            writer.writerow(["Perpetual Growth Rate (g)", f"{dcf.terminal_inputs.perpetual_growth_rate:.2f}%" if dcf.terminal_inputs.perpetual_growth_rate else "N/A", "Percentage", ""])
            writer.writerow(["Exit Multiple", f"{dcf.terminal_inputs.exit_multiple:.1f}x" if dcf.terminal_inputs.exit_multiple else "N/A", "Multiple", ""])
        else:
            writer.writerow(["Status", "DCF Valuation incomplete or unselected."])

        return buf.getvalue()

    @classmethod
    def generate_forecast_schedule_csv(cls, bundle: ReportBundle) -> str:
        """Export multi-year forecast schedule and UFCF derivations as CSV."""
        buf = io.StringIO()
        writer = csv.writer(buf)

        fc = bundle.forecast_result
        if not fc:
            writer.writerow(["Status", "Forecast Projections unselected or unavailable."])
            return buf.getvalue()

        writer.writerow(["FINANCIAL FORECAST & UFCF PROJECTIONS"])
        writer.writerow(["Company", bundle.company_name])
        writer.writerow(["Base Period", fc.base_period_label])
        writer.writerow(["Horizon", f"{len(fc.projected_years)} Years"])
        writer.writerow([])

        writer.writerow(["Line Item / Driver"] + fc.projected_years)
        writer.writerow(["Revenue"] + [f"{v:.2f}" for v in fc.revenue])
        writer.writerow(["Revenue Growth Rate (%)"] + [f"{v:.2f}%" for v in fc.revenue_growth_rate])
        writer.writerow(["Gross Profit"] + [f"{v:.2f}" for v in fc.gross_profit])
        writer.writerow(["Gross Profit Margin (%)"] + [f"{v:.2f}%" for v in fc.gross_profit_margin])
        writer.writerow(["EBITDA"] + [f"{v:.2f}" for v in fc.ebitda])
        writer.writerow(["EBITDA Margin (%)"] + [f"{v:.2f}%" for v in fc.ebitda_margin])
        writer.writerow(["Depreciation & Amortization"] + [f"{v:.2f}" for v in fc.depreciation_and_amortization])
        writer.writerow(["Operating Income (EBIT)"] + [f"{v:.2f}" for v in fc.ebit])
        writer.writerow(["Operating Margin (%)"] + [f"{v:.2f}%" for v in fc.ebit_margin])
        writer.writerow(["Effective Tax Rate (%)"] + [f"{v:.2f}%" for v in fc.effective_tax_rate])
        writer.writerow(["Tax on Operating Profit"] + [f"{v:.2f}" for v in fc.tax_expense])
        writer.writerow(["NOPAT (EBIT x (1 - t))"] + [f"{v:.2f}" for v in fc.nopat])
        writer.writerow(["(+) D&A"] + [f"{v:.2f}" for v in fc.depreciation_and_amortization])
        writer.writerow(["(-) CapEx"] + [f"{-v:.2f}" for v in fc.capex])
        writer.writerow(["(-) Change in Operating NWC"] + [f"{-v:.2f}" for v in fc.delta_operating_nwc])
        writer.writerow(["(=) Unlevered Free Cash Flow (UFCF)"] + [f"{v:.2f}" for v in fc.ufcf])

        return buf.getvalue()

    @classmethod
    def generate_historical_statements_csv(cls, bundle: ReportBundle) -> str:
        """Export multi-period historical statements as CSV."""
        buf = io.StringIO()
        writer = csv.writer(buf)

        hb = bundle.historical_bundle
        if not hb or not hb.periods:
            writer.writerow(["Status", "Historical statements unselected or unavailable."])
            return buf.getvalue()

        writer.writerow(["HISTORICAL FINANCIAL STATEMENTS"])
        writer.writerow(["Company", bundle.company_name])
        writer.writerow(["Currency", bundle.config.metadata.reporting_currency])
        writer.writerow(["Classification", hb.data_classification])
        writer.writerow([])

        periods = [p.label for p in hb.periods]
        writer.writerow(["Financial Metric / Line Item"] + periods)

        metric_codes = [
            ("Revenue", "revenue"),
            ("Revenue Growth YoY (%)", "revenue_growth_yoy"),
            ("Gross Profit", "gross_profit"),
            ("Gross Margin (%)", "gross_margin"),
            ("EBITDA", "ebitda"),
            ("EBITDA Margin (%)", "ebitda_margin"),
            ("Operating Income (EBIT)", "operating_income"),
            ("EBIT Margin (%)", "operating_margin"),
            ("Net Income", "net_income"),
            ("Operating Cash Flow", "operating_cash_flow"),
            ("CapEx", "capital_expenditures"),
            ("CFO Less CapEx", "cfo_less_capex"),
            ("UFCF Estimate", "ufcf_estimate"),
            ("Operating NWC", "operating_nwc"),
            ("Cash Conversion Cycle (days)", "cash_conversion_cycle"),
        ]

        for label, mcode in metric_codes:
            row = [label]
            for p in periods:
                val = None
                p_m = hb.metrics_by_period.get(p, {})
                if mcode in p_m:
                    val = p_m[mcode].value
                elif mcode in ("operating_nwc", "cash_conversion_cycle"):
                    wc = hb.working_capital.get(p)
                    if wc:
                        val = getattr(wc, mcode, None)
                elif mcode in ("operating_cash_flow", "capital_expenditures", "cfo_less_capex", "ufcf_estimate"):
                    cf = hb.cash_flow_metrics.get(p)
                    if cf:
                        val = getattr(cf, "capex_magnitude" if mcode == "capital_expenditures" else mcode, None)

                if val is not None:
                    row.append(f"{val:.2f}")
                else:
                    row.append("-")
            writer.writerow(row)

        return buf.getvalue()

    @classmethod
    def generate_sensitivity_matrix_csv(cls, bundle: ReportBundle) -> str:
        """Export 2D sensitivity matrix as CSV."""
        buf = io.StringIO()
        writer = csv.writer(buf)

        m = bundle.sensitivity_matrix_result
        if not m:
            writer.writerow(["Status", "Sensitivity matrix unselected or unavailable."])
            return buf.getvalue()

        writer.writerow([f"TWO-DIMENSIONAL SENSITIVITY MATRIX ({m.metric_label})"])
        writer.writerow(["Company", bundle.company_name])
        writer.writerow([])

        # Header row: WACC / Col Header
        col_headers = [f"WACC \\ {m.col_label}"] + [f"{c:.2f}%" if "%" in m.col_label else f"{c:.1f}x" for c in m.col_values]
        writer.writerow(col_headers)

        for r_idx, r_val in enumerate(m.row_values):
            row = [f"{r_val:.2f}%"]
            for c_idx in range(len(m.col_values)):
                cell = m.cells[r_idx][c_idx]
                if cell.is_valid and cell.output_value is not None:
                    marker = " *" if cell.is_baseline else ""
                    row.append(f"{cell.output_value:.2f}{marker}")
                else:
                    row.append("INVALID")
            writer.writerow(row)

        return buf.getvalue()

    @classmethod
    def generate_scenario_comparison_csv(cls, bundle: ReportBundle) -> str:
        """Export Base/Bull/Bear comparison table as CSV."""
        buf = io.StringIO()
        writer = csv.writer(buf)

        sc = bundle.scenario_result
        if not sc:
            writer.writerow(["Status", "Scenario analysis unselected or unavailable."])
            return buf.getvalue()

        writer.writerow(["SCENARIO ANALYSIS COMPARISON"])
        writer.writerow(["Company", bundle.company_name])
        writer.writerow([])

        writer.writerow(["Driver / Valuation Metric", "Base Case", "Bull Case", "Bear Case"])
        b, u, d = sc.base_case, sc.bull_case, sc.bear_case

        writer.writerow(["Revenue Growth Override (pp)", f"{b.revenue_growth_override_pp:+.2f}", f"{u.revenue_growth_override_pp:+.2f}", f"{d.revenue_growth_override_pp:+.2f}"])
        writer.writerow(["Operating Margin Override (pp)", f"{b.margin_override_pp:+.2f}", f"{u.margin_override_pp:+.2f}", f"{d.margin_override_pp:+.2f}"])
        writer.writerow(["WACC Adjustment (bps)", f"{b.wacc_adjustment_bps:+d}", f"{u.wacc_adjustment_bps:+d}", f"{d.wacc_adjustment_bps:+d}"])
        writer.writerow(["Effective WACC (%)", f"{b.effective_wacc:.2f}%", f"{u.effective_wacc:.2f}%", f"{d.effective_wacc:.2f}%"])
        writer.writerow(["Enterprise Value", f"{b.enterprise_value:.2f}" if b.enterprise_value else "N/A", f"{u.enterprise_value:.2f}" if u.enterprise_value else "N/A", f"{d.enterprise_value:.2f}" if d.enterprise_value else "N/A"])
        writer.writerow(["Equity Value", f"{b.equity_value:.2f}" if b.equity_value else "N/A", f"{u.equity_value:.2f}" if u.equity_value else "N/A", f"{d.equity_value:.2f}" if d.equity_value else "N/A"])
        writer.writerow(["Implied Share Price", f"{b.implied_share_price:.2f}" if b.implied_share_price else "N/A", f"{u.implied_share_price:.2f}" if u.implied_share_price else "N/A", f"{d.implied_share_price:.2f}" if d.implied_share_price else "N/A"])
        writer.writerow(["Upside / Downside (%)", "0.0%", f"{u.upside_downside_pct:+.1f}%" if u.upside_downside_pct else "N/A", f"{d.upside_downside_pct:+.1f}%" if d.upside_downside_pct else "N/A"])
        writer.writerow(["Status", b.status, u.status, d.status])

        return buf.getvalue()
