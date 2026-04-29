import csv
import json
import sys
from copy import deepcopy
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


DEFAULT_STATES = [
    "Bauchi",
    "Ondo",
    "Edo",
    "Taraba",
    "Plateau",
    "Ogun",
    "Gombe",
    "Lagos",
    "Ebonyi",
    "Benue",
    "Nasarawa",
    "Kogi",
    "Oyo",
]


def _write_csv(path: Path, headers: list[str], rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=headers)
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    if len(sys.argv) < 3:
        print("Usage: python backend/scripts/generate_historical_week_pack.py <year> <epi_week> [week_start] [week_end]")
        return 1

    year = int(sys.argv[1])
    epi_week = int(sys.argv[2])
    week_start = sys.argv[3] if len(sys.argv) > 3 else "1st January"
    week_end = sys.argv[4] if len(sys.argv) > 4 else f"7th January {year}"

    template_dir = ROOT / "backend" / "data" / "templates"
    historical_dir = ROOT / "backend" / "data" / "historical"

    report_template = json.loads((template_dir / "historical_report_template.json").read_text(encoding="utf-8"))
    report_payload = deepcopy(report_template)
    report_payload["report"]["year"] = year
    report_payload["report"]["epi_week"] = epi_week
    report_payload["report"]["week_start"] = week_start
    report_payload["report"]["week_end"] = week_end
    report_payload["report"]["source_path"] = f"REPLACE_WITH_NCDC_SITREP_PDF_FOR_WEEK_{epi_week}_{year}"
    report_payload["state_metrics"] = []
    for state in DEFAULT_STATES:
        report_payload["state_metrics"].append(
            {
                "state": state,
                "metric_scope": "cumulative",
                "suspected_cases": 0,
                "confirmed_cases": 0,
                "deaths": 0,
                "cfr": 0.0,
                "extraction_confidence": "medium",
                "source_note": "Fill from Table 3 / Figure 5.",
            }
        )

    report_path = historical_dir / "reports" / f"ncdc_lassa_week{epi_week}_{year}.json"
    report_path.write_text(json.dumps(report_payload, indent=2), encoding="utf-8")

    weather_headers = [
        "year",
        "epi_week",
        "state",
        "source_name",
        "temperature_c",
        "rainfall_mm",
        "humidity_pct",
        "dry_season_index",
    ]
    symptom_headers = [
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
    news_headers = [
        "year",
        "epi_week",
        "state",
        "source_name",
        "news_signal_count",
        "high_severity_news_count",
        "rodent_risk_mentions",
        "outbreak_mentions",
    ]

    weather_rows = [
        {
            "year": year,
            "epi_week": epi_week,
            "state": state,
            "source_name": "Historical weather source",
            "temperature_c": 0,
            "rainfall_mm": 0,
            "humidity_pct": 0,
            "dry_season_index": 0,
        }
        for state in DEFAULT_STATES
    ]
    symptom_rows = [
        {
            "year": year,
            "epi_week": epi_week,
            "state": state,
            "source_name": "Historical symptom source",
            "fever_cases": 0,
            "headache_cases": 0,
            "vomiting_cases": 0,
            "weakness_cases": 0,
            "bleeding_cases": 0,
            "rodent_contact_cases": 0,
            "suspected_cases": 0,
        }
        for state in DEFAULT_STATES
    ]
    news_rows = [
        {
            "year": year,
            "epi_week": epi_week,
            "state": state,
            "source_name": "Historical news source",
            "news_signal_count": 0,
            "high_severity_news_count": 0,
            "rodent_risk_mentions": 0,
            "outbreak_mentions": 0,
        }
        for state in DEFAULT_STATES
    ]

    weather_path = historical_dir / "weather" / f"historical_weather_week{epi_week}_{year}.csv"
    symptom_path = historical_dir / "symptoms" / f"historical_symptoms_week{epi_week}_{year}.csv"
    news_path = historical_dir / "news" / f"historical_news_week{epi_week}_{year}.csv"

    _write_csv(weather_path, weather_headers, weather_rows)
    _write_csv(symptom_path, symptom_headers, symptom_rows)
    _write_csv(news_path, news_headers, news_rows)

    print(
        {
            "report": str(report_path),
            "weather": str(weather_path),
            "symptoms": str(symptom_path),
            "news": str(news_path),
            "states_seeded": len(DEFAULT_STATES),
        }
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
