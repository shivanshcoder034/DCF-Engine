"""Pure-Python institutional PDF report generator compliant with standard PDF 1.4.

Produces a multi-page, publication-quality printable valuation memorandum complete with
cover headers, KPI highlight cards, running headers/footers with dynamic page numbering,
structured financial statement tables, sensitivity matrices, and audit disclosures.
"""

from __future__ import annotations

import io
import logging
from typing import Any, Dict, List, Optional, Tuple

from src.reporting.models import ReportBundle

logger = logging.getLogger(__name__)


class _PdfCanvas:
    """Low-level PDF 1.4 coordinate and drawing context."""

    def __init__(self, page_width: float = 612.0, page_height: float = 792.0):
        self.width = page_width
        self.height = page_height
        self.left_margin = 40.0
        self.right_margin = 40.0
        self.top_margin = 45.0
        self.bottom_margin = 45.0
        self.content_width = self.width - self.left_margin - self.right_margin

        self.pages: List[List[str]] = [[]]
        self.current_page_idx = 0
        self.y = self.height - self.top_margin

    @property
    def current_stream(self) -> List[str]:
        return self.pages[self.current_page_idx]

    def new_page(self) -> None:
        """Start a new document page."""
        self.pages.append([])
        self.current_page_idx += 1
        self.y = self.height - self.top_margin

    def ensure_space(self, height: float) -> None:
        """Advance to a new page if the required vertical space is unavailable."""
        if self.y - height < self.bottom_margin:
            self.new_page()

    def draw_text(
        self,
        text: str,
        x: float,
        y: float,
        font: str = "F1",
        size: float = 9.0,
        r: float = 0.1,
        g: float = 0.1,
        b: float = 0.1,
    ) -> None:
        """Draw an escaped text string at absolute coordinates."""
        clean = (
            str(text)
            .replace("\\", "\\\\")
            .replace("(", "\\(")
            .replace(")", "\\)")
            .encode("latin-1", errors="replace")
            .decode("latin-1")
        )
        self.current_stream.append(
            f"BT /{font} {size:.1f} Tf {r:.2f} {g:.2f} {b:.2f} rg {x:.1f} {y:.1f} Td ({clean}) Tj ET\n"
        )

    def draw_rect(
        self,
        x: float,
        y: float,
        w: float,
        h: float,
        fill_rgb: Optional[Tuple[float, float, float]] = None,
        stroke_rgb: Optional[Tuple[float, float, float]] = None,
        line_width: float = 0.5,
    ) -> None:
        """Draw a filled and/or stroked rectangle."""
        cmds: List[str] = []
        if stroke_rgb:
            cmds.append(f"{stroke_rgb[0]:.2f} {stroke_rgb[1]:.2f} {stroke_rgb[2]:.2f} RG {line_width:.1f} w ")
        if fill_rgb:
            cmds.append(f"{fill_rgb[0]:.2f} {fill_rgb[1]:.2f} {fill_rgb[2]:.2f} rg ")

        if fill_rgb and stroke_rgb:
            op = "B"
        elif fill_rgb:
            op = "f"
        elif stroke_rgb:
            op = "S"
        else:
            return

        cmds.append(f"{x:.1f} {y:.1f} {w:.1f} {h:.1f} re {op}\n")
        self.current_stream.append("".join(cmds))

    def draw_line(
        x1: float,
        y1: float,
        x2: float,
        y2: float,
        stroke_rgb: Tuple[float, float, float] = (0.8, 0.8, 0.8),
        line_width: float = 0.5,
        target_stream: Optional[List[str]] = None,
    ) -> None:
        """Draw a 2D line segment."""
        cmd = f"{stroke_rgb[0]:.2f} {stroke_rgb[1]:.2f} {stroke_rgb[2]:.2f} RG {line_width:.1f} w {x1:.1f} {y1:.1f} m {x2:.1f} {y2:.1f} l S\n"
        if target_stream is not None:
            target_stream.append(cmd)

    def build_pdf(self, header_title: str, report_date: str, company_name: str) -> bytes:
        """Compile pages, stamp running headers/footers with dynamic page counts, and return bytes."""
        total_pages = len(self.pages)

        # Stamp headers and footers on each page (except top header on page 1)
        for p_idx, stream in enumerate(self.pages):
            page_num = p_idx + 1

            # Header on pages 2..N
            if page_num > 1:
                hdr_y = self.height - 30.0
                stream.append(
                    f"BT /F2 8 Tf 0.35 0.38 0.45 rg 40.0 {hdr_y:.1f} Td ({header_title}) Tj ET\n"
                )
                date_txt = f"{report_date}"
                stream.append(
                    f"BT /F1 8 Tf 0.5 0.5 0.5 rg {self.width - 40.0 - (len(date_txt) * 5.0):.1f} {hdr_y:.1f} Td ({date_txt}) Tj ET\n"
                )
                stream.append(f"0.85 0.85 0.88 RG 0.5 w 40.0 {hdr_y - 4.0:.1f} m {self.width - 40.0:.1f} {hdr_y - 4.0:.1f} l S\n")

            # Footer on all pages
            ftr_y = 28.0
            stream.append(f"0.85 0.85 0.88 RG 0.5 w 40.0 {ftr_y + 10.0:.1f} m {self.width - 40.0:.1f} {ftr_y + 10.0:.1f} l S\n")
            comp_txt = f"{company_name} — Valuation Memorandum"
            stream.append(
                f"BT /F1 7.5 Tf 0.4 0.4 0.4 rg 40.0 {ftr_y:.1f} Td ({comp_txt}) Tj ET\n"
            )
            pg_txt = f"Page {page_num} of {total_pages}"
            mid_x = (self.width / 2.0) - (len(pg_txt) * 2.5)
            stream.append(
                f"BT /F2 7.5 Tf 0.2 0.3 0.6 rg {mid_x:.1f} {ftr_y:.1f} Td ({pg_txt}) Tj ET\n"
            )
            disclaim_txt = "Analytical & Illustrative Only • Not Investment Advice"
            stream.append(
                f"BT /F1 7.0 Tf 0.5 0.5 0.5 rg {self.width - 40.0 - (len(disclaim_txt) * 4.2):.1f} {ftr_y:.1f} Td ({disclaim_txt}) Tj ET\n"
            )

        # Assemble PDF Objects
        buf = io.BytesIO()
        buf.write(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
        offsets: List[int] = []

        # 1: Catalog
        offsets.append(buf.tell())
        buf.write(b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n")

        # 2: Pages
        offsets.append(buf.tell())
        kids = " ".join([f"{3 + i * 2} 0 R" for i in range(total_pages)])
        buf.write(f"2 0 obj\n<< /Type /Pages /Kids [{kids}] /Count {total_pages} >>\nendobj\n".encode("ascii"))

        # Font object indices
        f1_idx = 3 + total_pages * 2
        f2_idx = f1_idx + 1
        f3_idx = f1_idx + 2

        for i, page_cmds in enumerate(self.pages):
            page_obj_idx = 3 + i * 2
            content_obj_idx = page_obj_idx + 1
            raw_bytes = "".join(page_cmds).encode("latin-1", errors="replace")

            # Page object
            offsets.append(buf.tell())
            buf.write(
                f"{page_obj_idx} 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 {self.width:.1f} {self.height:.1f}] "
                f"/Resources << /Font << /F1 {f1_idx} 0 R /F2 {f2_idx} 0 R /F3 {f3_idx} 0 R >> >> "
                f"/Contents {content_obj_idx} 0 R >>\nendobj\n".encode("ascii")
            )

            # Contents object
            offsets.append(buf.tell())
            buf.write(f"{content_obj_idx} 0 obj\n<< /Length {len(raw_bytes)} >>\nstream\n".encode("ascii"))
            buf.write(raw_bytes)
            buf.write(b"\nendstream\nendobj\n")

        # Fonts: F1 = Helvetica, F2 = Helvetica-Bold, F3 = Helvetica-Oblique
        offsets.append(buf.tell())
        buf.write(f"{f1_idx} 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>\nendobj\n".encode("ascii"))
        offsets.append(buf.tell())
        buf.write(f"{f2_idx} 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold >>\nendobj\n".encode("ascii"))
        offsets.append(buf.tell())
        buf.write(f"{f3_idx} 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Oblique >>\nendobj\n".encode("ascii"))

        # Cross-reference table
        xref_offset = buf.tell()
        num_objs = len(offsets) + 1
        buf.write(f"xref\n0 {num_objs}\n0000000000 65535 f \n".encode("ascii"))
        for off in offsets:
            buf.write(f"{off:010d} 00000 n \n".encode("ascii"))

        # Trailer
        buf.write(f"trailer\n<< /Size {num_objs} /Root 1 0 R >>\nstartxref\n{xref_offset}\n%%EOF\n".encode("ascii"))
        return buf.getvalue()


class PdfReportGenerator:
    """High-level builder transforming ReportBundle domain models into structured PDF reports."""

    @classmethod
    def generate_pdf(cls, bundle: ReportBundle) -> bytes:
        """Construct full PDF report from bundle."""
        canvas = _PdfCanvas()
        meta = bundle.config.metadata
        sec = bundle.config.sections

        # 1. Title Banner & Cover Box
        cls._render_cover_header(canvas, bundle)

        # 2. Executive Valuation Summary
        if sec.include_executive_summary or sec.include_overview:
            cls._render_executive_summary(canvas, bundle)

        # 3. Historical Financial Analysis
        if sec.include_historical_analysis and bundle.historical_bundle and bundle.historical_bundle.periods:
            cls._render_historical_section(canvas, bundle)

        # 4. Forecast Projections & UFCF
        if sec.include_forecast_projections and bundle.forecast_result:
            cls._render_forecast_section(canvas, bundle)

        # 5. WACC & Capital Structure
        if sec.include_wacc_analysis and bundle.wacc_result:
            cls._render_wacc_section(canvas, bundle)

        # 6. DCF Valuation & Equity Bridge
        if sec.include_dcf_valuation and bundle.dcf_result:
            cls._render_dcf_section(canvas, bundle)

        # 7. Scenario Analysis (Base / Bull / Bear)
        if sec.include_scenario_analysis and bundle.scenario_result:
            cls._render_scenarios_section(canvas, bundle)

        # 8. Sensitivity Matrix & Simulation
        if sec.include_sensitivity_simulation and (bundle.sensitivity_matrix_result or bundle.monte_carlo_result):
            cls._render_sensitivity_section(canvas, bundle)

        # 9. Disclosures, Quality Issues & Disclaimers
        if sec.include_disclosures_limitations or sec.include_appendix:
            cls._render_disclosures_section(canvas, bundle)

        return canvas.build_pdf(
            header_title=meta.title,
            report_date=meta.report_date,
            company_name=bundle.company_name,
        )

    @classmethod
    def _render_cover_header(cls, c: _PdfCanvas, bundle: ReportBundle) -> None:
        """Render publication-grade title banner and metadata box."""
        meta = bundle.config.metadata

        # Header Banner Box
        banner_height = 68.0
        c.draw_rect(c.left_margin, c.y - banner_height, c.content_width, banner_height, fill_rgb=(0.12, 0.23, 0.54))

        # Title & Subtitle inside banner
        c.draw_text(meta.title, c.left_margin + 16.0, c.y - 24.0, font="F2", size=15.0, r=1.0, g=1.0, b=1.0)
        sub = meta.subtitle or "AI-Powered DCF Valuation and Sensitivity Engine"
        c.draw_text(sub, c.left_margin + 16.0, c.y - 42.0, font="F3", size=9.5, r=0.85, g=0.90, b=1.0)

        # Tag pill
        tag_text = f"CURRENCY: {meta.reporting_currency} | DATE: {meta.report_date}"
        c.draw_text(tag_text, c.left_margin + 16.0, c.y - 58.0, font="F2", size=7.5, r=0.7, g=0.8, b=1.0)

        c.y -= banner_height + 14.0

        # Metadata Row
        c.draw_rect(c.left_margin, c.y - 28.0, c.content_width, 28.0, fill_rgb=(0.96, 0.97, 0.99), stroke_rgb=(0.85, 0.88, 0.92))
        comp_str = f"Company: {bundle.company_name}" + (f" ({bundle.ticker})" if bundle.ticker else "")
        c.draw_text(comp_str, c.left_margin + 10.0, c.y - 18.0, font="F2", size=9.0, r=0.1, g=0.15, b=0.3)

        proj_str = f"Project: {meta.project_name or f'Project #{bundle.project_id}'}"
        c.draw_text(proj_str, c.left_margin + 200.0, c.y - 18.0, font="F1", size=8.5, r=0.2, g=0.25, b=0.35)

        by_str = f"Prepared By: {meta.prepared_by or 'Valuation Analyst'}"
        c.draw_text(by_str, c.left_margin + 360.0, c.y - 18.0, font="F1", size=8.5, r=0.2, g=0.25, b=0.35)

        c.y -= 38.0

    @classmethod
    def _render_executive_summary(cls, c: _PdfCanvas, bundle: ReportBundle) -> None:
        """Render high-level KPI cards and valuation conclusion overview."""
        c.ensure_space(110.0)
        cls._render_section_title(c, "1. Executive Valuation Summary")

        dcf = bundle.dcf_result
        meta = bundle.config.metadata

        # 4 KPI Highlight Cards
        card_w = (c.content_width - 24.0) / 4.0
        card_h = 48.0

        ev_val = f"${dcf.enterprise_value:,.1f}M" if dcf and dcf.enterprise_value else "N/A"
        eq_val = f"${dcf.equity_value:,.1f}M" if dcf and dcf.equity_value else "N/A"
        sp_val = f"${dcf.implied_share_price:,.2f}" if dcf and dcf.implied_share_price else "N/A"
        wacc_val = f"{dcf.wacc * 100.0:.2f}%" if dcf and dcf.wacc else "N/A"

        cards = [
            ("Enterprise Value", ev_val, "PV Cash Flows + PV Terminal"),
            ("Equity Value", eq_val, "EV Less Net Debt Claims"),
            ("Implied Share Price", sp_val, "Per Diluted Common Share"),
            ("Discount Rate (WACC)", wacc_val, "Blended Cost of Capital"),
        ]

        for i, (title, val_str, sub) in enumerate(cards):
            card_x = c.left_margin + i * (card_w + 8.0)
            c.draw_rect(card_x, c.y - card_h, card_w, card_h, fill_rgb=(0.95, 0.97, 1.0), stroke_rgb=(0.75, 0.82, 0.95), line_width=1.0)
            c.draw_text(title, card_x + 8.0, c.y - 14.0, font="F2", size=7.5, r=0.2, g=0.3, b=0.6)
            c.draw_text(val_str, card_x + 8.0, c.y - 30.0, font="F2", size=12.0, r=0.08, g=0.15, b=0.45)
            c.draw_text(sub, card_x + 8.0, c.y - 42.0, font="F1", size=6.5, r=0.45, g=0.5, b=0.6)

        c.y -= card_h + 14.0

        # Narrative / Summary Commentary
        if meta.narrative_summary:
            c.ensure_space(35.0)
            c.draw_rect(c.left_margin, c.y - 26.0, c.content_width, 26.0, fill_rgb=(0.98, 0.98, 0.99), stroke_rgb=(0.9, 0.9, 0.9))
            c.draw_text("Executive Narrative:", c.left_margin + 8.0, c.y - 11.0, font="F2", size=8.0, r=0.1, g=0.1, b=0.1)
            # Truncate clean string
            clean_narr = meta.narrative_summary[:140] + ("..." if len(meta.narrative_summary) > 140 else "")
            c.draw_text(clean_narr, c.left_margin + 8.0, c.y - 21.0, font="F1", size=7.5, r=0.3, g=0.3, b=0.3)
            c.y -= 34.0

    @classmethod
    def _render_historical_section(cls, c: _PdfCanvas, bundle: ReportBundle) -> None:
        """Render historical financial performance table."""
        hb = bundle.historical_bundle
        if not hb or not hb.periods:
            return

        c.ensure_space(140.0)
        cls._render_section_title(c, "2. Historical Financial Analysis")

        periods = [p.label for p in hb.periods[-5:]]  # Display up to last 5 periods
        num_cols = len(periods)
        label_w = 172.0
        val_col_w = (c.content_width - label_w) / max(num_cols, 1)

        # Header Row
        c.draw_rect(c.left_margin, c.y - 18.0, c.content_width, 18.0, fill_rgb=(0.12, 0.23, 0.54))
        c.draw_text("Financial Metric ($M)", c.left_margin + 6.0, c.y - 13.0, font="F2", size=8.0, r=1.0, g=1.0, b=1.0)
        for i, p_label in enumerate(periods):
            x = c.left_margin + label_w + i * val_col_w + val_col_w - 6.0 - (len(p_label) * 5.0)
            c.draw_text(p_label, x, c.y - 13.0, font="F2", size=8.0, r=1.0, g=1.0, b=1.0)
        c.y -= 18.0

        rows = [
            ("Revenue", "revenue", False),
            ("Revenue Growth YoY", "revenue_growth_yoy", True),
            ("Gross Profit", "gross_profit", False),
            ("Gross Profit Margin", "gross_margin", True),
            ("EBITDA", "ebitda", False),
            ("EBITDA Margin", "ebitda_margin", True),
            ("Operating Income (EBIT)", "operating_income", False),
            ("Operating Cash Flow (CFO)", "operating_cash_flow", False),
            ("Capital Expenditures (CapEx)", "capital_expenditures", False),
            ("Free Cash Flow (UFCF Est.)", "ufcf_estimate", False),
        ]

        for r_idx, (label, mcode, is_pct) in enumerate(rows):
            c.ensure_space(14.0)
            bg = (0.97, 0.98, 1.0) if r_idx % 2 == 1 else (1.0, 1.0, 1.0)
            c.draw_rect(c.left_margin, c.y - 14.0, c.content_width, 14.0, fill_rgb=bg, stroke_rgb=(0.9, 0.9, 0.92))
            c.draw_text(label, c.left_margin + 6.0, c.y - 10.0, font="F2" if "Revenue" in label or "Free Cash" in label else "F1", size=7.5, r=0.15, g=0.15, b=0.2)

            for i, p_label in enumerate(periods):
                val = None
                p_m = hb.metrics_by_period.get(p_label, {})
                if mcode in p_m:
                    val = p_m[mcode].value
                elif mcode in ("operating_cash_flow", "capital_expenditures", "ufcf_estimate"):
                    cf = hb.cash_flow_metrics.get(p_label)
                    if cf:
                        val = cf.capex_magnitude if mcode == "capital_expenditures" else getattr(cf, mcode, None)

                if val is not None:
                    txt = f"{val:.1f}%" if is_pct else f"${val:,.1f}"
                else:
                    txt = "-"

                tx_x = c.left_margin + label_w + i * val_col_w + val_col_w - 6.0 - (len(txt) * 4.5)
                c.draw_text(txt, tx_x, c.y - 10.0, font="F1", size=7.5, r=0.2, g=0.2, b=0.2)

            c.y -= 14.0

        c.y -= 10.0

    @classmethod
    def _render_forecast_section(cls, c: _PdfCanvas, bundle: ReportBundle) -> None:
        """Render forecast assumptions, income statement, and UFCF derivations."""
        fc = bundle.forecast_result
        if not fc:
            return

        c.ensure_space(140.0)
        cls._render_section_title(c, "3. Forecast Assumptions & Projections")

        years = fc.projected_years
        num_cols = len(years)
        label_w = 172.0
        val_col_w = (c.content_width - label_w) / max(num_cols, 1)

        c.draw_rect(c.left_margin, c.y - 18.0, c.content_width, 18.0, fill_rgb=(0.12, 0.23, 0.54))
        c.draw_text("Forecast Step / Driver ($M)", c.left_margin + 6.0, c.y - 13.0, font="F2", size=8.0, r=1.0, g=1.0, b=1.0)
        for i, yr in enumerate(years):
            x = c.left_margin + label_w + i * val_col_w + val_col_w - 6.0 - (len(yr) * 5.0)
            c.draw_text(yr, x, c.y - 13.0, font="F2", size=8.0, r=1.0, g=1.0, b=1.0)
        c.y -= 18.0

        flines = [
            ("Revenue", [f"${v:,.1f}" for v in fc.revenue], True),
            ("Revenue Growth Rate", [f"{v:.1f}%" for v in fc.revenue_growth_rate], False),
            ("Gross Profit", [f"${v:,.1f}" for v in fc.gross_profit], False),
            ("EBITDA", [f"${v:,.1f}" for v in fc.ebitda], True),
            ("Operating Income (EBIT)", [f"${v:,.1f}" for v in fc.ebit], False),
            ("NOPAT (EBIT x (1 - t))", [f"${v:,.1f}" for v in fc.nopat], True),
            ("(+) D&A Expense", [f"${v:,.1f}" for v in fc.depreciation_and_amortization], False),
            ("(-) Capital Expenditures", [f"-${v:,.1f}" for v in fc.capex], False),
            ("(-) Change in Operating NWC", [f"-${v:,.1f}" for v in fc.delta_operating_nwc], False),
            ("(=) Unlevered Free Cash Flow (UFCF)", [f"${v:,.1f}" for v in fc.ufcf], True),
        ]

        for r_idx, (label, val_strs, is_highlight) in enumerate(flines):
            c.ensure_space(14.0)
            bg = (0.92, 0.95, 1.0) if "(=)" in label else ((0.98, 0.98, 0.99) if r_idx % 2 == 1 else (1.0, 1.0, 1.0))
            c.draw_rect(c.left_margin, c.y - 14.0, c.content_width, 14.0, fill_rgb=bg, stroke_rgb=(0.9, 0.9, 0.92))
            c.draw_text(label, c.left_margin + 6.0, c.y - 10.0, font="F2" if is_highlight else "F1", size=7.5, r=0.1 if is_highlight else 0.2, g=0.15 if is_highlight else 0.2, b=0.35 if is_highlight else 0.2)

            for i, v_txt in enumerate(val_strs):
                tx_x = c.left_margin + label_w + i * val_col_w + val_col_w - 6.0 - (len(v_txt) * 4.5)
                c.draw_text(v_txt, tx_x, c.y - 10.0, font="F2" if is_highlight else "F1", size=7.5, r=0.1, g=0.15, b=0.3)

            c.y -= 14.0

        c.y -= 10.0

    @classmethod
    def _render_wacc_section(cls, c: _PdfCanvas, bundle: ReportBundle) -> None:
        """Render WACC parameters and capital structure breakdown."""
        wacc = bundle.wacc_result
        if not wacc:
            return

        c.ensure_space(110.0)
        cls._render_section_title(c, "4. WACC & Cost of Capital")

        # Two-column layout: Left = Cost of Equity & Debt, Right = Capital Structure & Blended WACC
        half_w = (c.content_width - 12.0) / 2.0
        h_box = 85.0

        # Left Box (Cost of Capital Components)
        c.draw_rect(c.left_margin, c.y - h_box, half_w, h_box, fill_rgb=(0.98, 0.99, 1.0), stroke_rgb=(0.85, 0.88, 0.95))
        c.draw_text("Cost of Equity & Debt (CAPM)", c.left_margin + 8.0, c.y - 14.0, font="F2", size=8.5, r=0.15, g=0.25, b=0.55)

        eq = wacc.cost_of_equity
        debt = wacc.cost_of_debt
        capm_lines = [
            f"Risk-Free Rate (Rf): {eq.risk_free_rate:.2f}%",
            f"Beta: {eq.beta:.2f}x | Equity Risk Premium: {eq.equity_risk_premium:.2f}%",
            f"Cost of Equity (Ke): {eq.cost_of_equity:.2f}%",
            f"Pre-tax Cost of Debt (Kd): {debt.pre_tax_cost_of_debt:.2f}%",
            f"Marginal Tax Rate (t): {debt.effective_tax_rate:.2f}%",
            f"After-tax Cost of Debt (Kd x (1 - t)): {debt.after_tax_cost_of_debt:.2f}%",
        ]
        for idx, line in enumerate(capm_lines):
            c.draw_text(line, c.left_margin + 8.0, c.y - 26.0 - idx * 10.0, font="F1", size=7.5, r=0.2, g=0.25, b=0.3)

        # Right Box (Weights & Blended WACC)
        rx = c.left_margin + half_w + 12.0
        c.draw_rect(rx, c.y - h_box, half_w, h_box, fill_rgb=(0.98, 0.99, 1.0), stroke_rgb=(0.85, 0.88, 0.95))
        c.draw_text("Capital Structure & Blended WACC", rx + 8.0, c.y - 14.0, font="F2", size=8.5, r=0.15, g=0.25, b=0.55)

        cs = wacc.capital_structure
        cs_lines = [
            f"Equity Value (E): ${cs.equity_value:,.1f}M ({cs.weight_equity * 100.0:.1f}%)",
            f"Total Debt (D): ${cs.total_debt:,.1f}M ({cs.weight_debt * 100.0:.1f}%)",
            f"Total Capital (E + D): ${cs.total_capital:,.1f}M",
            f"Formula: (We x Ke) + (Wd x Kd_after)",
            f"RESULTING WACC: {wacc.wacc * 100.0:.2f}%",
        ]
        for idx, line in enumerate(cs_lines):
            is_wacc = "RESULTING" in line
            c.draw_text(line, rx + 8.0, c.y - 26.0 - idx * 12.0, font="F2" if is_wacc else "F1", size=8.5 if is_wacc else 7.5, r=0.1 if is_wacc else 0.2, g=0.2 if is_wacc else 0.25, b=0.55 if is_wacc else 0.3)

        c.y -= h_box + 12.0

    @classmethod
    def _render_dcf_section(cls, c: _PdfCanvas, bundle: ReportBundle) -> None:
        """Render discounting schedule, terminal enterprise value, and equity bridge."""
        dcf = bundle.dcf_result
        if not dcf:
            return

        c.ensure_space(160.0)
        cls._render_section_title(c, "5. DCF Valuation & Equity Bridge")

        half_w = (c.content_width - 12.0) / 2.0

        # Left Column: Terminal Value & EV Breakdown
        c.draw_rect(c.left_margin, c.y - 130.0, half_w, 130.0, fill_rgb=(0.99, 0.99, 1.0), stroke_rgb=(0.85, 0.88, 0.95))
        c.draw_text("Enterprise Value Derivation", c.left_margin + 8.0, c.y - 14.0, font="F2", size=8.5, r=0.15, g=0.25, b=0.55)

        ev_lines = [
            ("Timing Convention", dcf.discounting_convention.replace("_", " ").title()),
            ("PV of Forecast UFCF", f"${dcf.pv_forecast_cash_flows:,.1f}M"),
            ("Terminal Value Method", dcf.terminal_inputs.method.replace("_", " ").title()),
            ("Perpetual g / Exit Mult.", f"{dcf.terminal_inputs.perpetual_growth_rate:.2f}%" if dcf.terminal_inputs.perpetual_growth_rate else f"{dcf.terminal_inputs.exit_multiple:.1f}x"),
            ("Nominal Terminal Value (TV_N)", f"${dcf.terminal_value:,.1f}M"),
            ("PV of Terminal Value", f"${dcf.pv_terminal_value:,.1f}M"),
            ("Terminal Value % of EV", f"{dcf.terminal_value_pct_of_ev:.1f}%"),
            ("ENTERPRISE VALUE (EV)", f"${dcf.enterprise_value:,.1f}M"),
        ]

        for idx, (label, val_str) in enumerate(ev_lines):
            is_ev = "ENTERPRISE" in label
            c.draw_text(label, c.left_margin + 8.0, c.y - 28.0 - idx * 13.0, font="F2" if is_ev else "F1", size=8.0 if is_ev else 7.5, r=0.1 if is_ev else 0.25, g=0.15 if is_ev else 0.25, b=0.45 if is_ev else 0.3)
            tx_x = c.left_margin + half_w - 8.0 - (len(val_str) * 4.8)
            c.draw_text(val_str, tx_x, c.y - 28.0 - idx * 13.0, font="F2" if is_ev else "F1", size=8.0 if is_ev else 7.5, r=0.1 if is_ev else 0.2, g=0.15 if is_ev else 0.2, b=0.45 if is_ev else 0.25)

        # Right Column: Enterprise-to-Equity Bridge
        rx = c.left_margin + half_w + 12.0
        c.draw_rect(rx, c.y - 130.0, half_w, 130.0, fill_rgb=(0.99, 0.99, 1.0), stroke_rgb=(0.85, 0.88, 0.95))
        c.draw_text("Enterprise-to-Equity Value Bridge", rx + 8.0, c.y - 14.0, font="F2", size=8.5, r=0.15, g=0.25, b=0.55)

        b = dcf.bridge_inputs
        bridge_lines = [
            ("Enterprise Value", f"${dcf.enterprise_value:,.1f}M"),
            ("(+) Cash & Cash Equivalents", f"+${b.cash_and_equivalents:,.1f}M"),
            ("(-) Interest-Bearing Debt", f"-${b.debt_value:,.1f}M"),
            ("(-) Minority Interest", f"-${b.minority_interest:,.1f}M"),
            ("(-) Preferred Stock Equity", f"-${b.preferred_equity:,.1f}M"),
            ("(=) IMPLIED EQUITY VALUE", f"${dcf.equity_value:,.1f}M" if dcf.equity_value else "N/A"),
            ("(/) Diluted Common Shares", f"{dcf.diluted_shares:,.1f}M"),
            ("(=) INTRINSIC VALUE / SHARE", f"${dcf.implied_share_price:,.2f}" if dcf.implied_share_price else "N/A"),
        ]

        for idx, (label, val_str) in enumerate(bridge_lines):
            is_final = "INTRINSIC" in label or "IMPLIED EQUITY" in label
            c.draw_text(label, rx + 8.0, c.y - 28.0 - idx * 13.0, font="F2" if is_final else "F1", size=8.0 if is_final else 7.5, r=0.08 if is_final else 0.25, g=0.15 if is_final else 0.25, b=0.45 if is_final else 0.3)
            tx_x = rx + half_w - 8.0 - (len(val_str) * 4.8)
            c.draw_text(val_str, tx_x, c.y - 28.0 - idx * 13.0, font="F2" if is_final else "F1", size=8.5 if is_final else 7.5, r=0.08 if is_final else 0.2, g=0.15 if is_final else 0.2, b=0.45 if is_final else 0.25)

        c.y -= 142.0

    @classmethod
    def _render_scenarios_section(cls, c: _PdfCanvas, bundle: ReportBundle) -> None:
        """Render Base, Bull, and Bear scenario comparison table."""
        sc = bundle.scenario_result
        if not sc:
            return

        c.ensure_space(110.0)
        cls._render_section_title(c, "6. Scenario Analysis (Base / Bull / Bear)")

        b, u, d = sc.base_case, sc.bull_case, sc.bear_case
        label_w = 172.0
        val_w = (c.content_width - label_w) / 3.0

        c.draw_rect(c.left_margin, c.y - 18.0, c.content_width, 18.0, fill_rgb=(0.12, 0.23, 0.54))
        c.draw_text("Scenario Driver / Metric", c.left_margin + 6.0, c.y - 13.0, font="F2", size=8.0, r=1.0, g=1.0, b=1.0)
        for i, header in enumerate(["Base Case", "Bull Case", "Bear Case"]):
            x = c.left_margin + label_w + i * val_w + val_w - 8.0 - (len(header) * 5.0)
            c.draw_text(header, x, c.y - 13.0, font="F2", size=8.0, r=1.0, g=1.0, b=1.0)
        c.y -= 18.0

        sc_rows = [
            ("Revenue Growth Override", f"{b.revenue_growth_override_pp:+.1f} pp", f"{u.revenue_growth_override_pp:+.1f} pp", f"{d.revenue_growth_override_pp:+.1f} pp"),
            ("Operating Margin Override", f"{b.margin_override_pp:+.1f} pp", f"{u.margin_override_pp:+.1f} pp", f"{d.margin_override_pp:+.1f} pp"),
            ("WACC Adjustment", f"{b.wacc_adjustment_bps:+d} bps", f"{u.wacc_adjustment_bps:+d} bps", f"{d.wacc_adjustment_bps:+d} bps"),
            ("Effective WACC", f"{b.effective_wacc:.2f}%", f"{u.effective_wacc:.2f}%", f"{d.effective_wacc:.2f}%"),
            ("Enterprise Value ($M)", f"${b.enterprise_value:,.1f}" if b.enterprise_value else "N/A", f"${u.enterprise_value:,.1f}" if u.enterprise_value else "N/A", f"${d.enterprise_value:,.1f}" if d.enterprise_value else "N/A"),
            ("Equity Value ($M)", f"${b.equity_value:,.1f}" if b.equity_value else "N/A", f"${u.equity_value:,.1f}" if u.equity_value else "N/A", f"${d.equity_value:,.1f}" if d.equity_value else "N/A"),
            ("Implied Share Price", f"${b.implied_share_price:,.2f}" if b.implied_share_price else "N/A", f"${u.implied_share_price:,.2f}" if u.implied_share_price else "N/A", f"${d.implied_share_price:,.2f}" if d.implied_share_price else "N/A"),
            ("Upside / Downside vs. Base", "0.0%", f"{u.upside_downside_pct:+.1f}%" if u.upside_downside_pct else "N/A", f"{d.upside_downside_pct:+.1f}%" if d.upside_downside_pct else "N/A"),
        ]

        for r_idx, (label, b_txt, u_txt, d_txt) in enumerate(sc_rows):
            c.ensure_space(14.0)
            is_sp = "Implied Share" in label
            bg = (0.95, 0.97, 1.0) if is_sp else ((0.98, 0.98, 0.99) if r_idx % 2 == 1 else (1.0, 1.0, 1.0))
            c.draw_rect(c.left_margin, c.y - 14.0, c.content_width, 14.0, fill_rgb=bg, stroke_rgb=(0.9, 0.9, 0.92))
            c.draw_text(label, c.left_margin + 6.0, c.y - 10.0, font="F2" if is_sp else "F1", size=7.5, r=0.1 if is_sp else 0.2, g=0.15 if is_sp else 0.2, b=0.35 if is_sp else 0.2)

            for i, val_str in enumerate([b_txt, u_txt, d_txt]):
                tx_x = c.left_margin + label_w + i * val_w + val_w - 8.0 - (len(val_str) * 4.5)
                c.draw_text(val_str, tx_x, c.y - 10.0, font="F2" if is_sp else "F1", size=7.5, r=0.1 if is_sp else 0.2, g=0.15 if is_sp else 0.2, b=0.35 if is_sp else 0.2)

            c.y -= 14.0

        c.y -= 10.0

    @classmethod
    def _render_sensitivity_section(cls, c: _PdfCanvas, bundle: ReportBundle) -> None:
        """Render 2D sensitivity matrix and Monte Carlo summary percentiles."""
        matrix = bundle.sensitivity_matrix_result
        mc = bundle.monte_carlo_result
        if not matrix and not mc:
            return

        c.ensure_space(130.0)
        cls._render_section_title(c, "7. Sensitivity Analysis & Simulation")

        # 2D Matrix
        if matrix:
            c.draw_text(f"Two-Dimensional Valuation Sensitivity Matrix ({matrix.metric_label})", c.left_margin, c.y - 8.0, font="F2", size=8.0, r=0.15, g=0.25, b=0.55)
            c.y -= 14.0

            row_headers = [f"{r:.2f}%" for r in matrix.row_values]
            col_headers = [f"{c:.2f}%" if "%" in matrix.col_label else f"{c:.1f}x" for c in matrix.col_values]
            n_cols = len(col_headers)
            w_col = (c.content_width - 60.0) / max(n_cols, 1)

            # Header row
            c.draw_rect(c.left_margin, c.y - 14.0, c.content_width, 14.0, fill_rgb=(0.15, 0.28, 0.6))
            c.draw_text(f"WACC \\ {matrix.col_label}", c.left_margin + 4.0, c.y - 10.0, font="F2", size=6.5, r=1.0, g=1.0, b=1.0)
            for j, ch in enumerate(col_headers):
                tx_x = c.left_margin + 60.0 + j * w_col + w_col - 4.0 - (len(ch) * 4.0)
                c.draw_text(ch, tx_x, c.y - 10.0, font="F2", size=6.5, r=1.0, g=1.0, b=1.0)
            c.y -= 14.0

            for i, rh in enumerate(row_headers):
                c.ensure_space(12.0)
                c.draw_rect(c.left_margin, c.y - 12.0, c.content_width, 12.0, fill_rgb=(0.98, 0.98, 0.99) if i % 2 == 1 else (1.0, 1.0, 1.0), stroke_rgb=(0.9, 0.9, 0.92))
                c.draw_text(rh, c.left_margin + 4.0, c.y - 9.0, font="F2", size=6.5, r=0.2, g=0.2, b=0.2)

                for j in range(n_cols):
                    cell = matrix.cells[i][j]
                    if cell.is_valid and cell.output_value is not None:
                        is_base = cell.is_baseline
                        val_txt = f"${cell.output_value:,.2f}" if "Share" in matrix.metric_label else f"${cell.output_value:,.0f}M"
                        if is_base:
                            val_txt += " *"
                            c.draw_rect(c.left_margin + 60.0 + j * w_col, c.y - 12.0, w_col, 12.0, fill_rgb=(1.0, 0.95, 0.78))
                        tx_x = c.left_margin + 60.0 + j * w_col + w_col - 4.0 - (len(val_txt) * 4.0)
                        c.draw_text(val_txt, tx_x, c.y - 9.0, font="F2" if is_base else "F1", size=6.0, r=0.1 if is_base else 0.2, g=0.15 if is_base else 0.2, b=0.35 if is_base else 0.2)
                    else:
                        c.draw_rect(c.left_margin + 60.0 + j * w_col, c.y - 12.0, w_col, 12.0, fill_rgb=(0.95, 0.95, 0.95))
                        tx_x = c.left_margin + 60.0 + j * w_col + w_col - 4.0 - 20.0
                        c.draw_text("INV", tx_x, c.y - 9.0, font="F1", size=5.5, r=0.8, g=0.2, b=0.2)

                c.y -= 12.0

            c.y -= 10.0

        # Monte Carlo Simulation
        if mc and mc.summary_stats:
            c.ensure_space(60.0)
            c.draw_text(
                f"Monte Carlo Probabilistic Simulation ({mc.total_iterations} draws | Seed: {mc.config.random_seed})",
                c.left_margin,
                c.y - 8.0,
                font="F2",
                size=8.0,
                r=0.15,
                g=0.25,
                b=0.55,
            )
            c.y -= 14.0

            mc_cols = ["Metric", "Mean", "Median (P50)", "Std Dev", "P10", "P90"]
            w_mc = c.content_width / len(mc_cols)
            c.draw_rect(c.left_margin, c.y - 14.0, c.content_width, 14.0, fill_rgb=(0.2, 0.35, 0.65))
            for k, mh in enumerate(mc_cols):
                tx_x = c.left_margin + k * w_mc + 6.0
                c.draw_text(mh, tx_x, c.y - 10.0, font="F2", size=6.5, r=1.0, g=1.0, b=1.0)
            c.y -= 14.0

            for m_key, m_label, is_sp in [
                ("enterprise_value", "Enterprise Value ($M)", False),
                ("equity_value", "Equity Value ($M)", False),
                ("implied_share_price", "Implied Share Price", True),
            ]:
                s = mc.summary_stats.get(m_key)
                if not s:
                    continue
                c.draw_rect(c.left_margin, c.y - 12.0, c.content_width, 12.0, fill_rgb=(0.98, 0.98, 0.99), stroke_rgb=(0.9, 0.9, 0.92))
                fmt = "${:,.2f}" if is_sp else "${:,.1f}"
                vals = [m_label, fmt.format(s.mean), fmt.format(s.median), fmt.format(s.std_dev), fmt.format(s.p10), fmt.format(s.p90)]
                for k, v_txt in enumerate(vals):
                    tx_x = c.left_margin + k * w_mc + 6.0
                    c.draw_text(v_txt, tx_x, c.y - 9.0, font="F2" if k == 0 else "F1", size=6.5, r=0.15, g=0.2, b=0.3)
                c.y -= 12.0

            c.y -= 10.0

    @classmethod
    def _render_disclosures_section(cls, c: _PdfCanvas, bundle: ReportBundle) -> None:
        """Render data quality issues, limitations, and analytical disclaimers."""
        c.ensure_space(110.0)
        cls._render_section_title(c, "8. Data Quality, Disclosures & Limitations")

        # Warnings / Diagnostics
        has_warnings = False
        all_warnings = bundle.missing_models_diagnostics + bundle.validation_warnings + bundle.data_quality_issues
        if all_warnings:
            has_warnings = True
            c.draw_rect(c.left_margin, c.y - (len(all_warnings[:6]) * 11.0 + 12.0), c.content_width, (len(all_warnings[:6]) * 11.0 + 12.0), fill_rgb=(1.0, 0.98, 0.95), stroke_rgb=(0.95, 0.8, 0.6))
            c.draw_text("Audit & Diagnostic Findings:", c.left_margin + 6.0, c.y - 10.0, font="F2", size=7.5, r=0.6, g=0.3, b=0.1)
            for idx, w in enumerate(all_warnings[:6]):
                trunc = w[:110] + ("..." if len(w) > 110 else "")
                c.draw_text(f"• {trunc}", c.left_margin + 12.0, c.y - 20.0 - idx * 11.0, font="F1", size=7.0, r=0.35, g=0.2, b=0.1)
            c.y -= (len(all_warnings[:6]) * 11.0 + 20.0)

        # Disclaimers Box
        c.ensure_space(75.0)
        c.draw_rect(c.left_margin, c.y - 70.0, c.content_width, 70.0, fill_rgb=(0.97, 0.97, 0.98), stroke_rgb=(0.88, 0.88, 0.9))
        c.draw_text("Analytical Disclaimers & Institutional Notice:", c.left_margin + 8.0, c.y - 12.0, font="F2", size=7.5, r=0.2, g=0.2, b=0.3)

        disc_lines = [
            "1. Not Investment Advice: This report is compiled for analytical, educational, and valuation modeling purposes only.",
            "   It does not constitute investment advice, a trade recommendation, or a fairness opinion under securities regulations.",
            "2. Input Contingency: Intrinsic valuation outputs and simulated ranges are strictly conditional on user-supplied assumptions.",
            "3. Simulation Limits: Monte Carlo iterations illustrate statistical distribution behavior under specified mathematical parameters",
            "   and must not be interpreted as empirical market probability forecasts or guaranteed returns.",
        ]
        for idx, line in enumerate(disc_lines):
            c.draw_text(line, c.left_margin + 8.0, c.y - 23.0 - idx * 9.0, font="F3", size=6.5, r=0.4, g=0.4, b=0.45)

        c.y -= 78.0

    @classmethod
    def _render_section_title(cls, c: _PdfCanvas, title: str) -> None:
        """Render a clean section header with an accent rule."""
        c.draw_text(title, c.left_margin, c.y - 12.0, font="F2", size=10.0, r=0.12, g=0.23, b=0.54)
        c.draw_rect(c.left_margin, c.y - 16.0, c.content_width, 1.0, fill_rgb=(0.12, 0.23, 0.54))
        c.y -= 24.0
