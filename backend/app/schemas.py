from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class GoogleTokenRequest(BaseModel):
    credential: str


class UserResponse(BaseModel):
    name: str
    email: str
    image_url: str | None = None
    role: str


class SessionResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


class SignalResponse(BaseModel):
    id: int
    title: str
    disease: str
    location: str
    source_type: str
    source_name: str
    classification: str
    confidence: float
    risk_factor: str
    summary: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SignalCreate(BaseModel):
    title: str = Field(min_length=5, max_length=255)
    disease: str = Field(min_length=2, max_length=100)
    location: str = Field(min_length=2, max_length=100)
    source_type: str = Field(min_length=2, max_length=50)
    source_name: str = Field(min_length=2, max_length=120)
    classification: str = Field(pattern="^(Red|Amber|Green)$")
    confidence: float = Field(ge=0, le=1)
    risk_factor: str = Field(pattern="^(LOW|MEDIUM|HIGH)$")
    summary: str = Field(min_length=8)


class PredictionResponse(BaseModel):
    id: int
    disease: str
    location: str
    risk_level: str
    risk_score: float
    model_name: str
    driver_summary: str
    recommended_action: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PredictionCreate(BaseModel):
    disease: str = Field(min_length=2, max_length=100)
    location: str = Field(min_length=2, max_length=100)
    risk_level: str = Field(pattern="^(Low|Medium|High)$")
    risk_score: float = Field(ge=0, le=1)
    model_name: str = Field(min_length=2, max_length=120)
    driver_summary: str = Field(min_length=8)
    recommended_action: str = Field(min_length=8)


class AlertResponse(BaseModel):
    id: int
    disease: str
    location: str
    level: str
    status: str
    message: str
    action: str
    signal_count: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AlertCreate(BaseModel):
    disease: str = Field(min_length=2, max_length=100)
    location: str = Field(min_length=2, max_length=100)
    level: str = Field(pattern="^(Red|Amber|Green)$")
    status: str = Field(min_length=2, max_length=40)
    message: str = Field(min_length=8)
    action: str = Field(min_length=8)
    signal_count: int = Field(ge=0)


class RecommendationResponse(BaseModel):
    id: int
    title: str
    category: str
    priority: str
    location: str | None = None
    description: str
    status: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class RecommendationCreate(BaseModel):
    title: str = Field(min_length=5, max_length=255)
    category: str = Field(min_length=2, max_length=80)
    priority: str = Field(pattern="^(High|Medium|Low)$")
    location: str | None = Field(default=None, max_length=100)
    description: str = Field(min_length=8)
    status: str = Field(min_length=2, max_length=40)


class ClinicReportResponse(BaseModel):
    id: int
    facility_name: str
    location: str
    disease: str
    symptom_summary: str
    patient_count: int
    severity: str
    notes: str | None = None
    reported_by: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ClinicReportCreate(BaseModel):
    facility_name: str = Field(min_length=3, max_length=150)
    location: str = Field(min_length=2, max_length=100)
    disease: str = Field(min_length=2, max_length=100)
    symptom_summary: str = Field(min_length=8)
    patient_count: int = Field(ge=1)
    severity: str = Field(pattern="^(Low|Medium|High)$")
    notes: str | None = None
    reported_by: str = Field(min_length=3, max_length=120)


class SymptomReportResponse(BaseModel):
    id: int
    facility_name: str
    location: str
    disease: str
    report_date: datetime
    fever_cases: int
    headache_cases: int
    vomiting_cases: int
    weakness_cases: int
    bleeding_cases: int
    contact_history_cases: int
    suspected_cases: int
    notes: str | None = None
    reported_by: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SymptomReportCreate(BaseModel):
    facility_name: str = Field(min_length=3, max_length=150)
    location: str = Field(min_length=2, max_length=100)
    disease: str = Field(min_length=2, max_length=100)
    report_date: datetime
    fever_cases: int = Field(ge=0)
    headache_cases: int = Field(ge=0)
    vomiting_cases: int = Field(ge=0)
    weakness_cases: int = Field(ge=0)
    bleeding_cases: int = Field(ge=0)
    contact_history_cases: int = Field(ge=0)
    suspected_cases: int = Field(ge=0)
    notes: str | None = None
    reported_by: str = Field(min_length=3, max_length=120)


class WeatherRecordResponse(BaseModel):
    id: int
    location: str
    disease: str
    source_name: str
    temperature_c: float
    rainfall_mm: float
    humidity_pct: float
    dry_season_index: float
    recorded_at: datetime
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class WeatherRecordCreate(BaseModel):
    location: str = Field(min_length=2, max_length=100)
    disease: str = Field(min_length=2, max_length=100)
    source_name: str = Field(min_length=2, max_length=120)
    temperature_c: float = Field(ge=-10, le=60)
    rainfall_mm: float = Field(ge=0, le=1000)
    humidity_pct: float = Field(ge=0, le=100)
    dry_season_index: float = Field(ge=0, le=1)
    recorded_at: datetime


class NewsRecordResponse(BaseModel):
    id: int
    title: str
    location: str
    disease: str
    source_name: str
    verification_status: str
    content: str
    published_at: datetime
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class NewsRecordCreate(BaseModel):
    title: str = Field(min_length=5, max_length=255)
    location: str = Field(min_length=2, max_length=100)
    disease: str = Field(min_length=2, max_length=100)
    source_name: str = Field(min_length=2, max_length=120)
    verification_status: str = Field(pattern="^(Verified|Review|Unverified)$")
    content: str = Field(min_length=20)
    published_at: datetime


class NewsAnalysisRequest(BaseModel):
    title: str = Field(min_length=5, max_length=255)
    location: str = Field(min_length=2, max_length=100)
    disease: str = Field(min_length=2, max_length=100)
    source_name: str = Field(min_length=2, max_length=120)
    verification_status: str = Field(pattern="^(Verified|Review|Unverified)$")
    content: str = Field(min_length=20)


class NewsAnalysisResponse(BaseModel):
    location: str
    disease: str
    source_trust: str
    matched_locations: list[str]
    matched_terms: list[str]
    signal_type: str
    classification: str
    risk_factor: str
    confidence: float
    summary: str
    signal_title: str
    should_generate_signal: bool


class NewsIngestionRequest(BaseModel):
    disease: str = Field(default="Lassa fever", min_length=2, max_length=100)
    max_items_per_source: int = Field(default=2, ge=1, le=10)
    auto_create_signals: bool = True


class WeatherIngestionRequest(BaseModel):
    disease: str = Field(default="Lassa fever", min_length=2, max_length=100)
    locations: list[str] = Field(default_factory=list)


class IngestionRunResponse(BaseModel):
    mode: str
    disease: str
    records_created: int
    errors: list[str]
    fetched_items: int | None = None
    signals_created: int | None = None
    sources_checked: list[str] | None = None
    locations_processed: list[str] | None = None


class ReportRequest(BaseModel):
    disease: str = Field(default="Lassa fever", min_length=2, max_length=100)
    analyst: str = Field(default="ClinicAI Sentinel Report Bot", min_length=3, max_length=120)


class ReportResponse(BaseModel):
    disease: str
    generated_at: str
    analyst: str
    report_path: str
    markdown_report_path: str
    html_report_path: str
    pdf_report_path: str
    report_title: str
    high_risk_locations: list[str]
    alert_count: int
    prediction_count: int
    content: str


class NotificationResponse(BaseModel):
    id: int
    disease: str
    location: str
    channel: str
    audience: str
    priority: str
    status: str
    title: str
    message: str
    recipient: str | None = None
    source_alert_id: int | None = None
    source_prediction_id: int | None = None
    created_at: datetime

    class Config:
        from_attributes = True


class NotificationCreate(BaseModel):
    disease: str = Field(min_length=2, max_length=100)
    location: str = Field(min_length=2, max_length=100)
    channel: str = Field(pattern="^(Email|SMS|WhatsApp|Dashboard)$")
    audience: str = Field(min_length=3, max_length=40)
    priority: str = Field(pattern="^(High|Medium|Low)$")
    status: str = Field(default="Queued", min_length=3, max_length=30)
    title: str = Field(min_length=5, max_length=255)
    message: str = Field(min_length=10)
    recipient: str | None = Field(default=None, max_length=150)
    source_alert_id: int | None = None
    source_prediction_id: int | None = None


class NotificationBatchRequest(BaseModel):
    disease: str = Field(default="Lassa fever", min_length=2, max_length=100)
    audience: str = Field(default="Public health", min_length=3, max_length=40)
    recipient_email: str | None = Field(default=None, max_length=150)
    recipient_sms: str | None = Field(default=None, max_length=150)
    recipient_whatsapp: str | None = Field(default=None, max_length=150)


class EmailDispatchResponse(BaseModel):
    processed: int
    sent: int
    failed: int
    mode: str
    outbox_paths: list[str] = Field(default_factory=list)


class SmsDispatchResponse(BaseModel):
    processed: int
    sent: int
    failed: int
    mode: str
    outbox_paths: list[str] = Field(default_factory=list)


class WhatsAppDispatchResponse(BaseModel):
    processed: int
    sent: int
    failed: int
    mode: str
    outbox_paths: list[str] = Field(default_factory=list)


class PipelineRunRequest(BaseModel):
    disease: str = Field(min_length=2, max_length=100)
    location: str = Field(min_length=2, max_length=100)
    analyst: str = Field(min_length=3, max_length=120)


class PipelineRunResponse(BaseModel):
    prediction: PredictionResponse
    alert: AlertResponse
    recommendations: list[RecommendationResponse]
    generated_signal: SignalResponse | None = None
    summary: str


class ModelStatusResponse(BaseModel):
    ready: bool
    model_name: str | None = None
    sample_count: int = 0
    generated_at: str | None = None
    accuracy: float | None = None
    mae: float | None = None
    artifact_path: str | None = None


class DatasetStatusResponse(BaseModel):
    disease: str
    historical_reports: int
    historical_state_metrics: int
    historical_weather_metrics: int
    historical_symptom_metrics: int
    historical_news_metrics: int
    training_rows: int
    covered_weeks: list[str]


class HistoricalReportSummaryResponse(BaseModel):
    year: int
    epi_week: int
    week_start: str
    week_end: str
    confirmed_current: int
    confirmed_cumulative: int
    deaths_cumulative: int
    cfr_cumulative: float
    source_name: str

    model_config = ConfigDict(from_attributes=True)


class DatasetBatchRunResponse(BaseModel):
    manifest: str
    reports_loaded: int
    weather_rows_loaded: int
    symptom_rows_loaded: int
    news_rows_loaded: int
    training_rows: int
    training_output_csv: str
    model_artifact_path: str
    model_accuracy: float
    model_mae: float


class TrainingRunResponse(BaseModel):
    id: int
    disease: str
    model_name: str
    trigger_source: str
    sample_count: int
    accuracy: float | None = None
    mae: float | None = None
    historical_reports: int
    training_rows: int
    notes: str | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
