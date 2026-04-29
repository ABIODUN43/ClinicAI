import csv
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.app.database import Base, SessionLocal, engine
from backend.app.models import NewsRecord


def parse_datetime(value: str) -> datetime:
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def main() -> int:
    if len(sys.argv) < 2:
        print("Usage: python backend/scripts/import_historical_news_articles.py <csv_path> [disease]")
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
                record = NewsRecord(
                    title=row["title"].strip(),
                    location=row["location"].strip(),
                    disease=row.get("disease", disease).strip() or disease,
                    source_name=row["source_name"].strip(),
                    verification_status=(row.get("verification_status") or "Verified").strip(),
                    content=row["content"].strip(),
                    published_at=parse_datetime(row["published_at"].strip()),
                )
                db.add(record)
                imported += 1

        db.commit()
    finally:
        db.close()

    print(f"Imported {imported} historical news articles from {csv_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
