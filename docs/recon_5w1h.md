# ReconAI Day 1 Project Brief

## 1. Who

The bank's reconciliation team is responsible for reviewing reconciliation results. Authorized analysts and reviewers make decisions about exceptions and any financial adjustments.

## 2. What

ReconAI validates and compares two data sources:

1. `ledger.csv`: Internal banking ledger records.
2. `settlement.csv`: External card or payment settlement records.

The Day 1 objective is to validate input data, detect data quality issues, calculate control totals, and report exceptions.

## 3. When

The process runs after the ledger and settlement files for the relevant reconciliation period are available.

The exact processing schedule and date window must be confirmed with the business team.

## 4. Where

The application runs in a Python environment. Input CSV files are stored in the `data` directory, and generated reports are saved in the `outputs` directory.

## 5. Why

Missing fields, invalid amounts, duplicate records, and differences between source totals can cause reconciliation errors. These issues must be identified and reported before further processing.

## 6. How

1. Read the ledger and settlement CSV files.
2. Validate required fields, data types, dates, amounts, and currency codes.
3. Create keyed dictionaries for valid records.
4. Detect duplicate records using sets.
5. Calculate record counts and amount totals by currency.
6. Compare source totals and report exceptions.
7. Save the schema manifest and control total report as JSON files.

## Human Decision and Control

Python performs deterministic validation and comparison. AI does not determine the authoritative match status. Authorized reconciliation analysts and reviewers remain responsible for exception dispositions, adjustments, write-offs, and ledger postings.