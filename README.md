# AI-Powered DCF Valuation and Sensitivity Engine

An institutional-grade financial modelling platform built in Python, designed to perform Discounted Cash Flow (DCF) valuations, scenario planning, multi-variable sensitivity analysis, and dynamic financial model exports.

> **Active Development Status:** The repository has completed **Phase 11: Dynamic Excel Financial Model Formula Linking** (v0.11.0). The application features an institutional, dynamic, formula-linked financial model export engine generating 8-sheet Excel workbooks with live formula linking across Assumptions, Forecast, WACC, and DCF Valuation schedules, alongside a unified financial dashboard, scenario analysis, sensitivity engine, and multi-format reporting.

---

## 1. Project Purpose & Overview

The **AI-Powered DCF Valuation and Sensitivity Engine** provides corporate finance analysts, investors, and valuation practitioners with a transparent, structured, and auditable environment to evaluate publicly listed companies.

Key capabilities delivered in Phases 1–11:
- **Phase 1 (Foundation):** Clean decoupled architecture, centralized configuration using `pathlib.Path`, and modular Streamlit shell.
- **Phase 2 (Data Management):** Persistent SQLite storage with SQLAlchemy ORM, company profiles, valuation project workspaces, manual three-statement data entry, and multi-step CSV/Excel spreadsheet imports with column auto-mapping and full audit provenance.
- **Phase 3 (Historical Analysis):** Multi-year revenue growth, CAGRs, profitability margins (Gross, EBITDA, EBIT, Net), working capital dynamics, cash conversion cycles (DSO, DIO, DPO, CCC), operating cash flows, historical UFCF estimates, and accounting integrity audit diagnostics.
- **Phase 4 (Financial Forecasting):**
  - **Configurable Horizon:** Model 3 to 10 forecast years (default 5 years) anchored to the latest verified historical annual period.
  - **Driver-Based Projections:** Constant or year-by-year schedules for revenue growth, gross margins, OpEx % of revenue, D&A % of revenue, CapEx % of revenue, and corporate tax rates.
  - **Working Capital Modeling:** Operating Net Working Capital modeled via turnover days (DSO, DIO, DPO) or revenue percentages, computing annual $\Delta\text{Operating NWC}$.
  - **Unlevered Free Cash Flow (UFCF) Derivation:** Formulaic projection: $\text{UFCF} = \text{NOPAT} + \text{D\&A} - \text{CapEx} - \Delta\text{Operating NWC}$.
  - **Scenario Versioning & Persistence:** Save, load, and manage named forecast models (`ForecastModel`) scoped to valuation projects.
- **Phase 5 (WACC Estimation Engine):**
  - **Cost of Equity via CAPM:** Deterministic formulation: $\text{Cost of Equity} = R_f + \beta \times \text{ERP}$, with provenance tracking and sanity checks on negative/extreme inputs.
  - **Cost of Debt & Tax Shield:** User-entered borrowing spread or historical accounting interest rate estimate ($\text{Interest Expense} / \text{Debt}$), with interest deductibility tax shield: $K_{d,\text{after}} = K_d \times (1 - t)$.
  - **Capital Structure Weighting:** Debt and equity amounts based on market capitalization or balance sheet book equity proxy, validating non-negative capital and non-zero capital bases.
  - **Named Scenario Persistence:** Save, load, and version named WACC cases (`WaccModel`) associated with valuation projects.
- **Phase 6 (DCF Valuation Engine):**
  - **Cash Flow Discounting Schedules:** Multi-period discounting with user-configurable timing conventions (End-of-Year $t=1, \dots, N$ or Mid-Year $t=0.5, \dots, N-0.5$).
  - **Dual Terminal Value Methodologies:**
    - *Gordon Growth Perpetuity:* $\text{TV} = \frac{\text{UFCF}_N \times (1 + g)}{\text{WACC} - g}$, enforcing $\text{WACC} > g$.
    - *Exit Multiple Method:* $\text{TV} = \text{Terminal EBITDA}_N \times \text{Exit Multiple}$.
  - **Enterprise Value Formulation:** $\text{Enterprise Value} = \text{PV of Forecast UFCF} + \text{PV of Terminal Value}$.
  - **Enterprise-to-Equity Value Bridge:** Explicit line-item reconciliation adding Cash & Equivalents, deducting Interest-Bearing Debt, Minority Interest, and Preferred Stock, plus signed non-operating adjustments.
  - **Implied Intrinsic Share Price:** Evaluated as $\text{Equity Value} / \text{Diluted Shares Outstanding}$ with safe withholding when share count is absent.
  - **Named DCF Scenario Persistence:** Save, load, and version named DCF models (`DcfModel`) in SQLite.
- **Phase 7 (Scenario Analysis):**
  - **Three Canonical Scenarios:** Standardized **Base**, **Bull**, and **Bear** valuation cases.
  - **Base Case Preservation:** Base case strictly reflects the selected saved forecast and WACC baseline without overrides.
  - **Explicit User-Editable Overrides:** Revenue growth (pp), operating margin (pp), WACC (bps), perpetual growth rate (bps), and exit multiple (x).
  - **Transparent Auditing & Diagnostics:** Baseline vs. override vs. resulting assumption table, linked model provenance, and validation warnings when $\text{WACC} \le g$.
  - **Cross-Scenario Comparison & Visuals:** Side-by-side output matrix, grouped EV/Equity bar charts, implied share price comparison, cash flow trajectory lines, and EV composition stacked charts.
  - **Named Scenario Persistence:** Save, update, reload, and delete named scenario analysis sets (`ScenarioModel`) in SQLite.
- **Phase 8 (Sensitivity Analysis & Simulation):**
  - **Two-Dimensional Sensitivity Matrices:** Evaluate WACC vs. Perpetual Growth Rate ($g$) or Exit Multiple, with editable ranges, steps, and guaranteed baseline intersection marking (`★`).
  - **Enforced Mathematical Validity:** Cells violating $\text{WACC} > g$ or non-positive discount rates are safely withheld with explicit diagnostic labels rather than silent zeros.
  - **Multi-Metric Support:** Computes Enterprise Value, Equity Value, and Implied Intrinsic Value per Share across the grid.
  - **Interactive Heatmap Visualizations:** Plotly heatmaps with cell-level hover diagnostics, custom color scales, and CSV matrix export.
  - **Optional Monte Carlo Simulation:** Random sampling across revenue growth, operating margin, WACC, and terminal assumptions with user-controlled iteration count (50–2,000) and random seed for 100% reproducibility.
  - **Restrained Distribution Models:** Normal ($\mu, \sigma$), Triangular ($a, c, b$), and Uniform ($a, b$) with clearly labeled illustrative starting defaults.
  - **Explicit Invalid-Draw Accounting:** Transparent counting and breakdown of invalid draws (e.g., $\text{WACC} \le g$) without contaminating valid sample statistics.
  - **Summary Percentile Statistics & Histograms:** Mean, median, standard deviation, and percentiles (Min, P10, P25, P75, P90, Max) with Plotly distribution histograms and reference lines.
  - **Named Persistence:** Save, reload, and delete named sensitivity configurations (`SensitivityModel`) in SQLite.
- **Phase 9 (Reporting, Presentation & Export Engine):**
  - **Customizable Valuation Reports:** Comprehensive report configuration specifying title, subtitle, company overrides, reporting currency, generation date, and narrative notes.
  - **Granular Section Inclusion:** 10 modular sections with independent toggle controls (Overview, Executive Summary, Historical Financials, Forecast Projections, WACC Analysis, DCF Valuation & Equity Bridge, Scenario Analysis, Sensitivity & Simulation, Disclosures & Caveats, and Appendix).
  - **In-App Live Preview:** Interactive preview replicating report hierarchy, headline KPI metric cards, formatted financial tables, and model provenance badges.
  - **Institutional Printable PDF Export:** Pure-Python PDF 1.4 document builder producing multi-page printable memorandums with running headers/footers, dynamic "Page X of Y" pagination, KPI highlight cards, and structured tables. Zero external C-library or system binary dependencies.
  - **Multi-Sheet Excel Financial Model Workbook:** Generated via `openpyxl` with professional typography, dark navy headers, thin borders, custom number formatting (`$#,##0.0`, `0.0%`, `0.00x`), auto-adjusted column widths, and freeze panes across 8 dedicated sheets.
  - **Modular Tabular CSV Exports:** Dedicated CSV exporters for Valuation Summary, Forecast Schedule, Historical Financial Statements, 2D Sensitivity Matrix, and Scenario Comparisons.
  - **Named Report Persistence:** Save, reload, update, and delete named report configurations (`ReportModel`) in SQLite.
- **Phase 10 (Financial Dashboards & Interactive Visualizations):**
  - **Connected Model Selection & Scope Area:** Select valuation projects, historical reporting scopes, saved forecasts, WACC estimations, DCF cases, scenario sets, and sensitivity models with explicit diagnostics for missing dependencies.
  - **Compact Headline KPI Bar:** Real-time visibility into historical revenue, operating margin, ending forecast UFCF, discount rate (WACC), Enterprise Value, Equity Value, and implied value per share.
  - **Historical Financial Trends:** Interactive Plotly charts for revenue and key line items, profitability margin evolution, cash flow vs. CapEx dynamics, and working capital cycles (DSO, DIO, DPO, CCC).
  - **Forecast & Cash-Flow Trajectories:** Merged historical vs. projected revenue trajectories with boundary markers, margin driver horizons, and UFCF component breakdown schedules.
  - **Valuation Waterfall Bridge:** Enterprise-to-Equity valuation bridge waterfall chart (`go.Waterfall`) transitioning from PV of cash flows and PV of terminal value to Enterprise Value, applying balance sheet bridge adjustments down to Equity Value.
  - **Terminal Value Share & Cash Flow Discounting:** Donut chart of terminal value contribution with high-share diagnostic alerts (>75% of EV), and nominal vs present value cash-flow discounting trajectories.
  - **Linked Scenario & Sensitivity Exploration:** Grouped Base/Bull/Bear valuation and share price comparisons, assumption override audit tables, 2D sensitivity matrix heatmaps with baseline indicators (`★`), and Monte Carlo distribution histograms with percentile reference lines.
- **Phase 11 (Dynamic Excel Financial Model Formula Linking — Current):**
  - **Dynamic Inter-Sheet Formula Linking:** Multi-tab Excel workbook generation via `openpyxl` with live formulas connecting inputs on the Assumptions sheet to forward projections, WACC estimations, discounting schedules, and the enterprise-to-equity valuation bridge.
  - **8 Institutional Sheets:** Read Me & Model Guide, Historical Financials, Assumptions, Forecast Projections, WACC Analysis, DCF Valuation & Equity Bridge, Scenario Analysis, and Sensitivity & Simulation.
  - **Color-Coded User Inputs:** Soft canary yellow fill (`#FEF9C3`) with gold borders identifying editable driver cells (growth rates, margins, turnover days, tax rates, CAPM inputs, terminal values, and balance sheet items).
  - **Spreadsheet Auto-Recalculation:** Configured `wb.calculation.fullCalcOnLoad = True` so spreadsheet applications (Excel, Calc, Sheets) automatically recalculate the entire formula graph upon open.
  - **Dual Export Workflow:** In-app selection in the Export Center between static Excel reports for executive distribution and dynamic formula-linked financial models for interactive scenario editing.

---

## 2. Technology Stack

- **Core Runtime & Computation:** Python (>= 3.10), [pandas](https://pandas.pydata.org/) (>= 2.2.0), [NumPy](https://numpy.org/) (>= 1.26.0)
- **User Interface & Visualizations:** [Streamlit](https://streamlit.io/) (>= 1.35.0), [Plotly](https://plotly.com/python/) (>= 5.22.0)
- **Database & ORM:** [SQLite](https://www.sqlite.org/) (embedded), [SQLAlchemy](https://www.sqlalchemy.org/) (>= 2.0.30)
- **Spreadsheet Processing & Model Export:** [openpyxl](https://openpyxl.readthedocs.io/) (>= 3.1.2)
- **Configuration & Environment Management:** [python-dotenv](https://github.com/theskumar/python-dotenv) (>= 1.0.1)

---

## 3. Repository Structure

```
dcf-valuation-engine/
│
├── app/                        # Presentation & UI layer (Streamlit)
│   ├── __init__.py             # App package definition
│   ├── main.py                 # Streamlit entry point, navigation & routing
│   ├── config.py               # Centralized configuration singleton (pathlib)
│   ├── pages/                  # Modular UI sub-pages
│   │   ├── __init__.py
│   │   ├── companies.py        # Company profile directory, editor & creator
│   │   ├── projects.py         # Valuation project workspaces & status manager
│   │   ├── financial_data.py   # Historical statement records & provenance viewer
│   │   ├── manual_entry.py     # Manual financial statement line-item entry form
│   │   ├── import_data.py      # CSV/Excel multi-step import processor & preview
│   │   ├── historical_analysis.py # Historical analysis view, Plotly charts & audit
│   │   ├── forecasting.py      # Financial forecasting & UFCF projection view
│   │   ├── wacc.py             # WACC estimation, CAPM, cost of debt & capital structure view
│   │   ├── dcf.py              # DCF valuation engine, cash flow discounting & equity bridge view
│   │   ├── scenarios.py        # Scenario analysis view, Base/Bull/Bear overrides & comparison
│   │   ├── sensitivity.py      # Sensitivity analysis view, 2D matrix heatmap & Monte Carlo simulation
│   │   ├── dashboard.py        # Central financial dashboard & interactive Plotly visualizer view
│   │   └── reports.py          # Reports & exports view, in-app preview & configuration management
│   └── components/             # Reusable UI elements (cards, badges)
│       ├── __init__.py
│       ├── badges.py
│       └── cards.py
│
├── src/                        # Domain logic & financial engine (Decoupled from UI)
│   ├── __init__.py
│   ├── data/                   # Data management, persistence & validation layer
│   │   ├── __init__.py
│   │   ├── models.py           # SQLAlchemy ORM models (Company, DcfModel, ScenarioModel, ReportModel, etc.)
│   │   ├── database.py         # Engine configuration & session context manager
│   │   ├── schemas.py          # Enums, standard line-item catalog & DTOs
│   │   ├── validators.py       # Multi-field structural & accounting validator
│   │   ├── repository.py       # Encapsulated data access objects (CRUD)
│   │   ├── services.py         # Transactional service coordinators
│   │   └── importers.py        # CSV/Excel parser, auto-mapping & preview
│   ├── analysis/               # Historical financial analysis engine (Phase 3)
│   │   ├── __init__.py
│   │   ├── engine.py           # Analysis orchestrator, scale & currency alignment
│   │   ├── metrics.py          # Growth, CAGR, profitability margins, tax rates
│   │   ├── working_capital.py  # NWC, Operating NWC, DSO, DIO, DPO, CCC
│   │   ├── cash_flow.py        # CFO, CapEx, OCF less CapEx, UFCF estimate
│   │   ├── formatting.py       # Formatted statement & ratio DataFrames
│   │   └── models.py           # Strongly typed metric & bundle dataclasses
│   ├── forecasting/            # Financial forecasting & projection engine (Phase 4)
│   │   ├── __init__.py
│   │   ├── models.py           # ForecastAssumptions, YearForecast, ForecastResult
│   │   ├── engine.py           # FinancialForecastingEngine baseline & projection logic
│   │   ├── services.py         # ForecastService for persisting scenario models
│   │   └── formatting.py       # Consolidated statement and UFCF bridge tables
│   ├── wacc/                   # WACC & Discount Rate Engine (Phase 5)
│   │   ├── __init__.py
│   │   ├── models.py           # Input models with provenance, intermediate & WaccResult
│   │   ├── calculations.py     # Deterministic CAPM, after-tax debt cost, capital weights
│   │   ├── engine.py           # WaccEngine baseline extraction & orchestration
│   │   ├── services.py         # WaccService for persisting named WACC models
│   │   └── formatting.py       # Matrices, capital structure tables & Plotly charts
│   ├── dcf/                    # DCF Valuation & Terminal Value Engine (Phase 6)
│   │   ├── __init__.py
│   │   ├── models.py           # DcfAssumptions, discounting schedules & DcfValuationResult
│   │   ├── calculations.py     # Deterministic discounting, Gordon Growth, exit multiples & bridge
│   │   ├── engine.py           # DcfEngine orchestrating linked forecast and WACC models
│   │   ├── services.py         # DcfService for persisting named DCF valuation scenarios
│   │   └── formatting.py       # Discounting schedules, bridge tables & valuation charts
│   ├── scenarios/              # Scenario Analysis Engine (Phase 7)
│   │   ├── __init__.py
│   │   ├── models.py           # ScenarioOverrides, ScenarioAnalysisAssumptions & Results
│   │   ├── engine.py           # ScenarioEngine applying overrides and executing 3-case DCFs
│   │   ├── services.py         # ScenarioService for persisting named ScenarioModel records
│   │   └── formatting.py       # Cross-scenario comparison, audit tables & Plotly comparison charts
│   ├── sensitivity/            # Sensitivity Analysis & Simulation Engine (Phase 8)
│   │   ├── __init__.py
│   │   ├── models.py           # AxisRangeConfig, DistributionConfig, SensitivityMatrixResult, MonteCarloSimulationResult
│   │   ├── engine.py           # SensitivityEngine 2D matrix recalculation & Monte Carlo RNG loops
│   │   ├── services.py         # SensitivityService for persisting named SensitivityModel records
│   │   └── formatting.py       # 2D tabular matrices, Plotly heatmaps, Monte Carlo histograms & percentile stats
│   ├── reporting/              # Reporting, Presentation & Export Engine (Phases 9 & 11)
│   │   ├── __init__.py
│   │   ├── models.py           # ReportSection, ReportMetadata, ReportConfig, ReportBundle
│   │   ├── engine.py           # ReportEngine compiling underlying models without formula duplication
│   │   ├── services.py         # ReportService for persisting named ReportModel configurations
│   │   ├── pdf_export.py       # Pure-Python PDF 1.4 publication report generator
│   │   ├── excel_export.py     # Multi-tab openpyxl static Excel report generator
│   │   ├── dynamic_excel_export.py # Dynamic formula-linked Excel financial model generator
│   │   └── csv_export.py       # Tabular CSV exporters for valuation, schedules, and matrices
│   └── dashboard/              # Financial Dashboards & Interactive Visualizations (Phase 10)
│       ├── __init__.py
│       └── charts.py           # Presentation Plotly chart suite (waterfalls, trends, margins, distributions)
│
├── database/                   # Designated directory for local SQLite database
│   ├── .gitkeep
│   └── dcf_engine.db           # Generated local database (ignored by Git)
│
├── data/                       # Designated directory for local raw files/datasets
│   └── .gitkeep
│
├── docs/                       # Technical & architectural documentation
│   ├── architecture.md         # Detailed architectural layers & design rules
│   └── development-roadmap.md  # Sequenced 12-phase implementation plan
│
├── .streamlit/
│   └── config.toml             # Professional finance-themed UI configuration
│
├── .env.example                # Example environment configuration variables
├── .gitignore                  # Git exclusion rules for Python, DBs, and secrets
├── requirements.txt            # Python dependencies
└── README.md                   # Project documentation and setup guide
```

---

## 4. Quick Start & Installation

### Step 1: Environment Setup
```powershell
# Windows (PowerShell)
python -m venv venv
.\venv\Scripts\Activate.ps1

# Linux / macOS
python3 -m venv venv
source venv/bin/activate
```

### Step 2: Install Dependencies
```bash
python -m pip install -r requirements.txt
```

### Step 3: Configure Environment
```powershell
# Windows PowerShell
Copy-Item .env.example .env

# Linux / macOS
cp .env.example .env
```

### Step 4: Launch the Application
```bash
python -m streamlit run app/main.py
```
*Navigate to `http://localhost:8501` in your browser.*

---

## 5. 12-Phase Development Roadmap

| Phase | Milestone | Focus Area | Status |
| :---: | :--- | :--- | :---: |
| **Phase 1** | **Foundation & Architecture** | Repository structure, configuration, shell, and docs | **Complete** |
| **Phase 2** | **Company & Financial Data** | SQLAlchemy models, statement storage, CSV/Excel imports | **Complete** |
| **Phase 3** | **Historical Financial Analysis** | Growth, margins, working capital cycles, cash flow analysis | **Complete** |
| **Phase 4** | **Financial Forecasting** | Driver-based revenue models, OpEx schedules, UFCF | **Complete** |
| **Phase 5** | **WACC & Discount Rate Engine** | CAPM, cost of debt, tax rates, capital weighting | **Complete** |
| **Phase 6** | **DCF Valuation & Terminal Value** | Gordon Growth, Exit Multiples, Enterprise & Equity Value | **Complete** |
| **Phase 7** | **Scenario Analysis (Base / Bull / Bear)** | Bull/Bear scenarios, parameter overrides, cross-scenario comparisons | **Complete** |
| **Phase 8** | **Sensitivity Analysis & Simulation** | 2D sensitivity matrices, driver heatmaps, Monte Carlo | **Complete** |
| **Phase 9** | **Reporting, Presentation & Export** | Multi-page PDF reports, openpyxl Excel models, CSVs | **Complete** |
| **Phase 10** | **Financial Dashboards & Visualizations** | Interactive Plotly valuation waterfalls, cash flow dashboards, and scenario exploration | **Complete** |
| **Phase 11** | **Dynamic Excel Formula Linking** | openpyxl financial models with dynamic formulas | **Complete** |
| **Phase 12** | AI-Assisted Document Analysis | Automated 10-K extraction and footnote synthesis | *Planned (Next)* |

---

## 6. Current Limitations & Disclaimer

### Current Limitations (Phase 11)
- Automated SEC 10-K filing ingestion, section splitting, and AI footnote parsing belong to Phase 12.
- Formula Recalculation in Excel: While `openpyxl` generates active, valid spreadsheet formulas and configures `fullCalcOnLoad = True`, `openpyxl` itself does not execute a calculation engine; formulas are dynamically evaluated upon opening the `.xlsx` workbook in spreadsheet software (Microsoft Excel, LibreOffice Calc, Google Sheets).
- Valuation models, sensitivity matrices, and simulated distributions describe analytical outputs under user-selected assumptions and historical statements; they do not constitute certified investment advice, recommendations, confidence intervals, or guaranteed future prices.

### Important Disclaimer
> **Not Investment Advice:** This software application is under active engineering development. It is designed for educational, research, and financial modelling purposes only. Nothing produced by this system constitutes financial, investment, legal, or tax advice. No valuation outputs should be relied upon for investment decisions without independent verification by qualified financial professionals.

