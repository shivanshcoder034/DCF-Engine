# System Architecture Document
## AI-Powered DCF Valuation and Sensitivity Engine

### 1. Architectural Philosophy and Design Principles

The **AI-Powered DCF Valuation and Sensitivity Engine** is architected as an institutional-grade financial analysis platform. The system is designed following strict software engineering principles:

- **Separation of Concerns (SoC):** The presentation layer (`app/`) is completely decoupled from the data management and analytical engines (`src/`). Under no circumstances should database queries, ORM manipulation, or financial calculation formulas be embedded directly within user interface components.
- **Service & Repository Pattern:** Database access is encapsulated within repository classes (`src/data/repository.py`), while transactional workflows, validation enforcement, and business integrity rules reside in service layer classes (`src/data/services.py`).
- **Pure Analytical Engines (`src/analysis/`):** Historical analysis is implemented as stateless, deterministic computational functions that consume verified records from the data layer and return strongly typed result dataclasses and DataFrames without mutating stored historical records.
- **Transparent Provenance & Integrity:** The system rigorously distinguishes reported historical actuals from derived metrics (e.g., calculated gross profits or EBITDA estimates). No calculated metrics are ever written back into raw financial record tables as fake reported numbers.
- **Audit Diagnostics:** The engine systematically audits input consistency, flagging accounting equation imbalances ($Assets \ne Liabilities + Equity$), period discontinuities, and conflicting multi-version records.

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
└───────────────────────────────┬─────────────────────────────────┘
                                │ Invokes analysis & services
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                 Historical Analysis Engine Layer                │
│                         (src/analysis/)                         │
│   src/analysis/engine.py          │  src/analysis/metrics.py    │
│   src/analysis/working_capital.py │  src/analysis/cash_flow.py  │
│   src/analysis/formatting.py      │  src/analysis/models.py     │
└───────────────────────────────┬─────────────────────────────────┘
                                │ Queries normalized records
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Data Management & Service Layer              │
│                           (src/data/)                           │
│   src/data/services.py    │   src/data/validators.py            │
│   src/data/importers.py   │   src/data/schemas.py               │
└───────────────────────────────┬─────────────────────────────────┘
                                │ Calls typed repositories
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                  Persistence & Repository Layer                 │
│   src/data/repository.py  │   src/data/models.py                │
│   src/data/database.py    │   database/dcf_engine.db            │
└───────────────────────────────┬─────────────────────────────────┘
                                │ Serves future engines
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│               Analytical & Valuation Engines (Phases 4-12)      │
│   src/forecasting/ │  src/valuation/  │  src/scenarios/         │
│   src/sensitivity/ │  src/exports/                              │
└─────────────────────────────────────────────────────────────────┘
```

---

### 3. Historical Analysis Engine Architecture (`src/analysis/`)

| Module | Core Responsibility |
| :--- | :--- |
| `engine.py` | Coordinates record retrieval via `FinancialDataService`, currency filtering, unit scale harmonization, period alignment, conflict resolution, and quality audit checks. Returns a complete `HistoricalAnalysisBundle`. |
| `metrics.py` | Pure calculation routines for revenue growth, multi-year CAGR, Gross Profit and Margin, EBITDA and Margin, EBIT and Margin, Net Profit Margin, and Effective Tax Rate. |
| `working_capital.py` | Calculates Net Working Capital (NWC), Operating Working Capital, period-over-period $\Delta NWC$, Days Sales Outstanding (DSO), Days Inventory Outstanding (DIO), Days Payables Outstanding (DPO), and the Cash Conversion Cycle (CCC). |
| `cash_flow.py` | Computes Operating Cash Flow (CFO), Capital Expenditure intensity, CFO Less CapEx, and historical Unlevered Free Cash Flow (UFCF) analytical estimates ($EBIT(1-T) + D\&A - CapEx - \Delta NWC$). |
| `formatting.py` | Formats metrics into multi-period pandas DataFrames for Income Statements, Balance Sheets, Cash Flows, and Efficiency Ratios with explicit type labels (Reported vs. Derived). |
| `models.py` | Strongly typed dataclasses: `FinancialPeriod`, `MetricResult`, `WorkingCapitalMetrics`, `CashFlowAnalysisMetrics`, `DataQualityIssue`, and `HistoricalAnalysisBundle`. |

---

### 4. Data Selection, Period Alignment, and Conflict Rules

1. **Chronological Period Sorting:**
   - Financial periods are grouped strictly by `period_end_date` and sorted chronologically.
   - Frequency isolation: Annual and quarterly periods are never blended into a single comparative time series.
2. **Currency Integrity:**
   - Calculations require single-currency consistency. If a project contains records across multiple currencies, the engine isolates records to the dominant or selected currency and logs a `DataQualityIssue(severity="warning")`.
3. **Duplicate and Conflict Handling:**
   - If multiple records exist for the same `(project_id, statement_type, line_item_code, period_end_date, data_classification)`, the engine selects the most recently updated record and generates an explicit audit notice detailing the conflicting record IDs.
4. **Scale Harmonization:**
   - All stored values are scaled to base monetary units using `FinancialUnit.multiplier(unit)` prior to formula evaluation, ensuring exact consistency across thousands, millions, and raw units.
5. **Zero Denominator & Undefined Math:**
   - Zero denominators (e.g. zero revenue for margin calculation, zero prior value for growth, non-positive values for CAGR) produce structured `MetricResult(value=None, status="unavailable", explanation=...)` rather than crashing, fabricating zero, or returning `NaN`/`inf`.

---

### 5. Historical Analysis Output Contracts

Every calculated metric is encapsulated within a `MetricResult` DTO:
- `metric_code`: Machine-readable identifier (e.g. `revenue_growth`, `gross_margin`, `ebitda_margin`, `ccc`).
- `metric_name`: Human-readable label.
- `value`: Numeric float value, or `None` if uncomputable.
- `unit_or_type`: Output unit (`percentage`, `currency`, `days`, `ratio`).
- `period_label`: Assigned period tag (e.g. `FY2023`, `Q3 2023`).
- `is_reported`: Boolean flag clearly distinguishing reported items from derived figures.
- `source_line_items`: Line-item codes used in the calculation.
- `status`: Execution status (`calculated`, `reported`, `unavailable`, `warning`).
- `explanation`: Contextual reason when a metric is unavailable or derived.

---

### 6. Decoupling Rules for Future Phases (Phases 4-12)

As development progresses into **Phase 4 (Financial Forecasting)** and **Phase 5 (WACC)**:
1. Forecasting routines will consume historical baselines from `HistoricalAnalysisBundle` (e.g. baseline margins, working capital days, CapEx % of revenue).
2. Future forecast schedules and WACC calculations will reside in their dedicated `src/` modules (`src/forecasting/`, `src/valuation/`) without modifying `src/analysis/` or database records.
3. The historical analysis engine remains an immutable retrospective audit tool.
