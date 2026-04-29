import csv
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.app.database import Base, SessionLocal, engine
from backend.app.models import SymptomReport


def parse_datetime(value: str) -> datetime:
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def main() -> int:
    if len(sys.argv) < 2:
        print("Usage: python backend/scripts/import_symptom_line_list.py <csv_path> [disease]")
        return 1

    csv_path = Path(sys.argv[1]).resolve()
    disease = sys.argv[2] if len(sys.argv) > 2 else "Lassa fever"

    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    imported = 0

    try:
        with csv_path.open("r", encoding="utf-8") as handle:
            reader = csv.DictReader(handle)
            for row in reader:
                record = SymptomReport(
                    facility_name=row["facility_name"].strip(),
                    location=row["location"].strip(),
                    disease=row.get("disease", disease).strip() or disease,
                    report_date=parse_datetime(row["report_date"].strip()),
                    fever_cases=int(row.get("fever_cases", 0) or 0),
                    headache_cases=int(row.get("headache_cases", 0) or 0),
                    vomiting_cases=int(row.get("vomiting_cases", 0) or 0),
                    weakness_cases=int(row.get("weakness_cases", 0) or 0),
                    bleeding_cases=int(row.get("bleeding_cases", 0) or 0),
                    contact_history_cases=int(row.get("contact_history_cases", 0) or 0),
                    suspected_cases=int(row.get("suspected_cases", 0) or 0),
                    notes=(row.get("notes") or "").strip() or None,
                    reported_by=(row.get("reported_by") or "historical.import@sentinel.local").strip(),
                )
                db.add(record)
                imported += 1

        db.commit()
    finally:
        db.close()

    print(f"Imported {imported} symptom line-list rows from {csv_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
