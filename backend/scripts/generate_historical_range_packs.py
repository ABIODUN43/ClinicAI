import calendar
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


def ordinal(value: int) -> str:
    if 10 <= value % 100 <= 20:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(value % 10, "th")
    return f"{value}{suffix}"


def build_date_labels(year: int, epi_week: int) -> tuple[str, str]:
    month_index = ((epi_week - 1) % 12) + 1
    month_name = calendar.month_name[month_index]
    start_day = ((epi_week - 1) * 7) % 28 + 1
    end_day = min(start_day + 6, 28)
    return f"{ordinal(start_day)} {month_name}", f"{ordinal(end_day)} {month_name} {year}"


def write_csv(path: Path, headers: list[str], rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    header_line = ",".join(headers)
    body_lines = [",".join(str(row[column]) for column in headers) for row in rows]
    path.write_text("\n".join([header_line, *body_lines]) + "\n", encoding="utf-8")


def generate_week_pack(year: int, epi_week: int) -> list[Path]:
    template_dir = ROOT / "backend" / "data" / "templates"
    historical_dir = ROOT / "backend" / "data" / "historical"

    week_start, week_end = build_date_labels(year, epi_week)
    report_template = json.loads((template_dir / "historical_report_template.json").read_text(encoding="utf-8"))
    report_payload = deepcopy(report_template)
    report_payload["report"]["year"] = year
    report_payload["report"]["epi_week"] = epi_week
    report_payload["report"]["week_start"] = week_start
    report_payload["report"]["week_end"] = week_end
    report_payload["report"]["source_path"] = f"REPLACE_WITH_NCDC_SITREP_PDF_FOR_WEEK_{epi_week}_{year}"
    report_payload["state_metrics"] = [
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
        for state in DEFAULT_STATES
    ]

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

    write_csv(weather_path, weather_headers, weather_rows)
    write_csv(symptom_path, symptom_headers, symptom_rows)
    write_csv(news_path, news_headers, news_rows)
    return [report_path, weather_path, symptom_path, news_path]


def main() -> int:
    if len(sys.argv) < 4:
        print("Usage: python backend/scripts/generate_historical_range_packs.py <year> <start_epi_week> <end_epi_week>")
        return 1

    year = int(sys.argv[1])
    start_week = int(sys.argv[2])
    end_week = int(sys.argv[3])

    if start_week > end_week:
        print("start_epi_week must be less than or equal to end_epi_week")
        return 1

    generated: list[Path] = []
    for epi_week in range(start_week, end_week + 1):
        generated.extend(generate_week_pack(year, epi_week))

    print(f"Generated {len(generated)} files for weeks {start_week} to {end_week} in {year}.")
    for path in generated:
        print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
