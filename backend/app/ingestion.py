from __future__ import annotations

import email.utils
import json
import re
from datetime import datetime, timezone
from html import unescape
from urllib.parse import quote
from xml.etree import ElementTree as ET

import requests
from sqlalchemy.orm import Session

from .models import NewsRecord, Signal, WeatherRecord
from .nlp import analyze_news_text

GOOGLE_NEWS_RSS_TEMPLATE = (
    "https://news.google.com/rss/search?q={query}&hl=en-NG&gl=NG&ceid=NG:en"
)

TRUSTED_NEWS_SOURCES = [
    {"name": "Nigeria Centre for Disease Control", "domain": "ncdc.gov.ng"},
    {"name": "World Health Organization", "domain": "who.int"},
    {"name": "The Guardian Nigeria", "domain": "guardian.ng"},
    {"name": "Punch Newspapers", "domain": "punchng.com"},
    {"name": "Premium Times", "domain": "premiumtimesng.com"},
    {"name": "Vanguard News", "domain": "vanguardngr.com"},
]

MONITORED_STATE_COORDINATES = {
    "Bauchi": (10.3158, 9.8442),
    "Benue": (7.3369, 8.7404),
    "Cross River": (4.9589, 8.3269),
    "Ebonyi": (6.2649, 8.0137),
    "Edo": (6.6342, 5.9304),
    "FCT": (9.0765, 7.3986),
    "Gombe": (10.2904, 11.1670),
    "Kaduna": (10.5105, 7.4165),
    "Kano": (12.0022, 8.5920),
    "Katsina": (12.9855, 7.6171),
    "Kebbi": (12.4539, 4.1975),
    "Kogi": (7.7337, 6.6906),
    "Kwara": (8.9669, 4.3874),
    "Lagos": (6.5244, 3.3792),
    "Nasarawa": (8.4998, 8.1997),
    "Niger": (9.9309, 5.5983),
    "Ogun": (7.1608, 3.3482),
    "Ondo": (7.2508, 5.2103),
    "Oyo": (8.1574, 3.6147),
    "Plateau": (9.2182, 9.5179),
    "Taraba": (7.9994, 10.7737),
}


def ingest_trusted_news(
    db: Session,
    *,
    disease: str = "Lassa fever",
    max_items_per_source: int = 3,
    auto_create_signals: bool = True,
) -> dict:
    created_records = 0
    created_signals = 0
    fetched_items = 0
    errors: list[str] = []
    sources_checked: list[str] = []

    for source in TRUSTED_NEWS_SOURCES:
        sources_checked.append(source["name"])
        try:
            items = fetch_google_news_rss(source["domain"], disease=disease, max_items=max_items_per_source)
        except Exception as exc:  # noqa: BLE001
            errors.append(f"{source['name']}: {exc}")
            continue

        fetched_items += len(items)
        for item in items:
            existing = (
                db.query(NewsRecord)
                .filter(
                    NewsRecord.title == item["title"],
                    NewsRecord.source_name == source["name"],
                )
                .first()
            )
            if existing:
                continue

            analysis = analyze_news_text(
                title=item["title"],
                content=item["content"],
                source_name=source["name"],
                verification_status="Verified",
                location=item.get("location"),
                disease=disease,
            )

            news_record = NewsRecord(
                title=item["title"],
                location=analysis["location"],
                disease=analysis["disease"],
                source_name=source["name"],
                verification_status="Verified",
                content=item["content"],
                published_at=item["published_at"],
            )
            db.add(news_record)
            created_records += 1

            if auto_create_signals and analysis["should_generate_signal"]:
                duplicate_signal = (
                    db.query(Signal)
                    .filter(
                        Signal.title == analysis["signal_title"],
                        Signal.source_name == source["name"],
                    )
                    .first()
                )
                if not duplicate_signal:
                    db.add(
                        Signal(
                            title=analysis["signal_title"],
                            disease=analysis["disease"],
                            location=analysis["location"],
                            source_type="Trusted crawl",
                            source_name=source["name"],
                            classification=analysis["classification"],
                            confidence=analysis["confidence"],
                            risk_factor=analysis["risk_factor"],
                            summary=analysis["summary"],
                        )
                    )
                    created_signals += 1

    db.commit()
    return {
        "mode": "trusted-news",
        "disease": disease,
        "sources_checked": sources_checked,
        "fetched_items": fetched_items,
        "records_created": created_records,
        "signals_created": created_signals,
        "errors": errors,
    }


def ingest_live_weather(
    db: Session,
    *,
    disease: str = "Lassa fever",
    locations: list[str] | None = None,
) -> dict:
    targets = locations or list(MONITORED_STATE_COORDINATES.keys())
    created_records = 0
    errors: list[str] = []
    processed_locations: list[str] = []

    for location in targets:
        normalized = location.strip()
        if not normalized:
            continue
        coords = MONITORED_STATE_COORDINATES.get(normalized)
        if not coords:
            errors.append(f"{normalized}: no coordinates configured")
            continue

        try:
            weather = fetch_open_meteo_weather(*coords)
        except Exception as exc:  # noqa: BLE001
            errors.append(f"{normalized}: {exc}")
            continue

        processed_locations.append(normalized)
        latest = (
            db.query(WeatherRecord)
            .filter(WeatherRecord.location == normalized, WeatherRecord.disease == disease)
            .order_by(WeatherRecord.recorded_at.desc())
            .first()
        )
        if latest and latest.recorded_at.replace(minute=0, second=0, microsecond=0) == weather["recorded_at"].replace(
            minute=0,
            second=0,
            microsecond=0,
        ):
            continue

        db.add(
            WeatherRecord(
                location=normalized,
                disease=disease,
                source_name="Open-Meteo live ingestion",
                temperature_c=weather["temperature_c"],
                rainfall_mm=weather["rainfall_mm"],
                humidity_pct=weather["humidity_pct"],
                dry_season_index=weather["dry_season_index"],
                recorded_at=weather["recorded_at"],
            )
        )
        created_records += 1

    db.commit()
    return {
        "mode": "live-weather",
        "disease": disease,
        "locations_processed": processed_locations,
        "records_created": created_records,
        "errors": errors,
    }


def fetch_google_news_rss(domain: str, *, disease: str, max_items: int) -> list[dict]:
    query = quote(f'"{disease}" Nigeria site:{domain}')
    url = GOOGLE_NEWS_RSS_TEMPLATE.format(query=query)
    response = requests.get(url, timeout=20)
    response.raise_for_status()

    root = ET.fromstring(response.text)
    items = []
    for item in root.findall(".//item")[:max_items]:
        title = (item.findtext("title") or "").strip()
        description = _strip_html(item.findtext("description") or "")
        link = (item.findtext("link") or "").strip()
        published_at = _parse_pub_date(item.findtext("pubDate"))
        content = description or title
        inferred_location = _guess_location_from_text(f"{title} {content}")
        items.append(
            {
                "title": title,
                "content": content,
                "link": link,
                "published_at": published_at,
                "location": inferred_location,
            }
        )
    return [item for item in items if item["title"] and item["content"]]


def fetch_open_meteo_weather(latitude: float, longitude: float) -> dict:
    response = requests.get(
        "https://api.open-meteo.com/v1/forecast",
        params={
            "latitude": latitude,
            "longitude": longitude,
            "current": "temperature_2m,relative_humidity_2m,rain",
            "daily": "precipitation_sum",
            "timezone": "Africa/Lagos",
            "forecast_days": 1,
        },
        timeout=20,
    )
    response.raise_for_status()
    payload = response.json()

    current = payload.get("current", {})
    daily = payload.get("daily", {})
    rainfall_mm = float((daily.get("precipitation_sum") or [current.get("rain", 0.0)])[0] or 0.0)
    humidity_pct = float(current.get("relative_humidity_2m") or 0.0)
    temperature_c = float(current.get("temperature_2m") or 0.0)
    dry_season_index = _dry_season_index(
        temperature_c=temperature_c,
        rainfall_mm=rainfall_mm,
        humidity_pct=humidity_pct,
    )
    recorded_at = _parse_iso_datetime(current.get("time"))
    return {
        "temperature_c": temperature_c,
        "rainfall_mm": rainfall_mm,
        "humidity_pct": humidity_pct,
        "dry_season_index": dry_season_index,
        "recorded_at": recorded_at,
    }


def fetch_open_meteo_historical_weather(
    latitude: float,
    longitude: float,
    *,
    start_date: str,
    end_date: str,
) -> dict:
    response = requests.get(
        "https://archive-api.open-meteo.com/v1/archive",
        params={
            "latitude": latitude,
            "longitude": longitude,
            "start_date": start_date,
            "end_date": end_date,
            "daily": "temperature_2m_mean,relative_humidity_2m_mean,precipitation_sum",
            "timezone": "Africa/Lagos",
        },
        timeout=25,
    )
    response.raise_for_status()
    payload = response.json()

    daily = payload.get("daily", {})
    temperatures = [float(value) for value in daily.get("temperature_2m_mean", []) if value is not None]
    humidities = [float(value) for value in daily.get("relative_humidity_2m_mean", []) if value is not None]
    precipitations = [float(value) for value in daily.get("precipitation_sum", []) if value is not None]

    if not temperatures or not humidities or not precipitations:
        raise ValueError("Open-Meteo archive response did not include complete daily values.")

    temperature_c = sum(temperatures) / len(temperatures)
    humidity_pct = sum(humidities) / len(humidities)
    rainfall_mm = sum(precipitations)
    dry_season_index = _dry_season_index(
        temperature_c=temperature_c,
        rainfall_mm=rainfall_mm,
        humidity_pct=humidity_pct,
    )

    return {
        "temperature_c": round(temperature_c, 1),
        "rainfall_mm": round(rainfall_mm, 1),
        "humidity_pct": round(humidity_pct, 1),
        "dry_season_index": dry_season_index,
        "start_date": start_date,
        "end_date": end_date,
    }


def _parse_iso_datetime(value: str | None) -> datetime:
    if not value:
        return datetime.now(timezone.utc)
    return datetime.fromisoformat(value).replace(tzinfo=timezone.utc)


def _dry_season_index(*, temperature_c: float, rainfall_mm: float, humidity_pct: float) -> float:
    score = 0.0
    score += max(temperature_c - 28, 0) * 0.03
    score += max(55 - humidity_pct, 0) * 0.01
    score += max(15 - rainfall_mm, 0) * 0.025
    return round(min(score, 1.0), 2)


def _strip_html(value: str) -> str:
    text = re.sub(r"<[^>]+>", " ", unescape(value))
    return re.sub(r"\s+", " ", text).strip()


def _parse_pub_date(value: str | None) -> datetime:
    if not value:
        return datetime.now(timezone.utc)
    parsed = email.utils.parsedate_to_datetime(value)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _guess_location_from_text(text: str) -> str | None:
    lowered = text.lower()
    for location in MONITORED_STATE_COORDINATES:
        if location.lower() in lowered:
            return location
    return None
