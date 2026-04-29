import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.app.database import Base, SessionLocal, engine
from backend.app.training_data import import_historical_news_csv


def main() -> int:
    if len(sys.argv) < 2:
        print("Usage: python backend/scripts/load_historical_news.py <csv_path> [disease]")
        return 1

    csv_path = Path(sys.argv[1]).resolve()
    disease = sys.argv[2] if len(sys.argv) > 2 else "Lassa fever"

    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        loaded = import_historical_news_csv(db, csv_path, disease=disease)
    finally:
        db.close()

    print(f"Loaded {loaded} historical news rows from {csv_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
