
# ReconAI - Day 1

A Python-based reconciliation project that validates ledger and settlement data, detects duplicate transaction keys, identifies reconciliation exceptions, and generates control-total reports.

## Requirements

- Python 3.11 recommended
- Git
- Visual Studio Code (optional)

The current implementation uses Python standard-library modules. No third-party Python packages are required unless additional dependencies are introduced later.

## Project structure

- `data/`: Main input CSV files and validation test fixtures
- `docs/`: Reconciliation brief and documentation
- `outputs/`: Generated JSON reports
- `src/`: Reconciliation logic
- `tests/`: Automated unit tests
- `schema_manifest.json`: Input contract and reconciliation configuration
- `run_day01.py`: Application entry point

## Setup

Clone the repository and open its folder.

Check the Python version:

```bash
python --version
```

Create a virtual environment:

```bash
python -m venv .venv
```

Activate it on Windows:

```powershell
.\.venv\Scripts\Activate.ps1
```

If using Command Prompt instead of PowerShell:

```bat
.venv\Scripts\activate.bat
```

No package installation is currently required.

## Run the tests

```bash
python -m unittest discover -s tests -v
```

## Run the application

```bash
python run_day01.py
```

The application reads the input files and schema manifest, performs reconciliation checks, and generates JSON reports in `outputs/`.

## Important notes

- The join-key configuration is documented in `schema_manifest.json`.
- Confirm the intended join key with the trainer because the assignment contains inconsistent examples.
- The program identifies exceptions. Final dispositions, adjustments, write-offs, and ledger postings remain the responsibility of authorized human reviewers.
- The CSV files contain synthetic training data, not real financial records.
