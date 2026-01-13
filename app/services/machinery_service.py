import csv
from pathlib import Path

DATA_FILE = Path("data/raw/machinery.csv")


def get_machinery():
    if not DATA_FILE.exists():
        return []
    with open(DATA_FILE, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))
