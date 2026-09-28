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

### Phase 4: Financial Forecasting & Projections Engine *(Status: Planned)*
- **Objective:** Generate multi-year forward-looking financial statement schedules and cash flow bridges.
- **Key Capabilities:**
  - Driver-based revenue forecasting (segment growth, volume/price dynamics).
  - Operating expense modeling and EBITDA-to-EBIT bridge calculations.
  - Depreciation & Amortization schedules and Capital Expenditures (CapEx).
  - Working capital forecasting and balance sheet balance reconciliation.
  - Formulaic derivation of Unlevered Free Cash Flows (NOPAT + D&A - CapEx - ΔNWC).

---

### Phase 5: WACC & Discount Rate Engine *(Status: Planned)*
- **Objective:** Compute the Weighted Average Cost of Capital (WACC) reflecting enterprise risk.
- **Key Capabilities:**
  - Cost of Equity estimation via the Capital Asset Pricing Model (CAPM).
  - Beta estimation, raw vs. adjusted betas, and Hamada unlevering/relevering routines.
  - Pre-tax and after-tax Cost of Debt schedules with effective marginal tax shield calculations.
  - Capital structure weightings based on market capitalization and net debt.

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
