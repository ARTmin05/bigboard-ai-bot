"""Сохранение заявок в CSV-файл (открывается в Excel).

Позже здесь же появится запись в Google Таблицу.
"""

import csv
from datetime import datetime
from pathlib import Path

LEADS_FILE = Path(__file__).parent / "leads.csv"
FIELDS = ["date", "user_id", "username", "name", "phone", "service", "comment"]


def save_lead(lead: dict) -> None:
    is_new_file = not LEADS_FILE.exists()
    row = {"date": datetime.now().strftime("%Y-%m-%d %H:%M"), **lead}

    # utf-8-sig — чтобы Excel правильно показал кириллицу
    with LEADS_FILE.open("a", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS, delimiter=";")
        if is_new_file:
            writer.writeheader()
        writer.writerow(row)
