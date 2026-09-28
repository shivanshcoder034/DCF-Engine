# System Architecture Document
## AI-Powered DCF Valuation and Sensitivity Engine

### 1. Architectural Philosophy and Design Principles

The **AI-Powered DCF Valuation and Sensitivity Engine** is architected as an institutional-grade financial analysis platform. The system is designed following strict software engineering principles:

- **Separation of Concerns (SoC):** The presentation layer (`app/`) is completely decoupled from the analytical and calculation engine (`src/`). Under no circumstances should financial valuation math or forecasting algorithms be embedded directly within user interface components or Streamlit scripts.
- **Stateless & Pure Calculation Engines:** Modules within `src/` (valuation, forecasting, sensitivity) operate as pure, testable computational engines that receive structured inputs (data models or parameter dataclasses) and return structured outputs (results dataclasses, pandas DataFrames, or matrix structures).
- **Centralized Configuration:** Paths, runtime settings, and environment variables are resolved through a single source of truth (`app.config.settings`) using Python's `pathlib.Path`, eliminating hardcoded relative paths and working directory dependencies.
- **Progressive Phased Delivery:** The architecture provides explicit hooks and modular boundaries for each subsequent phase without introducing premature speculative logic or mock calculations.

---

### 2. High-Level Architectural Layers

```
┌─────────────────────────────────────────────────────────────────┐
│                       Presentation Layer                        │
│                 (Streamlit Interface / Visuals)                 │
│      app/main.py  │  app/pages/  │  app/components/             │
└───────────────────────────────┬─────────────────────────────────┘
                                │ Calls typed engines
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Analytical & Engine Layer                    │
│                      (Decoupled Python Logic)                   │
│   src/valuation/     │   src/forecasting/    │  src/scenarios/  │
│   src/analysis/      │   src/sensitivity/    │  src/exports/    │
└───────────────────────────────┬─────────────────────────────────┘
                                │ Accesses validated records
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Data & Storage Layer                       │
│                   src/data/  │  database/                       │
│        (SQLite Persistence, SQLAlchemy ORM, File Storage)       │
└─────────────────────────────────────────────────────────────────┘
```

---

### 3. Directory Layout and Component Roles

#### `app/` (Presentation & Application Layer)
- **Role:** Handles user interface rendering, user input collection, page routing, and display orchestration using Streamlit and Plotly.
- **Key Modules:**
  - `main.py`: Entry point for the Streamlit application; manages top-level page routing, sidebar navigation, and global page setup.
  - `config.py`: Centralized configuration singleton (`settings`) defining directory paths, runtime environment, and non-sensitive application metadata.
  - `pages/`: (Future phases) Modular subpages for multi-page UI implementations as individual views expand.
  - `components/`: Reusable UI elements (e.g. status badges, layout cards, metric display formatters, input panels).
- **Boundary Rule:** UI code must only ingest user inputs, call functions in `src/`, and render the returned results. It must never perform raw financial formulas, financial statement adjustments, or direct database queries.

#### `src/` (Core Financial Engine Layer)
- **Role:** Houses all domain logic, financial modeling, forecasting algorithms, sensitivity engines, and export generators.
- **Key Packages:**
  - `src/data/`: Data models, financial statement ingestion, normalization, validation, and database abstraction.
  - `src/analysis/`: Historical financial statement analysis, growth rates (CAGR), margin trends, and financial ratios.
  - `src/forecasting/`: Driver-based multi-year financial forecasts, operating bridge models, and Unlevered Free Cash Flow schedules.
  - `src/valuation/`: Discounted Cash Flow math, WACC estimation (CAPM, cost of debt), terminal value methodologies (Gordon Growth, Exit Multiples), and enterprise-to-equity value bridge.
  - `src/scenarios/`: Multi-scenario management (Base, Bull, Bear) and parameter override logic.
  - `src/sensitivity/`: Multi-dimensional sensitivity matrices, tornado analysis, and simulation routines.
  - `src/exports/`: Excel financial workbook generation with dynamic formulas via `openpyxl`, alongside structured report generation.
- **Boundary Rule:** `src/` modules must have zero dependencies on `streamlit` or UI libraries. They must remain fully usable as a standalone Python library (e.g., via CLI, automated scripts, or backend APIs).

#### `database/` (Local Persistence Layer)
- **Role:** Designated local storage directory for the SQLite database file (`dcf_engine.db`) and future migration scripts.
- **Boundary Rule:** Files in this directory (except `.gitkeep`) are excluded from version control via `.gitignore` to prevent committing local application databases.

#### `data/` (Local File & Cache Store)
- **Role:** Designated local directory for imported raw files (e.g., company reports, local templates, cached raw statements).
- **Boundary Rule:** All user-specific data files (except `.gitkeep`) are excluded from Git tracking via `.gitignore`.

#### `docs/` (Technical Documentation)
- **Role:** Technical reference documentation, architecture design records, development roadmaps, and valuation methodology specifications.

---

### 4. Integration Pattern for Future Modules

When new capabilities are introduced in subsequent phases, developers must adhere to the following integration contract:

1. **Define Data Contracts in `src/`:**
   Create typed dataclasses or Pydantic models in the relevant `src/` package (e.g., `src/valuation/models.py`) specifying input assumptions and output metrics.
2. **Implement Pure Calculation Functions in `src/`:**
   Implement standalone, deterministic calculation functions in `src/` that take input models and return calculated output objects.
3. **Connect to Presentation in `app/`:**
   In the corresponding `app/` view or page, collect inputs from Streamlit widgets, construct the input dataclass, invoke the calculation function from `src/`, and render the resulting metrics and Plotly charts.
4. **Decoupled Testing:**
   Write unit tests directly against `src/` calculation functions without needing to mock or render Streamlit UI sessions.
