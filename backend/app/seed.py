from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from .models import (
    Alert,
    ClinicReport,
    NewsRecord,
    Prediction,
    Recommendation,
    Signal,
    SymptomReport,
    WeatherRecord,
)


SEED_SIGNALS = [
    {
        "title": "Spike in local reports tied to rodent exposure in Ondo",
        "disease": "Lassa fever",
        "location": "Ondo",
        "source_type": "News crawl",
        "source_name": "Verified national news",
        "classification": "Red",
        "confidence": 0.88,
        "risk_factor": "HIGH",
        "summary": "Verified reporting shows heightened rodent exposure concerns and possible case-linked discussion.",
    },
    {
        "title": "Community conversation shows increased symptom concern in Edo",
        "disease": "Lassa fever",
        "location": "Edo",
        "source_type": "Social signal",
        "source_name": "Community monitoring",
        "classification": "Amber",
        "confidence": 0.72,
        "risk_factor": "MEDIUM",
        "summary": "NLP pipeline flagged repeated symptom-related discussion requiring human verification.",
    },
    {
        "title": "Clinician-focused article mentions suspected Lassa admissions in Ebonyi",
        "disease": "Lassa fever",
        "location": "Ebonyi",
        "source_type": "Medical reporting",
        "source_name": "Verified clinical digest",
        "classification": "Red",
        "confidence": 0.91,
        "risk_factor": "HIGH",
        "summary": "Trusted health reporting mentions suspected admissions and recommends closer surveillance.",
    },
    {
        "title": "Water contamination discussions rising in Bauchi",
        "disease": "Cholera",
        "location": "Bauchi",
        "source_type": "News crawl",
        "source_name": "Regional press",
        "classification": "Amber",
        "confidence": 0.67,
        "risk_factor": "MEDIUM",
        "summary": "Environmental conditions and water safety concerns suggest increased cholera watch requirements.",
    },
]

SEED_PREDICTIONS = [
    {
        "disease": "Lassa fever",
        "location": "Ondo",
        "risk_level": "High",
        "risk_score": 0.78,
        "model_name": "Gradient Boosting Baseline",
        "driver_summary": "High-risk pattern from NCDC history, weather dryness, and high-confidence text signals.",
        "recommended_action": "Increase screening, reinforce isolation readiness, and intensify monitoring.",
    },
    {
        "disease": "Cholera",
        "location": "Bauchi",
        "risk_level": "Medium",
        "risk_score": 0.44,
        "model_name": "Gradient Boosting Baseline",
        "driver_summary": "Moderate environmental and text-signal evidence indicates need for verification.",
        "recommended_action": "Review water-related reports and intensify field verification.",
    },
    {
        "disease": "Mpox",
        "location": "Lagos",
        "risk_level": "Low",
        "risk_score": 0.32,
        "model_name": "Random Forest Baseline",
        "driver_summary": "Low-volume discussion with limited multi-source confirmation.",
        "recommended_action": "Continue routine monitoring and include in scheduled reports.",
    },
    {
        "disease": "Meningitis",
        "location": "Sokoto",
        "risk_level": "Low",
        "risk_score": 0.26,
        "model_name": "Random Forest Baseline",
        "driver_summary": "Low activity with no sustained cluster pattern detected.",
        "recommended_action": "Maintain background surveillance.",
    },
]

SEED_ALERTS = [
    {
        "disease": "Lassa fever",
        "location": "Ondo",
        "level": "Red",
        "status": "Urgent",
        "message": "High Lassa fever risk in Ondo region.",
        "action": "Escalate screening and prepare isolation units.",
        "signal_count": 312,
    },
    {
        "disease": "Lassa fever",
        "location": "Edo",
        "level": "Red",
        "status": "Urgent",
        "message": "Escalating symptom and rodent-related signals in Edo.",
        "action": "Increase surveillance review and community messaging.",
        "signal_count": 241,
    },
    {
        "disease": "Lassa fever",
        "location": "Ebonyi",
        "level": "Red",
        "status": "Urgent",
        "message": "Suspected admissions and trusted clinical reporting indicate high concern.",
        "action": "Prepare clinic isolation workflow and notify coordinators.",
        "signal_count": 219,
    },
    {
        "disease": "Cholera",
        "location": "Bauchi",
        "level": "Amber",
        "status": "Review",
        "message": "Moderate cholera risk signals require field validation.",
        "action": "Verify sources and monitor water-related reports.",
        "signal_count": 94,
    },
    {
        "disease": "Mpox",
        "location": "Lagos",
        "level": "Green",
        "status": "Stable",
        "message": "Low mpox activity at present.",
        "action": "Continue routine monitoring.",
        "signal_count": 35,
    },
    {
        "disease": "Meningitis",
        "location": "Sokoto",
        "level": "Green",
        "status": "Watch",
        "message": "Low meningitis activity with no sustained cluster.",
        "action": "Keep within periodic reports.",
        "signal_count": 22,
    },
]

SEED_RECOMMENDATIONS = [
    {
        "title": "Increase Lassa screening in Ondo clinics",
        "category": "Screening",
        "priority": "High",
        "location": "Ondo",
        "description": "Increase triage attention to fever, weakness, and bleeding symptoms in high-risk facilities.",
        "status": "High priority",
    },
    {
        "title": "Monitor hemorrhagic symptom clusters in Edo",
        "category": "Monitoring",
        "priority": "Medium",
        "location": "Edo",
        "description": "Escalate review of symptom clusters and compare with recent community and clinic reports.",
        "status": "Review today",
    },
    {
        "title": "Prepare isolation workflow in Ebonyi",
        "category": "Preparedness",
        "priority": "Medium",
        "location": "Ebonyi",
        "description": "Confirm staff readiness, room availability, and isolation protocols for suspected cases.",
        "status": "Operational",
    },
]

SEED_CLINIC_REPORTS = [
    {
        "facility_name": "Akure General Hospital",
        "location": "Ondo",
        "disease": "Lassa fever",
        "symptom_summary": "Increased fever, weakness, and bleeding symptom watch among suspected cases.",
        "patient_count": 7,
        "severity": "High",
        "notes": "Requires escalation to regional review team.",
        "reported_by": "Triage lead",
    },
    {
        "facility_name": "Benin City Primary Care Hub",
        "location": "Edo",
        "disease": "Lassa fever",
        "symptom_summary": "Symptom cluster with persistent fever and sore throat under review.",
        "patient_count": 4,
        "severity": "Medium",
        "notes": "Awaiting laboratory-linked verification.",
        "reported_by": "Surveillance nurse",
    },
]

SEED_SYMPTOM_REPORTS = [
    {
        "facility_name": "Akure General Hospital",
        "location": "Ondo",
        "disease": "Lassa fever",
        "report_date": datetime.now(timezone.utc) - timedelta(hours=12),
        "fever_cases": 10,
        "headache_cases": 7,
        "vomiting_cases": 4,
        "weakness_cases": 6,
        "bleeding_cases": 2,
        "contact_history_cases": 3,
        "suspected_cases": 5,
        "notes": "Cluster under review by triage team.",
        "reported_by": "Triage lead",
    },
    {
        "facility_name": "Benin City Primary Care Hub",
        "location": "Edo",
        "disease": "Lassa fever",
        "report_date": datetime.now(timezone.utc) - timedelta(hours=8),
        "fever_cases": 8,
        "headache_cases": 6,
        "vomiting_cases": 3,
        "weakness_cases": 5,
        "bleeding_cases": 1,
        "contact_history_cases": 2,
        "suspected_cases": 4,
        "notes": "Possible community exposure trend.",
        "reported_by": "Surveillance nurse",
    },
]

SEED_WEATHER_RECORDS = [
    {
        "location": "Ondo",
        "disease": "Lassa fever",
        "source_name": "NiMet feed",
        "temperature_c": 34.0,
        "rainfall_mm": 12.0,
        "humidity_pct": 49.0,
        "dry_season_index": 0.82,
        "recorded_at": datetime.now(timezone.utc) - timedelta(hours=4),
    },
    {
        "location": "Edo",
        "disease": "Lassa fever",
        "source_name": "NiMet feed",
        "temperature_c": 33.0,
        "rainfall_mm": 16.0,
        "humidity_pct": 52.0,
        "dry_season_index": 0.76,
        "recorded_at": datetime.now(timezone.utc) - timedelta(hours=4),
    },
]

SEED_NEWS_RECORDS = [
    {
        "title": "Rodent infestation concerns rise in Ondo communities",
        "location": "Ondo",
        "disease": "Lassa fever",
        "source_name": "Trusted Health Desk",
        "verification_status": "Verified",
        "content": "Residents and health workers reported growing rodent infestation, repeated fever complaints, and suspected Lassa fever concern across affected communities.",
        "published_at": datetime.now(timezone.utc) - timedelta(hours=6),
    },
    {
        "title": "Clinics in Edo review suspected fever clusters",
        "location": "Edo",
        "disease": "Lassa fever",
        "source_name": "Regional Clinical Digest",
        "verification_status": "Verified",
        "content": "Clinics in Edo are monitoring suspected fever clusters with weakness and possible exposure history while authorities review the reports.",
        "published_at": datetime.now(timezone.utc) - timedelta(hours=5),
    },
]


def seed_database(db: Session) -> None:
    if not db.query(Signal).first():
        db.add_all([Signal(**payload) for payload in SEED_SIGNALS])
    if not db.query(Prediction).first():
        db.add_all([Prediction(**payload) for payload in SEED_PREDICTIONS])
    if not db.query(Alert).first():
        db.add_all([Alert(**payload) for payload in SEED_ALERTS])
    if not db.query(Recommendation).first():
        db.add_all([Recommendation(**payload) for payload in SEED_RECOMMENDATIONS])
    if not db.query(ClinicReport).first():
        db.add_all([ClinicReport(**payload) for payload in SEED_CLINIC_REPORTS])
    if not db.query(SymptomReport).first():
        db.add_all([SymptomReport(**payload) for payload in SEED_SYMPTOM_REPORTS])
    if not db.query(WeatherRecord).first():
        db.add_all([WeatherRecord(**payload) for payload in SEED_WEATHER_RECORDS])
    if not db.query(NewsRecord).first():
        db.add_all([NewsRecord(**payload) for payload in SEED_NEWS_RECORDS])
    db.commit()
