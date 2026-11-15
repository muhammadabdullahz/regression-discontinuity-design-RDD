"""Download HMDA one-year files ('lar' = loans, 'ts' = lender list). Cached."""
import subprocess
from pathlib import Path

RAW = Path("data/raw")


def pull_hmda(year: int, kind: str = "lar") -> Path:
    RAW.mkdir(parents=True, exist_ok=True)
    name = f"{year}_public_{kind}_one_year_csv"
    csv = RAW / f"{name}.csv"
    if not csv.exists():
        zpath = RAW / f"{kind}.zip"
        url = f"https://files.ffiec.cfpb.gov/static-data/one-year/{year}/{name}.zip"
        subprocess.run(["wget", "-q", "-O", str(zpath), url], check=True)
        subprocess.run(["unzip", "-o", "-q", str(zpath), f"{name}.csv", "-d", str(RAW)], check=True)
        zpath.unlink()
    return csv
