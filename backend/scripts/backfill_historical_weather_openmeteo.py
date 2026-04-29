import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.app.ingestion import MONITORED_STATE_COORDINATES, fetch_open_meteo_historical_weather


def write_csv(path: Path, headers: list[str], rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=headers)
        writer.writeheader()
        writer.writerows(rows)


def build_weather_rows(report_path: Path) -> tuple[int, int, list[dict], list[str]]:
    payload = json.loads(report_path.read_text(encoding="utf-8"))
    report = payload["report"]
    year = int(report["year"])
    epi_week = int(report["epi_week"])
    start_date = normalize_date_label(report["week_start"], year)
    end_date = normalize_date_label(report["week_end"], year)

    states = sorted({item["state"] for item in payload.get("state_metrics", []) if item.get("state")})
    rows: list[dict] = []
    missing_states: list[str] = []

    for state in states:
        coords = MONITORED_STATE_COORDINATES.get(state)
        if not coords:
            missing_states.append(state)
            continue

        weather = fetch_open_meteo_historical_weather(
            coords[0],
            coords[1],
            start_date=start_date,
            end_date=end_date,
        )
        rows.append(
            {
                "year": year,
                "epi_week": epi_week,
                "state": state,
                "source_name": "Open-Meteo archive backfill",
                "temperature_c": weather["temperature_c"],
                "rainfall_mm": weather["rainfall_mm"],
                "humidity_pct": weather["humidity_pct"],
                "dry_season_index": weather["dry_season_index"],
            }
        )

    return year, epi_week, rows, missing_states


def normalize_date_label(label: str, fallback_year: int) -> str:
    cleaned = label.replace("–", "-").replace(",", " ").strip()
    parts = cleaned.split()
    if len(parts) == 2:
        day, month = parts
        year = str(fallback_year)
    elif len(parts) >= 3:
        day, month, year = parts[0], parts[1], parts[2]
    else:
        raise ValueError(f"Unsupported date label: {label}")

    numeric_day = "".join(character for character in day if character.isdigit())
    if not numeric_day:
        raise ValueError(f"Could not parse day from label: {label}")

    month_lookup = {
        "January": "01",
        "February": "02",
        "March": "03",
        "April": "04",
        "May": "05",
        "June": "06",
        "July": "07",
        "August": "08",
        "September": "09",
        "October": "10",
        "November": "11",
        "December": "12",
    }
    month_number = month_lookup.get(month)
    if not month_number:
        raise ValueError(f"Unsupported month in label: {label}")

    return f"{year}-{month_number}-{int(numeric_day):02d}"


def main() -> int:
    if len(sys.argv) < 2:
        print("Usage: python backend/scripts/backfill_historical_weather_openmeteo.py <report_json> [report_json ...]")
        return 1

    historical_dir = ROOT / "backend" / "data" / "historical" / "weather"
    headers = [
        "year",
        "epi_week",
        "state",
        "source_name",
        "temperature_c",
        "rainfall_mm",
        "humidity_pct",
        "dry_season_index",
    ]

    for report_arg in sys.argv[1:]:
        report_path = Path(report_arg).resolve()
        year, epi_week, rows, missing_states = build_weather_rows(report_path)
        output_path = historical_dir / f"historical_weather_week{epi_week}_{year}.csv"
        write_csv(output_path, headers, rows)
        print(f"Wrote {len(rows)} weather rows to {output_path}")
        if missing_states:
            print(f"Missing coordinates for: {', '.join(missing_states)}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
