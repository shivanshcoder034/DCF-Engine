# Development Roadmap
## AI-Powered DCF Valuation and Sensitivity Engine

This roadmap establishes the 12-phase engineering progression for the platform. Development progresses sequentially to maintain strict architectural separation, verifiable math, and institutional software quality.

---

### Phase 1: Project Foundation and Architecture *(Status: Complete)*
- **Objective:** Establish a clean, extensible, maintainable Python project foundation.
- **Key Deliverables:**
  - Decoupled `app/` (presentation) and `src/` (engine) repository structure.
  - Centralized application configuration (`app/config.py`) using `pathlib.Path`.
  - Streamlit application shell (`app/main.py`) with 9 planned top-level navigation sections.
  - Environment templates (`.env.example`), `.gitignore`, and pinned `requirements.txt`.
  - Initial system architecture specification (`docs/architecture.md`).

---

### Phase 2: Company Profiles & Financial Data Management *(Status: Complete)*
- **Objective:** Establish persistent company profiles, valuation project workspaces, and multi-period financial statement ingestion.
- **Key Deliverables:**
  - SQLite persistence layer via SQLAlchemy ORM models (`Company`, `ValuationProject`, `FinancialDataPoint`, `ImportBatch`).
  - Standardized schemas for Income Statements, Balance Sheets, and Cash Flow Statements.
  - Granular data classifications (`reported_actual`, `normalized`, `adjustment`, `assumption`).
  - Standard financial line-item catalog with support for custom items.
  - Multi-field validation engine distinguishing blocking errors from review warnings.
  - Complete multi-step CSV and Excel import workflow with column auto-mapping and duplicate conflict policies.
  - Traceable source provenance tracking for every stored data point.
  - Interactive company and project management interfaces with deletion safeguards.

---

### Phase 3: Historical Financial Analysis *(Status: Complete)*
- **Objective:** Compute foundational financial performance metrics, margin trends, working capital cycles, and cash flow indicators.
- **Key Deliverables:**
  - Dedicated analytical engine (`src/analysis/`) operating on verified historical records.
  - Multi-year revenue growth and Compound Annual Growth Rates (CAGR).
  - Profitability margin evolution: Gross Profit Margin, EBITDA Margin, EBIT Margin, and Net Profit Margin.
  - Operating expense and Depreciation & Amortization intensity analysis.
  - Net Working Capital (NWC), Operating NWC, and period-over-period $\Delta NWC$.
  - Working capital efficiency diagnostics: DSO, DIO, DPO, and Cash Conversion Cycle (CCC).
  - Operating cash flow analysis, CapEx intensity (% revenue), CFO Less CapEx, and historical Unlevered Free Cash Flow (UFCF) analytical estimates.
  - Multi-period formatted statement tables explicitly distinguishing reported vs. derived figures.
  - Interactive Plotly visualizations for revenue trends, margins, cash flow vs. CapEx, and working capital cycles.
  - Automated data-quality and audit diagnostics checking accounting balance sheet equilibrium and period continuity.

---

### Phase 4: Financial Forecasting & Projections Engine *(Status: Complete)*
- **Objective:** Generate deterministic multi-year forward-looking financial statement schedules and Unlevered Free Cash Flow (UFCF) projections.
- **Key Deliverables:**
  - Dedicated forecasting engine (`src/forecasting/`) calibrated from historical actuals.
  - Configurable horizon control (3 to 10 years, default 5 years).
  - Driver-based revenue projections (constant rate or year-by-year schedule).
  - Gross profit, operating expenses, and EBITDA-to-EBIT bridges.
  - Depreciation & Amortization schedules and Capital Expenditures (CapEx).
  - Operating Net Working Capital projections via turnover days (DSO, DIO, DPO) or revenue percentages.
  - Annual change in operating working capital ($\Delta\text{Operating NWC}$) and NOPAT derivations.
  - Formulaic Unlevered Free Cash Flow projections ($\text{UFCF} = \text{NOPAT} + \text{D\&A} - \text{CapEx} - \Delta\text{Operating NWC}$).
  - Scenario persistence via `ForecastModel` entities allowing users to save and reload versioned assumption sets.
  - Consolidated multi-period statement tables merging historical actuals and projected years.
  - Detailed UFCF derivation bridge table and interactive Plotly trajectory charts.

---

### Phase 5: WACC & Discount Rate Engine *(Status: Complete)*
- **Objective:** Compute a transparent, deterministic Weighted Average Cost of Capital (WACC) reflecting enterprise operating and financial risk.
- **Key Deliverables:**
  - Dedicated WACC estimation engine (`src/wacc/`) decoupled from Streamlit UI and historical records.
  - Cost of Equity computation via Capital Asset Pricing Model (CAPM): $K_e = R_f + (\beta \times \text{ERP})$.
  - Pre-tax Cost of Debt calculation supporting user-entered spreads or historical accounting interest estimates ($\text{Interest Expense} / \text{Debt}$) with non-zero denominator protection.
  - After-tax Cost of Debt: $K_{d,\text{after}} = K_d \times (1 - t)$ with source provenance tracking across manual statutory rates, Phase 4 forecast tax scenarios, or historical effective tax rates.
  - Capital structure weights: $W_e = E / (E + D)$, $W_d = D / (E + D)$ based on market capitalization or balance sheet book equity proxy (with explicit proxy warning flags).
  - Strict debt qualification: Interest-bearing debt only (Short-Term + Long-Term Debt), explicitly excluding accounts payable and operating liabilities.
  - Blended WACC formulation: $\text{WACC} = (W_e \times K_e) + (W_d \times K_{d,\text{after}})$.
  - Named WACC case persistence via `WaccModel` entities in SQLite, supporting multiple named scenarios per valuation project.
  - Streamlit interface (`app/pages/wacc.py`) featuring headline KPI cards, interactive assumption tabs, provenance notes, Plotly capital structure donut and contribution bar charts, and model audit diagnostics.

---

### Phase 6: DCF Valuation & Terminal Value Engine *(Status: Complete)*
- **Objective:** Compute enterprise value, equity value, and intrinsic share price by discounting projected Unlevered Free Cash Flows (UFCF) and adding discounted terminal enterprise value.
- **Key Deliverables:**
  - Dedicated DCF valuation package (`src/dcf/`) completely decoupled from presentation code and database direct access.
  - Multi-period cash flow discounting supporting user-configurable timing conventions: End-of-Year ($t = 1.0, \dots, N$) and Mid-Year ($t = 0.5, \dots, N - 0.5$).
  - Gordon Growth Perpetuity Model: $\text{TV} = \frac{\text{UFCF}_N \times (1 + g)}{\text{WACC} - g}$, enforcing $\text{WACC} > g$.
  - Exit Multiple Method: $\text{TV} = \text{Terminal EBITDA}_N \times \text{Exit Multiple}$.
  - Terminal value discounting aligned with explicit forecast period horizon.
  - Enterprise Value formulation: $\text{Enterprise Value} = \text{PV of Forecast UFCF} + \text{PV of Terminal Value}$.
  - Articulated Enterprise-to-Equity Value bridge: $\text{Equity Value} = \text{EV} + \text{Cash} - \text{Debt} - \text{Minority Interest} - \text{Preferred Stock} + \text{Other Adjustments}$.
  - Intrinsic share price derivation: $\text{Implied Value per Share} = \text{Equity Value} / \text{Diluted Common Shares Outstanding}$ with safe withholding when shares are unsupplied.
  - Named DCF scenario persistence via `DcfModel` in SQLite, supporting multiple named valuation cases per valuation project.
  - Streamlit interface (`app/pages/dcf.py`) featuring headline KPI metrics, interactive timing/terminal/bridge tabs, discounting schedule tables, equity bridge tables, Plotly trajectory and EV composition charts, and model audit diagnostics.

---

### Phase 7: Scenario Analysis (Base / Bull / Bear) *(Status: Complete)*
- **Objective:** Add scenario analysis capability that compares Base, Bull, and Bear valuation cases using existing forecast, WACC, and DCF engines.
- **Key Deliverables:**
  - Dedicated scenario orchestration package (`src/scenarios/`) decoupled from presentation code and database direct access.
  - Three standardized scenario cases: **Base**, **Bull**, and **Bear**.
  - Strict preservation of the Base case: uses selected saved forecast and WACC baseline without overrides.
  - Explicit user-editable overrides in well-defined units:
    - Revenue growth adjustment in percentage points (`pp`).
    - Operating margin adjustment in percentage points (`pp`).
    - Cost of capital (WACC) adjustment in basis points (`bps`, $100\text{ bps} = 1.0\%$).
    - Perpetual growth rate adjustment in basis points (`bps`) for Gordon Growth.
    - Exit multiple adjustment in multiple change (`x`) for Exit Multiple.
  - Illustrative initial starting assumptions with interactive "Reset to Defaults" buttons.
  - Deterministic recalculation of forecast cash flows and valuation outputs using existing Phase 4, 5, and 6 calculation engines.
  - Withholding of affected valuation outputs with explicit diagnostic reasons when assumptions are invalid (e.g. $\text{WACC} \le g$) or inputs are missing.
  - Cross-scenario comparison table displaying operational metrics, discount rates, cash flow present values, Enterprise Value, Equity Value, implied share price, and validation status.
  - Interactive Plotly visualizations: grouped EV and Equity Value bar chart, implied share price comparison, projected UFCF cash flow trajectory lines, and EV composition stacked charts.
  - Assumption auditability and delta bridge table tracing baseline value, applied override, resulting scenario assumption, and linked model provenance.
  - Named scenario set persistence via `ScenarioModel` in SQLite (`database/dcf_engine.db`), supporting saving, updating, reloading, and deleting named analysis sets scoped to valuation projects.
  - Streamlit user interface (`app/pages/scenarios.py`) integrated into centralized navigation.

---

### Phase 8: Sensitivity Analysis & Simulation *(Status: Complete)*
- **Objective:** Evaluate valuation sensitivity to critical operational and discount rate drivers using 2D matrices and Monte Carlo simulations.
- **Key Deliverables:**
  - Dedicated sensitivity module (`src/sensitivity/`) decoupled from presentation code and database direct access.
  - Two-dimensional valuation sensitivity matrices evaluating WACC vs. Perpetual Growth Rate ($g$) for Gordon Growth, or WACC vs. Exit Multiple for Exit Multiple cases.
  - Configurable axis ranges (min, max, step) with guaranteed inclusion and distinct marking (`★`) of baseline model assumptions.
  - Strict cell-level validity enforcement: cells where $\text{WACC} \le g$ or $\text{WACC} \le 0$ are withheld with informative labels rather than substituted zeros.
  - Metric support for Enterprise Value, Equity Value, and Implied Intrinsic Value per Share.
  - Interactive Plotly heatmap with cell hover tooltips, color gradients, and tabular matrix with CSV export.
  - Optional Monte Carlo probabilistic simulation with configurable iteration count (50–2,000) and user-controlled random seed ensuring 100% reproducibility.
  - Supported probability distributions: Normal ($\mu, \sigma$), Triangular ($a, c, b$), and Uniform ($a, b$) across revenue growth delta, operating margin delta, WACC, and terminal value assumptions.
  - Explicit accounting and disclosure of invalid draws without contaminating valid valuation statistics.
  - Full percentile summary statistics (Mean, Median, Std Dev, Min, P10, P25, P75, P90, Max) for Enterprise Value, Equity Value, and Implied Share Price.
  - Plotly empirical distribution histograms with vertical reference lines for Median, P10, and P90 percentiles.
  - Named persistence via `SensitivityModel` in SQLite (`database/dcf_engine.db`), supporting save, update, reload, and delete operations.
  - Streamlit user interface (`app/pages/sensitivity.py`) with dedicated tabs for matrix, simulation, assumptions audit, and persistence.

---

### Phase 9: Reporting, Presentation & Export Engine *(Status: Complete)*
- **Objective:** Build an institutional report-generation and multi-format export capability turning project analysis and valuation models into clear, reproducible deliverables.
- **Key Deliverables:**
  - Dedicated reporting package (`src/reporting/`) decoupled from presentation code and database direct access.
  - Multi-section report configuration specifying title, subtitle, company overrides, reporting currency, generation date, and analyst attribution.
  - Granular section inclusion controls across 10 modular sections: Overview, Executive Summary, Historical Analysis, Forecast Projections, WACC Analysis, DCF Valuation & Equity Bridge, Scenario Analysis, Sensitivity & Simulation, Disclosures & Caveats, and Appendix.
  - Unified analytical report compiler (`ReportEngine`) resolving underlying historical bundles, forecasts, WACC estimations, DCF valuation cases, scenario sets, and sensitivity matrices without formula duplication.
  - Explicit diagnostic handling for missing, deleted, or incompatible models, with outputs withheld rather than replaced with silent zeros.
  - Pure-Python publication-grade PDF report generator (`PdfReportGenerator`) compliant with standard PDF 1.4, featuring running headers/footers with dynamic page numbering, KPI highlight cards, and structured tables.
  - Institutional multi-sheet Excel workbook export engine (`ExcelReportGenerator`) via `openpyxl` with professional typography, header fills, number formats (`$#,##0.0`, `0.0%`, `0.00x`), thin borders, and auto-adjusted column widths.
  - Tabular CSV export suite (`CsvReportGenerator`) covering valuation summaries, forecast schedules, historical statements, sensitivity matrices, and scenario sets.
  - Named report configuration persistence via `ReportModel` in SQLite (`database/dcf_engine.db`), supporting save, update, reload, and delete operations.
  - Streamlit user interface (`app/pages/reports.py`) with 4 dedicated tabs: Configuration, In-App Live Preview, Export Center, and Saved Configurations.

---

### Phase 10: Financial Dashboards & Interactive Visualizations *(Status: Complete)*
- **Objective:** Deliver interactive, institutional-grade visual analytics and valuation dashboards connecting historical performance, forecast cash flows, DCF valuation bridge waterfalls, and scenario/sensitivity exploration.
- **Key Deliverables:**
  - Dedicated visual analytics package (`src/dashboard/`) decoupled from presentation logic and database direct access.
  - High-performance, presentation-grade Plotly chart generation suite (`src/dashboard/charts.py`):
    - Historical multi-line financial trend charts (Revenue, Gross Profit, EBITDA, Net Income) with metric multi-selection and period filtering.
    - Historical profitability margin evolution (Gross, EBITDA, EBIT, Net Margin).
    - Cash flow and CapEx dynamics comparing Operating Cash Flow (CFO), CapEx magnitude, CFO Less CapEx, and historical UFCF estimates.
    - Working capital cycle efficiency charts tracking DSO, DIO, DPO, and Cash Conversion Cycle (CCC).
    - Historical vs. projected revenue trajectories with visual boundary markers and dashed projection styles.
    - Forward-looking driver margin horizons (Gross, EBITDA, EBIT) across historical baseline and forecast periods.
    - Projected UFCF component breakdown schedules (NOPAT, D&A, -CapEx, -ΔNWC, = UFCF).
    - Institutional DCF Enterprise-to-Equity valuation waterfall chart (`go.Waterfall`) bridging PV of Forecast UFCF, PV of Terminal Value, Enterprise Value, Cash & Equivalents (+), Interest-Bearing Debt (-), Minority Interest (-), Preferred Stock (-), and Other Non-Operating Adjustments (+/-) down to Implied Equity Value.
    - Cash flow discounting trajectory comparing nominal UFCF vs. present value discounted at WACC.
    - Terminal value contribution donut chart with automated diagnostic warnings when terminal value concentration exceeds 75% of Enterprise Value.
    - Cross-scenario comparison grouped bar charts and per-share price benchmarks across Base, Bull, and Bear cases.
    - 2D valuation sensitivity heatmaps with cell hover details, custom color scales, and distinct baseline marking (`★`).
    - Monte Carlo probabilistic distribution histograms with vertical reference lines for Median, P10, and P90 percentiles.
  - Centralized Streamlit dashboard page (`app/pages/dashboard.py`) integrated into primary navigation:
    - Scope and model selection hub connecting valuation projects, historical frequency (Annual vs. Quarterly) and data classifications, saved forecasts, WACC estimations, DCF cases, scenario sets, and sensitivity configurations.
    - Explicit diagnostic notices for missing, deleted, or incompatible models without silent substitution.
    - 7-metric compact headline KPI row (Latest Revenue, Operating Margin, Forecast UFCF, WACC, Enterprise Value, Equity Value, and Value per Share).
    - 4 connected exploration tabs: Historical Performance, Forecast & Cash Flows, DCF Valuation & Bridge, and Scenario & Sensitivity Exploration.
    - Non-destructive navigation buttons linking directly to underlying model workbenches without duplicating assumption editors.

---

### Phase 11: Dynamic Excel Financial Model Formula Linking *(Status: Planned — Next Active Phase)*
- **Objective:** Export auditable multi-tab spreadsheet models with active dynamic formulas.
- **Key Capabilities:**
  - Multi-tab Excel workbook generation via `openpyxl` with live formulas linking historicals, forecast, WACC, and DCF.
  - Professional institutional financial formatting, color-coded assumption cells, and dynamic recalculation.

---

### Phase 12: AI-Assisted Document & Financial Statement Analysis *(Status: Planned)*
- **Objective:** Provide automated synthesis of regulatory financial filings.
- **Key Capabilities:**
  - Automated extraction of financial footnotes and risk factors from 10-K and 10-Q reports.
  - Contextual AI summary cards highlighting key growth drivers and management commentary.
