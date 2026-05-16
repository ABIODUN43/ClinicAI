import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.app.database import Base, SessionLocal, engine
from backend.app.services import run_daily_surveillance_cycle


def main() -> int:
    disease = sys.argv[1] if len(sys.argv) > 1 else "Lassa fever"
    analyst = sys.argv[2] if len(sys.argv) > 2 else "ClinicAI Sentinel Daily Automation"

    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        summary = run_daily_surveillance_cycle(
            db,
            disease=disease,
            analyst=analyst,
        )
    finally:
        db.close()

    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
