"""CSV and Excel import processor for historical financial statements.

Provides file inspection, sheet selection, column auto-mapping heuristics,
preview generation, batch validation, and sample template generation.
"""

from __future__ import annotations

import io
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd

from src.data.schemas import (
    DataClassification,
    FinancialUnit,
    PeriodType,
    SourceType,
    StatementType,
)
from src.data.validators import validate_financial_record

# Standard auto-mapping aliases (lowercase, stripped)
COLUMN_ALIASES: Dict[str, List[str]] = {
    "statement_type": [
        "statement", "statement_type", "statementtype", "stmt", "financial_statement", "type"
    ],
    "line_item_code": [
        "line_item", "line_item_code", "lineitem", "item_code", "metric", "account_code", "code", "line_item_id"
    ],
    "display_name": [
        "display_name", "item_name", "line_item_name", "description", "name", "account_name", "label", "item"
    ],
    "period_start_date": [
        "period_start", "start_date", "period_start_date", "from_date", "from", "period_start_dt"
    ],
    "period_end_date": [
        "period_end", "end_date", "period_end_date", "to_date", "to", "date", "reporting_date", "period_end_dt"
    ],
    "period_type": [
        "period_type", "frequency", "periodicity", "annual_quarterly", "tenor"
    ],
    "value": [
        "value", "amount", "financial_value", "val", "figure", "balance"
    ],
    "currency": [
        "currency", "curr", "ccy", "reporting_currency"
    ],
    "unit": [
        "unit", "scale", "multiplier", "units"
    ],
    "data_classification": [
        "classification", "data_classification", "data_type", "category"
    ],
    "source_reference": [
        "source", "source_reference", "source_description", "reference", "provenance", "notes"
    ],
}


def get_excel_sheet_names(file_bytes: bytes) -> List[str]:
    """Inspect an uploaded Excel file and return available sheet names."""
    excel_file = pd.ExcelFile(io.BytesIO(file_bytes), engine="openpyxl")
    return list(excel_file.sheet_names)


def load_file_dataframe(
    file_bytes: bytes,
    filename: str,
    sheet_name: Optional[str] = None,
) -> pd.DataFrame:
    """Load an uploaded file into a pandas DataFrame."""
    lower_name = filename.lower()
    if lower_name.endswith(".csv"):
        return pd.read_csv(io.BytesIO(file_bytes))
    elif lower_name.endswith(".xlsx"):
        target_sheet = sheet_name if sheet_name else 0
        return pd.read_excel(io.BytesIO(file_bytes), sheet_name=target_sheet, engine="openpyxl")
    else:
        raise ValueError(f"Unsupported file format '{filename}'. Only .csv and .xlsx files are supported.")


def suggest_column_mapping(df_columns: List[str]) -> Dict[str, Optional[str]]:
    """Suggest field-to-column mappings based on alias heuristics."""
    mapping: Dict[str, Optional[str]] = {}
    normalized_cols = {col.strip().lower().replace(" ", "_"): col for col in df_columns}

    for target_field, aliases in COLUMN_ALIASES.items():
        matched_col = None
        for alias in aliases:
            if alias in normalized_cols:
                matched_col = normalized_cols[alias]
                break
        mapping[target_field] = matched_col

    return mapping


def process_import_rows(
    df: pd.DataFrame,
    column_mapping: Dict[str, str],
    project_id: int,
    default_currency: str = "USD",
    default_unit: str = "units",
    default_classification: str = "reported_actual",
    default_period_type: str = "annual",
    source_filename: str = "uploaded_file",
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """Map, parse, and validate rows from an imported DataFrame.

    Returns:
        (accepted_records, rejected_rows_with_reasons)
    """
    accepted_records: List[Dict[str, Any]] = []
    rejected_rows: List[Dict[str, Any]] = []

    for index, row in df.iterrows():
        row_dict = row.to_dict()

        # Extract values using the column mapping with safe defaults
        def get_mapped_val(field_key: str, default: Any = None) -> Any:
            mapped_col = column_mapping.get(field_key)
            if mapped_col and mapped_col in row_dict:
                val = row_dict[mapped_col]
                if pd.notna(val):
                    return val
            return default

        candidate_record = {
            "project_id": project_id,
            "statement_type": get_mapped_val("statement_type", StatementType.INCOME_STATEMENT.value),
            "line_item_code": get_mapped_val("line_item_code"),
            "display_name": get_mapped_val("display_name"),
            "period_start_date": get_mapped_val("period_start_date"),
            "period_end_date": get_mapped_val("period_end_date"),
            "period_type": get_mapped_val("period_type", default_period_type),
            "value": get_mapped_val("value"),
            "currency": get_mapped_val("currency", default_currency),
            "unit": get_mapped_val("unit", default_unit),
            "data_classification": get_mapped_val("data_classification", default_classification),
            "source_type": SourceType.CSV_IMPORT.value if source_filename.endswith(".csv") else SourceType.EXCEL_IMPORT.value,
            "source_reference": f"Imported from {source_filename}: " + str(get_mapped_val("source_reference", "") or ""),
            "source_reporting_date": None,
        }

        # If display name is missing but code is present, generate it
        if not candidate_record["display_name"] and candidate_record["line_item_code"]:
            candidate_record["display_name"] = str(candidate_record["line_item_code"]).replace("_", " ").title()

        validation_result = validate_financial_record(candidate_record, record_index=int(index) + 1)

        if validation_result.is_valid and validation_result.data is not None:
            # Add warnings metadata to accepted record for review visibility
            accepted_payload = dict(validation_result.data)
            accepted_payload["_row_number"] = int(index) + 1
            accepted_payload["_warnings"] = [w.message for w in validation_result.warnings]
            accepted_records.append(accepted_payload)
        else:
            rejection_info = {
                "row_number": int(index) + 1,
                "raw_data": row_dict,
                "errors": [e.message for e in validation_result.errors],
                "warnings": [w.message for w in validation_result.warnings],
            }
            rejected_rows.append(rejection_info)

    return accepted_records, rejected_rows


def generate_sample_csv_template() -> str:
    """Generate a standard CSV template string with documented headers and representative format."""
    headers = [
        "statement_type",
        "line_item_code",
        "display_name",
        "period_start_date",
        "period_end_date",
        "period_type",
        "value",
        "currency",
        "unit",
        "data_classification",
        "source_reference",
    ]

    example_rows = [
        # Income Statement
        "income_statement,revenue,Revenue,2023-01-01,2023-12-31,annual,1500000000.0,USD,units,reported_actual,Annual Report 10-K FY2023",
        "income_statement,cogs,Cost of Goods Sold,2023-01-01,2023-12-31,annual,-900000000.0,USD,units,reported_actual,Annual Report 10-K FY2023",
        "income_statement,operating_expenses,Operating Expenses,2023-01-01,2023-12-31,annual,-350000000.0,USD,units,reported_actual,Annual Report 10-K FY2023",
        "income_statement,ebit,EBIT,2023-01-01,2023-12-31,annual,250000000.0,USD,units,reported_actual,Annual Report 10-K FY2023",
        # Balance Sheet
        "balance_sheet,cash_and_equivalents,Cash and Cash Equivalents,2023-01-01,2023-12-31,annual,450000000.0,USD,units,reported_actual,Annual Report 10-K FY2023",
        "balance_sheet,total_assets,Total Assets,2023-01-01,2023-12-31,annual,3200000000.0,USD,units,reported_actual,Annual Report 10-K FY2023",
        "balance_sheet,total_liabilities,Total Liabilities,2023-01-01,2023-12-31,annual,1800000000.0,USD,units,reported_actual,Annual Report 10-K FY2023",
        "balance_sheet,total_equity,Total Equity,2023-01-01,2023-12-31,annual,1400000000.0,USD,units,reported_actual,Annual Report 10-K FY2023",
        # Cash Flow Statement
        "cash_flow_statement,cfo,Cash Flow from Operating Activities,2023-01-01,2023-12-31,annual,320000000.0,USD,units,reported_actual,Annual Report 10-K FY2023",
        "cash_flow_statement,capex,Capital Expenditure,2023-01-01,2023-12-31,annual,-110000000.0,USD,units,reported_actual,Annual Report 10-K FY2023",
    ]

    return ",".join(headers) + "\n" + "\n".join(example_rows) + "\n"
