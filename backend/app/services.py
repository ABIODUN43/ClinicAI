from collections import defaultdict
from datetime import UTC, datetime
from email.message import EmailMessage
from pathlib import Path
import smtplib

from sqlalchemy import desc, func
from sqlalchemy.orm import Session

from .config import settings
from .data import ALERTS_DATA, ANALYTICS_DATA, HOME_DATA
from .historical_batch import execute_historical_batch, load_manifest_or_discover
from .ingestion import ingest_live_weather, ingest_trusted_news
from .ml import (
    model_ready,
    model_status,
    predict_from_feature_map,
    save_model_artifact,
    train_baseline_model,
    training_metrics_from_artifact,
)
from .nlp import analyze_news_text
from .models import (
    Alert,
    ClinicReport,
    NewsRecord,
    Notification,
    Prediction,
    Recommendation,
    Signal,
    SymptomReport,
    HistoricalNewsMetric,
    HistoricalReport,
    HistoricalStateMetric,
    HistoricalSymptomMetric,
    HistoricalWeatherMetric,
    TrainingRun,
    TrainingDatasetRow,
    WeatherRecord,
)
from .schemas import (
    AlertCreate,
    ClinicReportCreate,
    NewsIngestionRequest,
    NewsRecordCreate,
    NewsAnalysisRequest,
    NotificationBatchRequest,
    NotificationCreate,
    PipelineRunRequest,
    PredictionCreate,
    ReportRequest,
    RecommendationCreate,
    SignalCreate,
    SymptomReportCreate,
    WeatherIngestionRequest,
    WeatherRecordCreate,
)


def list_signals(
    db: Session,
    *,
    disease: str | None = None,
    location: str | None = None,
    classification: str | None = None,
    source_type: str | None = None,
    min_confidence: float | None = None,
    limit: int = 100,
) -> list[Signal]:
    query = db.query(Signal)
    if disease:
        query = query.filter(Signal.disease == disease)
    if location:
        query = query.filter(Signal.location == location)
    if classification:
        query = query.filter(Signal.classification == classification)
    if source_type:
        query = query.filter(Signal.source_type == source_type)
    if min_confidence is not None:
        query = query.filter(Signal.confidence >= min_confidence)
    return query.order_by(desc(Signal.confidence), desc(Signal.created_at)).limit(limit).all()


def list_predictions(
    db: Session,
    *,
    disease: str | None = None,
    location: str | None = None,
    risk_level: str | None = None,
    min_score: float | None = None,
    limit: int = 100,
) -> list[Prediction]:
    query = db.query(Prediction)
    if disease:
        query = query.filter(Prediction.disease == disease)
    if location:
        query = query.filter(Prediction.location == location)
    if risk_level:
        query = query.filter(Prediction.risk_level == risk_level)
    if min_score is not None:
        query = query.filter(Prediction.risk_score >= min_score)
    return query.order_by(desc(Prediction.risk_score), desc(Prediction.created_at)).limit(limit).all()


def list_alerts(
    db: Session,
    *,
    disease: str | None = None,
    location: str | None = None,
    level: str | None = None,
    limit: int = 100,
) -> list[Alert]:
    level_order = {"Red": 3, "Amber": 2, "Green": 1}
    query = db.query(Alert)
    if disease:
        query = query.filter(Alert.disease == disease)
    if location:
        query = query.filter(Alert.location == location)
    if level:
        query = query.filter(Alert.level == level)
    alerts = query.order_by(desc(Alert.created_at)).limit(limit).all()
    return sorted(alerts, key=lambda item: level_order.get(item.level, 0), reverse=True)


def list_recommendations(
    db: Session,
    *,
    priority: str | None = None,
    category: str | None = None,
    location: str | None = None,
    limit: int = 100,
) -> list[Recommendation]:
    priority_order = {"High": 3, "Medium": 2, "Low": 1}
    query = db.query(Recommendation)
    if priority:
        query = query.filter(Recommendation.priority == priority)
    if category:
        query = query.filter(Recommendation.category == category)
    if location:
        query = query.filter(Recommendation.location == location)
    recommendations = query.order_by(desc(Recommendation.created_at)).limit(limit).all()
    return sorted(recommendations, key=lambda item: priority_order.get(item.priority, 0), reverse=True)


def list_clinic_reports(
    db: Session,
    *,
    disease: str | None = None,
    location: str | None = None,
    severity: str | None = None,
    limit: int = 100,
) -> list[ClinicReport]:
    query = db.query(ClinicReport)
    if disease:
        query = query.filter(ClinicReport.disease == disease)
    if location:
        query = query.filter(ClinicReport.location == location)
    if severity:
        query = query.filter(ClinicReport.severity == severity)
    return query.order_by(desc(ClinicReport.created_at)).limit(limit).all()


def list_symptom_reports(
    db: Session,
    *,
    disease: str | None = None,
    location: str | None = None,
    limit: int = 100,
) -> list[SymptomReport]:
    query = db.query(SymptomReport)
    if disease:
        query = query.filter(SymptomReport.disease == disease)
    if location:
        query = query.filter(SymptomReport.location == location)
    return query.order_by(desc(SymptomReport.report_date), desc(SymptomReport.created_at)).limit(limit).all()


def list_weather_records(
    db: Session,
    *,
    disease: str | None = None,
    location: str | None = None,
    limit: int = 100,
) -> list[WeatherRecord]:
    query = db.query(WeatherRecord)
    if disease:
        query = query.filter(WeatherRecord.disease == disease)
    if location:
        query = query.filter(WeatherRecord.location == location)
    return query.order_by(desc(WeatherRecord.recorded_at), desc(WeatherRecord.created_at)).limit(limit).all()


def list_news_records(
    db: Session,
    *,
    disease: str | None = None,
    location: str | None = None,
    verification_status: str | None = None,
    limit: int = 100,
) -> list[NewsRecord]:
    query = db.query(NewsRecord)
    if disease:
        query = query.filter(NewsRecord.disease == disease)
    if location:
        query = query.filter(NewsRecord.location == location)
    if verification_status:
        query = query.filter(NewsRecord.verification_status == verification_status)
    return query.order_by(desc(NewsRecord.published_at), desc(NewsRecord.created_at)).limit(limit).all()


def list_notifications(
    db: Session,
    *,
    disease: str | None = None,
    location: str | None = None,
    channel: str | None = None,
    audience: str | None = None,
    limit: int = 100,
) -> list[Notification]:
    priority_order = {"High": 3, "Medium": 2, "Low": 1}
    query = db.query(Notification)
    if disease:
        query = query.filter(Notification.disease == disease)
    if location:
        query = query.filter(Notification.location == location)
    if channel:
        query = query.filter(Notification.channel == channel)
    if audience:
        query = query.filter(Notification.audience == audience)
    notifications = query.order_by(desc(Notification.created_at)).limit(limit).all()
    return sorted(
        notifications,
        key=lambda item: (priority_order.get(item.priority, 0), item.id),
        reverse=True,
    )


def create_signal(db: Session, payload: SignalCreate) -> Signal:
    signal = Signal(**payload.model_dump())
    db.add(signal)
    db.commit()
    db.refresh(signal)
    return signal


def create_prediction(db: Session, payload: PredictionCreate) -> Prediction:
    prediction = Prediction(**payload.model_dump())
    db.add(prediction)
    db.commit()
    db.refresh(prediction)
    return prediction


def create_alert(db: Session, payload: AlertCreate) -> Alert:
    alert = Alert(**payload.model_dump())
    db.add(alert)
    db.commit()
    db.refresh(alert)
    return alert


def create_recommendation(db: Session, payload: RecommendationCreate) -> Recommendation:
    recommendation = Recommendation(**payload.model_dump())
    db.add(recommendation)
    db.commit()
    db.refresh(recommendation)
    return recommendation


def create_clinic_report(db: Session, payload: ClinicReportCreate) -> ClinicReport:
    clinic_report = ClinicReport(**payload.model_dump())
    db.add(clinic_report)
    db.commit()
    db.refresh(clinic_report)
    return clinic_report


def create_symptom_report(db: Session, payload: SymptomReportCreate) -> SymptomReport:
    symptom_report = SymptomReport(**payload.model_dump())
    db.add(symptom_report)
    db.commit()
    db.refresh(symptom_report)
    return symptom_report


def create_weather_record(db: Session, payload: WeatherRecordCreate) -> WeatherRecord:
    weather_record = WeatherRecord(**payload.model_dump())
    db.add(weather_record)
    db.commit()
    db.refresh(weather_record)
    return weather_record


def create_news_record(db: Session, payload: NewsRecordCreate) -> NewsRecord:
    news_record = NewsRecord(**payload.model_dump())
    db.add(news_record)
    db.commit()
    db.refresh(news_record)
    return news_record


def create_notification(db: Session, payload: NotificationCreate) -> Notification:
    notification = Notification(**payload.model_dump())
    db.add(notification)
    db.commit()
    db.refresh(notification)
    return notification


def analyze_news_submission(payload: NewsAnalysisRequest) -> dict:
    return analyze_news_text(
        title=payload.title,
        content=payload.content,
        source_name=payload.source_name,
        verification_status=payload.verification_status,
        location=payload.location,
        disease=payload.disease,
    )


def run_trusted_news_ingestion(db: Session, payload: NewsIngestionRequest) -> dict:
    return ingest_trusted_news(
        db,
        disease=payload.disease,
        max_items_per_source=payload.max_items_per_source,
        auto_create_signals=payload.auto_create_signals,
    )


def run_live_weather_ingestion(db: Session, payload: WeatherIngestionRequest) -> dict:
    return ingest_live_weather(
        db,
        disease=payload.disease,
        locations=payload.locations,
    )


def generate_surveillance_report(db: Session, payload: ReportRequest) -> dict:
    disease = payload.disease
    generated_at = datetime.now(UTC)
    predictions = list_predictions(db, disease=disease, limit=20)
    alerts = list_alerts(db, disease=disease, limit=20)
    recommendations = list_recommendations(db, location=None, limit=10)
    signals = list_signals(db, disease=disease, limit=10)

    latest_report = (
        db.query(HistoricalReport)
        .filter(HistoricalReport.disease == disease)
        .order_by(desc(HistoricalReport.year), desc(HistoricalReport.epi_week))
        .first()
    )

    high_risk_locations = [item.location for item in predictions if item.risk_level == "High"]
    report_title = f"{disease} Daily Surveillance Summary"
    week_label = (
        f"{latest_report.year}-W{latest_report.epi_week:02d}"
        if latest_report
        else "No historical week loaded"
    )

    lines = [
        f"# {report_title}",
        "",
        f"- Generated at: {generated_at.isoformat()}",
        f"- Analyst: {payload.analyst}",
        f"- Historical coverage anchor: {week_label}",
        f"- Predictions reviewed: {len(predictions)}",
        f"- Alerts reviewed: {len(alerts)}",
        f"- High-risk locations: {', '.join(high_risk_locations) if high_risk_locations else 'None'}",
        "",
        "## Situation Summary",
        "",
    ]

    if predictions:
        for item in predictions[:5]:
            lines.append(
                f"- {item.location}: {item.risk_level} risk ({round(item.risk_score * 100)}%) via {item.model_name}."
            )
    else:
        lines.append("- No predictions are currently available.")

    lines.extend(["", "## Active Alerts", ""])
    if alerts:
        for item in alerts[:5]:
            lines.append(f"- {item.location}: {item.level} alert. {item.message} Action: {item.action}")
    else:
        lines.append("- No active alerts were found.")

    lines.extend(["", "## Signal Highlights", ""])
    if signals:
        for item in signals[:5]:
            lines.append(
                f"- {item.location}: {item.classification} signal from {item.source_name} at confidence {item.confidence:.2f}. {item.summary}"
            )
    else:
        lines.append("- No recent signals were found.")

    lines.extend(["", "## Recommended Actions", ""])
    if recommendations:
        for item in recommendations[:5]:
            lines.append(f"- {item.priority}: {item.description}")
    else:
        lines.append("- No recommendations are currently available.")

    content = "\n".join(lines)
    reports_dir = Path("backend/reports")
    reports_dir.mkdir(parents=True, exist_ok=True)
    slug = disease.lower().replace(" ", "_")
    stem = f"{slug}_summary_{generated_at.strftime('%Y%m%d_%H%M%S')}"
    markdown_report_path = reports_dir / f"{stem}.md"
    html_report_path = reports_dir / f"{stem}.html"
    pdf_report_path = reports_dir / f"{stem}.pdf"
    markdown_report_path.write_text(content, encoding="utf-8")
    html_report_path.write_text(
        _render_html_report(
            report_title=report_title,
            generated_at=generated_at.isoformat(),
            analyst=payload.analyst,
            week_label=week_label,
            predictions=predictions,
            alerts=alerts,
            recommendations=recommendations,
            signals=signals,
            high_risk_locations=high_risk_locations,
        ),
        encoding="utf-8",
    )
    pdf_report_path.write_bytes(
        _render_pdf_report(
            report_title=report_title,
            generated_at=generated_at.isoformat(),
            analyst=payload.analyst,
            week_label=week_label,
            high_risk_locations=high_risk_locations,
            predictions=predictions,
            alerts=alerts,
            recommendations=recommendations,
            signals=signals,
        )
    )

    return {
        "disease": disease,
        "generated_at": generated_at.isoformat(),
        "analyst": payload.analyst,
        "report_path": str(markdown_report_path.resolve()),
        "markdown_report_path": str(markdown_report_path.resolve()),
        "html_report_path": str(html_report_path.resolve()),
        "pdf_report_path": str(pdf_report_path.resolve()),
        "report_title": report_title,
        "high_risk_locations": high_risk_locations,
        "alert_count": len(alerts),
        "prediction_count": len(predictions),
        "content": content,
    }


def generate_alert_notifications(db: Session, payload: NotificationBatchRequest) -> dict:
    predictions = list_predictions(db, disease=payload.disease, limit=20)
    alerts = list_alerts(db, disease=payload.disease, limit=20)
    generated_notifications: list[Notification] = []
    channel_targets = [
        ("Dashboard", None),
        ("Email", payload.recipient_email),
        ("SMS", payload.recipient_sms),
        ("WhatsApp", payload.recipient_whatsapp),
    ]

    for alert in alerts:
        if alert.level not in {"Red", "Amber"}:
            continue

        matched_prediction = next(
            (
                item
                for item in predictions
                if item.disease == alert.disease and item.location == alert.location
            ),
            None,
        )
        priority = "High" if alert.level == "Red" else "Medium"
        title = f"{alert.level} {alert.disease} surveillance alert for {alert.location}"
        message = _notification_message(
            disease=alert.disease,
            location=alert.location,
            alert=alert,
            prediction=matched_prediction,
        )

        for channel, recipient in channel_targets:
            if channel != "Dashboard" and not recipient:
                continue

            notification = Notification(
                disease=alert.disease,
                location=alert.location,
                channel=channel,
                audience=payload.audience,
                priority=priority,
                status="Queued",
                title=title,
                message=message,
                recipient=recipient,
                source_alert_id=alert.id,
                source_prediction_id=matched_prediction.id if matched_prediction else None,
            )
            db.add(notification)
            generated_notifications.append(notification)

    db.commit()
    for notification in generated_notifications:
        db.refresh(notification)

    return {
        "notifications": generated_notifications,
        "count": len(generated_notifications),
        "channels": sorted({item.channel for item in generated_notifications}),
        "locations": sorted({item.location for item in generated_notifications}),
    }


def send_queued_email_notifications(db: Session) -> dict:
    queued_notifications = (
        db.query(Notification)
        .filter(Notification.channel == "Email", Notification.status == "Queued")
        .order_by(Notification.created_at.asc(), Notification.id.asc())
        .all()
    )

    if not queued_notifications:
        return {
            "processed": 0,
            "sent": 0,
            "failed": 0,
            "mode": _email_delivery_mode(),
            "outbox_paths": [],
        }

    outbox_paths: list[str] = []
    sent = 0
    failed = 0
    mode = _email_delivery_mode()

    if mode == "smtp":
        try:
            with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=20) as server:
                if settings.smtp_use_tls:
                    server.starttls()
                if settings.smtp_username:
                    server.login(settings.smtp_username, settings.smtp_password)

                for notification in queued_notifications:
                    try:
                        message = _build_email_message(notification)
                        server.send_message(message)
                        notification.status = "Sent"
                        sent += 1
                    except Exception as exc:  # pragma: no cover - defensive live-delivery path
                        notification.status = f"Failed: {str(exc)[:20]}"
                        failed += 1
        except Exception:
            mode = "outbox"

    if mode == "outbox":
        outbox_dir = Path(settings.email_outbox_path)
        outbox_dir.mkdir(parents=True, exist_ok=True)
        for notification in queued_notifications:
            try:
                message = _build_email_message(notification)
                path = outbox_dir / f"notification_{notification.id}_{datetime.now(UTC).strftime('%Y%m%d_%H%M%S')}.eml"
                path.write_text(message.as_string(), encoding="utf-8")
                notification.status = "Saved to outbox"
                outbox_paths.append(str(path.resolve()))
                sent += 1
            except Exception as exc:
                notification.status = f"Failed: {str(exc)[:20]}"
                failed += 1

    db.commit()
    return {
        "processed": len(queued_notifications),
        "sent": sent,
        "failed": failed,
        "mode": mode,
        "outbox_paths": outbox_paths,
    }


def send_queued_sms_notifications(db: Session) -> dict:
    queued_notifications = (
        db.query(Notification)
        .filter(Notification.channel == "SMS", Notification.status == "Queued")
        .order_by(Notification.created_at.asc(), Notification.id.asc())
        .all()
    )

    if not queued_notifications:
        return {
            "processed": 0,
            "sent": 0,
            "failed": 0,
            "mode": _sms_delivery_mode(),
            "outbox_paths": [],
        }

    outbox_paths: list[str] = []
    sent = 0
    failed = 0
    mode = _sms_delivery_mode()

    # Provider integration is intentionally deferred; outbox mode remains the safe MVP default.
    if mode == "provider":
        mode = "outbox"

    outbox_dir = Path(settings.sms_outbox_path)
    outbox_dir.mkdir(parents=True, exist_ok=True)
    for notification in queued_notifications:
        try:
            path = outbox_dir / f"sms_notification_{notification.id}_{datetime.now(UTC).strftime('%Y%m%d_%H%M%S')}.txt"
            path.write_text(_build_sms_message(notification), encoding="utf-8")
            notification.status = "Saved to sms outbox"
            outbox_paths.append(str(path.resolve()))
            sent += 1
        except Exception as exc:
            notification.status = f"Failed: {str(exc)[:20]}"
            failed += 1

    db.commit()
    return {
        "processed": len(queued_notifications),
        "sent": sent,
        "failed": failed,
        "mode": mode,
        "outbox_paths": outbox_paths,
    }


def send_queued_whatsapp_notifications(db: Session) -> dict:
    queued_notifications = (
        db.query(Notification)
        .filter(Notification.channel == "WhatsApp", Notification.status == "Queued")
        .order_by(Notification.created_at.asc(), Notification.id.asc())
        .all()
    )

    if not queued_notifications:
        return {
            "processed": 0,
            "sent": 0,
            "failed": 0,
            "mode": _whatsapp_delivery_mode(),
            "outbox_paths": [],
        }

    outbox_paths: list[str] = []
    sent = 0
    failed = 0
    mode = _whatsapp_delivery_mode()

    # Provider integration is intentionally deferred; outbox mode remains the safe MVP default.
    if mode == "provider":
        mode = "outbox"

    outbox_dir = Path(settings.whatsapp_outbox_path)
    outbox_dir.mkdir(parents=True, exist_ok=True)
    for notification in queued_notifications:
        try:
            path = outbox_dir / f"whatsapp_notification_{notification.id}_{datetime.now(UTC).strftime('%Y%m%d_%H%M%S')}.txt"
            path.write_text(_build_whatsapp_message(notification), encoding="utf-8")
            notification.status = "Saved to whatsapp outbox"
            outbox_paths.append(str(path.resolve()))
            sent += 1
        except Exception as exc:
            notification.status = f"Failed: {str(exc)[:20]}"
            failed += 1

    db.commit()
    return {
        "processed": len(queued_notifications),
        "sent": sent,
        "failed": failed,
        "mode": mode,
        "outbox_paths": outbox_paths,
    }


def _render_html_report(
    *,
    report_title: str,
    generated_at: str,
    analyst: str,
    week_label: str,
    predictions: list,
    alerts: list,
    recommendations: list,
    signals: list,
    high_risk_locations: list[str],
) -> str:
    summary_items = "".join(
        f"<li><strong>{item.location}</strong>: {item.risk_level} risk ({round(item.risk_score * 100)}%) via {item.model_name}.</li>"
        for item in predictions[:5]
    ) or "<li>No predictions are currently available.</li>"
    alert_items = "".join(
        f"<li><strong>{item.location}</strong>: {item.level} alert. {item.message} Action: {item.action}</li>"
        for item in alerts[:5]
    ) or "<li>No active alerts were found.</li>"
    signal_items = "".join(
        f"<li><strong>{item.location}</strong>: {item.classification} signal from {item.source_name} at confidence {item.confidence:.2f}. {item.summary}</li>"
        for item in signals[:5]
    ) or "<li>No recent signals were found.</li>"
    recommendation_items = "".join(
        f"<li><strong>{item.priority}</strong>: {item.description}</li>"
        for item in recommendations[:5]
    ) or "<li>No recommendations are currently available.</li>"

    high_risk_copy = ", ".join(high_risk_locations) if high_risk_locations else "None"
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{report_title}</title>
  <style>
    body {{
      margin: 0;
      font-family: "Segoe UI", Arial, sans-serif;
      background: #f6efe6;
      color: #1f2a24;
    }}
    .page {{
      max-width: 980px;
      margin: 0 auto;
      padding: 36px 28px 48px;
    }}
    .hero {{
      background: linear-gradient(135deg, #fffaf4 0%, #f7efe3 100%);
      border: 1px solid rgba(92, 74, 39, 0.12);
      border-radius: 28px;
      padding: 28px;
      box-shadow: 0 18px 40px rgba(73, 49, 18, 0.1);
    }}
    .eyebrow {{
      display: inline-block;
      padding: 7px 12px;
      border-radius: 999px;
      background: rgba(216, 71, 67, 0.12);
      color: #a83c39;
      font-weight: 700;
      font-size: 12px;
      letter-spacing: 0.04em;
      text-transform: uppercase;
    }}
    h1, h2 {{
      font-family: "Trebuchet MS", "Segoe UI", sans-serif;
      margin: 0;
    }}
    h1 {{
      margin-top: 16px;
      font-size: 34px;
    }}
    .lede {{
      margin-top: 14px;
      color: #58675f;
      line-height: 1.6;
      max-width: 70ch;
    }}
    .meta-grid {{
      display: grid;
      grid-template-columns: repeat(4, minmax(0, 1fr));
      gap: 14px;
      margin-top: 24px;
    }}
    .meta-card, .section {{
      background: rgba(255,255,255,0.72);
      border: 1px solid rgba(92, 74, 39, 0.08);
      border-radius: 20px;
      padding: 18px;
    }}
    .meta-card strong {{
      display: block;
      font-size: 22px;
      margin-bottom: 6px;
    }}
    .sections {{
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 18px;
      margin-top: 22px;
    }}
    .section h2 {{
      font-size: 20px;
      margin-bottom: 10px;
    }}
    ul {{
      margin: 0;
      padding-left: 18px;
      line-height: 1.6;
    }}
    .footer {{
      margin-top: 20px;
      padding: 18px;
      border-radius: 18px;
      background: rgba(13, 122, 95, 0.08);
      color: #294238;
    }}
    @media (max-width: 760px) {{
      .meta-grid, .sections {{
        grid-template-columns: 1fr;
      }}
    }}
  </style>
</head>
<body>
  <div class="page">
    <section class="hero">
      <div class="eyebrow">ClinicAI Sentinel export</div>
      <h1>{report_title}</h1>
      <p class="lede">
        This report summarizes the latest outbreak intelligence, model output, alerts, and recommended actions for rapid
        stakeholder review and presentation.
      </p>
      <div class="meta-grid">
        <div class="meta-card"><strong>{week_label}</strong><span>Historical anchor week</span></div>
        <div class="meta-card"><strong>{len(predictions)}</strong><span>Predictions reviewed</span></div>
        <div class="meta-card"><strong>{len(alerts)}</strong><span>Alerts reviewed</span></div>
        <div class="meta-card"><strong>{high_risk_copy}</strong><span>High-risk locations</span></div>
      </div>
      <div class="footer">
        Generated at {generated_at} by {analyst}.
      </div>
    </section>
    <section class="sections">
      <article class="section">
        <h2>Situation Summary</h2>
        <ul>{summary_items}</ul>
      </article>
      <article class="section">
        <h2>Active Alerts</h2>
        <ul>{alert_items}</ul>
      </article>
      <article class="section">
        <h2>Signal Highlights</h2>
        <ul>{signal_items}</ul>
      </article>
      <article class="section">
        <h2>Recommended Actions</h2>
        <ul>{recommendation_items}</ul>
      </article>
    </section>
  </div>
</body>
</html>"""


def _render_pdf_report(
    *,
    report_title: str,
    generated_at: str,
    analyst: str,
    week_label: str,
    high_risk_locations: list[str],
    predictions: list,
    alerts: list,
    recommendations: list,
    signals: list,
) -> bytes:
    lines = [
        report_title,
        "",
        f"Generated at: {generated_at}",
        f"Analyst: {analyst}",
        f"Historical anchor week: {week_label}",
        f"High-risk locations: {', '.join(high_risk_locations) if high_risk_locations else 'None'}",
        "",
        "Situation Summary",
    ]

    if predictions:
        lines.extend(
            [
                f"- {item.location}: {item.risk_level} risk ({round(item.risk_score * 100)}%) via {item.model_name}."
                for item in predictions[:5]
            ]
        )
    else:
        lines.append("- No predictions are currently available.")

    lines.extend(["", "Active Alerts"])
    if alerts:
        lines.extend(
            [f"- {item.location}: {item.level} alert. {item.message} Action: {item.action}" for item in alerts[:5]]
        )
    else:
        lines.append("- No active alerts were found.")

    lines.extend(["", "Signal Highlights"])
    if signals:
        lines.extend(
            [
                f"- {item.location}: {item.classification} signal from {item.source_name} at confidence {item.confidence:.2f}. {item.summary}"
                for item in signals[:5]
            ]
        )
    else:
        lines.append("- No recent signals were found.")

    lines.extend(["", "Recommended Actions"])
    if recommendations:
        lines.extend([f"- {item.priority}: {item.description}" for item in recommendations[:5]])
    else:
        lines.append("- No recommendations are currently available.")

    wrapped_lines: list[str] = []
    for line in lines:
        wrapped_lines.extend(_wrap_pdf_text(line, 94))

    content_stream_lines = ["BT", "/F1 11 Tf", "50 790 Td", "14 TL"]
    first_line = True
    for line in wrapped_lines:
        escaped = _escape_pdf_text(line)
        if first_line:
            content_stream_lines.append(f"({escaped}) Tj")
            first_line = False
        else:
            content_stream_lines.append(f"T* ({escaped}) Tj")
    content_stream_lines.append("ET")
    content_stream = "\n".join(content_stream_lines).encode("latin-1", errors="replace")

    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        f"<< /Length {len(content_stream)} >>\nstream\n".encode("latin-1") + content_stream + b"\nendstream",
    ]

    pdf = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for index, obj in enumerate(objects, start=1):
        offsets.append(len(pdf))
        pdf.extend(f"{index} 0 obj\n".encode("latin-1"))
        pdf.extend(obj)
        pdf.extend(b"\nendobj\n")

    xref_position = len(pdf)
    pdf.extend(f"xref\n0 {len(objects) + 1}\n".encode("latin-1"))
    pdf.extend(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        pdf.extend(f"{offset:010d} 00000 n \n".encode("latin-1"))

    pdf.extend(
        (
            f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\n"
            f"startxref\n{xref_position}\n%%EOF"
        ).encode("latin-1")
    )
    return bytes(pdf)


def _escape_pdf_text(value: str) -> str:
    return value.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def _wrap_pdf_text(value: str, width: int) -> list[str]:
    if not value:
        return [""]

    words = value.split()
    if not words:
        return [value]

    lines: list[str] = []
    current = words[0]
    for word in words[1:]:
        candidate = f"{current} {word}"
        if len(candidate) <= width:
            current = candidate
        else:
            lines.append(current)
            current = word
    lines.append(current)
    return lines


def get_model_status() -> dict:
    return model_status()


def train_operational_model(db: Session, disease: str = "Lassa fever") -> dict:
    rows = db.query(TrainingDatasetRow).filter(TrainingDatasetRow.disease == disease).all()
    artifact = train_baseline_model(rows)
    save_model_artifact(artifact)
    historical_reports = db.query(HistoricalReport).filter(HistoricalReport.disease == disease).count()
    record_training_run(
        db,
        disease=disease,
        artifact=artifact,
        trigger_source="manual-train",
        historical_reports=historical_reports,
        training_rows=len(rows),
        notes="Triggered from the operational training endpoint.",
    )
    return model_status()


def get_training_dataset_status(db: Session, disease: str = "Lassa fever") -> dict:
    reports = db.query(HistoricalReport).filter(HistoricalReport.disease == disease).all()
    state_metrics = db.query(HistoricalStateMetric).filter(HistoricalStateMetric.disease == disease).count()
    weather_metrics = db.query(HistoricalWeatherMetric).filter(HistoricalWeatherMetric.disease == disease).count()
    symptom_metrics = db.query(HistoricalSymptomMetric).filter(HistoricalSymptomMetric.disease == disease).count()
    news_metrics = db.query(HistoricalNewsMetric).filter(HistoricalNewsMetric.disease == disease).count()
    training_rows = db.query(TrainingDatasetRow).filter(TrainingDatasetRow.disease == disease).count()
    covered_weeks = sorted({f"{item.year}-W{item.epi_week:02d}" for item in reports})
    return {
        "disease": disease,
        "historical_reports": len(reports),
        "historical_state_metrics": state_metrics,
        "historical_weather_metrics": weather_metrics,
        "historical_symptom_metrics": symptom_metrics,
        "historical_news_metrics": news_metrics,
        "training_rows": training_rows,
        "covered_weeks": covered_weeks,
    }


def list_training_runs(db: Session, disease: str = "Lassa fever", limit: int = 20) -> list[TrainingRun]:
    return (
        db.query(TrainingRun)
        .filter(TrainingRun.disease == disease)
        .order_by(desc(TrainingRun.created_at), desc(TrainingRun.id))
        .limit(limit)
        .all()
    )


def list_historical_reports(db: Session, disease: str = "Lassa fever") -> list[HistoricalReport]:
    return (
        db.query(HistoricalReport)
        .filter(HistoricalReport.disease == disease)
        .order_by(desc(HistoricalReport.year), desc(HistoricalReport.epi_week))
        .all()
    )


def run_auto_historical_refresh(db: Session) -> dict:
    _manifest_path, manifest = load_manifest_or_discover("--auto")
    return execute_historical_batch(db, manifest, manifest_label="auto-discovery")


def record_training_run(
    db: Session,
    *,
    disease: str,
    artifact: dict,
    trigger_source: str,
    historical_reports: int,
    training_rows: int,
    notes: str | None = None,
) -> TrainingRun:
    metrics = training_metrics_from_artifact(artifact)
    run = TrainingRun(
        disease=disease,
        model_name=metrics["model_name"],
        trigger_source=trigger_source,
        sample_count=metrics["sample_count"],
        accuracy=metrics["accuracy"],
        mae=metrics["mae"],
        historical_reports=historical_reports,
        training_rows=training_rows,
        notes=notes,
    )
    db.add(run)
    db.commit()
    db.refresh(run)
    return run


def run_surveillance_pipeline(db: Session, payload: PipelineRunRequest) -> dict:
    symptom_reports = list_symptom_reports(db, disease=payload.disease, location=payload.location, limit=5)
    weather_records = list_weather_records(db, disease=payload.disease, location=payload.location, limit=3)
    news_records = list_news_records(db, disease=payload.disease, location=payload.location, limit=3)
    existing_signals = list_signals(db, disease=payload.disease, location=payload.location, limit=5)

    generated_signal = _generate_signal_from_news(db, payload.disease, payload.location, news_records)
    signal_pool = [generated_signal] + existing_signals if generated_signal else existing_signals
    feature_map = _build_live_feature_map(
        disease=payload.disease,
        location=payload.location,
        symptom_reports=symptom_reports,
        weather_records=weather_records,
        signals=signal_pool,
        news_records=news_records,
    )
    if model_ready():
        model_prediction = predict_from_feature_map(feature_map)
        risk_score = model_prediction["risk_score"]
        risk_level = model_prediction["risk_level"]
        driver_summary = model_prediction["driver_summary"]
        model_name = model_prediction["model_name"]
    else:
        risk_score, driver_summary = _calculate_risk_score(feature_map)
        risk_level = _score_to_risk_level(risk_score)
        model_name = "ClinicAI Sentinel Fusion Baseline"
    action_texts = _build_recommendation_texts(payload.disease, payload.location, risk_level, symptom_reports, weather_records, signal_pool)

    prediction = Prediction(
        disease=payload.disease,
        location=payload.location,
        risk_level=risk_level,
        risk_score=risk_score,
        model_name=model_name,
        driver_summary=driver_summary,
        recommended_action=" | ".join(action_texts[:3]),
    )
    db.add(prediction)
    db.flush()

    alert = Alert(
        disease=payload.disease,
        location=payload.location,
        level=_risk_to_alert_level(risk_level),
        status=_risk_to_status(risk_level),
        message=f"{risk_level} {payload.disease} risk detected in {payload.location}.",
        action=action_texts[0],
        signal_count=len(signal_pool) + len(symptom_reports) + len(news_records),
    )
    db.add(alert)
    db.flush()

    recommendations: list[Recommendation] = []
    for index, text in enumerate(action_texts[:3], start=1):
        recommendation = Recommendation(
            title=f"{payload.location} response action {index}",
            category="Response",
            priority=_risk_to_priority(risk_level, index),
            location=payload.location,
            description=text,
            status="Generated by pipeline",
        )
        db.add(recommendation)
        recommendations.append(recommendation)

    db.commit()
    db.refresh(prediction)
    db.refresh(alert)
    for recommendation in recommendations:
        db.refresh(recommendation)
    if generated_signal:
        db.refresh(generated_signal)

    return {
        "prediction": prediction,
        "alert": alert,
        "recommendations": recommendations,
        "generated_signal": generated_signal,
        "summary": (
            f"ClinicAI Sentinel analyzed structured symptom reports, weather conditions, and "
            f"verified text intelligence for {payload.location} and produced a {risk_level.lower()}-risk "
            f"{payload.disease} response package."
        ),
    }


def build_home_dashboard(db: Session) -> dict:
    home = dict(HOME_DATA)
    signals = list_signals(db)
    predictions = list_predictions(db)
    alerts = list_alerts(db)
    recommendations = list_recommendations(db)
    clinic_reports = list_clinic_reports(db)

    lassa_prediction = next((item for item in predictions if item.disease == "Lassa fever"), None)
    elevated_states = len({item.location for item in alerts if item.level in {"Red", "Amber"}})

    home["hero"] = {
        **HOME_DATA["hero"],
        "metrics": [
            {
                "value": f"{round((lassa_prediction.risk_score if lassa_prediction else 0) * 100):.0f}%",
                "label": "Lassa outbreak probability this week",
                "tone": "red",
                "status": lassa_prediction.risk_level if lassa_prediction else "Review",
            },
            {
                "value": f"{len(signals):,}",
                "label": "Signals currently tracked in the platform",
                "tone": "green",
                "status": "System live",
            },
            {
                "value": str(len(clinic_reports)),
                "label": "Clinic reports received from monitored facilities",
                "tone": "amber",
                "status": f"{elevated_states} states elevated",
            },
        ],
    }
    home["actions"] = [
        {"title": item.title, "tone": _priority_to_tone(item.priority), "status": item.status}
        for item in recommendations[:3]
    ]
    home["feed"] = [
        {
            "title": item.title,
            "tags": [
                {"label": item.disease, "tone": _level_to_tone(item.classification)},
                {"label": item.source_type, "tone": "amber"},
                {"label": f"Confidence {item.confidence:.2f}", "tone": "green"},
            ],
        }
        for item in signals[:3]
    ]
    home["priority_states"] = [
        {
            "state": item.location,
            "disease": item.disease,
            "alert": item.level,
            "signals": item.signal_count,
        }
        for item in alerts[:4]
    ]
    return home


def build_analytics_dashboard(db: Session) -> dict:
    analytics = dict(ANALYTICS_DATA)
    predictions = list_predictions(db)
    signals = list_signals(db)
    high_risk_predictions = [item for item in predictions if item.risk_level == "High"]
    avg_confidence = db.query(func.avg(Signal.confidence)).scalar() or 0

    analytics["summary_metrics"] = [
        {
            "value": f"{round((high_risk_predictions[0].risk_score if high_risk_predictions else 0) * 100):.0f}%",
            "label": "Predicted outbreak likelihood for Lassa fever",
        },
        {
            "value": f"{avg_confidence:.2f}",
            "label": "Average confidence across classified signals",
        },
        {
            "value": f"{len(signals):,}",
            "label": "Signals classified in the current demo dataset",
        },
    ]
    analytics["disease_probabilities"] = [
        {"label": item.disease, "value": round(item.risk_score * 100)}
        for item in predictions[:4]
    ]
    analytics["classified_signals"] = [
        {
            "source": item.source_name,
            "location": item.location,
            "level": item.classification,
            "confidence": f"{item.confidence:.2f}",
        }
        for item in signals[:4]
    ]
    analytics["recommendations"] = [
        {"title": item.title, "copy": item.description}
        for item in list_recommendations(db)[:3]
    ]
    return analytics


def build_alerts_dashboard(db: Session) -> dict:
    alerts_data = dict(ALERTS_DATA)
    alerts = list_alerts(db)
    grouped: dict[str, list[Alert]] = defaultdict(list)

    for item in alerts:
        grouped[item.disease].append(item)

    diseases = []
    table = []
    for disease, items in grouped.items():
        top_item = items[0]
        states = ", ".join(alert.location for alert in items[:3])
        total_signals = sum(alert.signal_count for alert in items)
        probability = _alert_probability(top_item.level)
        diseases.append(
            {
                "tone": _level_to_tone(top_item.level),
                "alert": f"{top_item.level} alert",
                "name": disease,
                "copy": top_item.message,
                "status": top_item.status,
                "probability": probability,
                "weekly_signals": str(total_signals),
                "states": str(len(items)),
                "primary_states": states,
                "cue": top_item.action,
            }
        )
        table.append(
            {
                "disease": disease,
                "level": top_item.level,
                "states": states,
                "action": top_item.action,
            }
        )

    alerts_data["diseases"] = diseases
    alerts_data["table"] = table
    return alerts_data


def _generate_signal_from_news(
    db: Session,
    disease: str,
    location: str,
    news_records: list[NewsRecord],
) -> Signal | None:
    if not news_records:
        return None

    latest = news_records[0]
    analysis = analyze_news_text(
        title=latest.title,
        content=latest.content,
        source_name=latest.source_name,
        verification_status=latest.verification_status,
        location=latest.location or location,
        disease=latest.disease or disease,
    )

    if not analysis["should_generate_signal"]:
        return None

    signal = Signal(
        title=analysis["signal_title"],
        disease=analysis["disease"],
        location=analysis["location"],
        source_type="NLP extraction",
        source_name=latest.source_name,
        classification=analysis["classification"],
        confidence=analysis["confidence"],
        risk_factor=analysis["risk_factor"],
        summary=analysis["summary"],
    )
    db.add(signal)
    db.flush()
    return signal


def _build_live_feature_map(
    *,
    disease: str,
    location: str,
    symptom_reports: list[SymptomReport],
    weather_records: list[WeatherRecord],
    signals: list[Signal],
    news_records: list[NewsRecord],
) -> dict:
    symptom_totals = {
        "fever": sum(item.fever_cases for item in symptom_reports),
        "headache": sum(item.headache_cases for item in symptom_reports),
        "vomiting": sum(item.vomiting_cases for item in symptom_reports),
        "weakness": sum(item.weakness_cases for item in symptom_reports),
        "bleeding": sum(item.bleeding_cases for item in symptom_reports),
        "contact": sum(item.contact_history_cases for item in symptom_reports),
        "suspected": sum(item.suspected_cases for item in symptom_reports),
    }
    latest_weather = weather_records[0] if weather_records else None
    return {
        "state": location,
        "disease": disease,
        "temperature_c": latest_weather.temperature_c if latest_weather else 0.0,
        "rainfall_mm": latest_weather.rainfall_mm if latest_weather else 0.0,
        "humidity_pct": latest_weather.humidity_pct if latest_weather else 0.0,
        "dry_season_index": latest_weather.dry_season_index if latest_weather else 0.0,
        "fever_cases": symptom_totals["fever"],
        "vomiting_cases": symptom_totals["vomiting"],
        "bleeding_cases": symptom_totals["bleeding"],
        "rodent_contact_cases": symptom_totals["contact"],
        "news_signal_count": len(news_records),
        "high_severity_news_count": sum(
            1 for item in news_records if any(term in item.content.lower() for term in ("rodent", "bleeding", "outbreak", "suspected"))
        ),
        "signal_strength": min(
            sum(item.confidence * {"Red": 1.0, "Amber": 0.6, "Green": 0.3}.get(item.classification, 0.2) for item in signals),
            5.0,
        ),
        "suspected_cases": symptom_totals["suspected"],
        "headache_cases": symptom_totals["headache"],
        "weakness_cases": symptom_totals["weakness"],
    }


def _calculate_risk_score(feature_map: dict) -> tuple[float, str]:
    symptom_score = min(
        (
            feature_map["fever_cases"] * 0.018
            + feature_map["headache_cases"] * 0.01
            + feature_map["vomiting_cases"] * 0.015
            + feature_map["weakness_cases"] * 0.012
            + feature_map["bleeding_cases"] * 0.06
            + feature_map["rodent_contact_cases"] * 0.04
            + feature_map["suspected_cases"] * 0.05
        ),
        0.45,
    )

    weather_score = min(
        (
            max(feature_map["temperature_c"] - 28, 0) * 0.012
            + max(60 - feature_map["humidity_pct"], 0) * 0.004
            + feature_map["dry_season_index"] * 0.18
            + max(20 - feature_map["rainfall_mm"], 0) * 0.003
        ),
        0.28,
    )

    signal_score = min(
        feature_map["signal_strength"] * 0.07 + feature_map["high_severity_news_count"] * 0.02,
        0.22,
    )
    source_bonus = min(feature_map["news_signal_count"] * 0.02, 0.05)
    baseline = 0.08 if feature_map["disease"] == "Lassa fever" and feature_map["state"] in {"Ondo", "Edo", "Ebonyi"} else 0.03
    risk_score = min(symptom_score + weather_score + signal_score + source_bonus + baseline, 0.98)
    summary = (
        f"Risk drivers for {feature_map['state']}: symptom pressure {symptom_score:.2f}, weather contribution {weather_score:.2f}, "
        f"text/NLP evidence {signal_score:.2f}, and source density {source_bonus:.2f}."
    )
    return risk_score, summary


def _build_recommendation_texts(
    disease: str,
    location: str,
    risk_level: str,
    symptom_reports: list[SymptomReport],
    weather_records: list[WeatherRecord],
    signals: list[Signal],
) -> list[str]:
    texts = [
        f"Increase screening in {location} for fever, weakness, vomiting, and bleeding symptoms linked to {disease}.",
        f"Notify the local public health officer and brief nearby clinics on the current {risk_level.lower()}-risk pattern.",
        f"Prepare isolation workflow, PPE checks, and escalation reporting for suspected {disease} cases.",
    ]

    bleeding_cases = sum(item.bleeding_cases for item in symptom_reports)
    if bleeding_cases > 0:
        texts.append(f"Prioritize review of hemorrhagic symptom clusters because {bleeding_cases} bleeding-linked cases were reported.")

    if weather_records and weather_records[0].dry_season_index >= 0.7:
        texts.append("Increase community messaging around rodent exposure and household hygiene due to elevated dry-season conditions.")

    if any(item.classification == "Red" for item in signals):
        texts.append("Escalate analyst review of high-confidence red-classified text signals before the next reporting cycle.")

    return texts


def _score_to_risk_level(risk_score: float) -> str:
    if risk_score >= 0.7:
        return "High"
    if risk_score >= 0.4:
        return "Medium"
    return "Low"


def _risk_to_alert_level(risk_level: str) -> str:
    return {"High": "Red", "Medium": "Amber"}.get(risk_level, "Green")


def _risk_to_status(risk_level: str) -> str:
    return {"High": "Urgent", "Medium": "Review"}.get(risk_level, "Stable")


def _risk_to_priority(risk_level: str, rank: int) -> str:
    if risk_level == "High" and rank == 1:
        return "High"
    if risk_level in {"High", "Medium"}:
        return "Medium"
    return "Low"


def _priority_to_tone(priority: str) -> str:
    return {"High": "red", "Medium": "amber"}.get(priority, "green")


def _level_to_tone(level: str) -> str:
    return {"Red": "red", "Amber": "amber"}.get(level, "green")


def _alert_probability(level: str) -> str:
    return {"Red": "78%", "Amber": "44%"}.get(level, "26%")


def _notification_message(
    *,
    disease: str,
    location: str,
    alert: Alert,
    prediction: Prediction | None,
) -> str:
    score_copy = ""
    if prediction:
        score_copy = (
            f" The current model output is {prediction.risk_level.lower()} risk at "
            f"{round(prediction.risk_score * 100)}%."
        )

    return (
        f"ClinicAI Sentinel has queued a {alert.level.lower()} alert for {disease} in {location}. "
        f"{alert.message} Recommended action: {alert.action}.{score_copy}"
    )


def _email_delivery_mode() -> str:
    return "smtp" if settings.smtp_host and settings.smtp_sender else "outbox"


def _build_email_message(notification: Notification) -> EmailMessage:
    message = EmailMessage()
    message["Subject"] = notification.title
    message["From"] = settings.smtp_sender
    message["To"] = notification.recipient or settings.smtp_sender
    message.set_content(
        "\n".join(
            [
                "ClinicAI Sentinel Notification",
                "",
                f"Disease: {notification.disease}",
                f"Location: {notification.location}",
                f"Audience: {notification.audience}",
                f"Priority: {notification.priority}",
                "",
                notification.message,
            ]
        )
    )
    return message


def _sms_delivery_mode() -> str:
    return "provider" if settings.sms_provider_url and settings.sms_api_key else "outbox"


def _build_sms_message(notification: Notification) -> str:
    recipient = notification.recipient or "No recipient configured"
    return (
        f"To: {recipient}\n"
        f"Sender: {settings.sms_sender_id}\n"
        f"Disease: {notification.disease}\n"
        f"Location: {notification.location}\n"
        f"Priority: {notification.priority}\n"
        f"Message: {notification.message}\n"
    )


def _whatsapp_delivery_mode() -> str:
    return "provider" if settings.whatsapp_provider_url and settings.whatsapp_api_key else "outbox"


def _build_whatsapp_message(notification: Notification) -> str:
    recipient = notification.recipient or "No recipient configured"
    return (
        f"To: {recipient}\n"
        f"Sender: {settings.whatsapp_sender_id}\n"
        f"Disease: {notification.disease}\n"
        f"Location: {notification.location}\n"
        f"Priority: {notification.priority}\n"
        f"Title: {notification.title}\n"
        f"Message: {notification.message}\n"
    )
