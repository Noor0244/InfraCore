import csv
import os
from typing import List, Dict

DATA_ROOT = os.path.join(os.getcwd(), "data", "raw")


def _ensure_file(path: str, headers: List[str] = None):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    if not os.path.exists(path):
        with open(path, "w", newline="", encoding="utf-8") as f:
            if headers:
                writer = csv.DictWriter(f, fieldnames=headers)
                writer.writeheader()


def read_csv(filename: str) -> List[Dict]:
    path = os.path.join(DATA_ROOT, filename)
    if not os.path.exists(path):
        return []
    with open(path, "r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        return list(reader)


def write_csv(filename: str, rows: List[Dict], headers: List[str] = None):
    path = os.path.join(DATA_ROOT, filename)
    _ensure_file(path, headers or (list(rows[0].keys()) if rows else []))
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=headers or rows[0].keys())
        writer.writeheader()
        for r in rows:
            writer.writerow(r)


def append_csv(filename: str, row: Dict, headers: List[str]):
    path = os.path.join(DATA_ROOT, filename)
    _ensure_file(path, headers)
    with open(path, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writerow(row)
import csv
from pathlib import Path


def read_csv_safe(path: str):
    file = Path(path)
    if not file.exists():
        return []
    with open(file, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))
