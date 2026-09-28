# System Architecture Document
## AI-Powered DCF Valuation and Sensitivity Engine

### 1. Architectural Philosophy and Design Principles

The **AI-Powered DCF Valuation and Sensitivity Engine** is architected as an institutional-grade financial analysis platform. The system is designed following strict software engineering principles:

- **Separation of Concerns (SoC):** The presentation layer (`app/`) is completely decoupled from the data management and analytical engines (`src/`). Under no circumstances should database queries, ORM manipulation, or financial calculation formulas be embedded directly within user interface components.
- **Service & Repository Pattern:** Database access is encapsulated within repository classes (`src/data/repository.py`), while transactional workflows, validation enforcement, and business integrity rules reside in service layer classes (`src/data/services.py`).
- **Atomic Persistence & Controlled Initialization:** SQLite database tables are created idempotently via SQLAlchemy (`src/data/database.py`). Session lifecycle is managed through scoped context managers ensuring automatic commit on success and rollback on exceptions.
- **Full Provenance & Auditability:** Every financial record maintains an auditable chain of custody, capturing its origin (manual entry vs. file import), source reference, import batch identifier, publication date, and data classification.
- **Non-Mutating Data Ingestion:** Historical financial figures are ingested and stored exactly as entered or reported. No calculated totals, margins, ratios, or inferred values are injected during the data-management phase.

---

### 2. High-Level Architectural Layers

```
┌─────────────────────────────────────────────────────────────────┐
│                       Presentation Layer                        │
│                 (Streamlit Interface / Visuals)                 │
│      app/main.py  │  app/pages/  │  app/components/             │
│      - companies.py      - projects.py                          │
│      - financial_data.py - manual_entry.py - import_data.py     │
└───────────────────────────────┬─────────────────────────────────┘
                                │ Invokes transactional services
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
│               Analytical & Valuation Engines (Phases 3-12)      │
│   src/analysis/   │  src/forecasting/ │  src/valuation/         │
│   src/scenarios/  │  src/sensitivity/ │  src/exports/           │
└─────────────────────────────────────────────────────────────────┘
```

---

### 3. Data-Management Modules (`src/data/`)

| Module | Core Responsibility |
| :--- | :--- |
| `models.py` | SQLAlchemy ORM declarative models: `Company`, `ValuationProject`, `ImportBatch`, and `FinancialDataPoint`. |
| `database.py` | Engine configuration, thread-safe connection pool, `SessionLocal` factory, and `get_db_session()` context manager. |
| `schemas.py` | Enums (`StatementType`, `PeriodType`, `DataClassification`, `SourceType`, `FinancialUnit`, `ProjectStatus`), standard line-item catalog (`STANDARD_LINE_ITEMS`), and validation dataclasses. |
| `validators.py` | Multi-field validation logic verifying dates, types, allowed line-item codes, and numeric integrity. Distinguishes blocking errors from review warnings. |
| `repository.py` | Encapsulated data-access operations providing typed CRUD and duplicate detection methods. |
| `services.py` | Transactional coordinators (`CompanyService`, `ProjectService`, `FinancialDataService`) enforcing business logic (e.g. blocking deletion of companies with active projects). |
| `importers.py` | Ingestion engine for `.csv` and `.xlsx` workbooks, sheet inspector, column auto-mapping heuristics, validation preview, and CSV template generator. |

---

### 4. Database Schema & Relational Design

The database utilizes SQLite located at `database/dcf_engine.db` (configurable via `DATABASE_URL`).

```
┌─────────────────────────┐
│        Company          │
├─────────────────────────┤
│ id (PK, Integer)        │
│ name (String)           │
│ ticker (String, opt)    │
│ exchange (String, opt)  │
│ country (String)        │
│ currency (String)       │
│ fiscal_year_end (String)│
│ description (Text)      │
└────────────┬────────────┘
             │ 1
             │
             │ has many
             ▼ *
┌─────────────────────────┐           ┌─────────────────────────┐
│    ValuationProject     │ 1       * │       ImportBatch       │
├─────────────────────────┼───────────┼─────────────────────────┤
│ id (PK, Integer)        │           │ id (PK, Integer)        │
│ company_id (FK)         │           │ project_id (FK)         │
│ name (String)           │           │ filename (String)       │
│ description (Text)      │           │ import_timestamp (DT)   │
│ status (Active/Archiv)  │           │ records_accepted (Int)  │
└────────────┬────────────┘           │ records_rejected (Int)  │
             │ 1                      │ status (String)         │
             │                        └────────────┬────────────┘
             │ has many                            │ 1
             ▼ *                                   │ provides batch id
┌──────────────────────────────────────────────────┴────────────┐
│                      FinancialDataPoint                       │
├───────────────────────────────────────────────────────────────┤
│ id (PK, Integer)                                              │
│ project_id (FK -> ValuationProject.id)                        │
│ statement_type (income_statement / balance_sheet / cash_flow) │
│ line_item_code (String, e.g. 'revenue', 'cogs', 'ppe')        │
│ display_name (String)                                         │
│ period_start_date (Date)                                      │
│ period_end_date (Date)                                        │
│ period_type (annual / quarterly)                              │
│ value (Float, supports positive and negative)                 │
│ currency (String, e.g. 'USD', 'EUR')                          │
│ unit (units / thousands / millions / billions)                │
│ data_classification (reported_actual / normalized / etc.)    │
│ source_type (manual_entry / csv_import / excel_import)        │
│ source_reference (String, citation or footnote notes)         │
│ source_reporting_date (Date, publication date)                │
│ import_batch_id (FK -> ImportBatch.id, nullable)              │
│ created_at / updated_at (DateTime)                            │
└───────────────────────────────────────────────────────────────┘
```

#### Safe Cascading Rules
- Foreign key `ValuationProject.company_id` uses `RESTRICT`. The `CompanyService` explicitly checks project counts and blocks company deletion if projects exist, preventing accidental data loss.
- Foreign key `FinancialDataPoint.import_batch_id` uses `SET NULL` on batch deletion, preserving individual data points even if batch records are cleaned up.

---

### 5. Financial Data Classifications & Line Items

#### Data Classifications
1. `reported_actual`: Official figures directly reported in regulatory filings (10-K, 10-Q, annual reports).
2. `normalized`: Historical figures adjusted for non-recurring expenses, restructuring, or standard realignments.
3. `adjustment`: Discretionary analyst pro-forma adjustments.
4. `assumption`: Baseline calibration assumptions.

#### Supported Statement Types
- `income_statement`: Operating and non-operating revenue, costs, and earnings.
- `balance_sheet`: Assets, liabilities, and shareholder equity balances.
- `cash_flow_statement`: Operating, investing, and financing cash flows.

#### Standard Line-Item Catalog
A standardized dictionary of financial line items is defined in `src/data/schemas.py`. Users may also input custom line-item codes with custom display names without breaking database schemas.

---

### 6. Validation and Ingestion Pipeline

Data ingestion follows a strict 8-step pipeline:

```
[ Upload File (.csv / .xlsx) ]
             │
             ▼
[ Inspect Workbook & Sheet Selection ]
             │
             ▼
[ Column Auto-Mapping (Heuristic Aliases) ]
             │
             ▼
[ User Review / Manual Field Adjustments ]
             │
             ▼
[ Deterministic Validation (src/data/validators.py) ]
  ├── Hard Errors: Missing dates, non-numeric values, invalid types ──► [ Rejection Log ]
  └── Soft Warnings: Unusually long/short periods, zero revenues  ─────► [ Review Notices ]
             │
             ▼
[ Duplicate Conflict Check ]
  ├── Policy A: Skip existing duplicates
  └── Policy B: Overwrite existing duplicates
             │
             ▼
[ Atomic Transactional Commit ]
  ├── Create ImportBatch provenance record
  └── Bulk insert/update FinancialDataPoint records
```

---

### 7. Decoupling Rules for Future Phases

As development progresses into **Phase 3 (Historical Analysis)** and **Phase 4 (Forecasting)**:
1. Analytical modules must query records through `FinancialDataService` or `FinancialDataRepository`.
2. Calculated metrics (e.g. gross margins, EBITDA bridges, CAGR) must **never** be saved back into `FinancialDataPoint` rows as fake reported actuals.
3. Analytical results must be returned as pure Python dataclasses or pandas DataFrames to be rendered by `app/pages/` or exported to Excel.
