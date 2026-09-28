# AI-Powered DCF Valuation and Sensitivity Engine

An institutional-grade financial modelling platform built in Python, designed to perform Discounted Cash Flow (DCF) valuations, scenario planning, multi-variable sensitivity analysis, and dynamic financial model exports.

> **Active Development Status:** The repository has completed **Phase 7: Scenario Analysis (Base / Bull / Bear)**. The application features a multi-case valuation engine that compares Base, Bull, and Bear cases using the existing Phase 4 forecast, Phase 5 WACC, and Phase 6 DCF engines. Users can model assumption overrides in explicit percentage points (`pp`), basis points (`bps`), and multiple units (`x`), observe cross-scenario valuation matrices, analyze visual charts (EV & Equity Value, Implied Share Price, UFCF Cash Flow Trajectory, and EV Composition), inspect assumption audits, and persist named scenario sets in SQLite.

---

## 1. Project Purpose & Overview

The **AI-Powered DCF Valuation and Sensitivity Engine** provides corporate finance analysts, investors, and valuation practitioners with a transparent, structured, and auditable environment to evaluate publicly listed companies.

Key capabilities delivered in Phases 1–7:
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
- **Phase 7 (Scenario Analysis — Current):**
  - **Three Canonical Scenarios:** Standardized **Base**, **Bull**, and **Bear** valuation cases.
  - **Base Case Preservation:** Base case strictly reflects the selected saved forecast and WACC baseline without overrides.
  - **Explicit User-Editable Overrides:**
    - *Revenue growth adjustment:* in percentage points (`pp`).
    - *Operating margin adjustment:* in percentage points (`pp`).
    - *Cost of Capital (WACC) adjustment:* in basis points (`bps`, $100\text{ bps} = 1.0\%$).
    - *Perpetual growth rate adjustment:* in basis points (`bps`) for Gordon Growth.
    - *Exit multiple adjustment:* as a multiple change (`x`) for Exit Multiple.
  - **Transparent Auditing & Diagnostics:** Baseline vs. override vs. resulting assumption table, linked model provenance, and validation warnings when $\text{WACC} \le g$.
  - **Cross-Scenario Comparison & Visuals:** Side-by-side output matrix, grouped EV/Equity bar charts, implied share price comparison, cash flow trajectory lines, and EV composition stacked charts.
  - **Named Scenario Persistence:** Save, update, reload, and delete named scenario analysis sets (`ScenarioModel`) in SQLite.

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
│   │   └── scenarios.py        # Scenario analysis view, Base/Bull/Bear overrides & comparison
│   └── components/             # Reusable UI elements (cards, badges)
│       ├── __init__.py
│       ├── badges.py
│       └── cards.py
│
├── src/                        # Domain logic & financial engine (Decoupled from UI)
│   ├── __init__.py
│   ├── data/                   # Data management, persistence & validation layer
│   │   ├── __init__.py
│   │   ├── models.py           # SQLAlchemy ORM models (Company, ForecastModel, DcfModel, ScenarioModel, etc.)
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
│   ├── sensitivity/            # 2D sensitivity matrices & simulation engine (Phase 8)
│   └── exports/                # Dynamic openpyxl Excel models & report generators (Phase 10)
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
| **Phase 8** | Sensitivity Analysis & Simulation | 2D sensitivity matrices, driver tornado charts, Monte Carlo | *Planned (Next)* |
| **Phase 9** | Financial Dashboards | Interactive Plotly statement and valuation charts | *Planned* |
| **Phase 10** | Dynamic Excel Model Exports | openpyxl financial models with dynamic formulas | *Planned* |
| **Phase 11** | Valuation Reports & Memos | Institutional PDF/Markdown investment memos | *Planned* |
| **Phase 12** | AI-Assisted Document Analysis | Automated 10-K extraction and footnote synthesis | *Planned* |

---

## 6. Current Limitations & Disclaimer

### Current Limitations (Phase 7)
- Multi-dimensional two-dimensional sensitivity matrices (e.g. WACC vs. Terminal Growth Rate, WACC vs. Exit Multiple) and Monte Carlo simulations belong to Phase 8.
- Dynamic multi-tab openpyxl Excel exports and automated investment memos belong to Phases 10–11.
- Scenario intrinsic valuations illustrate sensitivity to user-configured adjustments and do not constitute certified investment advice, recommendations, or probabilistic guarantees.

### Important Disclaimer
> **Not Investment Advice:** This software application is under active engineering development. It is designed for educational, research, and financial modelling purposes only. Nothing produced by this system constitutes financial, investment, legal, or tax advice. No valuation outputs should be relied upon for investment decisions without independent verification by qualified financial professionals.
