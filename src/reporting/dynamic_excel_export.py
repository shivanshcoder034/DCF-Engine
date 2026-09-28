"""Dynamic Excel Financial Model Generator using openpyxl.

Constructs an institutional-grade, multi-tab financial model workbook where
assumptions, financial statements, WACC estimations, DCF cash flow discounting,
and the Enterprise-to-Equity valuation bridge are interconnected via active Excel formulas.
"""

from __future__ import annotations

import io
import logging
from typing import Any, Dict, List, Optional, Tuple

import openpyxl
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

from src.dcf.models import DiscountingConvention, TerminalValueMethod
from src.reporting.models import ReportBundle

logger = logging.getLogger(__name__)

# Style constants for institutional financial modeling
NAVY_HEADER_FILL = PatternFill(start_color="1E3A8A", end_color="1E3A8A", fill_type="solid")
BLUE_SUBHEADER_FILL = PatternFill(start_color="2563EB", end_color="2563EB", fill_type="solid")
LIGHT_BLUE_FILL = PatternFill(start_color="EFF6FF", end_color="EFF6FF", fill_type="solid")
HIGHLIGHT_FILL = PatternFill(start_color="FEF3C7", end_color="FEF3C7", fill_type="solid")
INPUT_FILL = PatternFill(start_color="FFFBEB", end_color="FFFBEB", fill_type="solid")  # Cream/Yellow for user inputs
GRAY_FILL = PatternFill(start_color="F9FAFB", end_color="F9FAFB", fill_type="solid")

WHITE_BOLD_FONT = Font(name="Calibri", size=10, bold=True, color="FFFFFF")
TITLE_FONT = Font(name="Calibri", size=15, bold=True, color="1E3A8A")
SECTION_FONT = Font(name="Calibri", size=11, bold=True, color="1E3A8A")
BOLD_FONT = Font(name="Calibri", size=10, bold=True, color="111827")
REGULAR_FONT = Font(name="Calibri", size=10, color="1F2937")
MUTED_FONT = Font(name="Calibri", size=9, italic=True, color="6B7280")
INPUT_FONT = Font(name="Calibri", size=10, bold=True, color="1E40AF")  # Blue bold for inputs
KEY_METRIC_FONT = Font(name="Calibri", size=11, bold=True, color="1E3A8A")

THIN_SIDE = Side(border_style="thin", color="D1D5DB")
THICK_NAVY_SIDE = Side(border_style="medium", color="1E3A8A")
DOUBLE_BOTTOM_SIDE = Side(border_style="double", color="111827")
INPUT_SIDE = Side(border_style="thin", color="93C5FD")

STANDARD_BORDER = Border(left=THIN_SIDE, right=THIN_SIDE, top=THIN_SIDE, bottom=THIN_SIDE)
HEADER_BORDER = Border(left=THIN_SIDE, right=THIN_SIDE, top=THIN_SIDE, bottom=THICK_NAVY_SIDE)
TOTAL_BORDER = Border(top=THIN_SIDE, bottom=DOUBLE_BOTTOM_SIDE)
INPUT_BORDER = Border(left=INPUT_SIDE, right=INPUT_SIDE, top=INPUT_SIDE, bottom=INPUT_SIDE)

ALIGN_LEFT = Alignment(horizontal="left", vertical="center")
ALIGN_RIGHT = Alignment(horizontal="right", vertical="center")
ALIGN_CENTER = Alignment(horizontal="center", vertical="center")


def _autofit_columns(ws: openpyxl.worksheet.worksheet.Worksheet, min_width: int = 14, max_width: int = 42) -> None:
    """Adjust worksheet column widths according to content length while ignoring formulas."""
    for col in ws.columns:
        col_letter = get_column_letter(col[0].column)
        max_len = 0
        for cell in col:
            val_str = str(cell.value or "")
            if len(val_str) > max_len and not val_str.startswith("="):
                max_len = len(val_str)
        ws.column_dimensions[col_letter].width = max(min(max_len + 3, max_width), min_width)


class DynamicExcelModelGenerator:
    """Orchestrates generation of formula-linked multi-sheet financial model workbooks."""

    @classmethod
    def generate_workbook(cls, bundle: ReportBundle) -> bytes:
        """Build and return an Excel workbook with live formula linking as bytes."""
        wb = openpyxl.Workbook()
        # Enable full calculation on workbook load in Excel / spreadsheet software
        wb.calculation.fullCalcOnLoad = True

        # Remove default empty sheet
        wb.remove(wb.active)

        # Coordinate registry tracking cell locations across sheets for formula references
        coords: Dict[str, Any] = {}

        # 1. Read Me & Model Guide
        cls._build_readme_sheet(wb, bundle)

        # 2. Historical Financials
        if bundle.historical_bundle and bundle.historical_bundle.periods:
            cls._build_historical_sheet(wb, bundle, coords)

        # 3. Assumptions (Editable Inputs)
        cls._build_assumptions_sheet(wb, bundle, coords)

        # 4. Forecast Projections (Formula-linked to Assumptions & Historicals)
        if bundle.forecast_result:
            cls._build_forecast_sheet(wb, bundle, coords)

        # 5. WACC Analysis (Formula-linked to Assumptions)
        if bundle.wacc_result:
            cls._build_wacc_sheet(wb, bundle, coords)

        # 6. DCF Valuation & Equity Bridge (Formula-linked to Forecast, WACC, and Assumptions)
        if bundle.dcf_result:
            cls._build_dcf_sheet(wb, bundle, coords)

        # 7. Scenario Analysis (Saved cases and comparisons)
        if bundle.scenario_result:
            cls._build_scenarios_sheet(wb, bundle, coords)

        # 8. Sensitivity & Simulation (Saved matrices and Monte Carlo)
        if bundle.sensitivity_matrix_result or bundle.monte_carlo_result:
            cls._build_sensitivity_sheet(wb, bundle)

        # Fallback if no sheets created
        if not wb.sheetnames:
            ws = wb.create_sheet(title="Model Overview")
            ws["A1"] = "No financial model components were available for export."

        buf = io.BytesIO()
        wb.save(buf)
        buf.seek(0)
        return buf.getvalue()

    @classmethod
    def _build_readme_sheet(cls, wb: openpyxl.Workbook, bundle: ReportBundle) -> None:
        """Create Read Me, Model Architecture Guide, and Formatting Legend sheet."""
        ws = wb.create_sheet(title="Read Me & Guide")
        ws.views.sheetView[0].showGridLines = True

        meta = bundle.config.metadata

        # Title Block
        ws["A1"] = meta.title
        ws["A1"].font = TITLE_FONT
        ws["A2"] = "Dynamic Formula-Linked Financial Model & DCF Valuation Engine"
        ws["A2"].font = MUTED_FONT

        # Model Scope & Metadata Table
        row = 4
        ws.cell(row=row, column=1, value="MODEL IDENTIFIERS & METADATA").font = SECTION_FONT
        row += 1

        info_rows = [
            ("Company Target:", f"{bundle.company_name} ({bundle.ticker or 'N/A'})"),
            ("Valuation Project:", meta.project_name or f"Project #{bundle.project_id}"),
            ("Model Currency & Units:", f"{meta.reporting_currency} (in Millions, except per-share values)"),
            ("Fiscal Year End:", meta.fiscal_year_end),
            ("Generation Date:", meta.report_date),
            ("Prepared By:", meta.prepared_by or "Financial Modeling Analyst"),
            ("Excel Recalculation Mode:", "Active (fullCalcOnLoad = True)"),
        ]

        for label, val in info_rows:
            ws.cell(row=row, column=1, value=label).font = BOLD_FONT
            ws.cell(row=row, column=2, value=val).font = REGULAR_FONT
            row += 1

        row += 1

        # Formatting & Cell Legend
        ws.cell(row=row, column=1, value="CELL FORMATTING & INTERACTIVITY CONVENTIONS").font = SECTION_FONT
        row += 1

        headers = ["Cell Style / Fill", "Classification", "Description & Usage"]
        for col_idx, h in enumerate(headers, start=1):
            cell = ws.cell(row=row, column=col_idx, value=h)
            cell.font = WHITE_BOLD_FONT
            cell.fill = NAVY_HEADER_FILL
            cell.border = HEADER_BORDER
        row += 1

        legend_items = [
            ("Light Cream / Blue Text", INPUT_FILL, INPUT_FONT, "User-Editable Input", "Change these values to run sensitivity scenarios directly in Microsoft Excel."),
            ("White / Standard Font", None, REGULAR_FONT, "Formula-Linked Output", "Dynamic formula cells (=SUM, =NPV, =PRODUCT). Do not overwrite directly."),
            ("Light Blue Fill", LIGHT_BLUE_FILL, BOLD_FONT, "Subtotal / Schedule Total", "Key accounting and financial statement totals linking upstream steps."),
            ("Amber Highlight Fill", HIGHLIGHT_FILL, KEY_METRIC_FONT, "Key Valuation Output", "Headline intrinsic results: Enterprise Value, Equity Value, Implied Share Price."),
            ("Light Gray Fill", GRAY_FILL, MUTED_FONT, "Historical / Contextual Data", "Reported historical actuals and benchmark proxy references."),
        ]

        for sample_text, fill, font, category, desc in legend_items:
            c1 = ws.cell(row=row, column=1, value=sample_text)
            c1.font = font
            if fill:
                c1.fill = fill
            c1.border = STANDARD_BORDER

            c2 = ws.cell(row=row, column=2, value=category)
            c2.font = BOLD_FONT
            c2.border = STANDARD_BORDER

            c3 = ws.cell(row=row, column=3, value=desc)
            c3.font = REGULAR_FONT
            c3.border = STANDARD_BORDER
            row += 1

        row += 2

        # Sheet Flow & Formula Architecture
        ws.cell(row=row, column=1, value="MODEL SHEET ARCHITECTURE & DYNAMIC FLOW").font = SECTION_FONT
        row += 1

        flow_headers = ["Sheet Name", "Core Purpose", "Primary Upstream Inputs", "Downstream Dependencies"]
        for col_idx, h in enumerate(flow_headers, start=1):
            cell = ws.cell(row=row, column=col_idx, value=h)
            cell.font = WHITE_BOLD_FONT
            cell.fill = BLUE_SUBHEADER_FILL
            cell.border = HEADER_BORDER
        row += 1

        sheets_guide = [
            ("1. Historical Financials", "Multi-period reported actuals & ratios", "Company database records", "Forecast baseline (Year 0 anchor)"),
            ("2. Assumptions", "Centralized, editable drivers & parameters", "Model defaults & user calibration", "Forecast, WACC, and DCF Valuation"),
            ("3. Forecast", "Dynamic multi-year statement & UFCF schedule", "Assumptions & Historicals", "DCF Cash Flow Discounting Schedule"),
            ("4. WACC", "CAPM, Cost of Debt & Capital Weighting", "Assumptions (Rf, Beta, ERP, Debt)", "DCF Discount Rate Reference"),
            ("5. DCF Valuation", "Discounting, Terminal Value & Equity Bridge", "Forecast (UFCF), WACC, Assumptions", "Enterprise Value & Share Price Target"),
            ("6. Scenario Analysis", "Base, Bull, Bear case comparisons", "Saved scenario model records", "Comparative valuation benchmarks"),
            ("7. Sensitivity & Simulation", "2D parameter matrix & Monte Carlo", "Saved sensitivity configurations", "Probabilistic risk distribution"),
        ]

        for s_name, s_purpose, s_up, s_down in sheets_guide:
            ws.cell(row=row, column=1, value=s_name).font = BOLD_FONT
            ws.cell(row=row, column=2, value=s_purpose).font = REGULAR_FONT
            ws.cell(row=row, column=3, value=s_up).font = REGULAR_FONT
            ws.cell(row=row, column=4, value=s_down).font = REGULAR_FONT
            for c in range(1, 5):
                ws.cell(row=row, column=c).border = STANDARD_BORDER
            row += 1

        row += 2

        # Recalculation Notice
        ws.cell(row=row, column=1, value="IMPORTANT RECALCULATION & USAGE NOTICE").font = SECTION_FONT
        row += 1

        notices = [
            "1. Spreadsheet Software Calculation: This workbook contains active Excel formulas linking assumptions to outputs. Formulas are evaluated when opened in Microsoft Excel, LibreOffice Calc, or Google Sheets.",
            "2. Non-Circular Structure: Cash flow discounting and WACC weighting are structured without circular dependencies to ensure stable, immediate re-evaluation.",
            "3. Analytical Purpose Only: All valuation conclusions are conditional upon user assumptions and historical data. This model does not constitute certified investment advice.",
        ]
        for note in notices:
            ws.cell(row=row, column=1, value=note).font = MUTED_FONT
            row += 1

        _autofit_columns(ws, min_width=16, max_width=48)

    @classmethod
    def _build_historical_sheet(cls, wb: openpyxl.Workbook, bundle: ReportBundle, coords: Dict[str, Any]) -> None:
        """Create historical financial statements sheet and record anchor cell coordinates."""
        ws = wb.create_sheet(title="Historical Financials")
        ws.views.sheetView[0].showGridLines = True
        hbundle = bundle.historical_bundle
        if not hbundle:
            return

        meta = bundle.config.metadata
        ws["A1"] = f"{bundle.company_name} — Historical Financial Analysis"
        ws["A1"].font = TITLE_FONT
        ws["A2"] = f"Reporting Currency: {meta.reporting_currency} | Frequency: {hbundle.period_type.title()} | Classification: {hbundle.data_classification}"
        ws["A2"].font = MUTED_FONT

        row = 4
        periods = [p.label for p in hbundle.periods]
        headers = ["Financial Metric / Line Item", "Unit"] + periods

        for col_idx, h in enumerate(headers, start=1):
            cell = ws.cell(row=row, column=col_idx, value=h)
            cell.font = WHITE_BOLD_FONT
            cell.fill = NAVY_HEADER_FILL
            cell.alignment = ALIGN_LEFT if col_idx <= 2 else ALIGN_RIGHT
            cell.border = HEADER_BORDER
        row += 1

        items = [
            ("Revenue", "revenue", f"{meta.reporting_currency} M", "$#,##0.0"),
            ("Revenue Growth (%)", "revenue_growth", "%", "0.0%"),
            ("Gross Profit", "gross_profit", f"{meta.reporting_currency} M", "$#,##0.0"),
            ("Gross Profit Margin (%)", "gross_margin", "%", "0.0%"),
            ("EBITDA", "ebitda", f"{meta.reporting_currency} M", "$#,##0.0"),
            ("EBITDA Margin (%)", "ebitda_margin", "%", "0.0%"),
            ("Operating Income (EBIT)", "ebit", f"{meta.reporting_currency} M", "$#,##0.0"),
            ("Operating Margin (%)", "ebit_margin", "%", "0.0%"),
            ("Net Income", "net_income", f"{meta.reporting_currency} M", "$#,##0.0"),
            ("Operating Cash Flow (CFO)", "operating_cash_flow", f"{meta.reporting_currency} M", "$#,##0.0"),
            ("Capital Expenditures (CapEx)", "capital_expenditures", f"{meta.reporting_currency} M", "$#,##0.0"),
            ("CapEx % of Revenue", "capex_pct_revenue", "%", "0.0%"),
            ("CFO Less CapEx", "cfo_less_capex", f"{meta.reporting_currency} M", "$#,##0.0"),
            ("Historical UFCF Estimate", "ufcf_estimate", f"{meta.reporting_currency} M", "$#,##0.0"),
            ("Operating Net Working Capital (NWC)", "operating_nwc", f"{meta.reporting_currency} M", "$#,##0.0"),
            ("Days Sales Outstanding (DSO)", "dso", "Days", "0.0"),
            ("Days Inventory Outstanding (DIO)", "dio", "Days", "0.0"),
            ("Days Payables Outstanding (DPO)", "dpo", "Days", "0.0"),
            ("Cash Conversion Cycle (CCC)", "cash_conversion_cycle", "Days", "0.0"),
        ]

        # Record anchor column (latest historical period)
        latest_col_idx = len(periods) + 2
        latest_col_letter = get_column_letter(latest_col_idx)

        for label, metric_code, unit_str, num_fmt in items:
            ws.cell(row=row, column=1, value=label).font = BOLD_FONT if "Revenue" in label or "EBITDA" in label or "UFCF" in label else REGULAR_FONT
            ws.cell(row=row, column=1).border = STANDARD_BORDER

            ws.cell(row=row, column=2, value=unit_str).font = MUTED_FONT
            ws.cell(row=row, column=2).alignment = ALIGN_CENTER
            ws.cell(row=row, column=2).border = STANDARD_BORDER

            # Record row coordinates for the latest anchor period
            if metric_code == "revenue":
                coords["hist_anchor_rev"] = f"'Historical Financials'!{latest_col_letter}{row}"
            elif metric_code == "operating_nwc":
                coords["hist_anchor_nwc"] = f"'Historical Financials'!{latest_col_letter}{row}"
            elif metric_code == "ebitda":
                coords["hist_anchor_ebitda"] = f"'Historical Financials'!{latest_col_letter}{row}"

            for p_idx, p_label in enumerate(periods, start=3):
                cell = ws.cell(row=row, column=p_idx)
                cell.border = STANDARD_BORDER
                cell.alignment = ALIGN_RIGHT

                val = None
                p_metrics = hbundle.metrics_by_period.get(p_label, {})
                raw_items = hbundle.raw_line_items_by_period.get(p_label, {})

                if metric_code in p_metrics and p_metrics[metric_code].value is not None:
                    val = p_metrics[metric_code].value
                elif metric_code in raw_items and raw_items[metric_code] is not None:
                    val = raw_items[metric_code]
                elif metric_code in ("dso", "dio", "dpo", "cash_conversion_cycle", "operating_nwc"):
                    wc = hbundle.working_capital.get(p_label)
                    if wc:
                        val = getattr(wc, metric_code, None)
                elif metric_code in ("operating_cash_flow", "capital_expenditures", "cfo_less_capex", "ufcf_estimate", "capex_pct_revenue"):
                    cf = hbundle.cash_flow_metrics.get(p_label)
                    if cf:
                        val = cf.capex_magnitude if metric_code == "capital_expenditures" else getattr(cf, metric_code, None)

                if val is not None:
                    # Scale monetary values to millions if necessary
                    if num_fmt == "$#,##0.0" and abs(val) > 100_000.0:
                        val = val / 1_000_000.0
                    elif num_fmt == "0.0%" and abs(val) > 1.0:
                        val = val / 100.0
                    cell.value = float(val)
                    cell.number_format = num_fmt
                    cell.font = REGULAR_FONT
                else:
                    cell.value = "-"
                    cell.font = MUTED_FONT

            row += 1

        _autofit_columns(ws)

    @classmethod
    def _build_assumptions_sheet(cls, wb: openpyxl.Workbook, bundle: ReportBundle, coords: Dict[str, Any]) -> None:
        """Create centralized, user-editable assumptions sheet."""
        ws = wb.create_sheet(title="Assumptions")
        ws.views.sheetView[0].showGridLines = True

        meta = bundle.config.metadata
        ws["A1"] = f"{bundle.company_name} — Valuation Assumptions & Driver Control Center"
        ws["A1"].font = TITLE_FONT
        ws["A2"] = "Edit highlighted cream cells to dynamically update Forecast, WACC, and DCF Valuation models."
        ws["A2"].font = MUTED_FONT

        fc_assump = bundle.forecast_assumptions
        wacc_assump = bundle.wacc_assumptions
        dcf_assump = bundle.dcf_assumptions

        row = 4

        # =====================================================================
        # Section A: Multi-Year Forecast Drivers
        # =====================================================================
        ws.cell(row=row, column=1, value="A. FORWARD-LOOKING OPERATIONAL DRIVERS (EDITABLE)").font = SECTION_FONT
        row += 1

        horizon = len(fc_assump.revenue_growth_rates) if fc_assump else 5
        forecast_cols = [f"Year {i}" for i in range(1, horizon + 1)]
        headers = ["Operational Driver / Rate", "Input Basis"] + forecast_cols + ["Driver Provenance"]

        for col_idx, h in enumerate(headers, start=1):
            cell = ws.cell(row=row, column=col_idx, value=h)
            cell.font = WHITE_BOLD_FONT
            cell.fill = NAVY_HEADER_FILL
            cell.border = HEADER_BORDER
            cell.alignment = ALIGN_LEFT if col_idx <= 2 else ALIGN_CENTER
        row += 1

        driver_configs = [
            ("Revenue Growth Rate (%)", "Annual %", fc_assump.revenue_growth_rates if fc_assump else [5.0] * 5, "0.0%", True, "rev_growth"),
            ("Gross Profit Margin (%)", "% of Revenue", fc_assump.gross_margin_rates if fc_assump else [40.0] * 5, "0.0%", True, "gross_margin"),
            ("Operating Expenses (% Rev)", "% of Revenue", fc_assump.opex_pct_rates if fc_assump else [20.0] * 5, "0.0%", True, "opex_pct"),
            ("D&A Expense (% Rev)", "% of Revenue", fc_assump.da_pct_rates if fc_assump else [4.0] * 5, "0.0%", True, "da_pct"),
            ("Capital Expenditures (% Rev)", "% of Revenue", fc_assump.capex_pct_rates if fc_assump else [5.0] * 5, "0.0%", True, "capex_pct"),
            ("Operating NWC (% Rev)", "% of Revenue", fc_assump.nwc_pct_revenue if fc_assump else [10.0] * 5, "0.0%", True, "nwc_pct"),
        ]

        coords["assump_drivers"] = {}

        for label, basis, rates, num_fmt, is_pct, key in driver_configs:
            ws.cell(row=row, column=1, value=label).font = BOLD_FONT
            ws.cell(row=row, column=1).border = STANDARD_BORDER

            ws.cell(row=row, column=2, value=basis).font = MUTED_FONT
            ws.cell(row=row, column=2).alignment = ALIGN_CENTER
            ws.cell(row=row, column=2).border = STANDARD_BORDER

            coords["assump_drivers"][key] = {}

            for yr_idx in range(horizon):
                col_idx = 3 + yr_idx
                col_letter = get_column_letter(col_idx)
                cell = ws.cell(row=row, column=col_idx)

                rate_val = rates[yr_idx] if yr_idx < len(rates) else 5.0
                cell.value = (rate_val / 100.0) if is_pct else rate_val
                cell.number_format = num_fmt
                cell.fill = INPUT_FILL
                cell.font = INPUT_FONT
                cell.border = INPUT_BORDER
                cell.alignment = ALIGN_RIGHT

                # Store coordinate
                coords["assump_drivers"][key][yr_idx + 1] = f"'Assumptions'!{col_letter}{row}"

            prov_col = 3 + horizon
            ws.cell(row=row, column=prov_col, value="Calibrated from Historical Baseline" if fc_assump else "Application Default").font = MUTED_FONT
            ws.cell(row=row, column=prov_col).border = STANDARD_BORDER
            row += 1

        # Effective Corporate Tax Rate
        tax_rate_val = (fc_assump.tax_rate / 100.0) if fc_assump else 0.25
        ws.cell(row=row, column=1, value="Effective Tax Rate on EBIT (%)").font = BOLD_FONT
        ws.cell(row=row, column=1).border = STANDARD_BORDER
        ws.cell(row=row, column=2, value="Corporate Rate").font = MUTED_FONT
        ws.cell(row=row, column=2).alignment = ALIGN_CENTER
        ws.cell(row=row, column=2).border = STANDARD_BORDER

        tax_cell = ws.cell(row=row, column=3, value=tax_rate_val)
        tax_cell.number_format = "0.0%"
        tax_cell.fill = INPUT_FILL
        tax_cell.font = INPUT_FONT
        tax_cell.border = INPUT_BORDER
        tax_cell.alignment = ALIGN_RIGHT
        coords["tax_rate_cell"] = f"'Assumptions'!C{row}"

        for yr_idx in range(1, horizon):
            c_fill = ws.cell(row=row, column=3 + yr_idx, value="=C" + str(row))
            c_fill.number_format = "0.0%"
            c_fill.font = FORMULA_FONT
            c_fill.border = STANDARD_BORDER
            c_fill.alignment = ALIGN_RIGHT

        ws.cell(row=row, column=3 + horizon, value="Forecast statutory tax assumption").font = MUTED_FONT
        ws.cell(row=row, column=3 + horizon).border = STANDARD_BORDER
        row += 2

        # =====================================================================
        # Section B: WACC & Cost of Capital Parameters
        # =====================================================================
        ws.cell(row=row, column=1, value="B. COST OF CAPITAL (WACC) PARAMETERS (EDITABLE)").font = SECTION_FONT
        row += 1

        wacc_headers = ["Parameter / Capital Driver", "Value", "Unit", "Benchmark Source & Notes"]
        for col_idx, h in enumerate(wacc_headers, start=1):
            cell = ws.cell(row=row, column=col_idx, value=h)
            cell.font = WHITE_BOLD_FONT
            cell.fill = NAVY_HEADER_FILL
            cell.border = HEADER_BORDER
        row += 1

        # Fallback values from bundle or default
        eq_in = wacc_assump.equity_inputs if wacc_assump else None
        debt_in = wacc_assump.debt_inputs if wacc_assump else None
        cap_in = wacc_assump.capital_inputs if wacc_assump else None
        tax_in = wacc_assump.tax_inputs if wacc_assump else None

        rf_val = (eq_in.risk_free_rate / 100.0) if eq_in and eq_in.risk_free_rate is not None else 0.0425
        beta_val = eq_in.equity_beta if eq_in and eq_in.equity_beta is not None else 1.00
        erp_val = (eq_in.equity_risk_premium / 100.0) if eq_in and eq_in.equity_risk_premium is not None else 0.0500
        kd_val = (debt_in.pre_tax_cost_of_debt / 100.0) if debt_in and debt_in.pre_tax_cost_of_debt is not None else 0.0550
        wacc_tax_val = (tax_in.tax_rate / 100.0) if tax_in and tax_in.tax_rate is not None else 0.2100

        # Capital amounts in millions
        eq_amt = (cap_in.equity_value / 1_000_000.0) if cap_in and cap_in.equity_value else 10_000.0
        debt_amt = (cap_in.debt_value / 1_000_000.0) if cap_in and cap_in.debt_value else 2_500.0

        wacc_input_rows = [
            ("Risk-Free Rate (Rf)", rf_val, "0.00%", "Percentage", "10-Year Benchmark Treasury Yield Proxy", "rf"),
            ("Equity Beta (β)", beta_val, "0.00x", "Multiple", "Systematic risk exposure parameter", "beta"),
            ("Equity Risk Premium (ERP)", erp_val, "0.00%", "Percentage", "Expected long-term equity market return spread", "erp"),
            ("Pre-Tax Cost of Debt (Kd)", kd_val, "0.00%", "Percentage", "Corporate borrowing yield / spread", "kd"),
            ("Marginal Corporate Tax Rate (t)", wacc_tax_val, "0.00%", "Percentage", "Interest tax shield deduction rate", "wacc_tax"),
            ("Market Value of Equity (E)", eq_amt, "$#,##0.0", f"{meta.reporting_currency} Millions", "Market capitalization or equity base", "equity_val"),
            ("Total Interest-Bearing Debt (D)", debt_amt, "$#,##0.0", f"{meta.reporting_currency} Millions", "Short-term borrowings + long-term debt", "debt_val"),
        ]

        for label, val, num_fmt, unit_str, notes, key in wacc_input_rows:
            ws.cell(row=row, column=1, value=label).font = BOLD_FONT
            ws.cell(row=row, column=1).border = STANDARD_BORDER

            cell = ws.cell(row=row, column=2, value=val)
            cell.number_format = num_fmt
            cell.fill = INPUT_FILL
            cell.font = INPUT_FONT
            cell.border = INPUT_BORDER
            cell.alignment = ALIGN_RIGHT
            coords[f"assump_{key}"] = f"'Assumptions'!B{row}"

            ws.cell(row=row, column=3, value=unit_str).font = MUTED_FONT
            ws.cell(row=row, column=3).alignment = ALIGN_CENTER
            ws.cell(row=row, column=3).border = STANDARD_BORDER

            ws.cell(row=row, column=4, value=notes).font = MUTED_FONT
            ws.cell(row=row, column=4).border = STANDARD_BORDER
            row += 1

        row += 1

        # =====================================================================
        # Section C: Terminal Value Settings & DCF Timing
        # =====================================================================
        ws.cell(row=row, column=1, value="C. TERMINAL VALUE SETTINGS & DCF CONVENTIONS").font = SECTION_FONT
        row += 1

        term_method = dcf_assump.terminal_inputs.method if dcf_assump else TerminalValueMethod.GORDON_GROWTH.value
        g_val = (dcf_assump.terminal_inputs.perpetual_growth_rate / 100.0) if dcf_assump and dcf_assump.terminal_inputs.perpetual_growth_rate else 0.025
        mult_val = dcf_assump.terminal_inputs.exit_multiple if dcf_assump and dcf_assump.terminal_inputs.exit_multiple else 10.0
        timing_val = dcf_assump.discounting_convention if dcf_assump else DiscountingConvention.END_OF_YEAR.value

        dcf_input_rows = [
            ("Terminal Value Methodology", term_method.replace("_", " ").title(), "@", "Method", "Gordon Growth Perpetuity or Exit Multiple", "term_method"),
            ("Terminal Perpetual Growth Rate (g)", g_val, "0.00%", "Percentage", "Long-term perpetual growth rate (Gordon Growth)", "term_g"),
            ("Terminal Exit Multiple (EV/EBITDA)", mult_val, "0.0x", "Multiple", "Exit multiple applied to terminal EBITDA", "term_mult"),
            ("Cash Flow Timing Convention", timing_val.replace("_", " ").title(), "@", "Convention", "End-of-Year (t = 1.0) or Mid-Year (t = 0.5)", "timing"),
        ]

        for label, val, num_fmt, unit_str, notes, key in dcf_input_rows:
            ws.cell(row=row, column=1, value=label).font = BOLD_FONT
            ws.cell(row=row, column=1).border = STANDARD_BORDER

            cell = ws.cell(row=row, column=2, value=val)
            cell.number_format = num_fmt
            cell.fill = INPUT_FILL
            cell.font = INPUT_FONT
            cell.border = INPUT_BORDER
            cell.alignment = ALIGN_RIGHT
            coords[f"assump_{key}"] = f"'Assumptions'!B{row}"

            ws.cell(row=row, column=3, value=unit_str).font = MUTED_FONT
            ws.cell(row=row, column=3).alignment = ALIGN_CENTER
            ws.cell(row=row, column=3).border = STANDARD_BORDER

            ws.cell(row=row, column=4, value=notes).font = MUTED_FONT
            ws.cell(row=row, column=4).border = STANDARD_BORDER
            row += 1

        row += 1

        # =====================================================================
        # Section D: Enterprise-to-Equity Bridge Inputs
        # =====================================================================
        ws.cell(row=row, column=1, value="D. ENTERPRISE-TO-EQUITY BRIDGE ADJUSTMENTS").font = SECTION_FONT
        row += 1

        b_in = dcf_assump.bridge_inputs if dcf_assump else None
        cash_val = (b_in.cash_and_equivalents / 1_000_000.0) if b_in and b_in.cash_and_equivalents else 500.0
        debt_b_val = (b_in.debt_value / 1_000_000.0) if b_in and b_in.debt_value else 2_500.0
        min_val = (b_in.minority_interest / 1_000_000.0) if b_in and b_in.minority_interest else 0.0
        pref_val = (b_in.preferred_equity / 1_000_000.0) if b_in and b_in.preferred_equity else 0.0
        other_val = (b_in.other_adjustments / 1_000_000.0) if b_in and b_in.other_adjustments else 0.0
        shares_val = (dcf_assump.diluted_shares / 1_000_000.0) if dcf_assump and dcf_assump.diluted_shares else 100.0

        bridge_inputs_config = [
            ("(+) Cash & Cash Equivalents", cash_val, "$#,##0.0", f"{meta.reporting_currency} Millions", "Liquid non-operating balances", "cash"),
            ("(-) Interest-Bearing Debt", debt_b_val, "$#,##0.0", f"{meta.reporting_currency} Millions", "Short-term + Long-term debt claims", "debt"),
            ("(-) Minority Interest", min_val, "$#,##0.0", f"{meta.reporting_currency} Millions", "Non-controlling equity claims in subs", "minority"),
            ("(-) Preferred Stock Equity", pref_val, "$#,##0.0", f"{meta.reporting_currency} Millions", "Senior preferred non-common claims", "pref"),
            ("(+/-) Other Net Adjustments", other_val, "$#,##0.0", f"{meta.reporting_currency} Millions", "Non-operating investments or liabilities", "other"),
            ("Diluted Common Shares Outstanding", shares_val, "#,##0.0", "Millions of shares", "Common share base for per-share price", "shares"),
        ]

        for label, val, num_fmt, unit_str, notes, key in bridge_inputs_config:
            ws.cell(row=row, column=1, value=label).font = BOLD_FONT
            ws.cell(row=row, column=1).border = STANDARD_BORDER

            cell = ws.cell(row=row, column=2, value=val)
            cell.number_format = num_fmt
            cell.fill = INPUT_FILL
            cell.font = INPUT_FONT
            cell.border = INPUT_BORDER
            cell.alignment = ALIGN_RIGHT
            coords[f"assump_{key}"] = f"'Assumptions'!B{row}"

            ws.cell(row=row, column=3, value=unit_str).font = MUTED_FONT
            ws.cell(row=row, column=3).alignment = ALIGN_CENTER
            ws.cell(row=row, column=3).border = STANDARD_BORDER

            ws.cell(row=row, column=4, value=notes).font = MUTED_FONT
            ws.cell(row=row, column=4).border = STANDARD_BORDER
            row += 1

        _autofit_columns(ws)

    @classmethod
    def _build_forecast_sheet(cls, wb: openpyxl.Workbook, bundle: ReportBundle, coords: Dict[str, Any]) -> None:
        """Create multi-year forecast statement and UFCF schedule driven by live Excel formulas."""
        ws = wb.create_sheet(title="Forecast")
        ws.views.sheetView[0].showGridLines = True
        fc = bundle.forecast_result
        if not fc:
            return

        meta = bundle.config.metadata
        ws["A1"] = f"{bundle.company_name} — Financial Forecast & Unlevered Cash Flows"
        ws["A1"].font = TITLE_FONT
        ws["A2"] = "Dynamic formula-linked financial projections derived from historical actuals and the Assumptions sheet."
        ws["A2"].font = MUTED_FONT

        row = 4
        num_years = len(fc.annual_forecasts)
        periods = [f.period_label for f in fc.annual_forecasts]
        headers = ["Line Item / Derivation Step", "Base Period"] + periods

        for col_idx, h in enumerate(headers, start=1):
            cell = ws.cell(row=row, column=col_idx, value=h)
            cell.font = WHITE_BOLD_FONT
            cell.fill = NAVY_HEADER_FILL
            cell.border = HEADER_BORDER
            cell.alignment = ALIGN_LEFT if col_idx == 1 else ALIGN_RIGHT
        row += 1

        # Base values from bundle
        base_rev = fc.base_revenue / 1_000_000.0 if fc.base_revenue > 100_000 else fc.base_revenue
        base_nwc = fc.base_operating_nwc / 1_000_000.0 if abs(fc.base_operating_nwc) > 100_000 else fc.base_operating_nwc

        # Line items to generate with Excel formulas
        # Row tracking dictionary for cell reference formulas
        row_map: Dict[str, int] = {}

        # 1. Revenue
        r_rev = row
        row_map["rev"] = r_rev
        ws.cell(row=r_rev, column=1, value="Revenue ($M)").font = BOLD_FONT
        ws.cell(row=r_rev, column=1).border = STANDARD_BORDER

        # Base period cell references historical anchor if available, otherwise constant
        b_cell = ws.cell(row=r_rev, column=2)
        if "hist_anchor_rev" in coords:
            b_cell.value = f"={coords['hist_anchor_rev']}"
        else:
            b_cell.value = float(base_rev)
        b_cell.number_format = "$#,##0.0"
        b_cell.font = BOLD_FONT
        b_cell.alignment = ALIGN_RIGHT
        b_cell.border = STANDARD_BORDER

        for yr_idx in range(num_years):
            col_idx = 3 + yr_idx
            prev_col = get_column_letter(col_idx - 1)
            growth_ref = coords["assump_drivers"]["rev_growth"][yr_idx + 1]
            c = ws.cell(row=r_rev, column=col_idx)
            c.value = f"={prev_col}{r_rev} * (1 + {growth_ref})"
            c.number_format = "$#,##0.0"
            c.font = BOLD_FONT
            c.alignment = ALIGN_RIGHT
            c.border = STANDARD_BORDER
        row += 1

        # 2. Cost of Goods Sold (COGS)
        r_cogs = row
        row_map["cogs"] = r_cogs
        ws.cell(row=r_cogs, column=1, value="Cost of Goods Sold (COGS)").font = REGULAR_FONT
        ws.cell(row=r_cogs, column=1).border = STANDARD_BORDER
        ws.cell(row=r_cogs, column=2, value="-").alignment = ALIGN_CENTER
        ws.cell(row=r_cogs, column=2).border = STANDARD_BORDER

        for yr_idx in range(num_years):
            col_idx = 3 + yr_idx
            col_letter = get_column_letter(col_idx)
            gm_ref = coords["assump_drivers"]["gross_margin"][yr_idx + 1]
            c = ws.cell(row=r_cogs, column=col_idx)
            c.value = f"={col_letter}{r_rev} * (1 - {gm_ref})"
            c.number_format = "$#,##0.0"
            c.font = REGULAR_FONT
            c.alignment = ALIGN_RIGHT
            c.border = STANDARD_BORDER
        row += 1

        # 3. Gross Profit
        r_gp = row
        row_map["gp"] = r_gp
        ws.cell(row=r_gp, column=1, value="Gross Profit").font = BOLD_FONT
        ws.cell(row=r_gp, column=1).border = STANDARD_BORDER
        ws.cell(row=r_gp, column=2, value="-").alignment = ALIGN_CENTER
        ws.cell(row=r_gp, column=2).border = STANDARD_BORDER

        for yr_idx in range(num_years):
            col_idx = 3 + yr_idx
            col_letter = get_column_letter(col_idx)
            c = ws.cell(row=r_gp, column=col_idx)
            c.value = f"={col_letter}{r_rev} - {col_letter}{r_cogs}"
            c.number_format = "$#,##0.0"
            c.font = BOLD_FONT
            c.alignment = ALIGN_RIGHT
            c.border = STANDARD_BORDER
        row += 1

        # 4. Operating Expenses (OpEx)
        r_opex = row
        row_map["opex"] = r_opex
        ws.cell(row=r_opex, column=1, value="Operating Expenses (OpEx)").font = REGULAR_FONT
        ws.cell(row=r_opex, column=1).border = STANDARD_BORDER
        ws.cell(row=r_opex, column=2, value="-").alignment = ALIGN_CENTER
        ws.cell(row=r_opex, column=2).border = STANDARD_BORDER

        for yr_idx in range(num_years):
            col_idx = 3 + yr_idx
            col_letter = get_column_letter(col_idx)
            opex_ref = coords["assump_drivers"]["opex_pct"][yr_idx + 1]
            c = ws.cell(row=r_opex, column=col_idx)
            c.value = f"={col_letter}{r_rev} * {opex_ref}"
            c.number_format = "$#,##0.0"
            c.font = REGULAR_FONT
            c.alignment = ALIGN_RIGHT
            c.border = STANDARD_BORDER
        row += 1

        # 5. EBITDA
        r_ebitda = row
        row_map["ebitda"] = r_ebitda
        ws.cell(row=r_ebitda, column=1, value="EBITDA").font = BOLD_FONT
        ws.cell(row=r_ebitda, column=1).border = STANDARD_BORDER
        ws.cell(row=r_ebitda, column=2, value="-").alignment = ALIGN_CENTER
        ws.cell(row=r_ebitda, column=2).border = STANDARD_BORDER

        for yr_idx in range(num_years):
            col_idx = 3 + yr_idx
            col_letter = get_column_letter(col_idx)
            c = ws.cell(row=r_ebitda, column=col_idx)
            c.value = f"={col_letter}{r_gp} - {col_letter}{r_opex}"
            c.number_format = "$#,##0.0"
            c.font = BOLD_FONT
            c.alignment = ALIGN_RIGHT
            c.border = STANDARD_BORDER
        row += 1

        # 6. Depreciation & Amortization (D&A)
        r_da = row
        row_map["da"] = r_da
        ws.cell(row=r_da, column=1, value="Depreciation & Amortization (D&A)").font = REGULAR_FONT
        ws.cell(row=r_da, column=1).border = STANDARD_BORDER
        ws.cell(row=r_da, column=2, value="-").alignment = ALIGN_CENTER
        ws.cell(row=r_da, column=2).border = STANDARD_BORDER

        for yr_idx in range(num_years):
            col_idx = 3 + yr_idx
            col_letter = get_column_letter(col_idx)
            da_ref = coords["assump_drivers"]["da_pct"][yr_idx + 1]
            c = ws.cell(row=r_da, column=col_idx)
            c.value = f"={col_letter}{r_rev} * {da_ref}"
            c.number_format = "$#,##0.0"
            c.font = REGULAR_FONT
            c.alignment = ALIGN_RIGHT
            c.border = STANDARD_BORDER
        row += 1

        # 7. Operating Profit (EBIT)
        r_ebit = row
        row_map["ebit"] = r_ebit
        ws.cell(row=r_ebit, column=1, value="Operating Income (EBIT)").font = BOLD_FONT
        ws.cell(row=r_ebit, column=1).border = STANDARD_BORDER
        ws.cell(row=r_ebit, column=2, value="-").alignment = ALIGN_CENTER
        ws.cell(row=r_ebit, column=2).border = STANDARD_BORDER

        for yr_idx in range(num_years):
            col_idx = 3 + yr_idx
            col_letter = get_column_letter(col_idx)
            c = ws.cell(row=r_ebit, column=col_idx)
            c.value = f"={col_letter}{r_ebitda} - {col_letter}{r_da}"
            c.number_format = "$#,##0.0"
            c.font = BOLD_FONT
            c.alignment = ALIGN_RIGHT
            c.border = STANDARD_BORDER
        row += 1

        # 8. Tax Expense on Operating Profit
        r_tax = row
        row_map["tax"] = r_tax
        ws.cell(row=r_tax, column=1, value="Taxes on Operating Profit (EBIT x t)").font = REGULAR_FONT
        ws.cell(row=r_tax, column=1).border = STANDARD_BORDER
        ws.cell(row=r_tax, column=2, value="-").alignment = ALIGN_CENTER
        ws.cell(row=r_tax, column=2).border = STANDARD_BORDER

        for yr_idx in range(num_years):
            col_idx = 3 + yr_idx
            col_letter = get_column_letter(col_idx)
            tax_ref = coords.get("tax_rate_cell", "'Assumptions'!C10")
            c = ws.cell(row=r_tax, column=col_idx)
            c.value = f"=MAX(0, {col_letter}{r_ebit} * {tax_ref})"
            c.number_format = "$#,##0.0"
            c.font = REGULAR_FONT
            c.alignment = ALIGN_RIGHT
            c.border = STANDARD_BORDER
        row += 1

        # 9. NOPAT
        r_nopat = row
        row_map["nopat"] = r_nopat
        ws.cell(row=r_nopat, column=1, value="NOPAT (Net Operating Profit After Tax)").font = BOLD_FONT
        ws.cell(row=r_nopat, column=1).border = STANDARD_BORDER
        ws.cell(row=r_nopat, column=2, value="-").alignment = ALIGN_CENTER
        ws.cell(row=r_nopat, column=2).border = STANDARD_BORDER

        for yr_idx in range(num_years):
            col_idx = 3 + yr_idx
            col_letter = get_column_letter(col_idx)
            c = ws.cell(row=r_nopat, column=col_idx)
            c.value = f"={col_letter}{r_ebit} - {col_letter}{r_tax}"
            c.number_format = "$#,##0.0"
            c.font = BOLD_FONT
            c.alignment = ALIGN_RIGHT
            c.border = STANDARD_BORDER
        row += 1

        # 10. (+) Non-Cash D&A Addback
        r_add_da = row
        row_map["add_da"] = r_add_da
        ws.cell(row=r_add_da, column=1, value="(+) Non-Cash Depreciation & Amortization").font = REGULAR_FONT
        ws.cell(row=r_add_da, column=1).border = STANDARD_BORDER
        ws.cell(row=r_add_da, column=2, value="-").alignment = ALIGN_CENTER
        ws.cell(row=r_add_da, column=2).border = STANDARD_BORDER

        for yr_idx in range(num_years):
            col_idx = 3 + yr_idx
            col_letter = get_column_letter(col_idx)
            c = ws.cell(row=r_add_da, column=col_idx)
            c.value = f"={col_letter}{r_da}"
            c.number_format = "$#,##0.0"
            c.font = REGULAR_FONT
            c.alignment = ALIGN_RIGHT
            c.border = STANDARD_BORDER
        row += 1

        # 11. (-) Capital Expenditures (CapEx)
        r_capex = row
        row_map["capex"] = r_capex
        ws.cell(row=r_capex, column=1, value="(-) Capital Expenditures (CapEx)").font = REGULAR_FONT
        ws.cell(row=r_capex, column=1).border = STANDARD_BORDER
        ws.cell(row=r_capex, column=2, value="-").alignment = ALIGN_CENTER
        ws.cell(row=r_capex, column=2).border = STANDARD_BORDER

        for yr_idx in range(num_years):
            col_idx = 3 + yr_idx
            col_letter = get_column_letter(col_idx)
            capex_ref = coords["assump_drivers"]["capex_pct"][yr_idx + 1]
            c = ws.cell(row=r_capex, column=col_idx)
            c.value = f"={col_letter}{r_rev} * {capex_ref}"
            c.number_format = "$#,##0.0"
            c.font = REGULAR_FONT
            c.alignment = ALIGN_RIGHT
            c.border = STANDARD_BORDER
        row += 1

        # 12. Operating Working Capital Balance
        r_nwc = row
        row_map["nwc"] = r_nwc
        ws.cell(row=r_nwc, column=1, value="Operating Net Working Capital (Balance)").font = REGULAR_FONT
        ws.cell(row=r_nwc, column=1).border = STANDARD_BORDER

        b_nwc_cell = ws.cell(row=r_nwc, column=2)
        if "hist_anchor_nwc" in coords:
            b_nwc_cell.value = f"={coords['hist_anchor_nwc']}"
        else:
            b_nwc_cell.value = float(base_nwc)
        b_nwc_cell.number_format = "$#,##0.0"
        b_nwc_cell.alignment = ALIGN_RIGHT
        b_nwc_cell.border = STANDARD_BORDER

        for yr_idx in range(num_years):
            col_idx = 3 + yr_idx
            col_letter = get_column_letter(col_idx)
            nwc_ref = coords["assump_drivers"]["nwc_pct"][yr_idx + 1]
            c = ws.cell(row=r_nwc, column=col_idx)
            c.value = f"={col_letter}{r_rev} * {nwc_ref}"
            c.number_format = "$#,##0.0"
            c.font = REGULAR_FONT
            c.alignment = ALIGN_RIGHT
            c.border = STANDARD_BORDER
        row += 1

        # 13. (-) Change in Operating Working Capital (ΔNWC)
        r_delta_nwc = row
        row_map["delta_nwc"] = r_delta_nwc
        ws.cell(row=r_delta_nwc, column=1, value="(-) Change in Operating NWC (ΔNWC)").font = REGULAR_FONT
        ws.cell(row=r_delta_nwc, column=1).border = STANDARD_BORDER
        ws.cell(row=r_delta_nwc, column=2, value="-").alignment = ALIGN_CENTER
        ws.cell(row=r_delta_nwc, column=2).border = STANDARD_BORDER

        for yr_idx in range(num_years):
            col_idx = 3 + yr_idx
            col_letter = get_column_letter(col_idx)
            prev_letter = get_column_letter(col_idx - 1)
            c = ws.cell(row=r_delta_nwc, column=col_idx)
            c.value = f"={col_letter}{r_nwc} - {prev_letter}{r_nwc}"
            c.number_format = "$#,##0.0"
            c.font = REGULAR_FONT
            c.alignment = ALIGN_RIGHT
            c.border = STANDARD_BORDER
        row += 1

        # 14. (=) Unlevered Free Cash Flow (UFCF)
        r_ufcf = row
        row_map["ufcf"] = r_ufcf
        ws.cell(row=r_ufcf, column=1, value="(=) Unlevered Free Cash Flow (UFCF)").font = KEY_METRIC_FONT
        ws.cell(row=r_ufcf, column=1).fill = LIGHT_BLUE_FILL
        ws.cell(row=r_ufcf, column=1).border = TOTAL_BORDER

        ws.cell(row=r_ufcf, column=2, value="-").alignment = ALIGN_CENTER
        ws.cell(row=r_ufcf, column=2).fill = LIGHT_BLUE_FILL
        ws.cell(row=r_ufcf, column=2).border = TOTAL_BORDER

        coords["forecast_ufcf_cells"] = {}
        for yr_idx in range(num_years):
            col_idx = 3 + yr_idx
            col_letter = get_column_letter(col_idx)
            c = ws.cell(row=r_ufcf, column=col_idx)
            # Formula: NOPAT + D&A - CapEx - Delta_NWC
            c.value = f"={col_letter}{r_nopat} + {col_letter}{r_add_da} - {col_letter}{r_capex} - {col_letter}{r_delta_nwc}"
            c.number_format = "$#,##0.0"
            c.font = KEY_METRIC_FONT
            c.fill = LIGHT_BLUE_FILL
            c.border = TOTAL_BORDER
            c.alignment = ALIGN_RIGHT
            coords["forecast_ufcf_cells"][yr_idx + 1] = f"'Forecast'!{col_letter}{r_ufcf}"

        # Record final year EBITDA and UFCF cells for terminal value references
        final_col_letter = get_column_letter(2 + num_years)
        coords["forecast_final_ebitda"] = f"'Forecast'!{final_col_letter}{r_ebitda}"
        coords["forecast_final_ufcf"] = f"'Forecast'!{final_col_letter}{r_ufcf}"

        _autofit_columns(ws)

    @classmethod
    def _build_wacc_sheet(cls, wb: openpyxl.Workbook, bundle: ReportBundle, coords: Dict[str, Any]) -> None:
        """Create WACC derivation sheet with active formulas linking to Assumptions."""
        ws = wb.create_sheet(title="WACC")
        ws.views.sheetView[0].showGridLines = True
        wacc = bundle.wacc_result
        if not wacc:
            return

        meta = bundle.config.metadata
        ws["A1"] = f"{bundle.company_name} — Weighted Average Cost of Capital (WACC)"
        ws["A1"].font = TITLE_FONT
        ws["A2"] = "Deterministic CAPM, after-tax cost of debt, and capital structure weighting driven by formulas."
        ws["A2"].font = MUTED_FONT

        row = 4
        ws.cell(row=row, column=1, value="WACC COMPUTATION SCHEDULE").font = SECTION_FONT
        row += 1

        headers = ["Parameter / Formula Step", "Formula / Source Reference", "Calculated Rate / Value", "Unit", "Methodology Notes"]
        for col_idx, h in enumerate(headers, start=1):
            cell = ws.cell(row=row, column=col_idx, value=h)
            cell.font = WHITE_BOLD_FONT
            cell.fill = NAVY_HEADER_FILL
            cell.border = HEADER_BORDER
        row += 1

        rf_cell = coords.get("assump_rf", "'Assumptions'!B16")
        beta_cell = coords.get("assump_beta", "'Assumptions'!B17")
        erp_cell = coords.get("assump_erp", "'Assumptions'!B18")
        kd_cell = coords.get("assump_kd", "'Assumptions'!B19")
        tax_cell = coords.get("assump_wacc_tax", "'Assumptions'!B20")
        eq_cell = coords.get("assump_equity_val", "'Assumptions'!B21")
        debt_cell = coords.get("assump_debt_val", "'Assumptions'!B22")

        # 1. Risk-Free Rate
        r_rf = row
        ws.cell(row=r_rf, column=1, value="Risk-Free Rate (Rf)").font = REGULAR_FONT
        ws.cell(row=r_rf, column=2, value=f"={rf_cell}").font = MUTED_FONT
        c_rf = ws.cell(row=r_rf, column=3, value=f"={rf_cell}")
        c_rf.number_format = "0.00%"
        c_rf.font = REGULAR_FONT
        c_rf.alignment = ALIGN_RIGHT
        ws.cell(row=r_rf, column=4, value="Percentage").font = MUTED_FONT
        ws.cell(row=r_rf, column=5, value="10-Year Benchmark Sovereign Yield").font = MUTED_FONT
        for c in range(1, 6): ws.cell(row=r_rf, column=c).border = STANDARD_BORDER
        row += 1

        # 2. Beta
        r_beta = row
        ws.cell(row=r_beta, column=1, value="Equity Beta (β)").font = REGULAR_FONT
        ws.cell(row=r_beta, column=2, value=f"={beta_cell}").font = MUTED_FONT
        c_beta = ws.cell(row=r_beta, column=3, value=f"={beta_cell}")
        c_beta.number_format = "0.00x"
        c_beta.font = REGULAR_FONT
        c_beta.alignment = ALIGN_RIGHT
        ws.cell(row=r_beta, column=4, value="Multiple").font = MUTED_FONT
        ws.cell(row=r_beta, column=5, value="Systematic market risk sensitivity").font = MUTED_FONT
        for c in range(1, 6): ws.cell(row=r_beta, column=c).border = STANDARD_BORDER
        row += 1

        # 3. ERP
        r_erp = row
        ws.cell(row=r_erp, column=1, value="Equity Risk Premium (ERP)").font = REGULAR_FONT
        ws.cell(row=r_erp, column=2, value=f"={erp_cell}").font = MUTED_FONT
        c_erp = ws.cell(row=r_erp, column=3, value=f"={erp_cell}")
        c_erp.number_format = "0.00%"
        c_erp.font = REGULAR_FONT
        c_erp.alignment = ALIGN_RIGHT
        ws.cell(row=r_erp, column=4, value="Percentage").font = MUTED_FONT
        ws.cell(row=r_erp, column=5, value="Market equity risk premium proxy").font = MUTED_FONT
        for c in range(1, 6): ws.cell(row=r_erp, column=c).border = STANDARD_BORDER
        row += 1

        # 4. Cost of Equity (Ke)
        r_ke = row
        ws.cell(row=r_ke, column=1, value="Cost of Equity (Ke)").font = BOLD_FONT
        ws.cell(row=r_ke, column=2, value=f"=C{r_rf} + (C{r_beta} * C{r_erp})").font = MUTED_FONT
        c_ke = ws.cell(row=r_ke, column=3, value=f"=C{r_rf} + (C{r_beta} * C{r_erp})")
        c_ke.number_format = "0.00%"
        c_ke.font = BOLD_FONT
        c_ke.alignment = ALIGN_RIGHT
        c_ke.fill = LIGHT_BLUE_FILL
        ws.cell(row=r_ke, column=4, value="Percentage").font = BOLD_FONT
        ws.cell(row=r_ke, column=5, value="Capital Asset Pricing Model (CAPM): Rf + β x ERP").font = BOLD_FONT
        for c in range(1, 6): ws.cell(row=r_ke, column=c).border = STANDARD_BORDER
        row += 1

        # 5. Pre-tax Cost of Debt (Kd)
        r_kd = row
        ws.cell(row=r_kd, column=1, value="Pre-Tax Cost of Debt (Kd)").font = REGULAR_FONT
        ws.cell(row=r_kd, column=2, value=f"={kd_cell}").font = MUTED_FONT
        c_kd = ws.cell(row=r_kd, column=3, value=f"={kd_cell}")
        c_kd.number_format = "0.00%"
        c_kd.font = REGULAR_FONT
        c_kd.alignment = ALIGN_RIGHT
        ws.cell(row=r_kd, column=4, value="Percentage").font = MUTED_FONT
        ws.cell(row=r_kd, column=5, value="Effective borrowing yield").font = MUTED_FONT
        for c in range(1, 6): ws.cell(row=r_kd, column=c).border = STANDARD_BORDER
        row += 1

        # 6. Marginal Tax Rate
        r_tax = row
        ws.cell(row=r_tax, column=1, value="Marginal Tax Rate (t)").font = REGULAR_FONT
        ws.cell(row=r_tax, column=2, value=f"={tax_cell}").font = MUTED_FONT
        c_tax = ws.cell(row=r_tax, column=3, value=f"={tax_cell}")
        c_tax.number_format = "0.00%"
        c_tax.font = REGULAR_FONT
        c_tax.alignment = ALIGN_RIGHT
        ws.cell(row=r_tax, column=4, value="Percentage").font = MUTED_FONT
        ws.cell(row=r_tax, column=5, value="Interest expense tax shield rate").font = MUTED_FONT
        for c in range(1, 6): ws.cell(row=r_tax, column=c).border = STANDARD_BORDER
        row += 1

        # 7. After-tax Cost of Debt
        r_kd_after = row
        ws.cell(row=r_kd_after, column=1, value="After-Tax Cost of Debt (Kd x (1 - t))").font = BOLD_FONT
        ws.cell(row=r_kd_after, column=2, value=f"=C{r_kd} * (1 - C{r_tax})").font = MUTED_FONT
        c_kd_after = ws.cell(row=r_kd_after, column=3, value=f"=C{r_kd} * (1 - C{r_tax})")
        c_kd_after.number_format = "0.00%"
        c_kd_after.font = BOLD_FONT
        c_kd_after.alignment = ALIGN_RIGHT
        c_kd_after.fill = LIGHT_BLUE_FILL
        ws.cell(row=r_kd_after, column=4, value="Percentage").font = BOLD_FONT
        ws.cell(row=r_kd_after, column=5, value="Tax-shield adjusted borrowing rate").font = BOLD_FONT
        for c in range(1, 6): ws.cell(row=r_kd_after, column=c).border = STANDARD_BORDER
        row += 1

        # 8. Equity Value (E)
        r_e = row
        ws.cell(row=r_e, column=1, value="Market Value of Equity (E)").font = REGULAR_FONT
        ws.cell(row=r_e, column=2, value=f"={eq_cell}").font = MUTED_FONT
        c_e = ws.cell(row=r_e, column=3, value=f"={eq_cell}")
        c_e.number_format = "$#,##0.0"
        c_e.font = REGULAR_FONT
        c_e.alignment = ALIGN_RIGHT
        ws.cell(row=r_e, column=4, value=f"{meta.reporting_currency} M").font = MUTED_FONT
        ws.cell(row=r_e, column=5, value="Market capitalization proxy").font = MUTED_FONT
        for c in range(1, 6): ws.cell(row=r_e, column=c).border = STANDARD_BORDER
        row += 1

        # 9. Total Debt (D)
        r_d = row
        ws.cell(row=r_d, column=1, value="Total Debt Value (D)").font = REGULAR_FONT
        ws.cell(row=r_d, column=2, value=f"={debt_cell}").font = MUTED_FONT
        c_d = ws.cell(row=r_d, column=3, value=f"={debt_cell}")
        c_d.number_format = "$#,##0.0"
        c_d.font = REGULAR_FONT
        c_d.alignment = ALIGN_RIGHT
        ws.cell(row=r_d, column=4, value=f"{meta.reporting_currency} M").font = MUTED_FONT
        ws.cell(row=r_d, column=5, value="Total interest-bearing debt obligations").font = MUTED_FONT
        for c in range(1, 6): ws.cell(row=r_d, column=c).border = STANDARD_BORDER
        row += 1

        # 10. Total Capital (E + D)
        r_tot_cap = row
        ws.cell(row=r_tot_cap, column=1, value="Total Capital Base (E + D)").font = BOLD_FONT
        ws.cell(row=r_tot_cap, column=2, value=f"=C{r_e} + C{r_d}").font = MUTED_FONT
        c_tot = ws.cell(row=r_tot_cap, column=3, value=f"=C{r_e} + C{r_d}")
        c_tot.number_format = "$#,##0.0"
        c_tot.font = BOLD_FONT
        c_tot.alignment = ALIGN_RIGHT
        ws.cell(row=r_tot_cap, column=4, value=f"{meta.reporting_currency} M").font = BOLD_FONT
        ws.cell(row=r_tot_cap, column=5, value="Combined enterprise capital structure").font = MUTED_FONT
        for c in range(1, 6): ws.cell(row=r_tot_cap, column=c).border = STANDARD_BORDER
        row += 1

        # 11. Weight of Equity (We)
        r_we = row
        ws.cell(row=r_we, column=1, value="Equity Financing Weight (We = E / (E + D))").font = REGULAR_FONT
        ws.cell(row=r_we, column=2, value=f"=IF(C{r_tot_cap}>0, C{r_e} / C{r_tot_cap}, 0)").font = MUTED_FONT
        c_we = ws.cell(row=r_we, column=3, value=f"=IF(C{r_tot_cap}>0, C{r_e} / C{r_tot_cap}, 0)")
        c_we.number_format = "0.0%"
        c_we.font = REGULAR_FONT
        c_we.alignment = ALIGN_RIGHT
        ws.cell(row=r_we, column=4, value="Weight").font = MUTED_FONT
        ws.cell(row=r_we, column=5, value="Proportion of equity capital").font = MUTED_FONT
        for c in range(1, 6): ws.cell(row=r_we, column=c).border = STANDARD_BORDER
        row += 1

        # 12. Weight of Debt (Wd)
        r_wd = row
        ws.cell(row=r_wd, column=1, value="Debt Financing Weight (Wd = D / (E + D))").font = REGULAR_FONT
        ws.cell(row=r_wd, column=2, value=f"=IF(C{r_tot_cap}>0, C{r_d} / C{r_tot_cap}, 0)").font = MUTED_FONT
        c_wd = ws.cell(row=r_wd, column=3, value=f"=IF(C{r_tot_cap}>0, C{r_d} / C{r_tot_cap}, 0)")
        c_wd.number_format = "0.0%"
        c_wd.font = REGULAR_FONT
        c_wd.alignment = ALIGN_RIGHT
        ws.cell(row=r_wd, column=4, value="Weight").font = MUTED_FONT
        ws.cell(row=r_wd, column=5, value="Proportion of debt capital").font = MUTED_FONT
        for c in range(1, 6): ws.cell(row=r_wd, column=c).border = STANDARD_BORDER
        row += 1

        # 13. Blended WACC
        r_wacc = row
        ws.cell(row=r_wacc, column=1, value="Weighted Average Cost of Capital (WACC)").font = KEY_METRIC_FONT
        ws.cell(row=r_wacc, column=2, value=f"=(C{r_we} * C{r_ke}) + (C{r_wd} * C{r_kd_after})").font = MUTED_FONT
        c_wacc = ws.cell(row=r_wacc, column=3, value=f"=(C{r_we} * C{r_ke}) + (C{r_wd} * C{r_kd_after})")
        c_wacc.number_format = "0.00%"
        c_wacc.font = KEY_METRIC_FONT
        c_wacc.alignment = ALIGN_RIGHT
        c_wacc.fill = HIGHLIGHT_FILL
        ws.cell(row=r_wacc, column=4, value="Percentage").font = BOLD_FONT
        ws.cell(row=r_wacc, column=5, value="Blended corporate discount rate: (We x Ke) + (Wd x Kd_after)").font = BOLD_FONT
        for c in range(1, 6):
            ws.cell(row=r_wacc, column=c).border = TOTAL_BORDER
            ws.cell(row=r_wacc, column=c).fill = HIGHLIGHT_FILL

        coords["wacc_rate_cell"] = f"'WACC'!C{r_wacc}"

        _autofit_columns(ws)

    @classmethod
    def _build_dcf_sheet(cls, wb: openpyxl.Workbook, bundle: ReportBundle, coords: Dict[str, Any]) -> None:
        """Create DCF discounting, terminal valuation, and equity bridge sheet with live formulas."""
        ws = wb.create_sheet(title="DCF Valuation")
        ws.views.sheetView[0].showGridLines = True
        dcf = bundle.dcf_result
        if not dcf:
            return

        meta = bundle.config.metadata
        ws["A1"] = f"{bundle.company_name} — Discounted Cash Flow Valuation"
        ws["A1"].font = TITLE_FONT
        ws["A2"] = f"Terminal Method: {dcf.terminal_inputs.method.replace('_', ' ').title()} | Timing: {dcf.discounting_convention.replace('_', ' ').title()}"
        ws["A2"].font = MUTED_FONT

        # ---------------------------------------------------------------------
        # 1. Cash Flow Discounting Schedule
        # ---------------------------------------------------------------------
        row = 4
        ws.cell(row=row, column=1, value="1. FORECAST CASH FLOW DISCOUNTING SCHEDULE").font = SECTION_FONT
        row += 1

        num_years = len(dcf.annual_discounting_schedule)
        forecast_cols = [item.period_label for item in dcf.annual_discounting_schedule]
        headers = ["Cash Flow Discounting Metric", "Units"] + forecast_cols + ["Cumulative"]

        for col_idx, h in enumerate(headers, start=1):
            cell = ws.cell(row=row, column=col_idx, value=h)
            cell.font = WHITE_BOLD_FONT
            cell.fill = NAVY_HEADER_FILL
            cell.border = HEADER_BORDER
            cell.alignment = ALIGN_LEFT if col_idx <= 2 else ALIGN_RIGHT
        row += 1

        wacc_ref = coords.get("wacc_rate_cell", "'WACC'!C17")

        # Row 1: Forecast UFCF
        r_ufcf = row
        ws.cell(row=r_ufcf, column=1, value="Unlevered Free Cash Flow (UFCF)").font = BOLD_FONT
        ws.cell(row=r_ufcf, column=2, value=f"{meta.reporting_currency} M").font = MUTED_FONT
        for yr_idx in range(num_years):
            col_idx = 3 + yr_idx
            ufcf_ref = coords.get("forecast_ufcf_cells", {}).get(yr_idx + 1)
            c = ws.cell(row=r_ufcf, column=col_idx)
            c.value = f"={ufcf_ref}" if ufcf_ref else float(dcf.annual_discounting_schedule[yr_idx].ufcf / 1_000_000.0)
            c.number_format = "$#,##0.0"
            c.font = BOLD_FONT
            c.alignment = ALIGN_RIGHT
            c.border = STANDARD_BORDER

        # Sum of UFCF
        start_col = get_column_letter(3)
        end_col = get_column_letter(2 + num_years)
        c_tot_ufcf = ws.cell(row=r_ufcf, column=3 + num_years)
        c_tot_ufcf.value = f"=SUM({start_col}{r_ufcf}:{end_col}{r_ufcf})"
        c_tot_ufcf.number_format = "$#,##0.0"
        c_tot_ufcf.font = BOLD_FONT
        c_tot_ufcf.alignment = ALIGN_RIGHT
        c_tot_ufcf.border = STANDARD_BORDER
        row += 1

        # Row 2: Discount Period (t)
        r_t = row
        ws.cell(row=r_t, column=1, value="Discount Period (t)").font = REGULAR_FONT
        ws.cell(row=r_t, column=2, value="Years").font = MUTED_FONT
        is_mid_year = dcf.discounting_convention == DiscountingConvention.MID_YEAR.value

        for yr_idx in range(num_years):
            col_idx = 3 + yr_idx
            t_val = (yr_idx + 1) - 0.5 if is_mid_year else float(yr_idx + 1)
            c = ws.cell(row=r_t, column=col_idx, value=t_val)
            c.number_format = "0.0"
            c.font = REGULAR_FONT
            c.alignment = ALIGN_CENTER
            c.border = STANDARD_BORDER
        ws.cell(row=r_t, column=3 + num_years, value="-").alignment = ALIGN_CENTER
        ws.cell(row=r_t, column=3 + num_years).border = STANDARD_BORDER
        row += 1

        # Row 3: Discount Factor: 1 / (1 + WACC)^t
        r_df = row
        ws.cell(row=r_df, column=1, value=f"Discount Factor (WACC = {wacc_ref})").font = REGULAR_FONT
        ws.cell(row=r_df, column=2, value="Factor").font = MUTED_FONT
        for yr_idx in range(num_years):
            col_idx = 3 + yr_idx
            col_letter = get_column_letter(col_idx)
            c = ws.cell(row=r_df, column=col_idx)
            c.value = f"=1 / ((1 + {wacc_ref}) ^ {col_letter}{r_t})"
            c.number_format = "0.0000"
            c.font = REGULAR_FONT
            c.alignment = ALIGN_RIGHT
            c.border = STANDARD_BORDER
        ws.cell(row=r_df, column=3 + num_years, value="-").alignment = ALIGN_CENTER
        ws.cell(row=r_df, column=3 + num_years).border = STANDARD_BORDER
        row += 1

        # Row 4: Present Value of UFCF
        r_pv = row
        ws.cell(row=r_pv, column=1, value="Present Value of UFCF").font = BOLD_FONT
        ws.cell(row=r_pv, column=2, value=f"{meta.reporting_currency} M").font = MUTED_FONT
        for yr_idx in range(num_years):
            col_idx = 3 + yr_idx
            col_letter = get_column_letter(col_idx)
            c = ws.cell(row=r_pv, column=col_idx)
            c.value = f"={col_letter}{r_ufcf} * {col_letter}{r_df}"
            c.number_format = "$#,##0.0"
            c.font = BOLD_FONT
            c.alignment = ALIGN_RIGHT
            c.border = STANDARD_BORDER

        # Cumulative PV of Discrete Forecast UFCF
        c_pv_tot = ws.cell(row=r_pv, column=3 + num_years)
        c_pv_tot.value = f"=SUM({start_col}{r_pv}:{end_col}{r_pv})"
        c_pv_tot.number_format = "$#,##0.0"
        c_pv_tot.font = KEY_METRIC_FONT
        c_pv_tot.fill = LIGHT_BLUE_FILL
        c_pv_tot.border = TOTAL_BORDER
        c_pv_tot.alignment = ALIGN_RIGHT

        cum_pv_cell_ref = f"'DCF Valuation'!{get_column_letter(3 + num_years)}{r_pv}"
        coords["dcf_cum_pv_ufcf"] = cum_pv_cell_ref
        row += 2

        # ---------------------------------------------------------------------
        # 2. Terminal Value Calculation
        # ---------------------------------------------------------------------
        ws.cell(row=row, column=1, value="2. TERMINAL ENTERPRISE VALUE DERIVATION").font = SECTION_FONT
        row += 1

        tv_headers = ["Terminal Value Parameter / Step", "Formula / Source", "Value", "Unit", "Methodology Description"]
        for col_idx, h in enumerate(tv_headers, start=1):
            cell = ws.cell(row=row, column=col_idx, value=h)
            cell.font = WHITE_BOLD_FONT
            cell.fill = BLUE_SUBHEADER_FILL
            cell.border = HEADER_BORDER
        row += 1

        final_col_letter = get_column_letter(2 + num_years)
        final_ufcf_cell = f"{final_col_letter}{r_ufcf}"
        final_df_cell = f"{final_col_letter}{r_df}"

        is_gordon = dcf.terminal_inputs.method == TerminalValueMethod.GORDON_GROWTH.value
        g_ref = coords.get("assump_term_g", "'Assumptions'!B26")
        mult_ref = coords.get("assump_term_mult", "'Assumptions'!B27")
        final_ebitda_ref = coords.get("forecast_final_ebitda", "'Forecast'!G9")

        # Nominal Terminal Value (TV_N)
        r_tv_nom = row
        ws.cell(row=r_tv_nom, column=1, value="Terminal Enterprise Value (Nominal TV_N)").font = BOLD_FONT
        ws.cell(row=r_tv_nom, column=1).border = STANDARD_BORDER

        if is_gordon:
            ws.cell(row=r_tv_nom, column=2, value=f"=({final_ufcf_cell} * (1 + {g_ref})) / ({wacc_ref} - {g_ref})").font = MUTED_FONT
            c_tv = ws.cell(row=r_tv_nom, column=3)
            c_tv.value = f"=IF({wacc_ref} > {g_ref}, ({final_ufcf_cell} * (1 + {g_ref})) / ({wacc_ref} - {g_ref}), \"INVALID: WACC <= g\")"
            c_tv.number_format = "$#,##0.0"
            c_tv.font = BOLD_FONT
            c_tv.alignment = ALIGN_RIGHT
            ws.cell(row=r_tv_nom, column=4, value=f"{meta.reporting_currency} M").font = MUTED_FONT
            ws.cell(row=r_tv_nom, column=5, value="Gordon Growth Perpetuity: (UFCF_N x (1 + g)) / (WACC - g)").font = MUTED_FONT
        else:
            ws.cell(row=r_tv_nom, column=2, value=f"={final_ebitda_ref} * {mult_ref}").font = MUTED_FONT
            c_tv = ws.cell(row=r_tv_nom, column=3)
            c_tv.value = f"={final_ebitda_ref} * {mult_ref}"
            c_tv.number_format = "$#,##0.0"
            c_tv.font = BOLD_FONT
            c_tv.alignment = ALIGN_RIGHT
            ws.cell(row=r_tv_nom, column=4, value=f"{meta.reporting_currency} M").font = MUTED_FONT
            ws.cell(row=r_tv_nom, column=5, value="Exit Multiple: Terminal Year EBITDA x Exit Multiple").font = MUTED_FONT

        for c in range(1, 6): ws.cell(row=r_tv_nom, column=c).border = STANDARD_BORDER
        row += 1

        # Terminal Value Discount Factor
        r_tv_df = row
        ws.cell(row=r_tv_df, column=1, value="Terminal Discount Factor").font = REGULAR_FONT
        ws.cell(row=r_tv_df, column=2, value=f"={final_df_cell}").font = MUTED_FONT
        c_tv_df = ws.cell(row=r_tv_df, column=3, value=f"={final_df_cell}")
        c_tv_df.number_format = "0.0000"
        c_tv_df.font = REGULAR_FONT
        c_tv_df.alignment = ALIGN_RIGHT
        ws.cell(row=r_tv_df, column=4, value="Factor").font = MUTED_FONT
        ws.cell(row=r_tv_df, column=5, value="Aligned with forecast horizon end timing").font = MUTED_FONT
        for c in range(1, 6): ws.cell(row=r_tv_df, column=c).border = STANDARD_BORDER
        row += 1

        # Present Value of Terminal Value
        r_pv_tv = row
        ws.cell(row=r_pv_tv, column=1, value="Present Value of Terminal Value (PV TV)").font = BOLD_FONT
        ws.cell(row=r_pv_tv, column=2, value=f"=C{r_tv_nom} * C{r_tv_df}").font = MUTED_FONT
        c_pv_tv = ws.cell(row=r_pv_tv, column=3, value=f"=IF(ISNUMBER(C{r_tv_nom}), C{r_tv_nom} * C{r_tv_df}, \"INVALID\")")
        c_pv_tv.number_format = "$#,##0.0"
        c_pv_tv.font = KEY_METRIC_FONT
        c_pv_tv.fill = LIGHT_BLUE_FILL
        c_pv_tv.alignment = ALIGN_RIGHT
        ws.cell(row=r_pv_tv, column=4, value=f"{meta.reporting_currency} M").font = BOLD_FONT
        ws.cell(row=r_pv_tv, column=5, value="Discounted terminal enterprise value").font = MUTED_FONT
        for c in range(1, 6):
            ws.cell(row=r_pv_tv, column=c).border = TOTAL_BORDER
            ws.cell(row=r_pv_tv, column=c).fill = LIGHT_BLUE_FILL

        coords["dcf_pv_tv"] = f"'DCF Valuation'!C{r_pv_tv}"
        row += 2

        # ---------------------------------------------------------------------
        # 3. Enterprise Value to Equity Value Bridge
        # ---------------------------------------------------------------------
        ws.cell(row=row, column=1, value="3. ENTERPRISE VALUE TO EQUITY VALUE BRIDGE").font = SECTION_FONT
        row += 1

        bridge_headers = ["Accounting Bridge Step", "Live Formula / Cell Reference", "Amount", "Unit", "Accounting Operation & Bridge Notes"]
        for col_idx, h in enumerate(bridge_headers, start=1):
            cell = ws.cell(row=row, column=col_idx, value=h)
            cell.font = WHITE_BOLD_FONT
            cell.fill = NAVY_HEADER_FILL
            cell.border = HEADER_BORDER
        row += 1

        # 1. Enterprise Value
        r_ev = row
        ws.cell(row=r_ev, column=1, value="Enterprise Value (EV)").font = KEY_METRIC_FONT
        ws.cell(row=r_ev, column=2, value=f"=SUM({cum_pv_cell_ref}, C{r_pv_tv})").font = MUTED_FONT
        c_ev = ws.cell(row=r_ev, column=3, value=f"=IF(ISNUMBER(C{r_pv_tv}), {cum_pv_cell_ref} + C{r_pv_tv}, \"INVALID\")")
        c_ev.number_format = "$#,##0.0"
        c_ev.font = KEY_METRIC_FONT
        c_ev.fill = LIGHT_BLUE_FILL
        c_ev.alignment = ALIGN_RIGHT
        ws.cell(row=r_ev, column=4, value=f"{meta.reporting_currency} M").font = BOLD_FONT
        ws.cell(row=r_ev, column=5, value="PV of Discrete Forecast UFCF + PV of Terminal Value").font = BOLD_FONT
        for c in range(1, 6):
            ws.cell(row=r_ev, column=c).border = STANDARD_BORDER
            ws.cell(row=r_ev, column=c).fill = LIGHT_BLUE_FILL
        coords["dcf_ev"] = f"'DCF Valuation'!C{r_ev}"
        row += 1

        # 2. (+) Cash
        cash_ref = coords.get("assump_cash", "'Assumptions'!B31")
        r_cash = row
        ws.cell(row=r_cash, column=1, value="(+) Cash and Cash Equivalents").font = REGULAR_FONT
        ws.cell(row=r_cash, column=2, value=f"={cash_ref}").font = MUTED_FONT
        c_cash = ws.cell(row=r_cash, column=3, value=f"={cash_ref}")
        c_cash.number_format = "$#,##0.0"
        c_cash.font = REGULAR_FONT
        c_cash.alignment = ALIGN_RIGHT
        ws.cell(row=r_cash, column=4, value=f"{meta.reporting_currency} M").font = MUTED_FONT
        ws.cell(row=r_cash, column=5, value="Add liquid non-operating cash available to equity").font = MUTED_FONT
        for c in range(1, 6): ws.cell(row=r_cash, column=c).border = STANDARD_BORDER
        row += 1

        # 3. (-) Debt
        debt_b_ref = coords.get("assump_debt", "'Assumptions'!B32")
        r_debt = row
        ws.cell(row=r_debt, column=1, value="(-) Total Interest-Bearing Debt").font = REGULAR_FONT
        ws.cell(row=r_debt, column=2, value=f"=-{debt_b_ref}").font = MUTED_FONT
        c_debt = ws.cell(row=r_debt, column=3, value=f"=-{debt_b_ref}")
        c_debt.number_format = "$#,##0.0"
        c_debt.font = REGULAR_FONT
        c_debt.alignment = ALIGN_RIGHT
        ws.cell(row=r_debt, column=4, value=f"{meta.reporting_currency} M").font = MUTED_FONT
        ws.cell(row=r_debt, column=5, value="Deduct senior interest-bearing debt obligations").font = MUTED_FONT
        for c in range(1, 6): ws.cell(row=r_debt, column=c).border = STANDARD_BORDER
        row += 1

        # 4. (-) Minority Interest
        min_ref = coords.get("assump_minority", "'Assumptions'!B33")
        r_min = row
        ws.cell(row=r_min, column=1, value="(-) Minority Interest (Non-Controlling)").font = REGULAR_FONT
        ws.cell(row=r_min, column=2, value=f"=-{min_ref}").font = MUTED_FONT
        c_min = ws.cell(row=r_min, column=3, value=f"=-{min_ref}")
        c_min.number_format = "$#,##0.0"
        c_min.font = REGULAR_FONT
        c_min.alignment = ALIGN_RIGHT
        ws.cell(row=r_min, column=4, value=f"{meta.reporting_currency} M").font = MUTED_FONT
        ws.cell(row=r_min, column=5, value="Deduct third-party claims in consolidated subs").font = MUTED_FONT
        for c in range(1, 6): ws.cell(row=r_min, column=c).border = STANDARD_BORDER
        row += 1

        # 5. (-) Preferred Equity
        pref_ref = coords.get("assump_pref", "'Assumptions'!B34")
        r_pref = row
        ws.cell(row=r_pref, column=1, value="(-) Preferred Stock Equity").font = REGULAR_FONT
        ws.cell(row=r_pref, column=2, value=f"=-{pref_ref}").font = MUTED_FONT
        c_pref = ws.cell(row=r_pref, column=3, value=f"=-{pref_ref}")
        c_pref.number_format = "$#,##0.0"
        c_pref.font = REGULAR_FONT
        c_pref.alignment = ALIGN_RIGHT
        ws.cell(row=r_pref, column=4, value=f"{meta.reporting_currency} M").font = MUTED_FONT
        ws.cell(row=r_pref, column=5, value="Deduct senior preferred equity capital").font = MUTED_FONT
        for c in range(1, 6): ws.cell(row=r_pref, column=c).border = STANDARD_BORDER
        row += 1

        # 6. (+/-) Other Adjustments
        other_ref = coords.get("assump_other", "'Assumptions'!B35")
        r_other = row
        ws.cell(row=r_other, column=1, value="(+/-) Other Net Non-Operating Adjustments").font = REGULAR_FONT
        ws.cell(row=r_other, column=2, value=f"={other_ref}").font = MUTED_FONT
        c_other = ws.cell(row=r_other, column=3, value=f"={other_ref}")
        c_other.number_format = "$#,##0.0"
        c_other.font = REGULAR_FONT
        c_other.alignment = ALIGN_RIGHT
        ws.cell(row=r_other, column=4, value=f"{meta.reporting_currency} M").font = MUTED_FONT
        ws.cell(row=r_other, column=5, value="Associates, joint ventures, or non-operating claims").font = MUTED_FONT
        for c in range(1, 6): ws.cell(row=r_other, column=c).border = STANDARD_BORDER
        row += 1

        # 7. (=) Implied Equity Value
        r_eq = row
        ws.cell(row=r_eq, column=1, value="(=) Implied Equity Value").font = KEY_METRIC_FONT
        ws.cell(row=r_eq, column=2, value=f"=SUM(C{r_ev}:C{r_other})").font = MUTED_FONT
        c_eq = ws.cell(row=r_eq, column=3, value=f"=IF(ISNUMBER(C{r_ev}), SUM(C{r_ev}:C{r_other}), \"INVALID\")")
        c_eq.number_format = "$#,##0.0"
        c_eq.font = KEY_METRIC_FONT
        c_eq.fill = HIGHLIGHT_FILL
        c_eq.alignment = ALIGN_RIGHT
        ws.cell(row=r_eq, column=4, value=f"{meta.reporting_currency} M").font = BOLD_FONT
        ws.cell(row=r_eq, column=5, value="Net value of common equity ownership").font = BOLD_FONT
        for c in range(1, 6):
            ws.cell(row=r_eq, column=c).border = TOTAL_BORDER
            ws.cell(row=r_eq, column=c).fill = HIGHLIGHT_FILL
        coords["dcf_equity_val"] = f"'DCF Valuation'!C{r_eq}"
        row += 1

        # 8. (÷) Diluted Common Shares
        shares_ref = coords.get("assump_shares", "'Assumptions'!B36")
        r_shares = row
        ws.cell(row=r_shares, column=1, value="(÷) Diluted Shares Outstanding").font = REGULAR_FONT
        ws.cell(row=r_shares, column=2, value=f"={shares_ref}").font = MUTED_FONT
        c_shares = ws.cell(row=r_shares, column=3, value=f"={shares_ref}")
        c_shares.number_format = "#,##0.0"
        c_shares.font = REGULAR_FONT
        c_shares.alignment = ALIGN_RIGHT
        ws.cell(row=r_shares, column=4, value="Millions of shares").font = MUTED_FONT
        ws.cell(row=r_shares, column=5, value="Weighted average diluted share count").font = MUTED_FONT
        for c in range(1, 6): ws.cell(row=r_shares, column=c).border = STANDARD_BORDER
        row += 1

        # 9. (=) Implied Value per Share
        r_target = row
        ws.cell(row=r_target, column=1, value="(=) Implied Intrinsic Value per Diluted Share").font = KEY_METRIC_FONT
        ws.cell(row=r_target, column=2, value=f"=IF(AND(ISNUMBER(C{r_eq}), C{r_shares}>0), C{r_eq} / C{r_shares}, \"N/A\")").font = MUTED_FONT
        c_target = ws.cell(row=r_target, column=3, value=f"=IF(AND(ISNUMBER(C{r_eq}), C{r_shares}>0), C{r_eq} / C{r_shares}, \"N/A\")")
        c_target.number_format = "$#,##0.00"
        c_target.font = KEY_METRIC_FONT
        c_target.fill = HIGHLIGHT_FILL
        c_target.alignment = ALIGN_RIGHT
        ws.cell(row=r_target, column=4, value=f"{meta.reporting_currency} per share").font = BOLD_FONT
        ws.cell(row=r_target, column=5, value="Equity Value / Diluted Common Shares").font = BOLD_FONT
        for c in range(1, 6):
            ws.cell(row=r_target, column=c).border = TOTAL_BORDER
            ws.cell(row=r_target, column=c).fill = HIGHLIGHT_FILL
        coords["dcf_share_price"] = f"'DCF Valuation'!C{r_target}"

        _autofit_columns(ws)

    @classmethod
    def _build_scenarios_sheet(cls, wb: openpyxl.Workbook, bundle: ReportBundle, coords: Dict[str, Any]) -> None:
        """Create Scenario Analysis comparison sheet with live link to Base Case and saved Bull/Bear cases."""
        ws = wb.create_sheet(title="Scenario Analysis")
        ws.views.sheetView[0].showGridLines = True
        sc = bundle.scenario_result
        if not sc:
            return

        meta = bundle.config.metadata
        ws["A1"] = f"{bundle.company_name} — Scenario Analysis (Base / Bull / Bear)"
        ws["A1"].font = TITLE_FONT
        ws["A2"] = f"Scenario Set: {bundle.scenario_model_name or 'Default Scenarios'} | Base case linked to dynamic DCF model."
        ws["A2"].font = MUTED_FONT

        row = 4
        headers = ["Valuation & Operating Driver", "Base Case (Live Linked)", "Bull Case (Saved)", "Bear Case (Saved)"]
        for col_idx, h in enumerate(headers, start=1):
            cell = ws.cell(row=row, column=col_idx, value=h)
            cell.font = WHITE_BOLD_FONT
            cell.fill = NAVY_HEADER_FILL
            cell.border = HEADER_BORDER
            cell.alignment = ALIGN_LEFT if col_idx == 1 else ALIGN_RIGHT
        row += 1

        b_case = sc.base_case
        u_case = sc.bull_case
        d_case = sc.bear_case

        ev_ref = coords.get("dcf_ev", "'DCF Valuation'!C19")
        eq_ref = coords.get("dcf_equity_val", "'DCF Valuation'!C25")
        sp_ref = coords.get("dcf_share_price", "'DCF Valuation'!C27")

        u_ev = u_case.enterprise_value / 1_000_000.0 if u_case.enterprise_value and abs(u_case.enterprise_value) > 100_000 else u_case.enterprise_value
        d_ev = d_case.enterprise_value / 1_000_000.0 if d_case.enterprise_value and abs(d_case.enterprise_value) > 100_000 else d_case.enterprise_value
        u_eq = u_case.equity_value / 1_000_000.0 if u_case.equity_value and abs(u_case.equity_value) > 100_000 else u_case.equity_value
        d_eq = d_case.equity_value / 1_000_000.0 if d_case.equity_value and abs(d_case.equity_value) > 100_000 else d_case.equity_value

        s_rows = [
            ("Revenue Growth Override (pp)", "0.0 pp", f"{u_case.overrides.revenue_growth_delta_pp:+.2f} pp", f"{d_case.overrides.revenue_growth_delta_pp:+.2f} pp", "@"),
            ("Operating Margin Override (pp)", "0.0 pp", f"{u_case.overrides.margin_delta_pp:+.2f} pp", f"{d_case.overrides.margin_delta_pp:+.2f} pp", "@"),
            ("WACC Adjustment (bps)", "0 bps", f"{u_case.overrides.wacc_delta_bps:+.0f} bps", f"{d_case.overrides.wacc_delta_bps:+.0f} bps", "@"),
            ("Discount Rate (WACC)", b_case.effective_wacc / 100.0 if b_case.effective_wacc else 0.08, u_case.effective_wacc / 100.0 if u_case.effective_wacc else 0.08, d_case.effective_wacc / 100.0 if d_case.effective_wacc else 0.08, "0.00%"),
            ("Enterprise Value (EV) ($M)", f"={ev_ref}", u_ev, d_ev, "$#,##0.0"),
            ("Equity Value ($M)", f"={eq_ref}", u_eq, d_eq, "$#,##0.0"),
            ("Implied Intrinsic Value / Share", f"={sp_ref}", u_case.implied_value_per_share, d_case.implied_value_per_share, "$#,##0.00"),
            ("Validation Status", "Live Validated", "Saved Record", "Saved Record", "@"),
        ]

        for label, b_val, u_val, d_val, num_fmt in s_rows:
            is_bold = "Implied" in label or "Enterprise" in label or "Equity Value" in label
            ws.cell(row=row, column=1, value=label).font = BOLD_FONT if is_bold else REGULAR_FONT
            ws.cell(row=row, column=1).border = STANDARD_BORDER

            for c_idx, val in enumerate([b_val, u_val, d_val], start=2):
                cell = ws.cell(row=row, column=c_idx)
                cell.border = STANDARD_BORDER
                cell.alignment = ALIGN_RIGHT

                if str(val).startswith("="):
                    cell.value = str(val)
                    cell.font = KEY_METRIC_FONT if is_bold else BOLD_FONT
                    cell.fill = HIGHLIGHT_FILL if is_bold else LIGHT_BLUE_FILL
                    cell.number_format = num_fmt
                elif isinstance(val, (int, float)):
                    cell.value = float(val)
                    cell.font = BOLD_FONT if is_bold else REGULAR_FONT
                    cell.number_format = num_fmt
                else:
                    cell.value = str(val or "N/A")
                    cell.font = REGULAR_FONT

            row += 1

        _autofit_columns(ws)

    @classmethod
    def _build_sensitivity_sheet(cls, wb: openpyxl.Workbook, bundle: ReportBundle) -> None:
        """Create 2D sensitivity matrix and Monte Carlo summary sheet."""
        ws = wb.create_sheet(title="Sensitivity & Simulation")
        ws.views.sheetView[0].showGridLines = True

        ws["A1"] = f"{bundle.company_name} — Valuation Sensitivity & Probabilistic Simulation"
        ws["A1"].font = TITLE_FONT
        ws["A2"] = "Two-dimensional valuation matrix and Monte Carlo percentile summary statistics."
        ws["A2"].font = MUTED_FONT

        row = 4

        # 1. 2D Sensitivity Matrix
        matrix = bundle.sensitivity_matrix_result
        if matrix:
            ws.cell(row=row, column=1, value=f"TWO-DIMENSIONAL VALUATION SENSITIVITY MATRIX ({matrix.metric_label})").font = SECTION_FONT
            row += 1

            col_headers = [f"WACC \\ {matrix.col_label}"] + [f"{c:.2f}%" if "%" in matrix.col_label else f"{c:.1f}x" for c in matrix.col_values]
            for col_idx, ch in enumerate(col_headers, start=1):
                cell = ws.cell(row=row, column=col_idx, value=ch)
                cell.font = WHITE_BOLD_FONT
                cell.fill = NAVY_HEADER_FILL
                cell.border = HEADER_BORDER
                cell.alignment = ALIGN_CENTER
            row += 1

            for r_idx, r_val in enumerate(matrix.row_values):
                ws.cell(row=row, column=1, value=f"{r_val:.2f}%").font = BOLD_FONT
                ws.cell(row=row, column=1).border = STANDARD_BORDER
                ws.cell(row=row, column=1).alignment = ALIGN_CENTER

                for c_idx, c_val in enumerate(matrix.col_values):
                    cell_res = matrix.cells[r_idx][c_idx]
                    cell = ws.cell(row=row, column=c_idx + 2)
                    cell.border = STANDARD_BORDER
                    cell.alignment = ALIGN_RIGHT

                    if cell_res.is_valid and cell_res.output_value is not None:
                        val = cell_res.output_value
                        if "Share" in matrix.metric_label:
                            cell.value = val
                            cell.number_format = "$#,##0.00"
                        else:
                            val_m = val / 1_000_000.0 if abs(val) > 100_000 else val
                            cell.value = val_m
                            cell.number_format = "$#,##0.0"

                        if cell_res.is_baseline:
                            cell.fill = HIGHLIGHT_FILL
                            cell.font = BOLD_FONT
                        else:
                            cell.font = REGULAR_FONT
                    else:
                        cell.value = "INVALID (WACC ≤ g)"
                        cell.font = MUTED_FONT
                        cell.fill = GRAY_FILL

                row += 1

            row += 2

        # 2. Monte Carlo Simulation Summary
        mc = bundle.monte_carlo_result
        if mc and mc.summary_stats:
            ws.cell(row=row, column=1, value="MONTE CARLO PROBABILISTIC VALUATION SUMMARY").font = SECTION_FONT
            row += 1

            ws.cell(row=row, column=1, value=f"Total Iterations: {mc.total_iterations} | Valid Draws: {mc.valid_iterations} | Invalid Draws: {mc.invalid_iterations} | Random Seed: {mc.config.random_seed}").font = MUTED_FONT
            row += 1

            headers = ["Statistic / Percentile", "Enterprise Value ($M)", "Equity Value ($M)", "Implied Value / Share"]
            for col_idx, h in enumerate(headers, start=1):
                cell = ws.cell(row=row, column=col_idx, value=h)
                cell.font = WHITE_BOLD_FONT
                cell.fill = BLUE_SUBHEADER_FILL
                cell.border = HEADER_BORDER
                cell.alignment = ALIGN_LEFT if col_idx == 1 else ALIGN_RIGHT
            row += 1

            ev_s = mc.summary_stats.get("enterprise_value")
            eq_s = mc.summary_stats.get("equity_value")
            sp_s = mc.summary_stats.get("implied_share_price")

            stat_keys = [
                ("Mean", "mean"),
                ("Median (P50)", "median"),
                ("Std Deviation", "std_dev"),
                ("Minimum", "min_val"),
                ("10th Percentile (P10)", "p10"),
                ("25th Percentile (P25)", "p25"),
                ("75th Percentile (P75)", "p75"),
                ("90th Percentile (P90)", "p90"),
                ("Maximum", "max_val"),
            ]

            for label, attr in stat_keys:
                is_bold = "Median" in label or "Mean" in label
                ws.cell(row=row, column=1, value=label).font = BOLD_FONT if is_bold else REGULAR_FONT
                ws.cell(row=row, column=1).border = STANDARD_BORDER

                for c_idx, s in enumerate([ev_s, eq_s, sp_s], start=2):
                    cell = ws.cell(row=row, column=c_idx)
                    cell.border = STANDARD_BORDER
                    cell.alignment = ALIGN_RIGHT
                    val = getattr(s, attr, None) if s else None
                    if val is not None:
                        if c_idx == 4:
                            cell.value = float(val)
                            cell.number_format = "$#,##0.00"
                        else:
                            val_m = val / 1_000_000.0 if abs(val) > 100_000 else val
                            cell.value = float(val_m)
                            cell.number_format = "$#,##0.0"
                        cell.font = BOLD_FONT if is_bold else REGULAR_FONT
                    else:
                        cell.value = "-"
                        cell.font = MUTED_FONT
                row += 1

        _autofit_columns(ws)
