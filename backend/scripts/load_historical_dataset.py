import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.app.database import Base, SessionLocal, engine
from backend.app.training_data import persist_historical_report


def main() -> int:
    if len(sys.argv) < 2:
        print("Usage: python backend/scripts/load_historical_dataset.py <input_json>")
        return 1

    input_path = Path(sys.argv[1]).resolve()
    payload = json.loads(input_path.read_text(encoding="utf-8"))

    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        persist_historical_report(db, payload["report"], payload["state_metrics"])
    finally:
        db.close()

    print(f"Loaded historical report data from {input_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
