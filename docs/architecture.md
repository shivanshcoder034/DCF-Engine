# System Architecture Document
## AI-Powered DCF Valuation and Sensitivity Engine

### 1. Architectural Philosophy and Design Principles

The **AI-Powered DCF Valuation and Sensitivity Engine** is architected as an institutional-grade financial analysis and valuation platform. The system is designed following strict software engineering principles:

- **Separation of Concerns (SoC):** The presentation layer (`app/`) is completely decoupled from the data management (`src/data/`), historical analytics (`src/analysis/`), and forecasting engines (`src/forecasting/`). Under no circumstances should database queries, ORM manipulation, or mathematical projection algorithms be embedded directly within user interface components.
- **Service & Repository Pattern:** Database access is encapsulated within repository classes (`src/data/repository.py`), while transactional workflows, validation enforcement, and scenario persistence reside in service layer classes (`src/data/services.py`, `src/forecasting/services.py`).
- **Deterministic Forecasting Engines (`src/forecasting/`):** Projections are implemented as stateless, deterministic computational functions that consume historical baselines and user-specified drivers to produce multi-year schedules without modifying raw historical records.
- **Auditable Assumption Scenarios:** Forecast assumptions are explicitly versioned, scoped to project IDs, and persisted via `ForecastModel` entities. Every driver tracks its provenance (`historical_baseline`, `user_entered`, or `application_default`).
- **Unlevered Cash Flow Rigor:** Unlevered Free Cash Flow (UFCF) projections adhere strictly to corporate finance formulations: $\text{UFCF} = \text{NOPAT} + \text{D\&A} - \text{CapEx} - \Delta\text{Operating NWC}$. Discounting and WACC estimation are decoupled into subsequent valuation modules.

---

### 2. High-Level Architectural Layers

```
┌─────────────────────────────────────────────────────────────────┐
│                       Presentation Layer                        │
│                 (Streamlit Interface / Visuals)                 │
│      app/main.py  │  app/pages/  │  app/components/             │
│      - companies.py           - projects.py                     │
│      - financial_data.py      - manual_entry.py                 │
│      - import_data.py         - historical_analysis.py          │
│      - forecasting.py                                           │
└───────────────────────────────┬─────────────────────────────────┘
                                │ Invokes forecasting & analysis
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│             Financial Forecasting & Projection Engine           │
│                       (src/forecasting/)                        │
│   src/forecasting/engine.py       │  src/forecasting/models.py  │
│   src/forecasting/services.py     │  src/forecasting/formatting │
└───────────────┬───────────────────────────────┬─────────────────┘
                │ Consumes baselines            │ Persists models
                ▼                               ▼
┌───────────────────────────────┐ ┌───────────────────────────────┐
│   Historical Analysis Engine  │ │  Data Management & Storage    │
│        (src/analysis/)        │ │         (src/data/)           │
│ - HistoricalAnalysisBundle    │ │ - ForecastModel persistence   │
│ - Baselines & Turnover Days   │ │ - FinancialDataPoint records  │
│ - CAGR & Margin Baselines     │ │ - database/dcf_engine.db      │
└───────────────────────────────┘ └───────────────────────────────┘
                                                │
                                                ▼
┌─────────────────────────────────────────────────────────────────┐
│               Valuation & Downstream Modules (Phases 5-12)      │
│   src/valuation/ (WACC & DCF) │  src/scenarios/                 │
│   src/sensitivity/            │  src/exports/                   │
└─────────────────────────────────────────────────────────────────┘
```

---

### 3. Forecasting Engine Architecture (`src/forecasting/`)

| Module | Core Responsibility |
| :--- | :--- |
| `models.py` | Strongly typed dataclasses: `ForecastAssumptions` (multi-year growth, margin, OpEx, D&A, CapEx, WC turnover days, tax rate), `YearForecast` (annual income statement and cash flow metrics), and `ForecastResult` (consolidated multi-period bundle). |
| `engine.py` | `FinancialForecastingEngine`: Extracts baselines from `HistoricalAnalysisBundle`, generates intelligent defaults, and executes deterministic multi-period projections. |
| `services.py` | `ForecastService`: Coordinates saving, loading, listing, and deleting versioned `ForecastModel` entities in the SQLite database. |
| `formatting.py` | Multi-period statement and UFCF bridge table formatters merging historical actuals and forecast years into unified DataFrames. |

---

### 4. Projection Mathematical Formulas & Sign Conventions

1. **Revenue Trajectory:**
   $$\text{Revenue}_t = \text{Revenue}_{t-1} \times (1 + \text{Growth Rate}_t)$$
   *(Base Period: Last verified historical annual revenue).*
2. **COGS & Gross Profit:**
   $$\text{COGS}_t = \text{Revenue}_t \times (1 - \text{Gross Margin}_t) \quad\Big|\quad \text{Gross Profit}_t = \text{Revenue}_t - \text{COGS}_t$$
3. **Operating Expenses & EBITDA:**
   $$\text{OpEx}_t = \text{Revenue}_t \times \text{OpEx}\%_t \quad\Big|\quad \text{EBITDA}_t = \text{Gross Profit}_t - \text{OpEx}_t$$
4. **Depreciation, Amortization & Operating Profit (EBIT):**
   $$\text{D\&A}_t = \text{Revenue}_t \times \text{D\&A}\%_t \quad\Big|\quad \text{EBIT}_t = \text{EBITDA}_t - \text{D\&A}_t$$
5. **Operating Taxes & NOPAT:**
   $$\text{Taxes on EBIT}_t = \max(0, \text{EBIT}_t \times \text{Tax Rate}) \quad\Big|\quad \text{NOPAT}_t = \text{EBIT}_t \times (1 - \text{Tax Rate})$$
6. **Operating Working Capital (Operating NWC):**
   - *Turnover Days Method (Default):*
     $$\text{AR}_t = \frac{\text{Revenue}_t \times \text{DSO}_t}{365} \quad\Big|\quad \text{Inventory}_t = \frac{\text{COGS}_t \times \text{DIO}_t}{365} \quad\Big|\quad \text{AP}_t = \frac{\text{COGS}_t \times \text{DPO}_t}{365}$$
     $$\text{Operating NWC}_t = \text{AR}_t + \text{Inventory}_t - \text{AP}_t$$
   - *Revenue % Fallback:* $\text{Operating NWC}_t = \text{Revenue}_t \times \text{NWC}\%_t$
   - *Annual Change:* $\Delta\text{Operating NWC}_t = \text{Operating NWC}_t - \text{Operating NWC}_{t-1}$
7. **Capital Expenditures (CapEx):**
   $$\text{CapEx}_t = \text{Revenue}_t \times \text{CapEx}\%_t$$
8. **Unlevered Free Cash Flow (UFCF):**
   $$\text{UFCF}_t = \text{NOPAT}_t + \text{D\&A}_t - \text{CapEx}_t - \Delta\text{Operating NWC}_t$$
   *(Sign convention: CapEx and $\Delta\text{Operating NWC}$ increases are subtractions from operating cash flow).*

---

### 5. Persistence & Scenario Versioning

- **Entity:** `ForecastModel` table in SQLite (`database/dcf_engine.db`).
- **Columns:** `id`, `project_id` (FK to `valuation_projects.id`), `name`, `horizon_years`, `base_period_label`, `assumptions_json`, `description`, `created_at`, `updated_at`.
- **Isolation:** Multiple named forecast models (e.g. "Base Case", "Conservative Case", "Aggressive Growth") can be saved for the same project without overwriting one another or modifying raw historical records.

---

### 6. Decoupling Rules for Phase 5 (WACC) & Phase 6 (DCF Valuation)

1. Downstream DCF valuation modules will consume the projected `annual_forecasts` from `ForecastResult` (specifically the explicit `ufcf` stream).
2. Phase 5 will estimate the discount rate (WACC) independently based on capital structure, beta, risk-free rate, and cost of debt.
3. Phase 6 will discount the projected `ufcf` stream using WACC and compute the terminal value, enterprise value, and equity value per share.
4. Historical records, analysis bundles, and forecast schedules remain cleanly isolated.
