from datetime import datetime

from sqlalchemy import DateTime, Float, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from .database import Base


class Signal(Base):
    __tablename__ = "signals"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String(255))
    disease: Mapped[str] = mapped_column(String(100), index=True)
    location: Mapped[str] = mapped_column(String(100), index=True)
    source_type: Mapped[str] = mapped_column(String(50))
    source_name: Mapped[str] = mapped_column(String(120))
    classification: Mapped[str] = mapped_column(String(20), index=True)
    confidence: Mapped[float] = mapped_column(Float)
    risk_factor: Mapped[str] = mapped_column(String(20))
    summary: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Prediction(Base):
    __tablename__ = "predictions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    disease: Mapped[str] = mapped_column(String(100), index=True)
    location: Mapped[str] = mapped_column(String(100), index=True)
    risk_level: Mapped[str] = mapped_column(String(20), index=True)
    risk_score: Mapped[float] = mapped_column(Float)
    model_name: Mapped[str] = mapped_column(String(120))
    driver_summary: Mapped[str] = mapped_column(Text)
    recommended_action: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Alert(Base):
    __tablename__ = "alerts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    disease: Mapped[str] = mapped_column(String(100), index=True)
    location: Mapped[str] = mapped_column(String(100), index=True)
    level: Mapped[str] = mapped_column(String(20), index=True)
    status: Mapped[str] = mapped_column(String(40))
    message: Mapped[str] = mapped_column(Text)
    action: Mapped[str] = mapped_column(Text)
    signal_count: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Recommendation(Base):
    __tablename__ = "recommendations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String(255))
    category: Mapped[str] = mapped_column(String(80), index=True)
    priority: Mapped[str] = mapped_column(String(20), index=True)
    location: Mapped[str | None] = mapped_column(String(100), nullable=True)
    description: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(40))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ClinicReport(Base):
    __tablename__ = "clinic_reports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    facility_name: Mapped[str] = mapped_column(String(150), index=True)
    location: Mapped[str] = mapped_column(String(100), index=True)
    disease: Mapped[str] = mapped_column(String(100), index=True)
    symptom_summary: Mapped[str] = mapped_column(Text)
    patient_count: Mapped[int] = mapped_column(Integer)
    severity: Mapped[str] = mapped_column(String(20), index=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    reported_by: Mapped[str] = mapped_column(String(120))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class SymptomReport(Base):
    __tablename__ = "symptom_reports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    facility_name: Mapped[str] = mapped_column(String(150), index=True)
    location: Mapped[str] = mapped_column(String(100), index=True)
    disease: Mapped[str] = mapped_column(String(100), index=True)
    report_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    fever_cases: Mapped[int] = mapped_column(Integer, default=0)
    headache_cases: Mapped[int] = mapped_column(Integer, default=0)
    vomiting_cases: Mapped[int] = mapped_column(Integer, default=0)
    weakness_cases: Mapped[int] = mapped_column(Integer, default=0)
    bleeding_cases: Mapped[int] = mapped_column(Integer, default=0)
    contact_history_cases: Mapped[int] = mapped_column(Integer, default=0)
    suspected_cases: Mapped[int] = mapped_column(Integer, default=0)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    reported_by: Mapped[str] = mapped_column(String(120))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class WeatherRecord(Base):
    __tablename__ = "weather_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    location: Mapped[str] = mapped_column(String(100), index=True)
    disease: Mapped[str] = mapped_column(String(100), index=True)
    source_name: Mapped[str] = mapped_column(String(120))
    temperature_c: Mapped[float] = mapped_column(Float)
    rainfall_mm: Mapped[float] = mapped_column(Float)
    humidity_pct: Mapped[float] = mapped_column(Float)
    dry_season_index: Mapped[float] = mapped_column(Float)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class NewsRecord(Base):
    __tablename__ = "news_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String(255))
    location: Mapped[str] = mapped_column(String(100), index=True)
    disease: Mapped[str] = mapped_column(String(100), index=True)
    source_name: Mapped[str] = mapped_column(String(120))
    verification_status: Mapped[str] = mapped_column(String(40), index=True)
    content: Mapped[str] = mapped_column(Text)
    published_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class HistoricalReport(Base):
    __tablename__ = "historical_reports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    disease: Mapped[str] = mapped_column(String(100), index=True)
    year: Mapped[int] = mapped_column(Integer, index=True)
    epi_week: Mapped[int] = mapped_column(Integer, index=True)
    week_start: Mapped[str] = mapped_column(String(40))
    week_end: Mapped[str] = mapped_column(String(40))
    source_name: Mapped[str] = mapped_column(String(150))
    source_path: Mapped[str] = mapped_column(String(500))
    suspected_current: Mapped[int] = mapped_column(Integer)
    confirmed_current: Mapped[int] = mapped_column(Integer)
    probable_current: Mapped[int] = mapped_column(Integer)
    deaths_current: Mapped[int] = mapped_column(Integer)
    cfr_current: Mapped[float] = mapped_column(Float)
    suspected_cumulative: Mapped[int] = mapped_column(Integer)
    confirmed_cumulative: Mapped[int] = mapped_column(Integer)
    probable_cumulative: Mapped[int] = mapped_column(Integer)
    deaths_cumulative: Mapped[int] = mapped_column(Integer)
    cfr_cumulative: Mapped[float] = mapped_column(Float)
    suspected_previous_year: Mapped[int] = mapped_column(Integer)
    confirmed_previous_year: Mapped[int] = mapped_column(Integer)
    probable_previous_year: Mapped[int] = mapped_column(Integer)
    deaths_previous_year: Mapped[int] = mapped_column(Integer)
    cfr_previous_year: Mapped[float] = mapped_column(Float)
    extracted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class HistoricalStateMetric(Base):
    __tablename__ = "historical_state_metrics"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    disease: Mapped[str] = mapped_column(String(100), index=True)
    year: Mapped[int] = mapped_column(Integer, index=True)
    epi_week: Mapped[int] = mapped_column(Integer, index=True)
    state: Mapped[str] = mapped_column(String(100), index=True)
    metric_scope: Mapped[str] = mapped_column(String(20), index=True)
    suspected_cases: Mapped[int | None] = mapped_column(Integer, nullable=True)
    confirmed_cases: Mapped[int | None] = mapped_column(Integer, nullable=True)
    deaths: Mapped[int | None] = mapped_column(Integer, nullable=True)
    cfr: Mapped[float | None] = mapped_column(Float, nullable=True)
    extraction_confidence: Mapped[str] = mapped_column(String(20))
    source_note: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class HistoricalWeatherMetric(Base):
    __tablename__ = "historical_weather_metrics"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    disease: Mapped[str] = mapped_column(String(100), index=True)
    year: Mapped[int] = mapped_column(Integer, index=True)
    epi_week: Mapped[int] = mapped_column(Integer, index=True)
    state: Mapped[str] = mapped_column(String(100), index=True)
    source_name: Mapped[str] = mapped_column(String(150))
    temperature_c: Mapped[float | None] = mapped_column(Float, nullable=True)
    rainfall_mm: Mapped[float | None] = mapped_column(Float, nullable=True)
    humidity_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    dry_season_index: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class HistoricalSymptomMetric(Base):
    __tablename__ = "historical_symptom_metrics"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    disease: Mapped[str] = mapped_column(String(100), index=True)
    year: Mapped[int] = mapped_column(Integer, index=True)
    epi_week: Mapped[int] = mapped_column(Integer, index=True)
    state: Mapped[str] = mapped_column(String(100), index=True)
    source_name: Mapped[str] = mapped_column(String(150))
    fever_cases: Mapped[int] = mapped_column(Integer, default=0)
    headache_cases: Mapped[int] = mapped_column(Integer, default=0)
    vomiting_cases: Mapped[int] = mapped_column(Integer, default=0)
    weakness_cases: Mapped[int] = mapped_column(Integer, default=0)
    bleeding_cases: Mapped[int] = mapped_column(Integer, default=0)
    rodent_contact_cases: Mapped[int] = mapped_column(Integer, default=0)
    suspected_cases: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class HistoricalNewsMetric(Base):
    __tablename__ = "historical_news_metrics"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    disease: Mapped[str] = mapped_column(String(100), index=True)
    year: Mapped[int] = mapped_column(Integer, index=True)
    epi_week: Mapped[int] = mapped_column(Integer, index=True)
    state: Mapped[str] = mapped_column(String(100), index=True)
    source_name: Mapped[str] = mapped_column(String(150))
    news_signal_count: Mapped[int] = mapped_column(Integer, default=0)
    high_severity_news_count: Mapped[int] = mapped_column(Integer, default=0)
    rodent_risk_mentions: Mapped[int] = mapped_column(Integer, default=0)
    outbreak_mentions: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class TrainingDatasetRow(Base):
    __tablename__ = "training_dataset_rows"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    disease: Mapped[str] = mapped_column(String(100), index=True)
    year: Mapped[int] = mapped_column(Integer, index=True)
    epi_week: Mapped[int] = mapped_column(Integer, index=True)
    state: Mapped[str] = mapped_column(String(100), index=True)
    temperature_c: Mapped[float | None] = mapped_column(Float, nullable=True)
    rainfall_mm: Mapped[float | None] = mapped_column(Float, nullable=True)
    humidity_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    dry_season_index: Mapped[float | None] = mapped_column(Float, nullable=True)
    fever_cases: Mapped[int] = mapped_column(Integer, default=0)
    vomiting_cases: Mapped[int] = mapped_column(Integer, default=0)
    bleeding_cases: Mapped[int] = mapped_column(Integer, default=0)
    rodent_contact_cases: Mapped[int] = mapped_column(Integer, default=0)
    news_signal_count: Mapped[int] = mapped_column(Integer, default=0)
    high_severity_news_count: Mapped[int] = mapped_column(Integer, default=0)
    confirmed_cases_label: Mapped[int | None] = mapped_column(Integer, nullable=True)
    deaths_label: Mapped[int | None] = mapped_column(Integer, nullable=True)
    cfr_label: Mapped[float | None] = mapped_column(Float, nullable=True)
    risk_score_label: Mapped[float | None] = mapped_column(Float, nullable=True)
    risk_level_label: Mapped[str | None] = mapped_column(String(20), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class TrainingRun(Base):
    __tablename__ = "training_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    disease: Mapped[str] = mapped_column(String(100), index=True)
    model_name: Mapped[str] = mapped_column(String(150))
    trigger_source: Mapped[str] = mapped_column(String(50), index=True)
    sample_count: Mapped[int] = mapped_column(Integer)
    accuracy: Mapped[float | None] = mapped_column(Float, nullable=True)
    mae: Mapped[float | None] = mapped_column(Float, nullable=True)
    historical_reports: Mapped[int] = mapped_column(Integer, default=0)
    training_rows: Mapped[int] = mapped_column(Integer, default=0)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Notification(Base):
    __tablename__ = "notifications"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    disease: Mapped[str] = mapped_column(String(100), index=True)
    location: Mapped[str] = mapped_column(String(100), index=True)
    channel: Mapped[str] = mapped_column(String(30), index=True)
    audience: Mapped[str] = mapped_column(String(40), index=True)
    priority: Mapped[str] = mapped_column(String(20), index=True)
    status: Mapped[str] = mapped_column(String(30), index=True)
    title: Mapped[str] = mapped_column(String(255))
    message: Mapped[str] = mapped_column(Text)
    recipient: Mapped[str | None] = mapped_column(String(150), nullable=True)
    source_alert_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    source_prediction_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ContactPreference(Base):
    __tablename__ = "contact_preferences"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(120))
    email: Mapped[str] = mapped_column(String(150), index=True)
    role: Mapped[str] = mapped_column(String(40), index=True)
    location: Mapped[str | None] = mapped_column(String(100), nullable=True)
    sms_number: Mapped[str | None] = mapped_column(String(40), nullable=True)
    whatsapp_number: Mapped[str | None] = mapped_column(String(40), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class NotificationReply(Base):
    __tablename__ = "notification_replies"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    channel: Mapped[str] = mapped_column(String(30), index=True)
    sender: Mapped[str] = mapped_column(String(150), index=True)
    audience: Mapped[str] = mapped_column(String(40), index=True)
    body: Mapped[str] = mapped_column(Text)
    command: Mapped[str] = mapped_column(String(40), index=True)
    status: Mapped[str] = mapped_column(String(40), index=True)
    location: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    related_notification_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    provider_message_sid: Mapped[str | None] = mapped_column(String(120), nullable=True)
    profile_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
