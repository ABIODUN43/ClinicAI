import json
from pathlib import Path

from sqlalchemy.orm import Session

from .config import settings
from .ml import save_model_artifact, train_baseline_model
from .models import HistoricalReport, TrainingDatasetRow, TrainingRun
from .training_data import (
    export_training_rows_to_csv,
    import_historical_news_csv,
    import_historical_symptoms_csv,
    import_historical_weather_csv,
    persist_historical_report,
    rebuild_training_dataset,
)

ROOT = Path(__file__).resolve().parents[2]


def resolve_workspace_path(entry: str) -> Path:
    path = Path(entry)
    return path if path.is_absolute() else ROOT / path


def discover_historical_inputs(base_dir: Path) -> dict:
    reports = sorted(base_dir.joinpath("reports").glob("*.json"))
    weather_files = sorted(base_dir.joinpath("weather").glob("*.csv"))
    symptom_files = sorted(base_dir.joinpath("symptoms").glob("*.csv"))
    news_files = sorted(base_dir.joinpath("news").glob("*.csv"))
    return {
        "reports": [str(path) for path in reports],
        "weather_files": [str(path) for path in weather_files],
        "symptom_files": [str(path) for path in symptom_files],
        "news_files": [str(path) for path in news_files],
    }


def load_manifest_or_discover(argument: str | None) -> tuple[Path | None, dict]:
    if argument == "--auto":
        auto_dir = ROOT / "backend" / "data" / "historical"
        return None, {
            "disease": "Lassa fever",
            **discover_historical_inputs(auto_dir),
            "training_output_csv": "backend/data/training_dataset.csv",
            "model_artifact_path": settings.model_artifact_path,
        }

    manifest_path = Path(argument).resolve() if argument else ROOT / "backend" / "data" / "historical_batch_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("auto_discover"):
        auto_dir = resolve_workspace_path(manifest.get("auto_discover_dir", "backend/data/historical"))
        manifest = {
            **manifest,
            **discover_historical_inputs(auto_dir),
        }
    return manifest_path, manifest


def execute_historical_batch(db: Session, manifest: dict, manifest_label: str = "manifest") -> dict:
    disease = manifest.get("disease", "Lassa fever")
    reports_loaded = 0
    weather_loaded = 0
    symptoms_loaded = 0
    news_loaded = 0

    for report_file in manifest.get("reports", []):
        payload = json.loads(resolve_workspace_path(report_file).read_text(encoding="utf-8"))
        persist_historical_report(db, payload["report"], payload["state_metrics"])
        reports_loaded += 1

    for weather_file in manifest.get("weather_files", []):
        weather_loaded += import_historical_weather_csv(db, resolve_workspace_path(weather_file), disease=disease)

    for symptom_file in manifest.get("symptom_files", []):
        symptoms_loaded += import_historical_symptoms_csv(db, resolve_workspace_path(symptom_file), disease=disease)

    for news_file in manifest.get("news_files", []):
        news_loaded += import_historical_news_csv(db, resolve_workspace_path(news_file), disease=disease)

    rows = rebuild_training_dataset(db, disease=disease)
    training_output = resolve_workspace_path(manifest.get("training_output_csv", "backend/data/training_dataset.csv"))
    export_training_rows_to_csv(rows, training_output)

    training_rows = db.query(TrainingDatasetRow).filter(TrainingDatasetRow.disease == disease).all()
    artifact = train_baseline_model(training_rows)
    artifact_path = resolve_workspace_path(manifest.get("model_artifact_path", settings.model_artifact_path))
    save_model_artifact(artifact, artifact_path)
    historical_report_count = db.query(HistoricalReport).filter(HistoricalReport.disease == disease).count()
    metrics = artifact.get("training_metrics", {})
    run = TrainingRun(
        disease=disease,
        model_name=artifact.get("model_name", "ClinicAI Sentinel Baseline"),
        trigger_source="auto-refresh" if manifest_label == "auto-discovery" else "batch-manifest",
        sample_count=artifact.get("sample_count", len(training_rows)),
        accuracy=metrics.get("accuracy"),
        mae=metrics.get("mae"),
        historical_reports=historical_report_count,
        training_rows=len(training_rows),
        notes=f"Historical batch completed via {manifest_label}.",
    )
    db.add(run)
    db.commit()

    return {
        "manifest": manifest_label,
        "reports_loaded": reports_loaded,
        "weather_rows_loaded": weather_loaded,
        "symptom_rows_loaded": symptoms_loaded,
        "news_rows_loaded": news_loaded,
        "training_rows": len(rows),
        "training_output_csv": str(training_output),
        "model_artifact_path": str(artifact_path),
        "model_accuracy": artifact["training_metrics"]["accuracy"],
        "model_mae": artifact["training_metrics"]["mae"],
    }
