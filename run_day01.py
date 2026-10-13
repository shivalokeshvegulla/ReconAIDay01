from pathlib import Path

from src.recon import run_day01


if __name__ == "__main__":
    project_root = Path(__file__).resolve().parent

    results = run_day01(project_root)

    print("ReconAI Day 1 processing completed.")
    print(
        f"Matched transaction keys: "
        f"{results['comparison']['matched_key_count']}"
    )
    print(
        f"Exceptions found: "
        f"{len(results['comparison']['exceptions'])}"
    )