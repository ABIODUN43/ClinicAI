from contextlib import asynccontextmanager
from urllib.parse import parse_qs

from fastapi import Depends, FastAPI, Header, HTTPException, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from google.auth.transport import requests
from google.oauth2 import id_token
import jwt
from sqlalchemy.orm import Session

from .app.config import allowed_frontend_origins, settings
from .app.database import Base, engine, get_db
from .app.schemas import (
    AlertResponse,
    AlertCreate,
    ClinicReportCreate,
    ClinicReportResponse,
    ContactPreferenceCreate,
    ContactPreferenceResponse,
    DatasetBatchRunResponse,
    DatasetStatusResponse,
    EmailDispatchResponse,
    GoogleTokenRequest,
    HistoricalReportSummaryResponse,
    IngestionRunResponse,
    ModelStatusResponse,
    NewsAnalysisRequest,
    NewsAnalysisResponse,
    NewsIngestionRequest,
    NewsRecordCreate,
    NewsRecordResponse,
    NotificationBatchRequest,
    NotificationCreate,
    NotificationReplyResponse,
    NotificationResponse,
    PipelineRunRequest,
    PipelineRunResponse,
    PredictionCreate,
    PredictionResponse,
    ReportRequest,
    ReportResponse,
    RecommendationCreate,
    RecommendationResponse,
    SessionResponse,
    SignalCreate,
    SignalResponse,
    SmsDispatchResponse,
    SymptomReportCreate,
    SymptomReportResponse,
    SymptomReportUpdate,
    TrainingRunResponse,
    UserResponse,
    WeatherIngestionRequest,
    WeatherRecordCreate,
    WeatherRecordResponse,
    WhatsAppDispatchResponse,
)
from .app.seed import seed_database
from .app.services import (
    build_alerts_dashboard,
    build_analytics_dashboard,
    analyze_news_submission,
    build_home_dashboard,
    create_alert,
    create_clinic_report,
    create_news_record,
    create_notification,
    create_prediction,
    create_recommendation,
    create_signal,
    create_symptom_report,
    create_weather_record,
    delete_symptom_report,
    get_training_dataset_status,
    generate_alert_notifications,
    generate_surveillance_report,
    list_historical_reports,
    list_training_runs,
    list_alerts,
    list_clinic_reports,
    list_contact_preferences,
    list_news_records,
    list_notifications,
    list_notification_replies,
    list_predictions,
    list_recommendations,
    list_signals,
    list_symptom_reports,
    list_weather_records,
    get_model_status,
    run_surveillance_pipeline,
    run_auto_historical_refresh,
    run_live_weather_ingestion,
    run_daily_surveillance_cycle,
    record_whatsapp_reply,
    send_queued_email_notifications,
    send_queued_sms_notifications,
    send_queued_whatsapp_notifications,
    train_operational_model,
    update_symptom_report,
    upsert_contact_preference,
    run_trusted_news_ingestion,
)
from .app.security import bearer_scheme, create_access_token, require_bearer_token
from .app.security import require_role, resolve_user_role


def _decode_google_token_for_local_dev(credential: str) -> dict | None:
    if settings.environment != "development":
        return None

    try:
        token_info = jwt.decode(
            credential,
            options={
                "verify_signature": False,
                "verify_aud": False,
                "verify_exp": False,
            },
        )
    except jwt.PyJWTError:
        return None

    audience = token_info.get("aud")
    issuer = token_info.get("iss")
    email = token_info.get("email")
    name = token_info.get("name")

    if audience != settings.google_client_id:
        return None
    if issuer not in {"accounts.google.com", "https://accounts.google.com"}:
        return None
    if not email or not name:
        return None

    return token_info


@asynccontextmanager
async def lifespan(_: FastAPI):
    Base.metadata.create_all(bind=engine)
    db = next(get_db())
    try:
        seed_database(db)
    finally:
        db.close()
    yield


app = FastAPI(title=settings.app_name, lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_frontend_origins(),
    allow_origin_regex=r"^https?://(localhost|127\.0\.0\.1)(:\d+)?$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health_check():
    return {
        "status": "ok",
        "app_name": settings.app_name,
        "environment": settings.environment,
        "google_auth_configured": bool(settings.google_client_id),
        "frontend_origins": allowed_frontend_origins(),
    }


@app.post("/api/auth/google", response_model=SessionResponse)
def login_with_google(payload: GoogleTokenRequest):
    if not settings.google_client_id:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Google auth is not configured on the backend yet.",
        )

    try:
        token_info = id_token.verify_oauth2_token(
            payload.credential,
            requests.Request(),
            settings.google_client_id,
        )
    except ValueError as exc:
        token_info = _decode_google_token_for_local_dev(payload.credential)
        if token_info:
            email = token_info.get("email")
            name = token_info.get("name")
            image_url = token_info.get("picture")
            role = resolve_user_role(email, payload.requested_role)
            access_token = create_access_token(email=email, name=name, image_url=image_url, role=role)
            user = UserResponse(name=name, email=email, image_url=image_url, role=role)
            return SessionResponse(access_token=access_token, user=user)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Google token verification failed.",
        ) from exc

    email = token_info.get("email")
    name = token_info.get("name")
    image_url = token_info.get("picture")

    if not email or not name:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Google profile is missing required fields.",
        )

    role = resolve_user_role(email, payload.requested_role)
    access_token = create_access_token(email=email, name=name, image_url=image_url, role=role)
    user = UserResponse(name=name, email=email, image_url=image_url, role=role)
    return SessionResponse(access_token=access_token, user=user)


@app.get("/api/auth/me", response_model=UserResponse)
def get_current_user(credentials=Depends(bearer_scheme)):
    user = require_bearer_token(credentials)
    return UserResponse(
        name=user["name"],
        email=user["sub"],
        image_url=user.get("picture"),
        role=user.get("role", "admin"),
    )


@app.get("/api/contact-preferences", response_model=list[ContactPreferenceResponse])
def get_contact_preferences(
    role: str | None = None,
    email: str | None = None,
    limit: int = 50,
    credentials=Depends(bearer_scheme),
    db: Session = Depends(get_db),
):
    user = require_bearer_token(credentials)
    require_role(user, "clinic", "public_health", "admin")
    effective_email = None if user.get("role") == "admin" else user.get("sub")
    effective_role = role if user.get("role") == "admin" else user.get("role")
    return list_contact_preferences(db, role=effective_role, email=email or effective_email, limit=limit)


@app.post("/api/contact-preferences", response_model=ContactPreferenceResponse, status_code=status.HTTP_201_CREATED)
def post_contact_preferences(
    payload: ContactPreferenceCreate,
    credentials=Depends(bearer_scheme),
    db: Session = Depends(get_db),
):
    user = require_bearer_token(credentials)
    require_role(user, "clinic", "public_health", "admin")
    if user.get("role") != "admin":
        payload = ContactPreferenceCreate(
            **{
                **payload.model_dump(),
                "email": user.get("sub"),
                "role": user.get("role", payload.role),
                "name": user.get("name") or payload.name,
            }
        )
    return upsert_contact_preference(db, payload)


@app.get("/api/dashboard/home")
def get_home_dashboard(credentials=Depends(bearer_scheme), db: Session = Depends(get_db)):
    require_bearer_token(credentials)
    return build_home_dashboard(db)


@app.get("/api/dashboard/analytics")
def get_analytics_dashboard(credentials=Depends(bearer_scheme), db: Session = Depends(get_db)):
    user = require_bearer_token(credentials)
    require_role(user, "public_health", "admin")
    return build_analytics_dashboard(db)


@app.get("/api/dashboard/alerts")
def get_alerts_dashboard(credentials=Depends(bearer_scheme), db: Session = Depends(get_db)):
    require_bearer_token(credentials)
    return build_alerts_dashboard(db)


@app.get("/api/signals", response_model=list[SignalResponse])
def get_signals(
    disease: str | None = None,
    location: str | None = None,
    classification: str | None = None,
    source_type: str | None = None,
    min_confidence: float | None = None,
    limit: int = 100,
    credentials=Depends(bearer_scheme),
    db: Session = Depends(get_db),
):
    user = require_bearer_token(credentials)
    require_role(user, "public_health", "admin")
    return list_signals(
        db,
        disease=disease,
        location=location,
        classification=classification,
        source_type=source_type,
        min_confidence=min_confidence,
        limit=limit,
    )


@app.post("/api/signals", response_model=SignalResponse, status_code=status.HTTP_201_CREATED)
def post_signal(
    payload: SignalCreate,
    credentials=Depends(bearer_scheme),
    db: Session = Depends(get_db),
):
    user = require_bearer_token(credentials)
    require_role(user, "public_health", "admin")
    return create_signal(db, payload)


@app.get("/api/predictions", response_model=list[PredictionResponse])
def get_predictions(
    disease: str | None = None,
    location: str | None = None,
    risk_level: str | None = None,
    min_score: float | None = None,
    limit: int = 100,
    credentials=Depends(bearer_scheme),
    db: Session = Depends(get_db),
):
    user = require_bearer_token(credentials)
    require_role(user, "public_health", "admin")
    return list_predictions(
        db,
        disease=disease,
        location=location,
        risk_level=risk_level,
        min_score=min_score,
        limit=limit,
    )


@app.post("/api/predictions", response_model=PredictionResponse, status_code=status.HTTP_201_CREATED)
def post_prediction(
    payload: PredictionCreate,
    credentials=Depends(bearer_scheme),
    db: Session = Depends(get_db),
):
    user = require_bearer_token(credentials)
    require_role(user, "public_health", "admin")
    return create_prediction(db, payload)


@app.get("/api/alerts", response_model=list[AlertResponse])
def get_alerts(
    disease: str | None = None,
    location: str | None = None,
    level: str | None = None,
    limit: int = 100,
    credentials=Depends(bearer_scheme),
    db: Session = Depends(get_db),
):
    require_bearer_token(credentials)
    return list_alerts(db, disease=disease, location=location, level=level, limit=limit)


@app.post("/api/alerts", response_model=AlertResponse, status_code=status.HTTP_201_CREATED)
def post_alert(
    payload: AlertCreate,
    credentials=Depends(bearer_scheme),
    db: Session = Depends(get_db),
):
    require_bearer_token(credentials)
    return create_alert(db, payload)


@app.get("/api/recommendations", response_model=list[RecommendationResponse])
def get_recommendations(
    priority: str | None = None,
    category: str | None = None,
    location: str | None = None,
    limit: int = 100,
    credentials=Depends(bearer_scheme),
    db: Session = Depends(get_db),
):
    user = require_bearer_token(credentials)
    require_role(user, "clinic", "public_health", "admin")
    return list_recommendations(
        db,
        priority=priority,
        category=category,
        location=location,
        limit=limit,
    )


@app.post("/api/recommendations", response_model=RecommendationResponse, status_code=status.HTTP_201_CREATED)
def post_recommendation(
    payload: RecommendationCreate,
    credentials=Depends(bearer_scheme),
    db: Session = Depends(get_db),
):
    user = require_bearer_token(credentials)
    require_role(user, "public_health", "admin")
    return create_recommendation(db, payload)


@app.get("/api/clinic-reports", response_model=list[ClinicReportResponse])
def get_clinic_reports(
    disease: str | None = None,
    location: str | None = None,
    severity: str | None = None,
    limit: int = 100,
    credentials=Depends(bearer_scheme),
    db: Session = Depends(get_db),
):
    user = require_bearer_token(credentials)
    require_role(user, "public_health", "admin")
    return list_clinic_reports(
        db,
        disease=disease,
        location=location,
        severity=severity,
        limit=limit,
    )


@app.post("/api/clinic-reports", response_model=ClinicReportResponse, status_code=status.HTTP_201_CREATED)
def post_clinic_report(
    payload: ClinicReportCreate,
    credentials=Depends(bearer_scheme),
    db: Session = Depends(get_db),
):
    user = require_bearer_token(credentials)
    require_role(user, "clinic", "public_health", "admin")
    return create_clinic_report(db, payload)


@app.get("/api/symptom-reports", response_model=list[SymptomReportResponse])
def get_symptom_reports(
    disease: str | None = None,
    location: str | None = None,
    limit: int = 100,
    credentials=Depends(bearer_scheme),
    db: Session = Depends(get_db),
):
    user = require_bearer_token(credentials)
    require_role(user, "clinic", "public_health", "admin")
    return list_symptom_reports(db, disease=disease, location=location, limit=limit)


@app.post("/api/symptom-reports", response_model=SymptomReportResponse, status_code=status.HTTP_201_CREATED)
def post_symptom_report(
    payload: SymptomReportCreate,
    credentials=Depends(bearer_scheme),
    db: Session = Depends(get_db),
):
    user = require_bearer_token(credentials)
    require_role(user, "clinic", "public_health", "admin")
    return create_symptom_report(db, payload)


@app.put("/api/symptom-reports/{report_id}", response_model=SymptomReportResponse)
def put_symptom_report(
    report_id: int,
    payload: SymptomReportUpdate,
    credentials=Depends(bearer_scheme),
    db: Session = Depends(get_db),
):
    user = require_bearer_token(credentials)
    require_role(user, "clinic", "public_health", "admin")
    try:
        return update_symptom_report(
            db,
            report_id,
            payload,
            actor_role=user.role,
            actor_name=user.name,
        )
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc


@app.delete("/api/symptom-reports/{report_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_symptom_report(
    report_id: int,
    credentials=Depends(bearer_scheme),
    db: Session = Depends(get_db),
):
    user = require_bearer_token(credentials)
    require_role(user, "clinic", "public_health", "admin")
    try:
        delete_symptom_report(
            db,
            report_id,
            actor_role=user.role,
            actor_name=user.name,
        )
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc


@app.get("/api/weather-records", response_model=list[WeatherRecordResponse])
def get_weather_records(
    disease: str | None = None,
    location: str | None = None,
    limit: int = 100,
    credentials=Depends(bearer_scheme),
    db: Session = Depends(get_db),
):
    user = require_bearer_token(credentials)
    require_role(user, "public_health", "admin")
    return list_weather_records(db, disease=disease, location=location, limit=limit)


@app.post("/api/weather-records", response_model=WeatherRecordResponse, status_code=status.HTTP_201_CREATED)
def post_weather_record(
    payload: WeatherRecordCreate,
    credentials=Depends(bearer_scheme),
    db: Session = Depends(get_db),
):
    user = require_bearer_token(credentials)
    require_role(user, "public_health", "admin")
    return create_weather_record(db, payload)


@app.get("/api/news-records", response_model=list[NewsRecordResponse])
def get_news_records(
    disease: str | None = None,
    location: str | None = None,
    verification_status: str | None = None,
    limit: int = 100,
    credentials=Depends(bearer_scheme),
    db: Session = Depends(get_db),
):
    user = require_bearer_token(credentials)
    require_role(user, "public_health", "admin")
    return list_news_records(
        db,
        disease=disease,
        location=location,
        verification_status=verification_status,
        limit=limit,
    )


@app.post("/api/news-records", response_model=NewsRecordResponse, status_code=status.HTTP_201_CREATED)
def post_news_record(
    payload: NewsRecordCreate,
    credentials=Depends(bearer_scheme),
    db: Session = Depends(get_db),
):
    user = require_bearer_token(credentials)
    require_role(user, "public_health", "admin")
    return create_news_record(db, payload)


@app.get("/api/notifications", response_model=list[NotificationResponse])
def get_notifications(
    disease: str | None = None,
    location: str | None = None,
    channel: str | None = None,
    audience: str | None = None,
    limit: int = 100,
    credentials=Depends(bearer_scheme),
    db: Session = Depends(get_db),
):
    user = require_bearer_token(credentials)
    require_role(user, "public_health", "admin")
    return list_notifications(
        db,
        disease=disease,
        location=location,
        channel=channel,
        audience=audience,
        limit=limit,
    )


@app.post("/api/notifications", response_model=NotificationResponse, status_code=status.HTTP_201_CREATED)
def post_notification(
    payload: NotificationCreate,
    credentials=Depends(bearer_scheme),
    db: Session = Depends(get_db),
):
    user = require_bearer_token(credentials)
    require_role(user, "admin")
    return create_notification(db, payload)


@app.post("/api/notifications/generate", response_model=list[NotificationResponse], status_code=status.HTTP_201_CREATED)
def post_generate_notifications(
    payload: NotificationBatchRequest,
    credentials=Depends(bearer_scheme),
    db: Session = Depends(get_db),
):
    user = require_bearer_token(credentials)
    require_role(user, "public_health", "admin")
    result = generate_alert_notifications(db, payload)
    return result["notifications"]


@app.post("/api/notifications/send-email", response_model=EmailDispatchResponse, status_code=status.HTTP_201_CREATED)
def post_send_email_notifications(
    credentials=Depends(bearer_scheme),
    db: Session = Depends(get_db),
):
    user = require_bearer_token(credentials)
    require_role(user, "admin")
    return send_queued_email_notifications(db)


@app.post("/api/notifications/send-sms", response_model=SmsDispatchResponse, status_code=status.HTTP_201_CREATED)
def post_send_sms_notifications(
    credentials=Depends(bearer_scheme),
    db: Session = Depends(get_db),
):
    user = require_bearer_token(credentials)
    require_role(user, "admin")
    return send_queued_sms_notifications(db)


@app.post("/api/notifications/send-whatsapp", response_model=WhatsAppDispatchResponse, status_code=status.HTTP_201_CREATED)
def post_send_whatsapp_notifications(
    credentials=Depends(bearer_scheme),
    db: Session = Depends(get_db),
):
    user = require_bearer_token(credentials)
    require_role(user, "admin")
    return send_queued_whatsapp_notifications(db)


@app.get("/api/notifications/replies", response_model=list[NotificationReplyResponse])
def get_notification_replies(
    channel: str | None = None,
    command: str | None = None,
    location: str | None = None,
    limit: int = 100,
    credentials=Depends(bearer_scheme),
    db: Session = Depends(get_db),
):
    user = require_bearer_token(credentials)
    require_role(user, "public_health", "admin")
    return list_notification_replies(
        db,
        channel=channel,
        command=command,
        location=location,
        limit=limit,
    )


@app.post("/api/twilio/whatsapp/inbound")
async def post_twilio_whatsapp_inbound(
    request: Request,
    db: Session = Depends(get_db),
):
    raw_body = (await request.body()).decode("utf-8")
    form = parse_qs(raw_body)
    sender = (form.get("From", [""])[0] or "").strip()
    body = (form.get("Body", [""])[0] or "").strip()
    message_sid = form.get("MessageSid", [None])[0]
    profile_name = form.get("ProfileName", [None])[0]
    if not sender or not body:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Twilio inbound payload is missing From or Body.",
        )
    reply, response_text = record_whatsapp_reply(
        db,
        sender=sender,
        body=body,
        message_sid=str(message_sid) if message_sid else None,
        profile_name=str(profile_name) if profile_name else None,
    )
    twiml = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        f"<Response><Message>{response_text}</Message></Response>"
    )
    return Response(content=twiml, media_type="application/xml", headers={"X-ClinicAI-Reply-Id": str(reply.id)})


@app.post("/api/news-records/analyze", response_model=NewsAnalysisResponse)
def post_news_analysis(
    payload: NewsAnalysisRequest,
    credentials=Depends(bearer_scheme),
):
    user = require_bearer_token(credentials)
    require_role(user, "public_health", "admin")
    return analyze_news_submission(payload)


@app.post("/api/ingestion/news", response_model=IngestionRunResponse, status_code=status.HTTP_201_CREATED)
def post_news_ingestion(
    payload: NewsIngestionRequest,
    credentials=Depends(bearer_scheme),
    db: Session = Depends(get_db),
):
    user = require_bearer_token(credentials)
    require_role(user, "admin")
    return run_trusted_news_ingestion(db, payload)


@app.post("/api/ingestion/weather", response_model=IngestionRunResponse, status_code=status.HTTP_201_CREATED)
def post_weather_ingestion(
    payload: WeatherIngestionRequest,
    credentials=Depends(bearer_scheme),
    db: Session = Depends(get_db),
):
    user = require_bearer_token(credentials)
    require_role(user, "admin")
    return run_live_weather_ingestion(db, payload)


@app.post("/api/pipeline/run-analysis", response_model=PipelineRunResponse, status_code=status.HTTP_201_CREATED)
def post_pipeline_run(
    payload: PipelineRunRequest,
    credentials=Depends(bearer_scheme),
    db: Session = Depends(get_db),
):
    user = require_bearer_token(credentials)
    require_role(user, "public_health", "admin")
    return run_surveillance_pipeline(db, payload)


@app.get("/api/model/status", response_model=ModelStatusResponse)
def get_model_status_route(credentials=Depends(bearer_scheme)):
    user = require_bearer_token(credentials)
    require_role(user, "public_health", "admin")
    return get_model_status()


@app.post("/api/model/train", response_model=ModelStatusResponse, status_code=status.HTTP_201_CREATED)
def post_model_train(credentials=Depends(bearer_scheme), db: Session = Depends(get_db)):
    user = require_bearer_token(credentials)
    require_role(user, "admin")
    return train_operational_model(db)


@app.get("/api/dataset/status", response_model=DatasetStatusResponse)
def get_dataset_status_route(
    disease: str = "Lassa fever",
    credentials=Depends(bearer_scheme),
    db: Session = Depends(get_db),
):
    user = require_bearer_token(credentials)
    require_role(user, "public_health", "admin")
    return get_training_dataset_status(db, disease=disease)


@app.get("/api/dataset/reports", response_model=list[HistoricalReportSummaryResponse])
def get_dataset_reports_route(
    disease: str = "Lassa fever",
    credentials=Depends(bearer_scheme),
    db: Session = Depends(get_db),
):
    user = require_bearer_token(credentials)
    require_role(user, "public_health", "admin")
    return list_historical_reports(db, disease=disease)


@app.post("/api/dataset/run-auto", response_model=DatasetBatchRunResponse, status_code=status.HTTP_201_CREATED)
def post_dataset_run_auto_route(
    credentials=Depends(bearer_scheme),
    db: Session = Depends(get_db),
):
    user = require_bearer_token(credentials)
    require_role(user, "admin")
    return run_auto_historical_refresh(db)


@app.get("/api/model/history", response_model=list[TrainingRunResponse])
def get_model_history_route(
    disease: str = "Lassa fever",
    limit: int = 20,
    credentials=Depends(bearer_scheme),
    db: Session = Depends(get_db),
):
    user = require_bearer_token(credentials)
    require_role(user, "public_health", "admin")
    return list_training_runs(db, disease=disease, limit=limit)


@app.post("/api/reports/daily-summary", response_model=ReportResponse, status_code=status.HTTP_201_CREATED)
def post_daily_report_route(
    payload: ReportRequest,
    credentials=Depends(bearer_scheme),
    db: Session = Depends(get_db),
):
    user = require_bearer_token(credentials)
    require_role(user, "public_health", "admin")
    return generate_surveillance_report(db, payload)


@app.post("/api/automation/daily-cycle", status_code=status.HTTP_201_CREATED)
def post_automation_daily_cycle(
    x_clinicai_automation_key: str | None = Header(default=None),
    db: Session = Depends(get_db),
):
    if not settings.automation_secret:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Automation secret is not configured.",
        )
    if x_clinicai_automation_key != settings.automation_secret:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid automation key.",
        )
    return run_daily_surveillance_cycle(
        db,
        disease="Lassa fever",
        analyst="ClinicAI Sentinel Render Daily Automation",
    )
