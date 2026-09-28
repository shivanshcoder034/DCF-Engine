# AI-Powered DCF Valuation and Sensitivity Engine

An institutional-grade financial modelling platform built in Python, designed to perform Discounted Cash Flow (DCF) valuations, scenario planning, multi-variable sensitivity analysis, and dynamic financial model exports.

> **Active Development Status:** The repository has completed **Phase 2: Company Profiles & Financial Data Management**. Users can create and manage company profiles, configure valuation project workspaces, persist three-statement historical financial data via SQLite and SQLAlchemy, record manual statement entries, and import multi-period CSV/Excel files with automated column mapping, verification, and audit provenance. Future analytical phases (historical ratios, forecasts, WACC, DCF valuation) are scheduled sequentially.

---

## 1. Project Purpose & Overview

The **AI-Powered DCF Valuation and Sensitivity Engine** provides corporate finance analysts, investors, and valuation practitioners with a transparent, structured, and auditable environment to evaluate publicly listed companies.

Key capabilities delivered in Phase 2:
- **Company Profile Management:** Full CRUD management for corporate profiles (name, ticker, exchange, sector, industry, country, reporting currency, fiscal year end, description) with project deletion safeguards.
- **Valuation Project Workspaces:** Dedicated valuation engagements linked to specific companies, supporting active/archived lifecycles.
- **Normalized Financial Statement Persistence:** Atomic, normalized storage for three core financial statement types (`income_statement`, `balance_sheet`, `cash_flow_statement`) supporting both `annual` and `quarterly` frequencies.
- **Data Classification & Provenance:** Explicit tagging of every figure as `reported_actual`, `normalized`, `adjustment`, or `assumption`, with complete source provenance and audit trail tracking.
- **Standard & Custom Line Items:** Rich standard line-item catalog (Revenue, COGS, EBITDA, Net Income, PP&E, Operating Cash Flow, CapEx, etc.) with seamless extensibility for custom account items.
- **Manual Data Entry:** Dedicated form interface with real-time structural validation and custom line-item support.
- **Multi-Format Ingestion (CSV & Excel):** Intelligent import processor supporting `.csv` and `.xlsx` workbooks with multi-sheet detection, heuristic column auto-mapping, validation preview, and configurable duplicate resolution (skip vs. overwrite).
- **Downloadable CSV Import Template:** Built-in template generator ensuring quick data alignment.

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
│   │   └── import_data.py      # CSV/Excel multi-step import processor & preview
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
│   ├── analysis/               # Historical ratios, trends, and margin analysis (Phase 3)
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

## 5. Financial Data Management Guide

### Managing Companies & Projects
1. Navigate to **Company & Financial Data** -> **🏢 Companies**.
2. Register a new company profile with legal name, country, reporting currency, and optional ticker/exchange.
3. Switch to **📁 Valuation Projects** to initialize a new valuation workspace linked to the company.

### Ingesting Historical Statements
1. **Manual Entry:** Select **✍️ Manual Data Entry**, pick your active project, choose the statement type (`Income Statement`, `Balance Sheet`, `Cash Flow`), select the period frequency and dates, select a line item from the catalog (or add a custom item), enter the numeric value, and save.
2. **CSV / Excel Import:**
   - Go to **📥 Import (CSV / Excel)**.
   - Download the built-in template or upload an existing financial spreadsheet (`.csv` or `.xlsx`).
   - Select the target sheet for Excel workbooks.
   - Review or adjust the auto-mapped column headers.
   - Inspect the validation preview (accepted rows, rejected rows with exact error reasons).
   - Select your duplicate conflict resolution policy (`Skip Duplicates` or `Overwrite Duplicates`).
   - Click **Confirm & Save Validated Records** to persist atomically.

---

## 6. 12-Phase Development Roadmap

| Phase | Milestone | Focus Area | Status |
| :---: | :--- | :--- | :---: |
| **Phase 1** | **Foundation & Architecture** | Repository structure, configuration, shell, and docs | **Complete** |
| **Phase 2** | **Company & Financial Data** | SQLAlchemy models, statement storage, CSV/Excel imports | **Complete** |
| **Phase 3** | Historical Financial Analysis | Margins, CAGR, growth trends, working capital cycles | *Planned* |
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

## 7. Current Limitations & Disclaimer

### Current Limitations (Phase 2)
- Financial ratio calculations, forecasting routines, WACC models, and DCF discounting will be implemented in subsequent phases (Phases 3 through 6).
- Stored financial figures remain unmutated as historical data points.
- Third-party live market data feeds (e.g. real-time ticker quotes) are not connected in this phase.

### Important Disclaimer
> **Not Investment Advice:** This software application is under active engineering development. It is designed for educational, research, and financial modelling purposes only. Nothing produced by this system constitutes financial, investment, legal, or tax advice. No valuation outputs should be relied upon for investment decisions without independent verification by qualified financial professionals.
