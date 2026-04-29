HOME_DATA = {
    "product": {
        "name": "ClinicAI Sentinel",
        "tagline": "AI-powered Lassa fever early warning and decision support",
        "summary": (
            "ClinicAI Sentinel integrates epidemiological, environmental, symptom, and "
            "real-time text signals to predict Lassa fever risk and provide actionable "
            "guidance for healthcare teams in Nigeria."
        ),
    },
    "hero": {
        "tag": "Priority disease watch: Lassa fever",
        "title": "Detect outbreaks earlier and guide clinics with confidence.",
        "description": (
            "ClinicAI Sentinel is designed for healthcare providers, public-health analysts, "
            "and outbreak response teams. It combines historical NCDC data, weather patterns, "
            "symptom reports, and verified text intelligence to generate real-time Lassa fever "
            "risk predictions and practical next-step recommendations."
        ),
        "metrics": [
            {
                "value": "78%",
                "label": "Lassa outbreak probability this week",
                "tone": "red",
                "status": "Escalating",
            },
            {
                "value": "2,431",
                "label": "Signals ingested in the last 24 hours",
                "tone": "green",
                "status": "Model live",
            },
            {
                "value": "11",
                "label": "States with notable disease activity",
                "tone": "amber",
                "status": "Review spread",
            },
        ],
    },
    "why_cards": [
        {
            "title": "Real problem",
            "copy": "Lassa fever outbreaks are often detected late and poorly monitored at community level.",
        },
        {
            "title": "Practical output",
            "copy": "Clinics receive risk levels, alerts, and concrete response recommendations.",
        },
        {
            "title": "Winning edge",
            "copy": "The platform goes beyond prediction into decision support for real clinic use.",
        },
    ],
    "layers": [
        {
            "title": "1. Data collection",
            "copy": "NCDC historical data, weather feeds, symptom reports, and verified news sources.",
        },
        {
            "title": "2. Data processing",
            "copy": "Cleaning, normalization, noise removal, and feature preparation for model use.",
        },
        {
            "title": "3. NLP engine",
            "copy": "Unstructured text is converted into structured outbreak signals and risk factors.",
        },
        {
            "title": "4. Machine learning",
            "copy": "Historical outbreak, weather, and symptom patterns are used to predict current risk.",
        },
        {
            "title": "5. Action layer",
            "copy": "The system sends alerts and clinic-ready recommendations instead of raw scores alone.",
        },
    ],
    "data_sources": [
        {"title": "Historical outbreak data", "copy": "NCDC-confirmed case patterns for model training and trend reference."},
        {"title": "Weather intelligence", "copy": "Past and current environmental signals that may affect outbreak conditions."},
        {"title": "Clinic symptom reports", "copy": "Frontline symptom observations for community-level early warning."},
        {"title": "Verified news and text signals", "copy": "Trusted reporting processed by NLP to extract outbreak indicators."},
    ],
    "actions": [
        {"title": "Increase Lassa screening in Ondo clinics", "tone": "red", "status": "High priority"},
        {"title": "Monitor hemorrhagic symptom clusters in Edo", "tone": "amber", "status": "Review today"},
        {"title": "Prepare isolation workflow in Ebonyi", "tone": "green", "status": "Operational"},
    ],
    "feed": [
        {
            "title": "Spike in local reports tied to rodent exposure in Ondo",
            "tags": [
                {"label": "Lassa fever", "tone": "red"},
                {"label": "News crawl", "tone": "amber"},
                {"label": "Confidence 0.88", "tone": "green"},
            ],
        },
        {
            "title": "Community conversation shows increased symptom concern in Edo",
            "tags": [
                {"label": "Social signal", "tone": "red"},
                {"label": "Needs verification", "tone": "amber"},
                {"label": "Confidence 0.72", "tone": "green"},
            ],
        },
        {
            "title": "Clinician-focused article mentions suspected Lassa admissions in Ebonyi",
            "tags": [
                {"label": "Medical reporting", "tone": "red"},
                {"label": "Escalate", "tone": "amber"},
                {"label": "Confidence 0.91", "tone": "green"},
            ],
        },
    ],
    "priority_states": [
        {"state": "Ondo", "disease": "Lassa fever", "alert": "Red", "signals": 312},
        {"state": "Edo", "disease": "Lassa fever", "alert": "Red", "signals": 241},
        {"state": "Ebonyi", "disease": "Lassa fever", "alert": "Red", "signals": 219},
        {"state": "Bauchi", "disease": "Cholera", "alert": "Amber", "signals": 94},
    ],
    "impact_points": [
        "Enables earlier detection of high-risk Lassa fever activity.",
        "Improves clinic preparedness with recommendations, not just dashboards.",
        "Reduces response time in vulnerable communities.",
        "Creates a reusable architecture for more diseases later.",
    ],
    "differentiators": [
        "Multi-source data integration across epidemiological, weather, symptom, and text inputs.",
        "NLP engine for real-world signals from verified news and field language.",
        "Real-time prediction layer trained on historical outbreak evidence.",
        "Actionable decision support as the main product outcome.",
    ],
}

ANALYTICS_DATA = {
    "summary_metrics": [
        {
            "value": "78%",
            "label": "Predicted outbreak likelihood for Lassa fever",
        },
        {
            "value": "0.86",
            "label": "Average confidence across classified high-risk signals",
        },
        {
            "value": "1,248",
            "label": "Signals classified this week",
        },
    ],
    "disease_probabilities": [
        {"label": "Lassa fever", "value": 78},
        {"label": "Cholera", "value": 44},
        {"label": "Mpox", "value": 32},
        {"label": "Meningitis", "value": 26},
    ],
    "classified_signals": [
        {"source": "National news article", "location": "Ondo", "level": "Red", "confidence": "0.92"},
        {"source": "Social mention cluster", "location": "Edo", "level": "Amber", "confidence": "0.74"},
        {"source": "Health-report digest", "location": "Ebonyi", "level": "Red", "confidence": "0.89"},
        {"source": "Forum chatter", "location": "Kogi", "level": "Green", "confidence": "0.51"},
    ],
    "model_stack": [
        {"title": "Backend", "copy": "Python service layer for data ingestion, prediction, and recommendation delivery."},
        {"title": "ML baseline", "copy": "Random Forest or Gradient Boosting for risk scoring from structured outbreak signals."},
        {"title": "NLP baseline", "copy": "TF-IDF plus Logistic Regression for fast text signal classification before transformer upgrades."},
        {"title": "Realtime inputs", "copy": "Current weather, symptom reports, and NLP outputs flow into the prediction stage."},
    ],
    "recommendations": [
        {"title": "High risk in Ondo region", "copy": "Increase screening for fever and bleeding symptoms in triage."},
        {"title": "Edo rodent-related reports rising", "copy": "Push local surveillance review and community risk communication."},
        {"title": "Ebonyi confidence above threshold", "copy": "Prepare isolation units and brief response coordinators."},
    ],
    "demo_scenario": {
        "title": "Demo scenario",
        "copy": (
            "In a simulated Edo State case, the system combined dry weather, increased rodent-related reports, "
            "and symptom patterns to flag a high-risk Lassa signal before confirmed escalation."
        ),
    },
}

ALERTS_DATA = {
    "diseases": [
        {
            "tone": "red",
            "alert": "Red alert",
            "name": "Lassa fever",
            "copy": "Highest concern based on current Nigerian source activity and model confidence.",
            "status": "Urgent",
            "probability": "78%",
            "weekly_signals": "772",
            "states": "3",
            "primary_states": "Ondo, Edo, Ebonyi",
            "cue": "Escalate analyst review",
        },
        {
            "tone": "amber",
            "alert": "Amber alert",
            "name": "Cholera",
            "copy": "Signals are growing in a few states but evidence remains mixed and needs further validation.",
            "status": "Review",
            "probability": "44%",
            "weekly_signals": "291",
            "states": "2",
            "primary_states": "Bauchi, Kano",
            "cue": "Watch and verify sources",
        },
        {
            "tone": "green",
            "alert": "Green alert",
            "name": "Mpox",
            "copy": "Signals are currently low and mostly classified as informational rather than outbreak-related.",
            "status": "Stable",
            "probability": "32%",
            "weekly_signals": "124",
            "states": "0",
            "primary_states": "Lagos, FCT",
            "cue": "Routine monitoring only",
        },
        {
            "tone": "green",
            "alert": "Green alert",
            "name": "Meningitis",
            "copy": "Low-velocity discussion and no sustained multi-source spike in the latest model cycle.",
            "status": "Watch",
            "probability": "26%",
            "weekly_signals": "89",
            "states": "1",
            "primary_states": "Sokoto",
            "cue": "Keep in scheduled reports",
        },
    ],
    "table": [
        {"disease": "Lassa fever", "level": "Red", "states": "Ondo, Edo, Ebonyi", "action": "Escalate"},
        {"disease": "Cholera", "level": "Amber", "states": "Bauchi, Kano", "action": "Review"},
        {"disease": "Mpox", "level": "Green", "states": "Lagos, FCT", "action": "Monitor"},
        {"disease": "Meningitis", "level": "Green", "states": "Sokoto", "action": "Monitor"},
    ],
    "clinic_actions": [
        {"title": "High alert workflow", "copy": "Increase screening, intensify monitoring, and prepare isolation capacity."},
        {"title": "Medium alert workflow", "copy": "Verify signals, review local reports, and brief clinic leads on watch areas."},
        {"title": "Low alert workflow", "copy": "Maintain surveillance and include findings in routine reporting cycles."},
    ],
}
