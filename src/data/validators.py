"""Validation module for manual entry and imported financial records.

Implements rigorous integrity rules distinguishing blocking validation errors
from observational review warnings without silently mutating financial figures.
"""

from __future__ import annotations

import math
from datetime import date, datetime
from typing import Any, Dict, List, Optional, Set

from src.data.schemas import (
    DataClassification,
    FinancialUnit,
    PeriodType,
    RecordValidationResult,
    SourceType,
    StatementType,
    ValidationIssue,
)

VALID_STATEMENT_TYPES: Set[str] = {e.value for e in StatementType}
VALID_PERIOD_TYPES: Set[str] = {e.value for e in PeriodType}
VALID_CLASSIFICATIONS: Set[str] = {e.value for e in DataClassification}
VALID_UNITS: Set[str] = {e.value for e in FinancialUnit}
VALID_SOURCE_TYPES: Set[str] = {e.value for e in SourceType}


def parse_date(date_val: Any) -> Optional[date]:
    """Safely parse various date representations into a standard datetime.date."""
    if date_val is None:
        return None
    if isinstance(date_val, date) and not isinstance(date_val, datetime):
        return date_val
    if isinstance(date_val, datetime):
        return date_val.date()
    if isinstance(date_val, str):
        date_str = date_val.strip()
        if not date_str:
            return None
        # Try common date formats
        for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%d-%m-%Y", "%d/%m/%Y", "%m/%d/%Y", "%Y%m%d"):
            try:
                return datetime.strptime(date_str, fmt).date()
            except ValueError:
                continue
    return None


def parse_numeric_value(val: Any) -> tuple[Optional[float], Optional[str]]:
    """Parse a financial numeric value, returning (parsed_float, error_message).

    Permits negative values (standard in accounting) but rejects NaN, inf, or unparseable text.
    """
    if val is None:
        return None, "Financial value is missing."
    if isinstance(val, (int, float)):
        if math.isnan(val) or math.isinf(val):
            return None, "Financial value is NaN or Infinite."
        return float(val), None

    # Handle string inputs (e.g. accounting format with parentheses "(150)" or commas "1,200.50")
    if isinstance(val, str):
        cleaned = val.strip()
        if not cleaned:
            return None, "Financial value is empty."

        # Handle parentheses indicating negative values: "(123.45)" -> "-123.45"
        if cleaned.startswith("(") and cleaned.endswith(")"):
            cleaned = "-" + cleaned[1:-1].strip()

        # Remove currency symbols and thousand-separating commas
        cleaned = cleaned.replace("$", "").replace("€", "").replace("£", "").replace("₹", "").replace(",", "")

        try:
            parsed = float(cleaned)
            if math.isnan(parsed) or math.isinf(parsed):
                return None, "Financial value is NaN or Infinite."
            return parsed, None
        except ValueError:
            return None, f"Could not convert '{val}' to a valid numeric financial figure."

    return None, f"Unsupported data type for financial figure: {type(val).__name__}"


def validate_financial_record(
    record: Dict[str, Any],
    record_index: Optional[int] = None,
) -> RecordValidationResult:
    """Validate a single financial data record against structural and financial rules.

    Distinguishes blocking structural errors from review warnings.
    """
    issues: List[ValidationIssue] = []

    # 1. Project Reference
    project_id = record.get("project_id")
    if project_id is None:
        issues.append(ValidationIssue("project_id", "Associated valuation project ID is required.", is_error=True))
    elif not isinstance(project_id, int) or project_id <= 0:
        issues.append(ValidationIssue("project_id", f"Invalid project ID: {project_id}.", is_error=True))

    # 2. Statement Type
    stmt = str(record.get("statement_type", "")).strip().lower()
    if not stmt:
        issues.append(ValidationIssue("statement_type", "Statement type is required.", is_error=True))
    elif stmt not in VALID_STATEMENT_TYPES:
        issues.append(
            ValidationIssue(
                "statement_type",
                f"Invalid statement type '{stmt}'. Must be one of: {', '.join(sorted(VALID_STATEMENT_TYPES))}.",
                is_error=True,
            )
        )

    # 3. Line Item Code & Display Name
    line_code = str(record.get("line_item_code", "")).strip().lower()
    display_name = str(record.get("display_name", "")).strip()

    if not line_code:
        issues.append(ValidationIssue("line_item_code", "Line item code cannot be empty.", is_error=True))
    if not display_name:
        if line_code:
            display_name = line_code.replace("_", " ").title()
        else:
            issues.append(ValidationIssue("display_name", "Display name cannot be empty.", is_error=True))

    # 4. Reporting Period Dates
    start_date = parse_date(record.get("period_start_date"))
    end_date = parse_date(record.get("period_end_date"))

    if not start_date:
        issues.append(ValidationIssue("period_start_date", "Period start date is missing or invalid.", is_error=True))
    if not end_date:
        issues.append(ValidationIssue("period_end_date", "Period end date is missing or invalid.", is_error=True))

    if start_date and end_date:
        if end_date < start_date:
            issues.append(
                ValidationIssue(
                    "period_end_date",
                    f"Period end date ({end_date}) cannot be earlier than start date ({start_date}).",
                    is_error=True,
                )
            )
        else:
            duration_days = (end_date - start_date).days
            period_type = str(record.get("period_type", "")).strip().lower()

            if period_type == PeriodType.ANNUAL.value:
                if duration_days < 250 or duration_days > 400:
                    issues.append(
                        ValidationIssue(
                            "period_type",
                            f"Annual period duration is {duration_days} days (expected ~365 days). Please verify dates.",
                            is_error=False,  # Warning
                        )
                    )
            elif period_type == PeriodType.QUARTERLY.value:
                if duration_days < 60 or duration_days > 120:
                    issues.append(
                        ValidationIssue(
                            "period_type",
                            f"Quarterly period duration is {duration_days} days (expected ~90 days). Please verify dates.",
                            is_error=False,  # Warning
                        )
                    )

    # 5. Period Type
    p_type = str(record.get("period_type", "")).strip().lower()
    if not p_type:
        issues.append(ValidationIssue("period_type", "Period type is required.", is_error=True))
    elif p_type not in VALID_PERIOD_TYPES:
        issues.append(
            ValidationIssue(
                "period_type",
                f"Invalid period type '{p_type}'. Expected: {', '.join(sorted(VALID_PERIOD_TYPES))}.",
                is_error=True,
            )
        )

    # 6. Value
    raw_val = record.get("value")
    parsed_val, val_err = parse_numeric_value(raw_val)
    if val_err:
        issues.append(ValidationIssue("value", val_err, is_error=True))
    else:
        # Observational warning for zero values on core revenue
        if line_code in ("revenue", "total_assets") and parsed_val == 0.0:
            issues.append(
                ValidationIssue(
                    "value",
                    f"Line item '{line_code}' is recorded with a value of exactly 0.0. Please confirm if intended.",
                    is_error=False,
                )
            )

    # 7. Currency
    currency = str(record.get("currency", "")).strip().upper()
    if not currency:
        issues.append(ValidationIssue("currency", "Currency is required (e.g. USD, EUR, INR).", is_error=True))
    elif len(currency) > 10:
        issues.append(ValidationIssue("currency", f"Currency code '{currency}' exceeds maximum length.", is_error=True))

    # 8. Unit / Scale
    unit = str(record.get("unit", "")).strip().lower()
    if not unit:
        issues.append(ValidationIssue("unit", "Unit/scale is required (e.g. units, thousands, millions).", is_error=True))
    elif unit not in VALID_UNITS:
        issues.append(
            ValidationIssue(
                "unit",
                f"Invalid unit scale '{unit}'. Allowed: {', '.join(sorted(VALID_UNITS))}.",
                is_error=True,
            )
        )

    # 9. Data Classification
    classification = str(record.get("data_classification", "")).strip().lower()
    if not classification:
        issues.append(ValidationIssue("data_classification", "Data classification is required.", is_error=True))
    elif classification not in VALID_CLASSIFICATIONS:
        issues.append(
            ValidationIssue(
                "data_classification",
                f"Invalid classification '{classification}'. Allowed: {', '.join(sorted(VALID_CLASSIFICATIONS))}.",
                is_error=True,
            )
        )

    # Prepare normalized data payload if no blocking errors
    has_blocking_errors = any(i.is_error for i in issues)
    normalized_data = None
    if not has_blocking_errors:
        normalized_data = {
            "project_id": project_id,
            "statement_type": stmt,
            "line_item_code": line_code,
            "display_name": display_name,
            "period_start_date": start_date,
            "period_end_date": end_date,
            "period_type": p_type,
            "value": parsed_val,
            "currency": currency,
            "unit": unit,
            "data_classification": classification,
            "source_type": str(record.get("source_type", SourceType.MANUAL_ENTRY.value)).strip().lower(),
            "source_reference": str(record.get("source_reference", "")).strip() or None,
            "source_reporting_date": parse_date(record.get("source_reporting_date")),
            "import_batch_id": record.get("import_batch_id"),
        }

    return RecordValidationResult(
        is_valid=not has_blocking_errors,
        record_index=record_index,
        data=normalized_data,
        issues=issues,
    )
