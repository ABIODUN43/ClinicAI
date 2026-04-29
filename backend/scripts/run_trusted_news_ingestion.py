import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.app.database import Base, SessionLocal, engine
from backend.app.schemas import NewsIngestionRequest
from backend.app.services import run_trusted_news_ingestion


def main() -> int:
    disease = sys.argv[1] if len(sys.argv) > 1 else "Lassa fever"
    max_items = int(sys.argv[2]) if len(sys.argv) > 2 else 2

    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        result = run_trusted_news_ingestion(
            db,
            NewsIngestionRequest(
                disease=disease,
                max_items_per_source=max_items,
                auto_create_signals=True,
            ),
        )
    finally:
        db.close()

    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
