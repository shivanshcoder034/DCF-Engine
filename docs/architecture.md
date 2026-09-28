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

### 11. Scenario Analysis Engine Architecture (`src/scenarios/`)

| Module | Core Responsibility |
| :--- | :--- |
| `models.py` | Strongly typed dataclasses: `ScenarioOverrides` (growth delta pp, margin delta pp, WACC delta bps, terminal delta bps/x), `ScenarioAnalysisAssumptions` (container linking DCF, forecast, and WACC models with Bull/Bear overrides), `ScenarioCaseResult` (valuation outputs, effective metrics, diagnostics for an individual scenario case), and `ScenarioAnalysisResult` (consolidated 3-case bundle). |
| `engine.py` | `ScenarioEngine`: Orchestrates deterministic recalculation of Base, Bull, and Bear cases. Applies percentage-point shifts to forecast revenue and operating margins, basis-point adjustments to WACC discount rates, and terminal parameter deltas. Reuses Phase 4 forecast, Phase 5 WACC, and Phase 6 DCF calculation engines. Enforces withholding of invalid scenarios (e.g. $\text{WACC} \le g$). |
| `services.py` | `ScenarioService`: Coordinates saving, loading, listing, and deleting named `ScenarioModel` entities in the SQLite database. |
| `formatting.py` | Formats cross-scenario comparison matrix tables, detailed assumption auditability DataFrames, and generates interactive Plotly charts (EV & Equity Value grouped bar chart, implied share price comparison, projected UFCF cash flow trajectory lines, and EV composition stacked bar chart). |

---

### 12. Scenario Override Formulas, Units & Validation Logic

1. **Revenue Growth Adjustment ($\Delta g_{\text{rev}}$):**
   $$g_{\text{rev}, t}^{\text{scenario}} = g_{\text{rev}, t}^{\text{base}} + \Delta g_{\text{rev}}$$
   - Expressed in **percentage points** (`pp`) added directly to each forecast year's growth rate.
   - Prevents silent distortion from relative percentage interpretations (e.g., $+2.0\text{ pp}$ on a $6.0\%$ rate yields $8.0\%$, not $6.12\%$).
2. **Operating Margin Adjustment ($\Delta m$):**
   $$\text{Gross Margin}_t^{\text{scenario}} = \text{Gross Margin}_t^{\text{base}} + \Delta m$$
   $$\text{EBIT Margin}_t^{\text{scenario}} = \text{EBIT Margin}_t^{\text{base}} + \Delta m$$
   - Expressed in **percentage points** (`pp`) applied to operating profitability across all forecast periods.
3. **Cost of Capital / WACC Adjustment ($\Delta\text{WACC}_{\text{bps}}$):**
   $$\text{WACC}^{\text{scenario}} = \text{WACC}^{\text{base}} + \left(\frac{\Delta\text{WACC}_{\text{bps}}}{100.0}\right)$$
   - Expressed in **basis points** (`bps`), where $100\text{ bps} = 1.00\text{ percentage point} = 1.0\%$.
   - Validates that effective $\text{WACC} > 0\%$.
4. **Terminal Value Parameter Adjustments:**
   - *Gordon Growth Perpetuity Model:*
     $$g^{\text{scenario}} = g^{\text{base}} + \left(\frac{\Delta g_{\text{bps}}}{100.0}\right)$$
     - Expressed in **basis points** (`bps`).
     - **Mathematical Validity Condition:** If $\text{WACC}^{\text{scenario}} \le g^{\text{scenario}}$, the denominator $(\text{WACC} - g)$ is non-positive. In this case, terminal value and Enterprise Value are withheld and a diagnostic warning is prominently issued.
   - *Exit Multiple Method:*
     $$\text{Multiple}^{\text{scenario}} = \text{Multiple}^{\text{base}} + \Delta\text{Multiple}$$
     - Expressed as a multiple delta (`x EBITDA`).
5. **Base Case Isolation & Persistence Integrity:**
   - The Base case strictly uses the selected saved forecast and WACC baseline without overrides ($\Delta = 0$).
   - Editing Bull or Bear overrides never mutates or overwrites the saved `ForecastModel`, `WaccModel`, or `DcfModel` records in the database.
   - Scenario sets are persisted under a distinct `ScenarioModel` entity in SQLite (`scenario_models` table).

---

---

### 13. Sensitivity Analysis & Simulation Architecture (`src/sensitivity/`)

| Module | Core Responsibility |
| :--- | :--- |
| `models.py` | Strongly typed dataclasses: `AxisRangeConfig` (min, max, step), `DistributionConfig` (distribution type and parameters), `SensitivityCellResult` (individual grid cell with baseline intersection flag and validity status), `SensitivityMatrixResult` (2D valuation matrix), `MonteCarloSummaryStats` (mean, median, standard deviation, percentiles), `MonteCarloSimulationResult` (sampling outputs, draw counts, statistics, histograms), and `SensitivityConfig` (persisted configuration container). |
| `engine.py` | `SensitivityEngine`: Evaluates deterministic 2D sensitivity matrices by keeping baseline forecast cash flows constant and recalculating WACC and terminal value models; executes reproducible Monte Carlo simulations using `numpy.random.default_rng` across Normal, Triangular, and Uniform distributions with full invalid draw accounting. |
| `services.py` | `SensitivityService`: Coordinates saving, loading, listing, and deleting named `SensitivityModel` entities in the SQLite database. |
| `formatting.py` | Generates formatted 2D tabular matrices, interactive Plotly heatmaps with cell hover diagnostics and baseline markers (`★`), Monte Carlo summary statistics tables, and empirical distribution histograms. |

---

### 14. Sensitivity Matrix & Monte Carlo Mathematical Models

1. **Two-Dimensional Valuation Sensitivity Matrix:**
   - Evaluates a 2D parameter grid across:
     - **Row Axis:** Discount Rate / WACC ($\text{WACC}_1, \dots, \text{WACC}_R$).
     - **Column Axis:** Terminal Value parameter ($\text{Param}_1, \dots, \text{Param}_C$), representing Perpetual Growth Rate ($g$) under Gordon Growth, or Exit Multiple under the Exit Multiple method.
   - **Optimization & Decoupling:** Operational Unlevered Free Cash Flows (UFCF) and terminal year EBITDA are evaluated once from the baseline forecast, while discounting factors and terminal values are recalculated per cell.
   - **Mathematical Constraint Enforcement:**
     - For Gordon Growth: If $\text{WACC}_r \le g_c$, the denominator $(\text{WACC} - g)$ is non-positive. The cell is marked invalid with status `"invalid"` and reason `"WACC <= g"`. Outputs are strictly withheld rather than replaced with silent zeros.
     - For Exit Multiple: If $\text{Multiple}_c \le 0$, the cell is marked invalid.
   - **Baseline Intersection:** The exact cell corresponding to the baseline model's WACC and terminal parameter is identified and flagged (`★`).

2. **Monte Carlo Probabilistic Valuation Simulation:**
   - **Reproducibility Guarantee:** Random number generation is seeded via user-controlled `random_seed` using `numpy.random.default_rng(abs(seed))`, ensuring deterministic results for identical inputs.
   - **Supported Statistical Distributions:**
     - *Normal Distribution:* Sampled with mean $\mu$ and standard deviation $\sigma$: $X \sim \mathcal{N}(\mu, \sigma^2)$.
     - *Triangular Distribution:* Sampled with lower bound $a$, mode $c$, and upper bound $b$: $X \sim \text{Triangular}(a, c, b)$.
     - *Uniform Distribution:* Sampled with minimum $a$ and maximum $b$: $X \sim \mathcal{U}(a, b)$.
   - **Selective Randomization:** Users can independently toggle simulation for:
     - Revenue growth delta ($\Delta g_{\text{rev}}$ in percentage points)
     - Operating margin delta ($\Delta m$ in percentage points)
     - Cost of Capital / WACC (percentage rate)
     - Terminal value parameter ($g$ percentage rate or Exit Multiple)
   - **Invalid Draw Accounting & Discard Protocol:**
     - If a random draw violates feasibility (e.g. sampled $\text{WACC} \le \text{sampled } g$, non-positive WACC, or non-positive exit multiple), it is recorded under `invalid_reasons` and excluded from valuation arrays.
     - Discarded draws never contaminate the valid distribution or bias summary statistics.
   - **Percentile Derivations:**
     $$\text{Percentiles: } P_{10}, P_{25}, P_{50} \text{ (Median)}, P_{75}, P_{90}, \text{Min, Max, Mean, Std Dev}$$
     Computed across valid draws for Enterprise Value, Equity Value, and Implied Intrinsic Value per Share.

3. **Persistence Scope:**
   - `SensitivityModel` records in SQLite store configuration parameters (matrix axis ranges, selected distributions, iteration count, and random seed). Raw simulated samples are re-evaluated deterministically on-demand to conserve database storage.

---

### 15. Reporting, Presentation & Export Architecture (`src/reporting/`)

| Module | Core Responsibility |
| :--- | :--- |
| `models.py` | Strongly typed domain dataclasses: `ReportSection` (enum of 10 supported sections), `ReportSectionConfig` (granular inclusion toggles), `ReportMetadata` (title, subtitle, company name, ticker, reporting currency, fiscal year-end, report date, prepared by, narrative notes), `ReportModelReferences` (linked IDs and names for historical frequency/classification, forecast, WACC, DCF, scenario, and sensitivity models), `ReportConfig` (persisted container specification), and `ReportBundle` (compiled analytical container holding resolved models, calculations, and diagnostic logs). |
| `engine.py` | `ReportEngine.compile_report_bundle`: Coordinates retrieval of saved models via project services, invokes domain calculation engines (`HistoricalAnalysisEngine`, `FinancialForecastingEngine`, `WaccEngine`, `DcfEngine`, `ScenarioAnalysisEngine`, `SensitivityEngine`) without formula reimplementation, isolates missing model errors, and compiles comprehensive warnings and data quality findings. |
| `services.py` | `ReportService`: Handles CRUD persistence operations for `ReportModel` entities in SQLite (`database/dcf_engine.db`) scoped to `ValuationProject`. |
| `pdf_export.py` | `PdfReportGenerator`: Pure-Python publication-grade PDF 1.4 document builder producing multi-page printable memorandums with running headers/footers, dynamic "Page X of Y" pagination, KPI highlight cards, and structured tables. Zero external C-library or system binary dependencies. |
| `excel_export.py` | `ExcelReportGenerator`: Multi-sheet institutional financial model workbook generator using `openpyxl`, with professional styling, dark navy headers, thin borders, custom number formatting (`$#,##0.0`, `0.0%`, `0.00x`), auto-adjusted column widths, and freeze panes across 8 dedicated sheets. |
| `csv_export.py` | `CsvReportGenerator`: Standardized, unambiguous CSV exporters for Valuation Summary, Forecast Projections Schedule, Historical Financial Statements, 2D Sensitivity Matrix, and Base/Bull/Bear Scenario Comparisons. |

---

### 16. Multi-Format Export Capabilities & Content Integrity

1. **Analytical Source of Truth:**
   - The reporting engine never recalculates or approximates financial metrics independently. All calculations are executed directly by underlying engines (`HistoricalAnalysisEngine`, `FinancialForecastingEngine`, `WaccEngine`, `DcfEngine`, `ScenarioAnalysisEngine`, `SensitivityEngine`).
2. **Missing Model & Invalid Output Handling:**
   - If a referenced model ID has been deleted or cannot be resolved, the reporting engine surfaces a diagnostic notice (`⚠️ Missing Dependency: Model ID X was not found`) and withholds affected outputs rather than substituting an arbitrary default or silent zero.
   - Cells in sensitivity matrices with invalid mathematical conditions ($\text{WACC} \le g$) are marked with `INVALID` and withheld from valuation sums.
3. **Multi-Format Export Matrix:**
   - **PDF:** Polished printable PDF report formatted for standard 8.5" x 11" Letter page dimensions, running headers and footers with dynamic page numbering, institutional typography, and executive disclaimers.
   - **Excel:** Structured multi-tab workbook with dedicated sheets for Executive Summary, Historical Financials, Forecast Projections, WACC Analysis, DCF Valuation & Equity Bridge, Scenario Analysis, Sensitivity & Simulation, and Audit & Disclosures.
   - **CSV:** Tabular CSV exports formatted for downstream data integration and auditing.
4. **Persistence & Snapshot Integrity:**
   - `ReportModel` records in SQLite persist metadata, narrative commentary, model reference foreign keys, and section inclusion flags in JSON format.
   - Large raw simulation iterations are not redundantly duplicated in database storage, ensuring instant loading and database compactness.

---

### 17. Decoupling Rules for Phase 10 (Financial Dashboards & Interactive Visualizations)

1. **Dashboard Decoupling:** Phase 10 interactive dashboards will consume compiled analytical data structures from `ReportBundle` or domain result objects (`HistoricalAnalysisBundle`, `ForecastResult`, `WaccResult`, `DcfValuationResult`, `ScenarioAnalysisResult`, `SensitivityMatrixResult`, `MonteCarloSimulationResult`).
2. **Formula Integrity:** Presentation and dashboard layers must not duplicate domain formulas, WACC weighting, or cash flow discounting algorithms.
3. **Database Isolation:** All reports, scenarios, sensitivity models, and dashboards remain scoped to `ValuationProject` via foreign keys.


