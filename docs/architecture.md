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

### 6. WACC & Discount Rate Engine Architecture (`src/wacc/`)

| Module | Core Responsibility |
| :--- | :--- |
| `models.py` | Strongly typed dataclasses: `InputProvenance`, `CostOfEquityInputs`, `CostOfDebtInputs`, `CapitalStructureInputs`, `TaxRateInputs`, `WaccAssumptions` (container for all WACC drivers with JSON serialization), and evaluation results (`CostOfEquityResult`, `CostOfDebtResult`, `CapitalStructureResult`, `WaccResult`). |
| `calculations.py` | Pure, deterministic mathematical functions for CAPM, pre-tax/after-tax borrowing rates, capital structure weights, and blended WACC formula derivation. Enforces finite numeric checks, non-negative capital, non-zero capital base, and incomplete-input detection. |
| `engine.py` | `WaccEngine`: Extracts baseline debt balances, book equity, accounting interest rates ($\text{Interest Expense} / \text{Debt}$), and effective tax rates from `HistoricalAnalysisBundle`; manages default assumption creation with explicit provenance tags; orchestrates WACC evaluation. |
| `services.py` | `WaccService`: Coordinates saving, loading, listing, and deleting named `WaccModel` entities in the SQLite database. |
| `formatting.py` | Formats capital structure matrices, cost of capital breakdowns, and Plotly visualization specifications (capital structure donut chart and WACC contribution stacked bar chart). |

---

### 7. WACC Mathematical Formulas & Sign Conventions

1. **Cost of Equity — Capital Asset Pricing Model (CAPM):**
   $$\text{Cost of Equity } (K_e) = R_f + (\beta \times \text{ERP})$$
   - $R_f$: Benchmark risk-free sovereign rate (e.g. 10-Year US Treasury yield).
   - $\beta$: Equity beta measuring systematic market sensitivity.
   - $\text{ERP}$: Equity Risk Premium reflecting long-term expected market excess return.
2. **Cost of Debt & Corporate Tax Shield:**
   $$\text{After-Tax Cost of Debt } (K_{d,\text{after}}) = K_d \times (1 - t)$$
   - $K_d$: Pre-tax borrowing cost (user-entered market yield or historical accounting interest rate estimate: $\text{Interest Expense} / \text{Total Interest-Bearing Debt}$).
   - $t$: Marginal corporate income tax rate applied to debt interest deductibility.
   - *Tax Shield Benefit:* $K_d - K_{d,\text{after}} = K_d \times t$.
   - *Equity Isolation:* No tax shield is applied to the equity component.
3. **Capital Structure Weighting:**
   $$\text{Total Capital Base } (V) = \text{Equity Value } (E) + \text{Debt Balance } (D)$$
   $$\text{Equity Weight } (W_e) = \frac{E}{V} \quad\Big|\quad \text{Debt Weight } (W_d) = \frac{D}{V}$$
   - *Equity Component ($E$):* Preferred market capitalization (Shares $\times$ Price). If market cap is unavailable, book value of equity from the balance sheet may be used as a proxy, accompanied by a prominent warning banner.
   - *Debt Component ($D$):* Interest-bearing borrowings only (Short-Term Debt + Long-Term Debt). Non-interest-bearing liabilities (Accounts Payable, Accruals) are strictly excluded.
   - *Validation:* $E \ge 0$, $D \ge 0$, $V > 0$, and $W_e + W_d = 100.0\%$.
4. **Weighted Average Cost of Capital (WACC):**
   $$\text{WACC} = (W_e \times K_e) + (W_d \times K_{d,\text{after}})$$
   - Evaluated as a percentage rate.
   - If any required component is missing or invalid, final WACC is withheld and incomplete inputs are explicitly enumerated.

---

### 8. Persistence & Scenario Versioning

- **Entities:**
  - `ForecastModel`: Table storing multi-year financial projection assumption sets (`horizon_years`, `base_period_label`, `assumptions_json`).
  - `WaccModel`: Table storing named cost-of-capital assumption scenarios (`name`, `assumptions_json`, `description`, timestamps).
  - `DcfModel`: Table storing named DCF valuation assumption sets, linking `forecast_model_id`, `wacc_model_id`, `discounting_convention`, `terminal_inputs`, `bridge_inputs`, and `diluted_shares`.
- **Project Isolation:** All scenarios are linked via `project_id` foreign keys with cascade deletion. Multiple named scenarios can coexist without colliding or mutating historical financial actuals.

---

### 9. DCF Valuation Engine Architecture (`src/dcf/`)

| Module | Core Responsibility |
| :--- | :--- |
| `models.py` | Strongly typed dataclasses: `DiscountingConvention`, `TerminalValueMethod`, `TerminalValueInputs`, `EquityBridgeInputs`, `DcfAssumptions`, `YearDiscountingResult`, `TerminalValueResult`, `EquityBridgeResult`, and `DcfValuationResult`. |
| `calculations.py` | Pure, deterministic mathematical functions for discounting cash flows ($DF = (1 + \text{WACC})^{-t}$), evaluating Gordon Growth ($\text{WACC} > g$) and Exit Multiple terminal values, executing the equity bridge, and computing implied intrinsic value per share. |
| `engine.py` | `DcfEngine`: Extracts baseline cash and debt for the equity bridge, coordinates linked Phase 4 forecast cash flows and Phase 5 WACC rates, builds default assumptions, and orchestrates valuation execution. |
| `services.py` | `DcfService`: Coordinates saving, loading, listing, and deleting named `DcfModel` entities in SQLite. |
| `formatting.py` | Formats cash flow discounting schedules, enterprise-to-equity bridge tables, and generates Plotly visualization charts (cash flow discounting trajectory and EV composition donut). |

---

### 10. DCF Mathematical Formulas, Terminal Values & Equity Bridge

1. **Cash Flow Discounting Schedule:**
   $$\text{Discount Factor}_t = \frac{1}{(1 + \text{WACC})^t}$$
   - *End-of-Year Convention (Default):* $t = 1.0, 2.0, \dots, N$.
   - *Mid-Year Convention:* $t = 0.5, 1.5, \dots, N - 0.5$.
   $$\text{PV of Forecast UFCF} = \sum_{t=1}^N \left(\text{UFCF}_t \times \text{Discount Factor}_t\right)$$
2. **Terminal Value (TV) Formulations:**
   - *Method A — Gordon Growth Perpetuity:*
     $$\text{UFCF}_{N+1} = \text{UFCF}_N \times (1 + g) \quad\Big|\quad \text{Terminal Value} = \frac{\text{UFCF}_{N+1}}{\text{WACC} - g}$$
     *(Enforces strict requirement: $\text{WACC} > g$. If condition is violated, terminal value is withheld).*
   - *Method B — Exit Multiple Method:*
     $$\text{Terminal Value} = \text{Terminal Year EBITDA}_N \times \text{Exit Multiple}$$
   - *Discounting Terminal Value:*
     $$\text{PV of Terminal Value} = \text{Terminal Value} \times \frac{1}{(1 + \text{WACC})^N}$$
3. **Enterprise Value (EV):**
   $$\text{Enterprise Value} = \text{PV of Forecast UFCF} + \text{PV of Terminal Value}$$
4. **Enterprise Value to Equity Value Bridge:**
   $$\text{Equity Value} = \text{EV} + \text{Cash} - \text{Debt} - \text{Minority Interest} - \text{Preferred Stock} + \text{Other Adjustments}$$
   - Cash and liquid equivalents are added.
   - Total interest-bearing debt (Short-Term + Long-Term) is deducted.
   - Non-controlling minority interest claims and preferred equity claims are deducted.
   - Net Debt is defined as $\text{Debt} - \text{Cash}$.
5. **Implied Intrinsic Value Per Share:**
   $$\text{Implied Value per Share} = \frac{\text{Equity Value}}{\text{Diluted Common Shares Outstanding}}$$
   - Requires positive diluted share count. If missing or non-positive, implied per share value is safely withheld while preserving Enterprise and Equity Value.

---

### 11. Decoupling Rules for Phase 7 (Scenario Analysis) & Phase 8 (Sensitivity)

1. **Scenario Analysis (Phase 7):** Will consume saved `ForecastModel`, `WaccModel`, and `DcfModel` configurations to run comparative cross-scenario tables (Base vs. Bull vs. Bear) without modifying underlying valuation calculations.
2. **Sensitivity Analysis (Phase 8):** Will evaluate 2D matrices (e.g. WACC vs. Perpetual Growth Rate $g$, or WACC vs. Exit Multiple) using the pure calculation functions in `src/dcf/calculations.py`.
3. **Historical Data Isolation:** Historical statements, analysis bundles, forecast projections, WACC hurdles, and DCF models remain modular, auditable, and decoupled.
