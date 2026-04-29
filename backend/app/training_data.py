import csv
import re
from collections import Counter
from datetime import datetime
from pathlib import Path

from sqlalchemy import delete
from sqlalchemy.orm import Session

from .models import (
    HistoricalReport,
    HistoricalNewsMetric,
    HistoricalStateMetric,
    HistoricalSymptomMetric,
    HistoricalWeatherMetric,
    NewsRecord,
    SymptomReport,
    TrainingDatasetRow,
    WeatherRecord,
)


WEEK_RANGE_SPLIT_RE = re.compile(r"\s*[–-]\s*")
DOMINANT_CASE_RE = re.compile(
    r"Of the \d+% confirmed cases,\s*(.+?)\.",
    flags=re.IGNORECASE | re.DOTALL,
)
PERCENTAGE_PAIR_RE = re.compile(r"([A-Z][A-Za-z ]+?)\s+reported\s+(\d+)%", flags=re.IGNORECASE)
CURRENT_WEEK_STATES_RE = re.compile(
    r"These were reported in\s+(.+?)\s+States\s+\(Table 3\)",
    flags=re.IGNORECASE | re.DOTALL,
)
TOTAL_ACTIVE_STATES_RE = re.compile(
    r"In total for \d{4},\s+(\d+)\s+States have recorded at least one confirmed case",
    flags=re.IGNORECASE,
)
TOP_STATES_RE = re.compile(
    r"reported from\s+(?:four|five|six|\d+)\s+states?\s*\((.+?)\)",
    flags=re.IGNORECASE | re.DOTALL,
)
FALLBACK_STATE_ORDER = [
    "Bauchi",
    "Ondo",
    "Edo",
    "Taraba",
    "Plateau",
    "Benue",
    "Ebonyi",
    "Nasarawa",
    "Kogi",
    "Ogun",
    "Gombe",
    "Lagos",
    "Oyo",
]

STATE_OVERRIDE_HEADERS = [
    "state",
    "suspected_cases",
    "confirmed_cases",
    "deaths",
    "cfr",
    "metric_scope",
    "extraction_confidence",
    "source_note",
]


def extract_report_metadata(pdf_path: str | Path) -> dict:
    try:
        from pypdf import PdfReader
    except ImportError as exc:
        raise RuntimeError(
            "The 'pypdf' package is required to extract NCDC PDF reports. Install it in the backend environment to continue."
        ) from exc

    path = Path(pdf_path)
    reader = PdfReader(str(path))
    text = "\n".join((page.extract_text() or "") for page in reader.pages[:2])

    week_match = re.search(r"Epi Week\s*(\d+):\s*([^\n]+?)\s+(\d{4})", text)
    if not week_match:
        raise ValueError("Could not extract epidemiological week metadata from the PDF.")

    epi_week = int(week_match.group(1))
    week_range = week_match.group(2).strip()
    year = int(week_match.group(3))
    week_start, week_end = _split_week_range(week_range)

    summary_rows = re.findall(
        r"(Current week\s*\(week\s*\d+\)|2026\s*Cumulative\s*\(week\s*\d+\)|2025\s*Cumulative\s*\(week\s*\d+\))\s+"
        r"(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+([\d.]+)%",
        text,
        flags=re.IGNORECASE | re.MULTILINE,
    )
    if len(summary_rows) < 3:
        raise ValueError("Could not extract the summary table values from the PDF.")

    parsed = {}
    for label, suspected, confirmed, probable, deaths, cfr in summary_rows:
        key = "current" if "Current week" in label else "cumulative_2026" if "2026" in label else "cumulative_2025"
        parsed[key] = {
            "suspected": int(suspected),
            "confirmed": int(confirmed),
            "probable": int(probable),
            "deaths": int(deaths),
            "cfr": float(cfr),
        }

    return {
        "disease": "Lassa fever",
        "year": year,
        "epi_week": epi_week,
        "week_start": week_start,
        "week_end": week_end,
        "source_name": "Nigeria Centre for Disease Control and Prevention SITREP",
        "source_path": str(path),
        "summary": parsed,
    }


def infer_state_metrics_from_text(pdf_path: str | Path, summary: dict | None = None) -> list[dict]:
    try:
        from pypdf import PdfReader
    except ImportError as exc:
        raise RuntimeError(
            "The 'pypdf' package is required to extract NCDC PDF reports. Install it in the backend environment to continue."
        ) from exc

    path = Path(pdf_path)
    reader = PdfReader(str(path))
    text = "\n".join((page.extract_text() or "") for page in reader.pages[:4])
    extracted_summary = summary or extract_report_metadata(path)["summary"]

    cumulative_confirmed = extracted_summary["cumulative_2026"]["confirmed"]
    cumulative_deaths = extracted_summary["cumulative_2026"]["deaths"]
    cumulative_cfr = extracted_summary["cumulative_2026"]["cfr"]

    dominant_pairs = _parse_dominant_state_percentages(text)
    current_states = _parse_state_list_match(CURRENT_WEEK_STATES_RE.search(text))
    top_states = _parse_state_list_match(TOP_STATES_RE.search(text))
    total_active_states = _parse_total_active_states(text)

    if not dominant_pairs and not current_states:
        return []

    inferred_counts: dict[str, int] = {}
    used_total = 0
    for state, percent in dominant_pairs:
        confirmed_cases = round(cumulative_confirmed * (percent / 100))
        inferred_counts[state] = confirmed_cases
        used_total += confirmed_cases

    ordered_states: list[str] = []
    for state in [*top_states, *current_states]:
        if state not in ordered_states:
            ordered_states.append(state)

    for state, _ in dominant_pairs:
        if state not in ordered_states:
            ordered_states.insert(0, state)

    while total_active_states and len(ordered_states) < total_active_states:
        for state in FALLBACK_STATE_ORDER:
            if state not in ordered_states:
                ordered_states.append(state)
                break
        else:
            break

    remaining_states = [state for state in ordered_states if state not in inferred_counts]
    remaining_confirmed = max(cumulative_confirmed - used_total, 0)
    if remaining_states:
        inferred_counts.update(_distribute_remainder(remaining_confirmed, remaining_states))

    deaths_by_state = _allocate_integer_total(inferred_counts, cumulative_deaths)
    dominant_state_map = dict(dominant_pairs)

    metrics: list[dict] = []
    for state in ordered_states:
        confirmed_cases = inferred_counts.get(state, 0)
        deaths = deaths_by_state.get(state, 0)
        cfr = round((deaths / confirmed_cases) * 100, 1) if confirmed_cases else 0.0
        confidence = "medium" if state in dominant_state_map else "low"
        note = (
            "Confirmed counts inferred from highlight percentages in the SITREP."
            if confidence == "medium"
            else "Confirmed counts distributed from remaining cumulative total using active-state highlights."
        )
        metrics.append(
            {
                "state": state,
                "metric_scope": "cumulative",
                "suspected_cases": None,
                "confirmed_cases": confirmed_cases,
                "deaths": deaths,
                "cfr": cfr or cumulative_cfr,
                "extraction_confidence": confidence,
                "source_note": note,
            }
        )

    return metrics


def manual_state_metrics_for_report(year: int, epi_week: int) -> list[dict]:
    if (year, epi_week) != (2026, 2):
        return []

    return [
        {
            "state": "Bauchi",
            "metric_scope": "cumulative",
            "suspected_cases": 72,
            "confirmed_cases": 25,
            "deaths": 7,
            "cfr": 28.0,
            "extraction_confidence": "high",
            "source_note": "Derived from Figure 5 state bars and CFR markers in the week 2 2026 SITREP.",
        },
        {
            "state": "Ondo",
            "metric_scope": "cumulative",
            "suspected_cases": None,
            "confirmed_cases": 16,
            "deaths": 1,
            "cfr": 6.3,
            "extraction_confidence": "medium",
            "source_note": "Confirmed count derived from Figure 5; death count inferred from CFR marker and national total.",
        },
        {
            "state": "Edo",
            "metric_scope": "cumulative",
            "suspected_cases": 51,
            "confirmed_cases": 7,
            "deaths": 3,
            "cfr": 42.9,
            "extraction_confidence": "high",
            "source_note": "State suspected count from Table 3 image, confirmed and CFR from Figure 5.",
        },
        {
            "state": "Taraba",
            "metric_scope": "cumulative",
            "suspected_cases": None,
            "confirmed_cases": 5,
            "deaths": 0,
            "cfr": 0.0,
            "extraction_confidence": "medium",
            "source_note": "Confirmed count derived from Figure 5 and report highlights; no death marker shown.",
        },
        {
            "state": "Ogun",
            "metric_scope": "cumulative",
            "suspected_cases": 2,
            "confirmed_cases": 1,
            "deaths": 0,
            "cfr": 0.0,
            "extraction_confidence": "high",
            "source_note": "Visible in Table 3 image and Figure 5.",
        },
        {
            "state": "Gombe",
            "metric_scope": "cumulative",
            "suspected_cases": 3,
            "confirmed_cases": 0,
            "deaths": 0,
            "cfr": 0.0,
            "extraction_confidence": "medium",
            "source_note": "Suspected count visible in Table 3 image; no confirmed bar shown in Figure 5.",
        },
        {
            "state": "Lagos",
            "metric_scope": "cumulative",
            "suspected_cases": 2,
            "confirmed_cases": 0,
            "deaths": 0,
            "cfr": 0.0,
            "extraction_confidence": "medium",
            "source_note": "Suspected count visible in Table 3 image; no confirmed bar shown in Figure 5.",
        },
        {
            "state": "Ebonyi",
            "metric_scope": "cumulative",
            "suspected_cases": 3,
            "confirmed_cases": 0,
            "deaths": 0,
            "cfr": 0.0,
            "extraction_confidence": "medium",
            "source_note": "Suspected count visible in Table 3 image; no confirmed bar shown in Figure 5.",
        },
        {
            "state": "Benue",
            "metric_scope": "cumulative",
            "suspected_cases": 4,
            "confirmed_cases": 0,
            "deaths": 0,
            "cfr": 0.0,
            "extraction_confidence": "medium",
            "source_note": "Suspected count visible in Table 3 image; no confirmed bar shown in Figure 5.",
        },
        {
            "state": "Oyo",
            "metric_scope": "cumulative",
            "suspected_cases": 1,
            "confirmed_cases": 0,
            "deaths": 0,
            "cfr": 0.0,
            "extraction_confidence": "medium",
            "source_note": "Suspected count visible in Table 3 image; no confirmed bar shown in Figure 5.",
        },
    ]


def build_extraction_meta(state_metrics: list[dict], source: str) -> dict:
    confidence_counts = Counter(item.get("extraction_confidence", "unknown") for item in state_metrics)
    low_confidence_states = [
        item["state"]
        for item in state_metrics
        if item.get("extraction_confidence") == "low"
    ]
    missing_suspected_states = [
        item["state"]
        for item in state_metrics
        if item.get("suspected_cases") in (None, "")
    ]
    return {
        "source": source,
        "state_count": len(state_metrics),
        "confidence_counts": dict(confidence_counts),
        "low_confidence_states": low_confidence_states,
        "missing_suspected_states": missing_suspected_states,
        "review_recommended": bool(low_confidence_states or missing_suspected_states),
    }


def merge_state_metric_overrides(state_metrics: list[dict], override_csv_path: str | Path | None) -> tuple[list[dict], bool]:
    if not override_csv_path:
        return state_metrics, False

    path = Path(override_csv_path)
    if not path.exists():
        return state_metrics, False

    metrics_by_state = {item["state"]: dict(item) for item in state_metrics}
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            state = (row.get("state") or "").strip()
            if not state:
                continue
            current = metrics_by_state.get(
                state,
                {
                    "state": state,
                    "metric_scope": "cumulative",
                    "suspected_cases": None,
                    "confirmed_cases": 0,
                    "deaths": 0,
                    "cfr": 0.0,
                    "extraction_confidence": "high",
                    "source_note": "Added from extraction override review file.",
                },
            )
            if row.get("suspected_cases", "").strip():
                current["suspected_cases"] = int(row["suspected_cases"])
            if row.get("confirmed_cases", "").strip():
                current["confirmed_cases"] = int(row["confirmed_cases"])
            if row.get("deaths", "").strip():
                current["deaths"] = int(row["deaths"])
            if row.get("cfr", "").strip():
                current["cfr"] = float(row["cfr"])
            if row.get("metric_scope", "").strip():
                current["metric_scope"] = row["metric_scope"].strip()
            if row.get("extraction_confidence", "").strip():
                current["extraction_confidence"] = row["extraction_confidence"].strip()
            if row.get("source_note", "").strip():
                current["source_note"] = row["source_note"].strip()
            metrics_by_state[state] = current

    merged = sorted(metrics_by_state.values(), key=lambda item: item["state"])
    return merged, True


def write_state_metric_review_csv(state_metrics: list[dict], output_path: str | Path) -> Path:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=STATE_OVERRIDE_HEADERS)
        writer.writeheader()
        for item in state_metrics:
            writer.writerow(
                {
                    "state": item.get("state"),
                    "suspected_cases": item.get("suspected_cases", ""),
                    "confirmed_cases": item.get("confirmed_cases", ""),
                    "deaths": item.get("deaths", ""),
                    "cfr": item.get("cfr", ""),
                    "metric_scope": item.get("metric_scope", "cumulative"),
                    "extraction_confidence": item.get("extraction_confidence", ""),
                    "source_note": item.get("source_note", ""),
                }
            )
    return path


def persist_historical_report(db: Session, payload: dict, state_metrics: list[dict]) -> None:
    db.execute(
        delete(HistoricalReport).where(
            HistoricalReport.disease == payload["disease"],
            HistoricalReport.year == payload["year"],
            HistoricalReport.epi_week == payload["epi_week"],
        )
    )
    db.execute(
        delete(HistoricalStateMetric).where(
            HistoricalStateMetric.disease == payload["disease"],
            HistoricalStateMetric.year == payload["year"],
            HistoricalStateMetric.epi_week == payload["epi_week"],
        )
    )

    report = HistoricalReport(
        disease=payload["disease"],
        year=payload["year"],
        epi_week=payload["epi_week"],
        week_start=payload["week_start"],
        week_end=payload["week_end"],
        source_name=payload["source_name"],
        source_path=payload["source_path"],
        suspected_current=payload["summary"]["current"]["suspected"],
        confirmed_current=payload["summary"]["current"]["confirmed"],
        probable_current=payload["summary"]["current"]["probable"],
        deaths_current=payload["summary"]["current"]["deaths"],
        cfr_current=payload["summary"]["current"]["cfr"],
        suspected_cumulative=payload["summary"]["cumulative_2026"]["suspected"],
        confirmed_cumulative=payload["summary"]["cumulative_2026"]["confirmed"],
        probable_cumulative=payload["summary"]["cumulative_2026"]["probable"],
        deaths_cumulative=payload["summary"]["cumulative_2026"]["deaths"],
        cfr_cumulative=payload["summary"]["cumulative_2026"]["cfr"],
        suspected_previous_year=payload["summary"]["cumulative_2025"]["suspected"],
        confirmed_previous_year=payload["summary"]["cumulative_2025"]["confirmed"],
        probable_previous_year=payload["summary"]["cumulative_2025"]["probable"],
        deaths_previous_year=payload["summary"]["cumulative_2025"]["deaths"],
        cfr_previous_year=payload["summary"]["cumulative_2025"]["cfr"],
    )
    db.add(report)

    for metric in state_metrics:
        db.add(
            HistoricalStateMetric(
                disease=payload["disease"],
                year=payload["year"],
                epi_week=payload["epi_week"],
                state=metric["state"],
                metric_scope=metric["metric_scope"],
                suspected_cases=metric["suspected_cases"],
                confirmed_cases=metric["confirmed_cases"],
                deaths=metric["deaths"],
                cfr=metric["cfr"],
                extraction_confidence=metric["extraction_confidence"],
                source_note=metric["source_note"],
            )
        )

    db.commit()


def rebuild_training_dataset(db: Session, disease: str = "Lassa fever") -> list[TrainingDatasetRow]:
    db.execute(delete(TrainingDatasetRow).where(TrainingDatasetRow.disease == disease))

    label_rows = (
        db.query(HistoricalStateMetric)
        .filter(HistoricalStateMetric.disease == disease, HistoricalStateMetric.metric_scope == "cumulative")
        .all()
    )

    dataset_rows: list[TrainingDatasetRow] = []
    for label in label_rows:
        weather = _historical_or_live_weather(db, disease, label.state, label.year, label.epi_week)
        symptom = _historical_or_live_symptoms(db, disease, label.state, label.year, label.epi_week)
        news = _historical_or_live_news(db, disease, label.state, label.year, label.epi_week)
        risk_score = _label_risk_score(label.confirmed_cases or 0, label.cfr or 0.0)
        risk_level = _score_to_level(risk_score)

        row = TrainingDatasetRow(
            disease=disease,
            year=label.year,
            epi_week=label.epi_week,
            state=label.state,
            temperature_c=weather.get("temperature_c"),
            rainfall_mm=weather.get("rainfall_mm"),
            humidity_pct=weather.get("humidity_pct"),
            dry_season_index=weather.get("dry_season_index"),
            fever_cases=symptom["fever_cases"],
            vomiting_cases=symptom["vomiting_cases"],
            bleeding_cases=symptom["bleeding_cases"],
            rodent_contact_cases=symptom["rodent_contact_cases"],
            news_signal_count=news["news_signal_count"],
            high_severity_news_count=news["high_severity_news_count"],
            confirmed_cases_label=label.confirmed_cases,
            deaths_label=label.deaths,
            cfr_label=label.cfr,
            risk_score_label=risk_score,
            risk_level_label=risk_level,
        )
        db.add(row)
        dataset_rows.append(row)

    db.commit()
    for row in dataset_rows:
        db.refresh(row)
    return dataset_rows


def export_training_rows_to_csv(rows: list[TrainingDatasetRow], output_path: str | Path) -> None:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "disease",
                "year",
                "epi_week",
                "state",
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
                "confirmed_cases_label",
                "deaths_label",
                "cfr_label",
                "risk_score_label",
                "risk_level_label",
            ],
        )
        writer.writeheader()
        for row in rows:
            writer.writerow(
                {
                    "disease": row.disease,
                    "year": row.year,
                    "epi_week": row.epi_week,
                    "state": row.state,
                    "temperature_c": row.temperature_c,
                    "rainfall_mm": row.rainfall_mm,
                    "humidity_pct": row.humidity_pct,
                    "dry_season_index": row.dry_season_index,
                    "fever_cases": row.fever_cases,
                    "vomiting_cases": row.vomiting_cases,
                    "bleeding_cases": row.bleeding_cases,
                    "rodent_contact_cases": row.rodent_contact_cases,
                    "news_signal_count": row.news_signal_count,
                    "high_severity_news_count": row.high_severity_news_count,
                    "confirmed_cases_label": row.confirmed_cases_label,
                    "deaths_label": row.deaths_label,
                    "cfr_label": row.cfr_label,
                    "risk_score_label": row.risk_score_label,
                    "risk_level_label": row.risk_level_label,
                }
            )


def import_historical_weather_csv(db: Session, csv_path: str | Path, disease: str = "Lassa fever") -> int:
    path = Path(csv_path)
    loaded = 0
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            year = int(row["year"])
            epi_week = int(row["epi_week"])
            state = row["state"].strip()
            db.execute(
                delete(HistoricalWeatherMetric).where(
                    HistoricalWeatherMetric.disease == disease,
                    HistoricalWeatherMetric.year == year,
                    HistoricalWeatherMetric.epi_week == epi_week,
                    HistoricalWeatherMetric.state == state,
                )
            )
            db.add(
                HistoricalWeatherMetric(
                    disease=disease,
                    year=year,
                    epi_week=epi_week,
                    state=state,
                    source_name=row.get("source_name", "Historical weather import").strip() or "Historical weather import",
                    temperature_c=_optional_float(row.get("temperature_c")),
                    rainfall_mm=_optional_float(row.get("rainfall_mm")),
                    humidity_pct=_optional_float(row.get("humidity_pct")),
                    dry_season_index=_optional_float(row.get("dry_season_index")),
                )
            )
            loaded += 1
    db.commit()
    return loaded


def import_historical_symptoms_csv(db: Session, csv_path: str | Path, disease: str = "Lassa fever") -> int:
    path = Path(csv_path)
    loaded = 0
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            year = int(row["year"])
            epi_week = int(row["epi_week"])
            state = row["state"].strip()
            db.execute(
                delete(HistoricalSymptomMetric).where(
                    HistoricalSymptomMetric.disease == disease,
                    HistoricalSymptomMetric.year == year,
                    HistoricalSymptomMetric.epi_week == epi_week,
                    HistoricalSymptomMetric.state == state,
                )
            )
            db.add(
                HistoricalSymptomMetric(
                    disease=disease,
                    year=year,
                    epi_week=epi_week,
                    state=state,
                    source_name=row.get("source_name", "Historical symptom import").strip() or "Historical symptom import",
                    fever_cases=int(row.get("fever_cases", 0) or 0),
                    headache_cases=int(row.get("headache_cases", 0) or 0),
                    vomiting_cases=int(row.get("vomiting_cases", 0) or 0),
                    weakness_cases=int(row.get("weakness_cases", 0) or 0),
                    bleeding_cases=int(row.get("bleeding_cases", 0) or 0),
                    rodent_contact_cases=int(row.get("rodent_contact_cases", 0) or 0),
                    suspected_cases=int(row.get("suspected_cases", 0) or 0),
                )
            )
            loaded += 1
    db.commit()
    return loaded


def import_historical_news_csv(db: Session, csv_path: str | Path, disease: str = "Lassa fever") -> int:
    path = Path(csv_path)
    loaded = 0
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            year = int(row["year"])
            epi_week = int(row["epi_week"])
            state = row["state"].strip()
            db.execute(
                delete(HistoricalNewsMetric).where(
                    HistoricalNewsMetric.disease == disease,
                    HistoricalNewsMetric.year == year,
                    HistoricalNewsMetric.epi_week == epi_week,
                    HistoricalNewsMetric.state == state,
                )
            )
            db.add(
                HistoricalNewsMetric(
                    disease=disease,
                    year=year,
                    epi_week=epi_week,
                    state=state,
                    source_name=row.get("source_name", "Historical news import").strip() or "Historical news import",
                    news_signal_count=int(row.get("news_signal_count", 0) or 0),
                    high_severity_news_count=int(row.get("high_severity_news_count", 0) or 0),
                    rodent_risk_mentions=int(row.get("rodent_risk_mentions", 0) or 0),
                    outbreak_mentions=int(row.get("outbreak_mentions", 0) or 0),
                )
            )
            loaded += 1
    db.commit()
    return loaded


def _historical_or_live_weather(db: Session, disease: str, location: str, year: int, epi_week: int) -> dict:
    historical = (
        db.query(HistoricalWeatherMetric)
        .filter(
            HistoricalWeatherMetric.disease == disease,
            HistoricalWeatherMetric.state == location,
            HistoricalWeatherMetric.year == year,
            HistoricalWeatherMetric.epi_week == epi_week,
        )
        .first()
    )
    if historical:
        return {
            "temperature_c": historical.temperature_c,
            "rainfall_mm": historical.rainfall_mm,
            "humidity_pct": historical.humidity_pct,
            "dry_season_index": historical.dry_season_index,
        }
    return _latest_week_weather(db, disease, location, year, epi_week)


def _historical_or_live_symptoms(db: Session, disease: str, location: str, year: int, epi_week: int) -> dict:
    historical = (
        db.query(HistoricalSymptomMetric)
        .filter(
            HistoricalSymptomMetric.disease == disease,
            HistoricalSymptomMetric.state == location,
            HistoricalSymptomMetric.year == year,
            HistoricalSymptomMetric.epi_week == epi_week,
        )
        .first()
    )
    if historical:
        return {
            "fever_cases": historical.fever_cases,
            "vomiting_cases": historical.vomiting_cases,
            "bleeding_cases": historical.bleeding_cases,
            "rodent_contact_cases": historical.rodent_contact_cases,
        }
    return _weekly_symptom_aggregate(db, disease, location, year, epi_week)


def _historical_or_live_news(db: Session, disease: str, location: str, year: int, epi_week: int) -> dict:
    historical = (
        db.query(HistoricalNewsMetric)
        .filter(
            HistoricalNewsMetric.disease == disease,
            HistoricalNewsMetric.state == location,
            HistoricalNewsMetric.year == year,
            HistoricalNewsMetric.epi_week == epi_week,
        )
        .first()
    )
    if historical:
        return {
            "news_signal_count": historical.news_signal_count,
            "high_severity_news_count": historical.high_severity_news_count,
        }
    return _weekly_news_aggregate(db, disease, location, year, epi_week)


def _latest_week_weather(db: Session, disease: str, location: str, year: int, epi_week: int) -> dict:
    record = (
        db.query(WeatherRecord)
        .filter(WeatherRecord.disease == disease, WeatherRecord.location == location)
        .order_by(WeatherRecord.recorded_at.desc())
        .first()
    )
    if not record or not _matches_week(record.recorded_at, year, epi_week):
        return {}
    return {
        "temperature_c": record.temperature_c,
        "rainfall_mm": record.rainfall_mm,
        "humidity_pct": record.humidity_pct,
        "dry_season_index": record.dry_season_index,
    }


def _weekly_symptom_aggregate(db: Session, disease: str, location: str, year: int, epi_week: int) -> dict:
    reports = [
        item
        for item in db.query(SymptomReport).filter(SymptomReport.disease == disease, SymptomReport.location == location).all()
        if _matches_week(item.report_date, year, epi_week)
    ]
    return {
        "fever_cases": sum(item.fever_cases for item in reports),
        "vomiting_cases": sum(item.vomiting_cases for item in reports),
        "bleeding_cases": sum(item.bleeding_cases for item in reports),
        "rodent_contact_cases": sum(item.contact_history_cases for item in reports),
    }


def _weekly_news_aggregate(db: Session, disease: str, location: str, year: int, epi_week: int) -> dict:
    records = [
        item
        for item in db.query(NewsRecord).filter(NewsRecord.disease == disease, NewsRecord.location == location).all()
        if _matches_week(item.published_at, year, epi_week)
    ]
    severity_hits = 0
    for item in records:
        lowered = item.content.lower()
        if any(term in lowered for term in ("rodent", "bleeding", "outbreak", "suspected")):
            severity_hits += 1
    return {
        "news_signal_count": len(records),
        "high_severity_news_count": severity_hits,
    }


def _matches_week(value: datetime | None, year: int, epi_week: int) -> bool:
    if value is None:
        return False
    iso = value.isocalendar()
    return iso.year == year and iso.week == epi_week


def _label_risk_score(confirmed_cases: int, cfr: float) -> float:
    return round(min((confirmed_cases / 25) * 0.7 + (cfr / 100) * 0.3, 1.0), 4)


def _score_to_level(score: float) -> str:
    if score >= 0.67:
        return "High"
    if score >= 0.34:
        return "Medium"
    return "Low"


def _optional_float(value: str | None) -> float | None:
    if value is None or value == "":
        return None
    return float(value)


def _split_week_range(week_range: str) -> tuple[str, str]:
    parts = WEEK_RANGE_SPLIT_RE.split(week_range, maxsplit=1)
    if len(parts) != 2:
        raise ValueError(f"Could not split epidemiological week range: {week_range}")
    return parts[0].strip(), parts[1].strip()


def _parse_dominant_state_percentages(text: str) -> list[tuple[str, int]]:
    match = DOMINANT_CASE_RE.search(text)
    if not match:
        return []
    pairs: list[tuple[str, int]] = []
    for state, percent in PERCENTAGE_PAIR_RE.findall(match.group(1)):
        pairs.append((_normalize_state_name(state), int(percent)))
    return pairs


def _parse_state_list_match(match: re.Match[str] | None) -> list[str]:
    if not match:
        return []
    state_block = re.sub(r"\s+", " ", match.group(1)).strip()
    cleaned = state_block.replace(" and ", ", ")
    states: list[str] = []
    for state in cleaned.split(","):
        normalized = _normalize_state_name(state)
        if normalized and normalized not in states:
            states.append(normalized)
    return states


def _parse_total_active_states(text: str) -> int:
    match = TOTAL_ACTIVE_STATES_RE.search(text)
    return int(match.group(1)) if match else 0


def _normalize_state_name(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip().title()


def _distribute_remainder(total: int, states: list[str]) -> dict[str, int]:
    if not states:
        return {}
    base = total // len(states)
    remainder = total % len(states)
    distributed: dict[str, int] = {}
    for index, state in enumerate(states):
        distributed[state] = base + (1 if index < remainder else 0)
    return distributed


def _allocate_integer_total(counts: dict[str, int], total_deaths: int) -> dict[str, int]:
    if not counts:
        return {}
    total_cases = sum(counts.values()) or 1
    allocation: dict[str, int] = {}
    remainders: list[tuple[float, str]] = []
    allocated = 0
    for state, cases in counts.items():
        proportional = (cases / total_cases) * total_deaths
        floor_value = int(proportional)
        allocation[state] = floor_value
        allocated += floor_value
        remainders.append((proportional - floor_value, state))
    for _, state in sorted(remainders, reverse=True)[: max(total_deaths - allocated, 0)]:
        allocation[state] += 1
    return allocation
