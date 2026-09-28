# AI-Powered DCF Valuation and Sensitivity Engine

An institutional-grade financial modelling platform built in Python, designed to perform Discounted Cash Flow (DCF) valuations, scenario planning, multi-variable sensitivity analysis, and dynamic financial model exports.

> **Active Development Status:** The repository has completed **Phase 4: Financial Forecasting & Projections Engine**. The application features a deterministic forecasting engine that projects multi-year income statements, operating working capital schedules, and Unlevered Free Cash Flows (UFCF) calibrated from historical actuals. Users can model revenue growth, gross margins, operating expenses, turnover days (DSO, DIO, DPO), CapEx intensity, and corporate tax rates, with the ability to persist versioned scenarios directly into the project database.

---

## 1. Project Purpose & Overview

The **AI-Powered DCF Valuation and Sensitivity Engine** provides corporate finance analysts, investors, and valuation practitioners with a transparent, structured, and auditable environment to evaluate publicly listed companies.

Key capabilities delivered in Phases 1–4:
- **Phase 1 (Foundation):** Clean decoupled architecture, centralized configuration using `pathlib.Path`, and modular Streamlit shell.
- **Phase 2 (Data Management):** Persistent SQLite storage with SQLAlchemy ORM, company profiles, valuation project workspaces, manual three-statement data entry, and multi-step CSV/Excel spreadsheet imports with column auto-mapping and full audit provenance.
- **Phase 3 (Historical Analysis):** Multi-year revenue growth, CAGRs, profitability margins (Gross, EBITDA, EBIT, Net), working capital dynamics, cash conversion cycles (DSO, DIO, DPO, CCC), operating cash flows, historical UFCF estimates, and accounting integrity audit diagnostics.
- **Phase 4 (Financial Forecasting - Current):**
  - **Configurable Horizon:** Model 3 to 10 forecast years (default 5 years) anchored to the latest verified historical annual period.
  - **Driver-Based Projections:** Constant or year-by-year schedules for revenue growth, gross margins, OpEx % of revenue, D&A % of revenue, CapEx % of revenue, and corporate tax rates.
  - **Working Capital Modeling:** Operating Net Working Capital modeled via turnover days (DSO, DIO, DPO) or revenue percentages, computing annual $\Delta\text{Operating NWC}$.
  - **Unlevered Free Cash Flow (UFCF) Derivation:** Formulaic projection: $\text{UFCF} = \text{NOPAT} + \text{D\&A} - \text{CapEx} - \Delta\text{Operating NWC}$.
  - **Scenario Versioning & Persistence:** Save, load, and manage named forecast models (`ForecastModel`) scoped to valuation projects.
  - **Consolidated Statement Tables:** Multi-period tables merging historical actuals with projected years.
  - **Interactive Plotly Visualizations:** Revenue growth trajectory, margin evolution, and cash flow / UFCF bar-and-line charts.

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
│   │   └── forecasting.py      # Financial forecasting & UFCF projection view
│   └── components/             # Reusable UI elements (cards, badges)
│       ├── __init__.py
│       ├── badges.py
│       └── cards.py
│
├── src/                        # Domain logic & financial engine (Decoupled from UI)
│   ├── __init__.py
│   ├── data/                   # Data management, persistence & validation layer
│   │   ├── __init__.py
│   │   ├── models.py           # SQLAlchemy ORM models (Company, ForecastModel, etc.)
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
│   ├── valuation/              # DCF calculations, WACC, and terminal value (Phases 5-6)
│   ├── scenarios/              # Cross-scenario comparison engine (Phase 7)
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
| **Phase 5** | WACC & Discount Rate Engine | CAPM, cost of debt, tax rates, capital weighting | *Planned* |
| **Phase 6** | DCF Valuation & Terminal Value | Gordon Growth, Exit Multiples, Enterprise & Equity Value | *Planned* |
| **Phase 7** | Scenario Analysis | Bull/Bear scenarios, parameter overrides, comparisons | *Planned* |
| **Phase 8** | Sensitivity Analysis & Simulation | 2D sensitivity matrices, driver tornado charts | *Planned* |
| **Phase 9** | Financial Dashboards | Interactive Plotly statement and valuation charts | *Planned* |
| **Phase 10** | Dynamic Excel Model Exports | openpyxl financial models with dynamic formulas | *Planned* |
| **Phase 11** | Valuation Reports & Memos | Institutional PDF/Markdown investment memos | *Planned* |
| **Phase 12** | AI-Assisted Document Analysis | Automated 10-K extraction and footnote synthesis | *Planned* |

---

## 6. Current Limitations & Disclaimer

### Current Limitations (Phase 4)
- Weighted Average Cost of Capital (WACC) estimation (CAPM, Beta, cost of debt) belongs to Phase 5.
- DCF discounting, terminal value models (Gordon Growth and Exit Multiples), and enterprise/equity value per share calculations belong to Phase 6.
- Cross-scenario comparison matrix tables belong to Phase 7.
- Forecasts represent user-specified mathematical projections based on historical actuals and driver assumptions, not investment recommendations or guarantees.

### Important Disclaimer
> **Not Investment Advice:** This software application is under active engineering development. It is designed for educational, research, and financial modelling purposes only. Nothing produced by this system constitutes financial, investment, legal, or tax advice. No valuation outputs should be relied upon for investment decisions without independent verification by qualified financial professionals.
