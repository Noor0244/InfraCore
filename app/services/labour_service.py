import csv
from pathlib import Path

DATA_FILE = Path("data/raw/labour.csv")


def get_labour():
    if not DATA_FILE.exists():
        return []
    with open(DATA_FILE, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))
