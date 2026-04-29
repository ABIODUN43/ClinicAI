import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.app.database import Base, SessionLocal, engine
from backend.app.historical_batch import execute_historical_batch, load_manifest_or_discover


def main() -> int:
    argument = sys.argv[1] if len(sys.argv) > 1 else "--auto"
    manifest_path, manifest = load_manifest_or_discover(argument)

    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        result = execute_historical_batch(
            db,
            manifest,
            manifest_label=str(manifest_path) if manifest_path else "auto-discovery",
        )
    finally:
        db.close()

    print(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
