import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.app.database import Base, SessionLocal, engine
from backend.app.training_data import export_training_rows_to_csv, rebuild_training_dataset


def main() -> int:
    disease = sys.argv[1] if len(sys.argv) > 1 else "Lassa fever"
    output_path = Path(sys.argv[2]).resolve() if len(sys.argv) > 2 else ROOT / "backend" / "data" / "training_dataset.csv"

    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        rows = rebuild_training_dataset(db, disease=disease)
        export_training_rows_to_csv(rows, output_path)
    finally:
        db.close()
    print(f"Wrote {len(rows)} training rows to {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
