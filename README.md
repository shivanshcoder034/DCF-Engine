# AI-Powered DCF Valuation and Sensitivity Engine

An institutional-grade financial modelling platform built in Python, designed to perform Discounted Cash Flow (DCF) valuations, scenario planning, multi-variable sensitivity analysis, and dynamic financial model exports.

> **Active Development Status:** The repository has completed **Phase 3: Historical Financial Analysis**. The application features an immutable, deterministic financial analysis engine that processes stored multi-period historical statements, evaluates growth rates, multi-year CAGRs, profitability margins (Gross, EBITDA, EBIT, Net), working capital dynamics, cash conversion cycles (DSO, DIO, DPO, CCC), operating cash flows, and historical Unlevered Free Cash Flow (UFCF) analytical estimates with interactive Plotly visual charts and accounting integrity audit diagnostics.

---

## 1. Project Purpose & Overview

The **AI-Powered DCF Valuation and Sensitivity Engine** provides corporate finance analysts, investors, and valuation practitioners with a transparent, structured, and auditable environment to evaluate publicly listed companies.

Key capabilities delivered in Phases 1–3:
- **Phase 1 (Foundation):** Clean decoupled architecture, centralized configuration using `pathlib.Path`, and modular Streamlit shell.
- **Phase 2 (Data Management):** Persistent SQLite storage with SQLAlchemy ORM, company profiles, valuation project workspaces, manual three-statement data entry, and multi-step CSV/Excel spreadsheet imports with column auto-mapping and full audit provenance.
- **Phase 3 (Historical Analysis - Current):**
  - **Revenue & Growth:** Period-over-period growth rates and multi-year CAGR calculations across valid chronological periods.
  - **Profitability Margins:** Gross Profit Margin, EBITDA Margin, EBIT Margin, and Net Profit Margin, clearly distinguishing reported vs. derived figures and properly handling negative profits.
  - **Operating Expenses & D&A:** OpEx and Depreciation & Amortization intensity (% of revenue).
  - **Working Capital Analysis:** Net Working Capital ($CA - CL$), Operating Working Capital ($AR + Inventory - AP$), and period changes ($\Delta NWC$).
  - **Working Capital Efficiency:** Days Sales Outstanding (DSO), Days Inventory Outstanding (DIO), Days Payables Outstanding (DPO), and Cash Conversion Cycle ($CCC = DSO + DIO - DPO$) using average balances or labeled ending-balance approximations.
  - **Tax Rate Analysis:** Effective tax rate calculations ($Tax / PBT$) with sign normalization and unprofitable period checks.
  - **Cash Flow Diagnostics:** Operating Cash Flow (CFO), CapEx intensity, Operating Cash Flow Less CapEx, and historical Unlevered Free Cash Flow (UFCF) analytical estimates ($EBIT(1-T) + D\&A - CapEx - \Delta NWC$).
  - **Interactive Plotly Charts:** Dual-axis revenue & YoY growth charts, multi-metric margin evolution lines, CFO vs. CapEx bars, and working capital cycle visualizations.
  - **Data Quality & Audit Panel:** Automated audit checks verifying balance sheet equilibrium ($Assets = Liabilities + Equity$), period continuity, and conflicting multi-version records.

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
│   │   └── historical_analysis.py # Historical analysis view, Plotly charts & audit
│   └── components/             # Reusable UI elements (cards, badges)
│       ├── __init__.py
│       ├── badges.py
│       └── cards.py
│
├── src/                        # Domain logic & financial engine (Decoupled from UI)
│   ├── __init__.py
│   ├── data/                   # Data management, persistence & validation layer
│   │   ├── __init__.py
│   │   ├── models.py           # SQLAlchemy ORM models (Company, Project, etc.)
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
│   ├── valuation/              # DCF calculations, WACC, and terminal value (Phases 5-6)
│   ├── forecasting/            # Driver-based financial forecasting & UFCF (Phase 4)
│   ├── scenarios/              # Scenario profiles: Base, Bull, Bear (Phase 7)
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
| **Phase 4** | Forecasting & Free Cash Flows | Driver-based revenue models, OpEx schedules, UFCF | *Planned* |
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

### Current Limitations (Phase 3)
- Future financial forecasting (revenue drivers, expense schedules, working capital forecasts) belongs to Phase 4.
- Weighted Average Cost of Capital (WACC) estimation and DCF enterprise/equity valuation models belong to Phases 5 and 6.
- The historical UFCF figure presented is an unprojected analytical metric ($EBIT(1-T) + D\&A - CapEx - \Delta NWC$) evaluating historical cash flow generation, not a forecast or discounted valuation output.

### Important Disclaimer
> **Not Investment Advice:** This software application is under active engineering development. It is designed for educational, research, and financial modelling purposes only. Nothing produced by this system constitutes financial, investment, legal, or tax advice. No valuation outputs should be relied upon for investment decisions without independent verification by qualified financial professionals.
