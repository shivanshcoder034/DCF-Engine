# Development Roadmap
## AI-Powered DCF Valuation and Sensitivity Engine

This roadmap establishes the phased engineering progression for the platform. Development progresses sequentially to maintain strict architectural separation, verifiable math, and code quality.

---

### Phase 1: Project Foundation and Architecture *(Current - Completed)*
- **Objective:** Establish a clean, extensible, maintainable Python project foundation.
- **Deliverables:**
  - Repository structure with decoupled `app/` (presentation) and `src/` (engine) layers.
  - Centralized application configuration (`app/config.py`) using `pathlib`.
  - Minimal Streamlit application shell (`app/main.py`) with 9 planned navigation sections and phase placeholders.
  - Dependency definition (`requirements.txt`) and Git exclusion rules (`.gitignore`).
  - Environment configuration blueprint (`.env.example`).
  - Architecture specifications (`docs/architecture.md`) and development roadmap (`docs/development-roadmap.md`).

---

### Phase 2: Company Profiles & Financial Data Management
- **Objective:** Ingest, standardize, and persist historical financial statements.
- **Key Capabilities:**
  - Company metadata schema (ticker, company name, sector, currency, fiscal year end).
  - Income Statement, Balance Sheet, and Cash Flow Statement data models.
  - Local database persistence via SQLite and SQLAlchemy ORM.
  - Data validation rules and accounting balance verification (e.g. Assets = Liabilities + Equity).

---

### Phase 3: Historical Financial Analysis
- **Objective:** Compute foundational financial metrics and performance trends.
- **Key Capabilities:**
  - Multi-year revenue and operating income Compound Annual Growth Rates (CAGR).
  - Profitability margin evolution (Gross, EBITDA, Operating, and Net Profit Margins).
  - Working capital metrics (Days Sales Outstanding, Days Inventory Outstanding, Days Payable Outstanding).
  - Return on Invested Capital (ROIC), Return on Capital Employed (ROCE), and Return on Equity (ROE).

---

### Phase 4: Projections & Free Cash Flow Forecasting Engine
- **Objective:** Generate multi-year forward-looking financial schedules.
- **Key Capabilities:**
  - Driver-based revenue forecasting (growth rate schedules, segment growth).
  - Operating expense modeling and EBITDA/EBIT bridges.
  - Depreciation & Amortization schedules and Capital Expenditures (CapEx).
  - Net Working Capital (NWC) projections and annual ΔNWC impact.
  - Formulaic derivation of Unlevered Free Cash Flow (UFCF = NOPAT + D&A - CapEx - ΔNWC).

---

### Phase 5: WACC & Discount Rate Engine
- **Objective:** Compute the Weighted Average Cost of Capital (WACC).
- **Key Capabilities:**
  - Cost of Equity computation using the Capital Asset Pricing Model (CAPM).
  - Beta estimation, unlevering and relevering procedures.
  - Cost of Debt computation (pre-tax cost and effective tax shield).
  - Capital structure weightings based on market capitalization and net debt.

---

### Phase 6: DCF Valuation & Terminal Value Engine
- **Objective:** Execute core DCF discounting and determine intrinsic share value.
- **Key Capabilities:**
  - Discounting explicit forecast Unlevered Free Cash Flows using calculated WACC.
  - Perpetual Growth Method (Gordon Growth Model) terminal value formulation.
  - Exit Multiple Method (EV/EBITDA multiple) terminal value formulation.
  - Enterprise Value to Equity Value bridge (adding cash, deducting total debt, non-operating adjustments).
  - Implied intrinsic value per share vs. current market quote comparison.

---

### Phase 7: Scenario & Sensitivity Analysis
- **Objective:** Stress-test valuation outputs across variables and market environments.
- **Key Capabilities:**
  - Preset scenario modeling (Base Case, Bull Case, Bear Case) with custom parameter overrides.
  - Two-dimensional sensitivity tables (e.g., WACC vs. Terminal Growth Rate, WACC vs. Exit Multiple).
  - Valuation driver ranking and visual tornado analysis.

---

### Phase 8: Financial Reporting & Dynamic Excel Model Exports
- **Objective:** Produce institutional deliverables and transparent spreadsheets.
- **Key Capabilities:**
  - Automated generation of multi-tab Excel models using `openpyxl` with dynamic spreadsheet formulas.
  - Executive valuation report summary export.
  - Audit logs documenting all valuation inputs and modeling assumptions.

---

### Phase 9: AI-Assisted Document & Financial Analysis *(Optional Extension)*
- **Objective:** Provide automated synthesis of regulatory financial filings.
- **Key Capabilities:**
  - Automated extraction of financial footnotes and risk factors from 10-K / 10-Q reports.
  - Contextual AI summary cards highlighting key growth drivers and management commentary.
