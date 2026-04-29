import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.app.database import Base, SessionLocal, engine
from backend.app.ingestion import MONITORED_STATE_COORDINATES
from backend.app.schemas import (
    NewsIngestionRequest,
    NotificationBatchRequest,
    PipelineRunRequest,
    ReportRequest,
    WeatherIngestionRequest,
)
from backend.app.services import (
    generate_alert_notifications,
    generate_surveillance_report,
    run_live_weather_ingestion,
    run_surveillance_pipeline,
    run_trusted_news_ingestion,
    send_queued_email_notifications,
    send_queued_sms_notifications,
    send_queued_whatsapp_notifications,
)


def main() -> int:
    disease = sys.argv[1] if len(sys.argv) > 1 else "Lassa fever"
    analyst = sys.argv[2] if len(sys.argv) > 2 else "ClinicAI Sentinel Daily Automation"
    locations = list(MONITORED_STATE_COORDINATES.keys())

    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        news_result = run_trusted_news_ingestion(
            db,
            NewsIngestionRequest(
                disease=disease,
                max_items_per_source=2,
                auto_create_signals=True,
            ),
        )
        weather_result = run_live_weather_ingestion(
            db,
            WeatherIngestionRequest(
                disease=disease,
                locations=locations,
            ),
        )

        pipeline_runs = []
        for location in locations:
            result = run_surveillance_pipeline(
                db,
                PipelineRunRequest(
                    disease=disease,
                    location=location,
                    analyst=analyst,
                ),
            )
            pipeline_runs.append(
                {
                    "location": location,
                    "risk_level": result["prediction"].risk_level,
                    "risk_score": result["prediction"].risk_score,
                    "alert_level": result["alert"].level,
                    "recommendations": len(result["recommendations"]),
                }
            )

        report_result = generate_surveillance_report(
            db,
            ReportRequest(
                disease=disease,
                analyst=analyst,
            ),
        )
        notification_result = generate_alert_notifications(
            db,
            NotificationBatchRequest(
                disease=disease,
                audience="Public health",
                recipient_email="surveillance@clinicai-sentinel.local",
                recipient_sms="+2348000000000",
                recipient_whatsapp="+2348000000000",
            ),
        )
        email_dispatch_result = send_queued_email_notifications(db)
        sms_dispatch_result = send_queued_sms_notifications(db)
        whatsapp_dispatch_result = send_queued_whatsapp_notifications(db)

        summary = {
            "disease": disease,
            "analyst": analyst,
            "news_ingestion": news_result,
            "weather_ingestion": weather_result,
            "pipeline_runs": pipeline_runs,
            "high_risk_locations": [
                item["location"] for item in pipeline_runs if item["risk_level"] == "High"
            ],
            "report": {
                "report_title": report_result["report_title"],
                "report_path": report_result["report_path"],
                "alert_count": report_result["alert_count"],
                "prediction_count": report_result["prediction_count"],
            },
            "notifications": {
                "count": notification_result["count"],
                "channels": notification_result["channels"],
                "locations": notification_result["locations"],
            },
            "email_dispatch": email_dispatch_result,
            "sms_dispatch": sms_dispatch_result,
            "whatsapp_dispatch": whatsapp_dispatch_result,
        }
    finally:
        db.close()

    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
