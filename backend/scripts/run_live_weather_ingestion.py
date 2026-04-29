import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.app.database import Base, SessionLocal, engine
from backend.app.schemas import WeatherIngestionRequest
from backend.app.services import run_live_weather_ingestion


def main() -> int:
    disease = sys.argv[1] if len(sys.argv) > 1 else "Lassa fever"
    locations = [item.strip() for item in sys.argv[2].split(",")] if len(sys.argv) > 2 else []

    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        result = run_live_weather_ingestion(
            db,
            WeatherIngestionRequest(
                disease=disease,
                locations=locations,
            ),
        )
    finally:
        db.close()

    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
