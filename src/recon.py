import csv
import json
from pathlib import Path
from datetime import date
from decimal import Decimal, InvalidOperation

#DataQualityError is used to raise an exception when input data cannot be read or validated.
class DataQualityError(Exception):
    """Raised when input data cannot be read or validated."""
# This function loads a manifest file, reads rows from a CSV file, and 
# validates each row against the manifest's required fields and allowed currencies. 
# It returns a list of dictionaries containing the validation results for each row.
def load_manifest(path: Path) -> dict:
    try:
        with path.open("r", encoding="utf-8") as file:
            return json.load(file)
    except (FileNotFoundError, PermissionError, json.JSONDecodeError) as e:
        raise DataQualityError(f"Could not load manifest {path.name}: {type(e).__name__}"
        ) from e

#reads rows from a CSV file and validates required fields
def read_rows(path: Path, required_fields: set[str]) -> list[tuple[int, dict[str, str]]]:
    try:
        with path.open( "r", newline="", encoding="utf-8-sig") as file:
            reader = csv.DictReader(file)
            # Check if the CSV has a header
            if reader.fieldnames is None:
                raise DataQualityError(f"CSV has no header: {path.name}")
            missing = required_fields - set(reader.fieldnames)
            # If any required fields are missing, raise an error
            if missing:
                raise DataQualityError(f"Missing required columns in {path.name}: {sorted(missing)}")
            return [(line, row) for line, row in enumerate(reader, start=2)]
    except( FileNotFoundError, IsADirectoryError, PermissionError, UnicodeError,csv.Error) as e:
        raise DataQualityError(f"Could not read {path.name}: {type(e).__name__}") from e

#To validate all rows in a CSV and collect structured results.
def validate_row(row: dict[str, str], line_number: int, source: str, allowed_currencies: set[str]) -> list[str]:
    errors = []
    required_fields = {"txn_ref", "value_date", "currency", "amount"}
    #Validating the row for missing required fields
    for field in required_fields:
        if not row.get(field, "").strip():
            errors.append(f"Missing required field: {field}")
    #date validation
    value_date = row.get("value_date", "").strip()
    if value_date:
        try:
            parsed_date = date.fromisoformat(value_date)
            if parsed_date.isoformat() != value_date:
                errors.append("Invalid date format: value_date (expected YYYY-MM-DD)")
        except ValueError:
            errors.append("Invalid date: value_date")
    #Currency validation
    currency = row.get("currency", "").strip()
    if currency and currency not in allowed_currencies:
        errors.append(f"Unsupported currency: {currency}")
    #Amount validation
    amount = row.get("amount", "").strip()
    if amount:
        try:
            Decimal(amount)
        except InvalidOperation:
            errors.append("Invalid amount: amount must be numeric")
    
    return errors

# This function loads a manifest file, reads rows from a CSV file, and 
# validates each row against the manifest's required fields and allowed currencies. 
# It returns a list of dictionaries containing the validation results for each row.
def load_validate(
    data_dir: Path,
    filename: str,
    manifest: dict
) -> list[dict]:
    path = data_dir / filename

    required_fields = set(manifest["required_fields"])
    allowed_currencies = set(manifest["allowed_currencies"])

    rows = read_rows(path, required_fields)
    results = []

    for line_number, row in rows:
        errors = validate_row(
            row,
            line_number,
            filename,
            allowed_currencies
        )

        results.append({
            "source": filename,
            "row_number": line_number,
            "txn_ref": row.get("txn_ref", ""),
            "valid": len(errors) == 0,
            "errors": errors,
            "row": row
        })

    return results

# This function builds an index of valid rows based on a unique key composed of transaction reference, value date, and currency.

def build_index(
    validation_results: list[dict]
) -> tuple[dict[tuple[str, str, str], dict], list[dict]]:
    index = {}
    seen_keys = set()
    duplicates = []

    for result in validation_results:
        if not result["valid"]:
            continue

        row = result["row"]
        key = (
            row["txn_ref"],
            row["value_date"],
            row["currency"],
        )

        if key in seen_keys:
            duplicates.append({
                "source": result["source"],
                "row_number": result["row_number"],
                "key": key,
                "reason": "Duplicate transaction key",
            })
            continue

        seen_keys.add(key)
        index[key] = result

    return index, duplicates


def process_sources(data_dir: Path, manifest: dict) -> dict:
    ledger_results = load_validate(
        data_dir, "ledger.csv", manifest
    )
    settlement_results = load_validate(
        data_dir, "settlement.csv", manifest
    )

    ledger_index, ledger_duplicates = build_index(ledger_results)
    settlement_index, settlement_duplicates = build_index(
        settlement_results
    )

    return {
        "ledger_results": ledger_results,
        "settlement_results": settlement_results,
        "ledger_index": ledger_index,
        "settlement_index": settlement_index,
        "ledger_duplicates": ledger_duplicates,
        "settlement_duplicates": settlement_duplicates,
    }

def compare_sources(
    ledger_index: dict,
    settlement_index: dict,
    amount_tolerance: Decimal,
) -> dict:
    exceptions = []

    ledger_keys = set(ledger_index.keys())
    settlement_keys = set(settlement_index.keys())

    # Transactions in ledger but missing from settlement
    for key in sorted(ledger_keys - settlement_keys):
        exceptions.append({
            "type": "missing_in_settlement",
            "key": key,
            "ledger_row": ledger_index[key]["row"],
        })

    # Transactions in settlement but missing from ledger
    for key in sorted(settlement_keys - ledger_keys):
        exceptions.append({
            "type": "missing_in_ledger",
            "key": key,
            "settlement_row": settlement_index[key]["row"],
        })

    # Compare amounts for transactions present in both sources
    for key in sorted(ledger_keys & settlement_keys):
        ledger_amount = Decimal(ledger_index[key]["row"]["amount"])
        settlement_amount = Decimal(
            settlement_index[key]["row"]["amount"]
        )

        difference = abs(ledger_amount - settlement_amount)

        if difference > amount_tolerance:
            exceptions.append({
                "type": "amount_mismatch",
                "key": key,
                "ledger_amount": str(ledger_amount),
                "settlement_amount": str(settlement_amount),
                "difference": str(difference),
            })

    return {
        "exceptions": exceptions,
        "matched_key_count": len(ledger_keys & settlement_keys),
    }

def summarize_source(validation_results: list[dict]) -> dict:
    row_count = len(validation_results)
    valid_count = 0
    invalid_count = 0
    raw_totals = {}
    validated_totals = {}

    for result in validation_results:
        row = result["row"]
        currency = row.get("currency", "").strip()
        amount_text = row.get("amount", "").strip()

        # Count valid and invalid records
        if result["valid"]:
            valid_count += 1
        else:
            invalid_count += 1

        # Calculate totals for amounts that can be parsed
        if currency and amount_text:
            try:
                amount = Decimal(amount_text)
            except InvalidOperation:
                continue

            raw_totals[currency] = (
                raw_totals.get(currency, Decimal("0")) + amount
            )

            if result["valid"]:
                validated_totals[currency] = (
                    validated_totals.get(currency, Decimal("0"))
                    + amount
                )

    return {
        "row_count": row_count,
        "valid_count": valid_count,
        "invalid_count": invalid_count,
        "raw_totals_by_currency": {
            currency: str(total)
            for currency, total in raw_totals.items()
        },
        "validated_totals_by_currency": {
            currency: str(total)
            for currency, total in validated_totals.items()
        },
    }

def build_control_totals(processed_sources: dict) -> dict:
    ledger_summary = summarize_source(
        processed_sources["ledger_results"]
    )
    settlement_summary = summarize_source(
        processed_sources["settlement_results"]
    )

    currencies = (
        set(ledger_summary["raw_totals_by_currency"])
        | set(settlement_summary["raw_totals_by_currency"])
    )

    raw_differences = {}

    for currency in sorted(currencies):
        ledger_total = Decimal(
            ledger_summary["raw_totals_by_currency"].get(currency, "0")
        )
        settlement_total = Decimal(
            settlement_summary["raw_totals_by_currency"].get(currency, "0")
        )

        raw_differences[currency] = str(ledger_total - settlement_total)

    return {
        "ledger": ledger_summary,
        "settlement": settlement_summary,
        "raw_total_difference_ledger_minus_settlement": raw_differences,
    }

def write_json(path: Path, data: dict) -> None:
    try:
        with path.open("w", encoding="utf-8") as file:
            json.dump(data, file, indent=4)
    except (OSError, TypeError, ValueError) as e:
        raise DataQualityError(
            f"Could not write {path.name}: {type(e).__name__}"
        ) from e

def run_day01(project_root: Path) -> dict:
    data_dir = project_root / "data"
    output_dir = project_root / "outputs"
    manifest_path = project_root / "schema_manifest.json"

    output_dir.mkdir(parents=True, exist_ok=True)

    manifest = load_manifest(manifest_path)

    processed_sources = process_sources(data_dir, manifest)
    bad_amount_results = load_validate(
        data_dir,
        "bad_amount.csv",
        manifest,
    )
    duplicate_results = load_validate(
        data_dir,
        "duplicate_settlement.csv",
        manifest,
    )

    _, duplicate_test_records = build_index(duplicate_results)
    comparison = compare_sources(
        processed_sources["ledger_index"],
        processed_sources["settlement_index"],
        Decimal(manifest["amount_tolerance"]),
    )

    control_totals = build_control_totals(processed_sources)

    results = {
        "validation": {
            "ledger": processed_sources["ledger_results"],
            "settlement": processed_sources["settlement_results"],
            "bad_amount": bad_amount_results,
        },
        "duplicates": {
            "ledger": processed_sources["ledger_duplicates"],
            "settlement": processed_sources["settlement_duplicates"],
            "duplicate_test": duplicate_test_records,
        },
        "comparison": comparison,
        "control_totals": control_totals,
    }

    write_json(
        output_dir / "row_validation_results.json",
        results["validation"],
    )

    write_json(
        output_dir / "duplicate_report.json",
        results["duplicates"],
    )

    write_json(
        output_dir / "reconciliation_exceptions.json",
        {"exceptions": comparison["exceptions"]},
    )

    write_json(
        output_dir / "control_total_report.json",
        control_totals,
    )

    return results
