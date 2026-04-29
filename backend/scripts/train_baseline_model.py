import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.app.database import Base, SessionLocal, engine
from backend.app.ml import save_model_artifact, train_baseline_model
from backend.app.models import TrainingDatasetRow


def main() -> int:
    output_path = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else ROOT / "backend" / "artifacts" / "clinicai_baseline_model.json"

    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        rows = db.query(TrainingDatasetRow).filter(TrainingDatasetRow.disease == "Lassa fever").all()
        artifact = train_baseline_model(rows)
    finally:
        db.close()

    saved = save_model_artifact(artifact, output_path)
    print(
        {
            "artifact": str(saved),
            "sample_count": artifact["sample_count"],
            "accuracy": artifact["training_metrics"]["accuracy"],
            "mae": artifact["training_metrics"]["mae"],
        }
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
