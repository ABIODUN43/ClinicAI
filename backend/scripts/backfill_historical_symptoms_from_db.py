import csv
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.app.database import SessionLocal
from backend.app.models import SymptomReport


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
        reports = (
            db.query(SymptomReport)
            .filter(SymptomReport.disease == disease)
            .order_by(SymptomReport.report_date.asc())
            .all()
        )
    finally:
        db.close()

    if not reports:
        print(f"No symptom reports found for {disease}.")
        return 0

    grouped: dict[tuple[int, int, str], dict] = defaultdict(
        lambda: {
            "fever_cases": 0,
            "headache_cases": 0,
            "vomiting_cases": 0,
            "weakness_cases": 0,
            "bleeding_cases": 0,
            "rodent_contact_cases": 0,
            "suspected_cases": 0,
        }
    )

    for report in reports:
        state = normalize_state(report.location)
        if not state:
            continue
        year, epi_week = to_week_key(report.report_date)
        bucket = grouped[(year, epi_week, state)]
        bucket["fever_cases"] += int(report.fever_cases or 0)
        bucket["headache_cases"] += int(report.headache_cases or 0)
        bucket["vomiting_cases"] += int(report.vomiting_cases or 0)
        bucket["weakness_cases"] += int(report.weakness_cases or 0)
        bucket["bleeding_cases"] += int(report.bleeding_cases or 0)
        bucket["rodent_contact_cases"] += int(report.contact_history_cases or 0)
        bucket["suspected_cases"] += int(report.suspected_cases or 0)

    headers = [
        "year",
        "epi_week",
        "state",
        "source_name",
        "fever_cases",
        "headache_cases",
        "vomiting_cases",
        "weakness_cases",
        "bleeding_cases",
        "rodent_contact_cases",
        "suspected_cases",
    ]

    weather_dir = ROOT / "backend" / "data" / "historical" / "symptoms"
    week_map: dict[tuple[int, int], list[dict]] = defaultdict(list)

    for (year, epi_week, state), values in sorted(grouped.items()):
        week_map[(year, epi_week)].append(
            {
                "year": year,
                "epi_week": epi_week,
                "state": state,
                "source_name": "Aggregated symptom reports from ClinicAI Sentinel DB",
                **values,
            }
        )

    for (year, epi_week), rows in week_map.items():
        output_path = weather_dir / f"historical_symptoms_week{epi_week}_{year}.csv"
        write_csv(output_path, headers, rows)
        print(f"Wrote {len(rows)} symptom rows to {output_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
