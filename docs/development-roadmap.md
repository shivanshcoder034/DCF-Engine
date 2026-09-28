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

### Phase 6: DCF Valuation & Terminal Value Engine *(Status: Planned)*
- **Objective:** Discount projected free cash flows to determine enterprise value and intrinsic equity value.
- **Key Capabilities:**
  - Present Value (PV) discounting of explicit forecast period Unlevered Free Cash Flows using calculated WACC.
  - Perpetual Growth Method (Gordon Growth Model) terminal value formulation.
  - Exit Multiple Method (EV/EBITDA multiple) terminal value formulation.
  - Enterprise Value to Equity Value bridge (adding cash, deducting net debt, non-operating adjustments).
  - Implied intrinsic value per share vs. current market pricing comparison.

---

### Phase 7: Scenario Analysis *(Status: Planned)*
- **Objective:** Stress-test valuation outputs across macroeconomic and operational environments.
- **Key Capabilities:**
  - Preset scenario modelling: Base Case, Bull Case, Bear Case.
  - Custom assumption parameter overrides (growth rate deltas, margin compression/expansion, WACC shifts).
  - Cross-scenario comparative tables and valuation summaries.

---

### Phase 8: Sensitivity Analysis & Simulation *(Status: Planned)*
- **Objective:** Evaluate valuation sensitivity to critical operational and discount rate drivers.
- **Key Capabilities:**
  - Two-dimensional sensitivity matrices (e.g. WACC vs. Terminal Growth Rate, WACC vs. Exit Multiple).
  - Valuation driver ranking and visual tornado analysis.
  - Monte Carlo probabilistic valuation distributions.

---

### Phase 9: Financial Dashboards & Interactive Visualizations *(Status: Planned)*
- **Objective:** Deliver interactive, institutional-grade visual analytics.
- **Key Capabilities:**
  - Interactive Plotly valuation bridge waterfalls and historical financial performance charts.
  - Dynamic forecast scenario comparison visualizers.
  - Custom financial KPI dashboard panels.

---

### Phase 10: Dynamic Excel Financial Model Exports *(Status: Planned)*
- **Objective:** Export auditable multi-tab spreadsheet models with dynamic formulas.
- **Key Capabilities:**
  - Multi-tab Excel workbook generation via `openpyxl`.
  - Dynamic Excel spreadsheet formulas linking historical statements, forecasting schedules, WACC, and DCF tables.
  - Professional institutional financial formatting and color-coded assumptions.

---

### Phase 11: Institutional Valuation Reports & Memos *(Status: Planned)*
- **Objective:** Produce comprehensive downloadable valuation deliverables.
- **Key Capabilities:**
  - Automated executive valuation investment memo generation.
  - Comprehensive audit trail of all model inputs, data sources, and analytical conclusions.
  - Exportable report layouts in PDF and Markdown formats.

---

### Phase 12: AI-Assisted Document & Financial Statement Analysis *(Status: Planned)*
- **Objective:** Provide automated synthesis of regulatory financial filings.
- **Key Capabilities:**
  - Automated extraction of financial footnotes and risk factors from 10-K and 10-Q reports.
  - Contextual AI summary cards highlighting key growth drivers and management commentary.
