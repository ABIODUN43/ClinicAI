import csv
import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


BASELINE_WEATHER = {
    "Bauchi": {"temperature_c": 34.2, "rainfall_mm": 6.0, "humidity_pct": 42.0, "dry_season_index": 0.88},
    "Ondo": {"temperature_c": 32.8, "rainfall_mm": 14.0, "humidity_pct": 56.0, "dry_season_index": 0.71},
    "Edo": {"temperature_c": 33.1, "rainfall_mm": 15.0, "humidity_pct": 54.0, "dry_season_index": 0.74},
    "Taraba": {"temperature_c": 31.6, "rainfall_mm": 11.0, "humidity_pct": 58.0, "dry_season_index": 0.63},
    "Plateau": {"temperature_c": 29.8, "rainfall_mm": 10.0, "humidity_pct": 53.0, "dry_season_index": 0.6},
    "Ogun": {"temperature_c": 31.4, "rainfall_mm": 18.0, "humidity_pct": 62.0, "dry_season_index": 0.52},
    "Gombe": {"temperature_c": 35.0, "rainfall_mm": 4.0, "humidity_pct": 40.0, "dry_season_index": 0.9},
    "Lagos": {"temperature_c": 30.8, "rainfall_mm": 22.0, "humidity_pct": 70.0, "dry_season_index": 0.34},
    "Ebonyi": {"temperature_c": 31.9, "rainfall_mm": 17.0, "humidity_pct": 60.0, "dry_season_index": 0.58},
    "Benue": {"temperature_c": 32.2, "rainfall_mm": 13.0, "humidity_pct": 57.0, "dry_season_index": 0.61},
    "Nasarawa": {"temperature_c": 32.4, "rainfall_mm": 9.0, "humidity_pct": 52.0, "dry_season_index": 0.66},
    "Kogi": {"temperature_c": 33.0, "rainfall_mm": 12.0, "humidity_pct": 55.0, "dry_season_index": 0.64},
    "Oyo": {"temperature_c": 31.7, "rainfall_mm": 19.0, "humidity_pct": 64.0, "dry_season_index": 0.49},
}


def write_csv(path: Path, headers: list[str], rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=headers)
        writer.writeheader()
        writer.writerows(rows)


def week_adjusted_weather(epi_week: int, baseline: dict) -> dict:
    week_delta = epi_week - 2
    return {
        "temperature_c": round(baseline["temperature_c"] + (0.15 * week_delta), 1),
        "rainfall_mm": round(max(baseline["rainfall_mm"] - (1.2 * week_delta), 0.0), 1),
        "humidity_pct": round(max(baseline["humidity_pct"] - (0.8 * week_delta), 30.0), 1),
        "dry_season_index": round(min(baseline["dry_season_index"] + (0.015 * week_delta), 0.98), 2),
    }


def symptom_proxy(confirmed_cases: int) -> dict:
    if confirmed_cases <= 0:
        return {
            "fever_cases": 0,
            "headache_cases": 0,
            "vomiting_cases": 0,
            "weakness_cases": 0,
            "bleeding_cases": 0,
            "rodent_contact_cases": 0,
            "suspected_cases": 0,
        }
    return {
        "fever_cases": max(math.ceil(confirmed_cases * 0.78), 1),
        "headache_cases": max(math.ceil(confirmed_cases * 0.56), 1),
        "vomiting_cases": max(math.ceil(confirmed_cases * 0.29), 1),
        "weakness_cases": max(math.ceil(confirmed_cases * 0.44), 1),
        "bleeding_cases": max(math.ceil(confirmed_cases * 0.16), 1),
        "rodent_contact_cases": max(math.ceil(confirmed_cases * 0.24), 1),
        "suspected_cases": max(math.ceil(confirmed_cases * 0.62), 1),
    }


def news_proxy(confirmed_cases: int) -> dict:
    if confirmed_cases <= 0:
        return {
            "news_signal_count": 0,
            "high_severity_news_count": 0,
            "rodent_risk_mentions": 0,
            "outbreak_mentions": 0,
        }
    signal_count = max(math.ceil(confirmed_cases / 6), 1)
    high_severity = max(math.ceil(signal_count * 0.55), 1)
    return {
        "news_signal_count": signal_count,
        "high_severity_news_count": high_severity,
        "rodent_risk_mentions": max(high_severity - 1, 1),
        "outbreak_mentions": max(math.ceil(signal_count * 0.4), 1),
    }


def build_rows(report_path: Path) -> tuple[list[dict], list[dict], list[dict]]:
    payload = json.loads(report_path.read_text(encoding="utf-8"))
    epi_week = payload["report"]["epi_week"]
    year = payload["report"]["year"]
    metric_map = {item["state"]: item for item in payload["state_metrics"]}

    weather_rows: list[dict] = []
    symptom_rows: list[dict] = []
    news_rows: list[dict] = []
    for state, baseline in BASELINE_WEATHER.items():
        confirmed_cases = int(metric_map.get(state, {}).get("confirmed_cases") or 0)
        weather = week_adjusted_weather(epi_week, baseline)
        symptoms = symptom_proxy(confirmed_cases)
        news = news_proxy(confirmed_cases)

        weather_rows.append(
            {
                "year": year,
                "epi_week": epi_week,
                "state": state,
                "source_name": "Derived dry-season weather baseline proxy",
                **weather,
            }
        )
        symptom_rows.append(
            {
                "year": year,
                "epi_week": epi_week,
                "state": state,
                "source_name": "Derived clinic symptom proxy from NCDC weekly state burden",
                **symptoms,
            }
        )
        news_rows.append(
            {
                "year": year,
                "epi_week": epi_week,
                "state": state,
                "source_name": "Derived news-signal proxy from NCDC weekly state burden",
                **news,
            }
        )
    return weather_rows, symptom_rows, news_rows


def main() -> int:
    if len(sys.argv) < 2:
        print("Usage: python backend/scripts/populate_historical_feature_proxies.py <report_json> [report_json ...]")
        return 1

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

    historical_dir = ROOT / "backend" / "data" / "historical"
    for report_arg in sys.argv[1:]:
        report_path = Path(report_arg).resolve()
        weather_rows, symptom_rows, news_rows = build_rows(report_path)
        payload = json.loads(report_path.read_text(encoding="utf-8"))
        epi_week = payload["report"]["epi_week"]
        year = payload["report"]["year"]

        write_csv(
            historical_dir / "weather" / f"historical_weather_week{epi_week}_{year}.csv",
            weather_headers,
            weather_rows,
        )
        write_csv(
            historical_dir / "symptoms" / f"historical_symptoms_week{epi_week}_{year}.csv",
            symptom_headers,
            symptom_rows,
        )
        write_csv(
            historical_dir / "news" / f"historical_news_week{epi_week}_{year}.csv",
            news_headers,
            news_rows,
        )
        print(f"Generated proxy feature CSVs for week {epi_week}, {year}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
