import csv
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.app.database import SessionLocal
from backend.app.models import NewsRecord
from backend.app.nlp import analyze_news_text


def write_csv(path: Path, headers: list[str], rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=headers)
        writer.writeheader()
        writer.writerows(rows)


def to_week_key(value: datetime) -> tuple[int, int]:
    iso_year, iso_week, _ = value.isocalendar()
    return iso_year, iso_week


def normalize_state(location: str) -> str:
    return (location or "").strip()


def main() -> int:
    disease = sys.argv[1] if len(sys.argv) > 1 else "Lassa fever"
    db = SessionLocal()
    try:
        records = (
            db.query(NewsRecord)
            .filter(NewsRecord.disease == disease)
            .order_by(NewsRecord.published_at.asc())
            .all()
        )
    finally:
        db.close()

    if not records:
        print(f"No news records found for {disease}.")
        return 0

    grouped: dict[tuple[int, int, str], dict] = defaultdict(
        lambda: {
            "news_signal_count": 0,
            "high_severity_news_count": 0,
            "rodent_risk_mentions": 0,
            "outbreak_mentions": 0,
        }
    )

    for record in records:
        state = normalize_state(record.location)
        if not state:
            continue

        analysis = analyze_news_text(
            title=record.title,
            content=record.content,
            source_name=record.source_name,
            verification_status=record.verification_status,
            location=record.location,
            disease=record.disease,
        )
        year, epi_week = to_week_key(record.published_at)
        bucket = grouped[(year, epi_week, state)]
        bucket["news_signal_count"] += 1

        if analysis["classification"] == "Red" or analysis["confidence"] >= 0.58:
            bucket["high_severity_news_count"] += 1
        if "rodent" in analysis["matched_terms"]:
            bucket["rodent_risk_mentions"] += 1
        if "outbreak" in analysis["matched_terms"] or "suspected cases" in analysis["matched_terms"] or "deaths" in analysis["matched_terms"]:
            bucket["outbreak_mentions"] += 1

    headers = [
        "year",
        "epi_week",
        "state",
        "source_name",
        "news_signal_count",
        "high_severity_news_count",
        "rodent_risk_mentions",
        "outbreak_mentions",
    ]

    news_dir = ROOT / "backend" / "data" / "historical" / "news"
    week_map: dict[tuple[int, int], list[dict]] = defaultdict(list)

    for (year, epi_week, state), values in sorted(grouped.items()):
        week_map[(year, epi_week)].append(
            {
                "year": year,
                "epi_week": epi_week,
                "state": state,
                "source_name": "Aggregated NLP-classified news records from ClinicAI Sentinel DB",
                **values,
            }
        )

    for (year, epi_week), rows in week_map.items():
        output_path = news_dir / f"historical_news_week{epi_week}_{year}.csv"
        write_csv(output_path, headers, rows)
        print(f"Wrote {len(rows)} news rows to {output_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
