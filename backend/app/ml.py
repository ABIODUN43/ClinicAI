import json
import math
from datetime import datetime, timezone
from pathlib import Path

from .config import settings
from .models import TrainingDatasetRow


FEATURE_FIELDS = [
    "temperature_c",
    "rainfall_mm",
    "humidity_pct",
    "dry_season_index",
    "fever_cases",
    "vomiting_cases",
    "bleeding_cases",
    "rodent_contact_cases",
    "news_signal_count",
    "high_severity_news_count",
]

RISK_LEVEL_VALUES = {"Low": 0.2, "Medium": 0.55, "High": 0.85}


def train_baseline_model(rows: list[TrainingDatasetRow]) -> dict:
    if len(rows) < 3:
        raise ValueError("At least 3 training rows are required to train the baseline model.")

    feature_stats = _feature_stats(rows)
    prepared_rows = [_prepared_row(row, feature_stats) for row in rows]
    centroid_artifact = _build_centroid_artifact(rows, feature_stats)
    centroid_artifact["training_metrics"] = evaluate_artifact(centroid_artifact, rows)

    candidate_artifacts = [centroid_artifact]
    knn_artifact = _build_knn_artifact(rows, feature_stats, prepared_rows)
    if knn_artifact:
        candidate_artifacts.append(knn_artifact)

    return max(
        candidate_artifacts,
        key=lambda artifact: (
            artifact.get("training_metrics", {}).get("accuracy", 0.0),
            -artifact.get("training_metrics", {}).get("mae", 1.0),
            artifact.get("sample_count", 0),
        ),
    )


def _build_centroid_artifact(rows: list[TrainingDatasetRow], feature_stats: dict) -> dict:
    grouped = {"Low": [], "Medium": [], "High": []}
    for row in rows:
        if row.risk_level_label in grouped:
            grouped[row.risk_level_label].append(row)

    centroids = {}
    for level, level_rows in grouped.items():
        if not level_rows:
            continue
        centroids[level] = {
            "count": len(level_rows),
            "center": _centroid(level_rows, feature_stats),
            "average_risk_score": _average([row.risk_score_label or RISK_LEVEL_VALUES[level] for row in level_rows]),
        }

    artifact = {
        "model_type": "centroid-baseline",
        "model_name": "ClinicAI Sentinel Centroid Baseline",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "sample_count": len(rows),
        "feature_fields": FEATURE_FIELDS,
        "feature_stats": feature_stats,
        "centroids": centroids,
        "label_distribution": {level: len(items) for level, items in grouped.items()},
        "fallback_risk_score": _average([row.risk_score_label or 0.4 for row in rows]),
    }
    return artifact


def _build_knn_artifact(rows: list[TrainingDatasetRow], feature_stats: dict, prepared_rows: list[dict]) -> dict | None:
    candidate_ks = [value for value in (3, 5, 7, 9) if value < len(prepared_rows)]
    if not candidate_ks:
        return None

    best_k = None
    best_metrics = None
    for k in candidate_ks:
        metrics = _evaluate_knn_leave_one_out(prepared_rows, k)
        if best_metrics is None or (
            metrics["accuracy"],
            -metrics["mae"],
        ) > (
            best_metrics["accuracy"],
            -best_metrics["mae"],
        ):
            best_k = k
            best_metrics = metrics

    if best_k is None or best_metrics is None:
        return None

    return {
        "model_type": "knn-baseline",
        "model_name": f"ClinicAI Sentinel KNN Baseline (k={best_k})",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "sample_count": len(rows),
        "feature_fields": FEATURE_FIELDS,
        "feature_stats": feature_stats,
        "k": best_k,
        "training_samples": prepared_rows,
        "label_distribution": _label_distribution(rows),
        "fallback_risk_score": _average([row.risk_score_label or 0.4 for row in rows]),
        "training_metrics": best_metrics,
    }


def evaluate_artifact(artifact: dict, rows: list[TrainingDatasetRow]) -> dict:
    if not rows:
        return {"accuracy": 0.0, "mae": 0.0}

    correct = 0
    abs_error = 0.0
    for row in rows:
        prediction = predict_from_feature_map(row_to_feature_map(row), artifact)
        if prediction["risk_level"] == row.risk_level_label:
            correct += 1
        abs_error += abs(prediction["risk_score"] - (row.risk_score_label or 0.0))

    return {
        "accuracy": round(correct / len(rows), 4),
        "mae": round(abs_error / len(rows), 4),
    }


def save_model_artifact(artifact: dict, path: str | Path | None = None) -> Path:
    target = Path(path or settings.model_artifact_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(artifact, indent=2), encoding="utf-8")
    return target


def load_model_artifact(path: str | Path | None = None) -> dict | None:
    target = Path(path or settings.model_artifact_path)
    if not target.exists():
        return None
    return json.loads(target.read_text(encoding="utf-8"))


def model_ready(path: str | Path | None = None) -> bool:
    return Path(path or settings.model_artifact_path).exists()


def model_status(path: str | Path | None = None) -> dict:
    target = Path(path or settings.model_artifact_path)
    artifact = load_model_artifact(target)
    if not artifact:
        return {
            "ready": False,
            "model_name": None,
            "sample_count": 0,
            "generated_at": None,
            "accuracy": None,
            "mae": None,
            "artifact_path": str(target),
        }

    metrics = artifact.get("training_metrics", {})
    return {
        "ready": True,
        "model_name": artifact.get("model_name"),
        "sample_count": artifact.get("sample_count", 0),
        "generated_at": artifact.get("generated_at"),
        "accuracy": metrics.get("accuracy"),
        "mae": metrics.get("mae"),
        "artifact_path": str(target),
    }


def training_metrics_from_artifact(artifact: dict) -> dict:
    metrics = artifact.get("training_metrics", {})
    return {
        "model_name": artifact.get("model_name", "ClinicAI Sentinel Baseline"),
        "sample_count": artifact.get("sample_count", 0),
        "accuracy": metrics.get("accuracy"),
        "mae": metrics.get("mae"),
        "generated_at": artifact.get("generated_at"),
    }


def predict_from_feature_map(feature_map: dict, artifact: dict | None = None) -> dict:
    model = artifact or load_model_artifact()
    if not model:
        raise RuntimeError("No trained model artifact is available yet.")

    if model.get("model_type") == "knn-baseline":
        return _predict_knn(feature_map, model)

    normalized = _normalize_feature_map(feature_map, model["feature_stats"])
    centroids = model.get("centroids", {})
    if not centroids:
        fallback_score = round(model.get("fallback_risk_score", 0.4), 4)
        return {
            "risk_score": fallback_score,
            "risk_level": _score_to_level(fallback_score),
            "confidence": 0.3,
            "driver_summary": "Model artifact has no class centroids yet; fallback score used.",
            "model_name": model.get("model_name", "ClinicAI Sentinel Baseline"),
        }

    distances = {}
    for level, centroid in centroids.items():
        distances[level] = _euclidean_distance(normalized, centroid["center"])

    weights = {level: 1 / max(distance, 0.05) for level, distance in distances.items()}
    weight_sum = sum(weights.values()) or 1.0
    weighted_score = 0.0
    for level, weight in weights.items():
        weighted_score += weight * centroids[level].get("average_risk_score", RISK_LEVEL_VALUES[level])
    risk_score = round(max(0.0, min(weighted_score / weight_sum, 0.99)), 4)
    nearest_level = min(distances, key=distances.get)
    confidence = round(min(weights[nearest_level] / weight_sum + 0.35, 0.95), 4)

    top_factors = _top_feature_drivers(normalized)
    summary = (
        f"ML baseline matched {feature_map.get('state', 'the selected state')} closest to the {nearest_level.lower()}-risk "
        f"training centroid. Strongest feature drivers: {', '.join(top_factors)}."
    )
    return {
        "risk_score": risk_score,
        "risk_level": _score_to_level(risk_score),
        "confidence": confidence,
        "driver_summary": summary,
        "model_name": model.get("model_name", "ClinicAI Sentinel Baseline"),
    }


def row_to_feature_map(row: TrainingDatasetRow) -> dict:
    return {field: getattr(row, field) for field in FEATURE_FIELDS} | {"state": row.state}


def _feature_stats(rows: list[TrainingDatasetRow]) -> dict:
    stats = {}
    for field in FEATURE_FIELDS:
        values = [float(getattr(row, field) or 0.0) for row in rows]
        mean = _average(values)
        variance = _average([(value - mean) ** 2 for value in values])
        stats[field] = {
            "mean": round(mean, 6),
            "std": round(math.sqrt(variance) or 1.0, 6),
        }
    return stats


def _prepared_row(row: TrainingDatasetRow, stats: dict) -> dict:
    feature_map = row_to_feature_map(row)
    return {
        "state": row.state,
        "risk_level": row.risk_level_label,
        "risk_score": row.risk_score_label or RISK_LEVEL_VALUES.get(row.risk_level_label, 0.4),
        "normalized": _normalize_feature_map(feature_map, stats),
    }


def _centroid(rows: list[TrainingDatasetRow], stats: dict) -> dict:
    center = {}
    for field in FEATURE_FIELDS:
        values = [float(getattr(row, field) or 0.0) for row in rows]
        mean = _average(values)
        std = stats[field]["std"] or 1.0
        center[field] = round((mean - stats[field]["mean"]) / std, 6)
    return center


def _normalize_feature_map(feature_map: dict, stats: dict) -> dict:
    normalized = {}
    for field in FEATURE_FIELDS:
        value = float(feature_map.get(field) or 0.0)
        std = stats[field]["std"] or 1.0
        normalized[field] = round((value - stats[field]["mean"]) / std, 6)
    return normalized


def _euclidean_distance(left: dict, right: dict) -> float:
    total = 0.0
    for field in FEATURE_FIELDS:
        total += (left.get(field, 0.0) - right.get(field, 0.0)) ** 2
    return math.sqrt(total)


def _top_feature_drivers(normalized: dict) -> list[str]:
    sorted_fields = sorted(FEATURE_FIELDS, key=lambda item: abs(normalized.get(item, 0.0)), reverse=True)
    return [field.replace("_", " ") for field in sorted_fields[:3]]


def _average(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def _label_distribution(rows: list[TrainingDatasetRow]) -> dict:
    distribution = {"Low": 0, "Medium": 0, "High": 0}
    for row in rows:
        if row.risk_level_label in distribution:
            distribution[row.risk_level_label] += 1
    return distribution


def _evaluate_knn_leave_one_out(samples: list[dict], k: int) -> dict:
    correct = 0
    abs_error = 0.0
    if len(samples) <= 1:
        return {"accuracy": 0.0, "mae": 0.0}

    for index, sample in enumerate(samples):
        pool = samples[:index] + samples[index + 1 :]
        prediction = _predict_knn_from_samples(sample["normalized"], pool, k)
        if prediction["risk_level"] == sample["risk_level"]:
            correct += 1
        abs_error += abs(prediction["risk_score"] - sample["risk_score"])

    return {
        "accuracy": round(correct / len(samples), 4),
        "mae": round(abs_error / len(samples), 4),
    }


def _predict_knn(feature_map: dict, model: dict) -> dict:
    normalized = _normalize_feature_map(feature_map, model["feature_stats"])
    prediction = _predict_knn_from_samples(normalized, model.get("training_samples", []), int(model.get("k", 3)))
    top_factors = _top_feature_drivers(normalized)
    summary = (
        f"ML baseline compared {feature_map.get('state', 'the selected state')} against the nearest "
        f"historical training neighbors. Strongest feature drivers: {', '.join(top_factors)}."
    )
    return {
        "risk_score": prediction["risk_score"],
        "risk_level": prediction["risk_level"],
        "confidence": prediction["confidence"],
        "driver_summary": summary,
        "model_name": model.get("model_name", "ClinicAI Sentinel KNN Baseline"),
    }


def _predict_knn_from_samples(normalized: dict, samples: list[dict], k: int) -> dict:
    if not samples:
        fallback_score = 0.4
        return {
            "risk_score": fallback_score,
            "risk_level": _score_to_level(fallback_score),
            "confidence": 0.3,
        }

    ordered = sorted(
        samples,
        key=lambda item: _euclidean_distance(normalized, item["normalized"]),
    )
    neighbors = ordered[: max(1, min(k, len(ordered)))]

    weights = []
    for neighbor in neighbors:
        distance = _euclidean_distance(normalized, neighbor["normalized"])
        weights.append(1 / max(distance, 0.05))

    total_weight = sum(weights) or 1.0
    weighted_score = sum(weight * neighbor["risk_score"] for weight, neighbor in zip(weights, neighbors)) / total_weight
    level_weights = {"Low": 0.0, "Medium": 0.0, "High": 0.0}
    for weight, neighbor in zip(weights, neighbors):
        level_weights[neighbor["risk_level"]] += weight

    nearest_level = max(level_weights, key=level_weights.get)
    confidence = round(min(level_weights[nearest_level] / total_weight + 0.25, 0.95), 4)
    risk_score = round(max(0.0, min(weighted_score, 0.99)), 4)
    return {
        "risk_score": risk_score,
        "risk_level": _score_to_level(risk_score),
        "confidence": confidence,
    }


def _score_to_level(score: float) -> str:
    if score >= 0.67:
        return "High"
    if score >= 0.34:
        return "Medium"
    return "Low"
