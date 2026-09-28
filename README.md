# AI-Powered DCF Valuation and Sensitivity Engine

An institutional-grade financial modelling platform built in Python, designed to perform Discounted Cash Flow (DCF) valuations, scenario planning, multi-variable sensitivity analysis, and dynamic financial model exports.

> **Active Development Status:** This repository is currently in **Phase 1: Project Foundation and Architecture**. The application foundation, centralized configuration, and presentation shell are established. Core financial calculations, data pipelines, and valuation algorithms will be implemented in subsequent phases.

---

## 1. Project Purpose & Overview

The **AI-Powered DCF Valuation and Sensitivity Engine** provides corporate finance analysts, investors, and valuation practitioners with a transparent, structured, and auditable environment to evaluate publicly listed companies.

When completed, the engine will support:
- Company profile management and multi-year historical financial statement ingestion.
- Comprehensive historical financial analysis (CAGR, margin trends, capital efficiency).
- Multi-year forecasting of operating metrics and Unlevered Free Cash Flows (UFCF).
- Weighted Average Cost of Capital (WACC) estimation via CAPM and debt cost schedules.
- Enterprise Value and Equity Value determination via Perpetual Growth and Exit Multiple methods.
- Dynamic scenario planning (Base, Bull, Bear) and two-dimensional sensitivity matrices.
- Dynamic Excel financial model exports with live spreadsheet formulas.
- Downloadable valuation reports and audit trails.

---

## 2. Technology Stack

- **Core Runtime & Computation:** Python (>= 3.10), [pandas](https://pandas.pydata.org/) (>= 2.2.0), [NumPy](https://numpy.org/) (>= 1.26.0)
- **User Interface & Visualizations:** [Streamlit](https://streamlit.io/) (>= 1.35.0), [Plotly](https://plotly.com/python/) (>= 5.22.0)
- **Database & ORM Foundation:** [SQLite](https://www.sqlite.org/) (embedded), [SQLAlchemy](https://www.sqlalchemy.org/) (>= 2.0.30)
- **Financial Model Export Foundation:** [openpyxl](https://openpyxl.readthedocs.io/) (>= 3.1.2)
- **Configuration Management:** [python-dotenv](https://github.com/theskumar/python-dotenv) (>= 1.0.1)

---

## 3. Repository Structure

```
dcf-valuation-engine/
│
├── app/                        # Presentation & UI layer (Streamlit)
│   ├── __init__.py             # App package definition
│   ├── main.py                 # Streamlit entry point & navigation dispatcher
│   ├── config.py               # Centralized configuration singleton (pathlib)
│   ├── pages/                  # Modular UI page views (future phases)
│   │   └── __init__.py
│   └── components/             # Reusable UI components (cards, badges)
│       ├── __init__.py
│       ├── badges.py
│       └── cards.py
│
├── src/                        # Domain logic & financial engine (Decoupled from UI)
│   ├── __init__.py
│   ├── data/                   # Data ingestion, schema models, & persistence
│   │   └── __init__.py
│   ├── analysis/               # Historical ratios, trends, and margin analysis
│   │   └── __init__.py
│   ├── valuation/              # DCF calculations, WACC, and terminal value models
│   │   └── __init__.py
│   ├── forecasting/            # Driver-based financial forecasting & UFCF schedules
│   │   └── __init__.py
│   ├── scenarios/              # Scenario profiles (Base, Bull, Bear)
│   │   └── __init__.py
│   ├── sensitivity/            # 2D sensitivity matrices & simulation engine
│   │   └── __init__.py
│   └── exports/                # openpyxl Excel models & report generators
│       └── __init__.py
│
├── database/                   # Designated directory for local SQLite database
│   └── .gitkeep
│
├── data/                       # Designated directory for local raw files/datasets
│   └── .gitkeep
│
├── docs/                       # Technical & architectural documentation
│   ├── architecture.md         # Detailed architectural layers & design rules
│   └── development-roadmap.md  # Sequenced phased implementation plan
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

## 4. Prerequisites

- **Python:** Python 3.10 to 3.13 installed on your system. Verify with:
  ```bash
  python --version
  ```
- **Git:** Git version control installed.

---

## 5. Installation Instructions

### Step 1: Clone the Repository
```bash
git clone <repository-url>
cd "AI-Powered DCF Valuation and Sensitivity Engine"
```

### Step 2: Set Up a Virtual Environment (Recommended)

**On Windows (PowerShell):**
```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

**On macOS / Linux:**
```bash
python3 -m venv venv
source venv/bin/activate
```

### Step 3: Install Dependencies
```bash
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

---

## 6. Configuration & Environment Variables

The application uses centralized configuration defined in `app/config.py`. You can customize settings via environment variables or a local `.env` file:

1. Copy `.env.example` to `.env`:
   ```powershell
   # Windows PowerShell
   Copy-Item .env.example .env

   # Linux / macOS
   cp .env.example .env
   ```

2. Available environment variables:

| Variable | Default Value | Description |
| :--- | :--- | :--- |
| `APP_ENV` | `development` | Runtime environment (`development`, `staging`, `production`) |
| `APP_DEBUG` | `True` | Debug flag (`True` or `False`) |
| `APP_HOST` | `localhost` | Streamlit host address |
| `APP_PORT` | `8501` | Streamlit port |
| `LOG_LEVEL` | `INFO` | Application logging level |
| `DATABASE_URL` | `sqlite:///database/dcf_engine.db` | Local database connection string |
| `DATA_DIR` | `data` | Local data cache directory relative to project root |
| `DATABASE_DIR` | `database` | Local database directory relative to project root |
| `DOCS_DIR` | `docs` | Documentation directory relative to project root |

---

## 7. How to Launch the Application

Run the Streamlit application from the project root directory:

```bash
streamlit run app/main.py
```

Or run via Python module:
```bash
python -m streamlit run app/main.py
```

Once launched, navigate to `http://localhost:8501` in your browser.

---

## 8. Development Roadmap Summary

| Phase | Milestone | Scope | Status |
| :---: | :--- | :--- | :---: |
| **Phase 1** | **Foundation & Architecture** | Project structure, configuration, shell, and docs | **Complete** |
| **Phase 2** | Company & Financial Data Management | Financial statement schemas, normalization, SQLite persistence | *Planned* |
| **Phase 3** | Historical Financial Analysis | Margins, CAGR, growth trends, working capital cycles | *Planned* |
| **Phase 4** | Forecasting & Free Cash Flow Engine | Revenue drivers, operating schedules, UFCF projections | *Planned* |
| **Phase 5** | WACC & Discount Rate Engine | CAPM, cost of debt, tax rates, capital weighting | *Planned* |
| **Phase 6** | DCF Valuation & Terminal Value | Gordon Growth, Exit Multiples, Enterprise & Equity Value | *Planned* |
| **Phase 7** | Scenario & Sensitivity Analysis | Bull/Bear scenarios, 2D sensitivity matrices, simulations | *Planned* |
| **Phase 8** | Reporting & Dynamic Excel Exports | openpyxl financial models with live formulas and memos | *Planned* |

For comprehensive phase descriptions, see [docs/development-roadmap.md](file:///c:/Users/mail2/OneDrive/Desktop/AI-Powered%20DCF%20Valuation%20and%20Sensitivity%20Engine/docs/development-roadmap.md).

---

## 9. Current Limitations & Disclaimer

### Current Limitations (Phase 1)
- The application currently provides the foundational architecture and presentation shell.
- Navigation sections for future modules (Phases 2 through 8) are displayed as informational placeholders.
- Financial calculation engines, database persistence, and external data ingestion are not yet connected.

### Important Disclaimer
> **Not Investment Advice:** This software application is under active engineering development. It is designed for educational, research, and financial modelling purposes only. Nothing produced by this system constitutes financial, investment, legal, or tax advice. No valuation outputs should be relied upon for investment decisions without independent verification by qualified financial professionals.
