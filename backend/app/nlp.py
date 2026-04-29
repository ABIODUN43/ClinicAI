import re


TRUSTED_SOURCE_HINTS = {
    "ncdc": "High",
    "nigeria centre for disease control": "High",
    "who": "High",
    "world health organization": "High",
    "guardian": "High",
    "punch": "High",
    "premium times": "High",
    "vanguard": "High",
}

SOURCE_TRUST_SCORES = {
    "High": 0.18,
    "Medium": 0.11,
    "Watch": 0.05,
    "Low": 0.0,
}

NIGERIA_LOCATIONS = [
    "Abia",
    "Adamawa",
    "Akwa Ibom",
    "Anambra",
    "Bauchi",
    "Bayelsa",
    "Benue",
    "Borno",
    "Cross River",
    "Delta",
    "Ebonyi",
    "Edo",
    "Ekiti",
    "Enugu",
    "FCT",
    "Federal Capital Territory",
    "Gombe",
    "Imo",
    "Jigawa",
    "Kaduna",
    "Kano",
    "Katsina",
    "Kebbi",
    "Kogi",
    "Kwara",
    "Lagos",
    "Nasarawa",
    "Niger",
    "Ogun",
    "Ondo",
    "Osun",
    "Oyo",
    "Plateau",
    "Rivers",
    "Sokoto",
    "Taraba",
    "Yobe",
    "Zamfara",
]

LOCATION_ALIASES = {
    "Abuja": "FCT",
    "Federal Capital Territory": "FCT",
}

DISEASE_TERMS = {
    "Lassa fever": ("lassa", "lassa fever"),
    "Cholera": ("cholera",),
    "Mpox": ("mpox", "monkeypox"),
    "Meningitis": ("meningitis",),
}

SIGNAL_PATTERNS = {
    "rodent_risk": {
        "keywords": ("rodent", "rats", "mice", "infestation", "rodent activity"),
        "weight": 0.18,
    },
    "outbreak_signal": {
        "keywords": ("outbreak", "cluster", "spread", "surge", "transmission"),
        "weight": 0.18,
    },
    "suspected_cases": {
        "keywords": ("suspected case", "suspected cases", "confirmed case", "confirmed cases", "case count"),
        "weight": 0.15,
    },
    "fatality_signal": {
        "keywords": ("death", "deaths", "fatality", "fatalities", "died"),
        "weight": 0.2,
    },
    "symptom_signal": {
        "keywords": ("fever", "bleeding", "vomiting", "weakness", "headache", "sore throat"),
        "weight": 0.12,
    },
    "sanitation_risk": {
        "keywords": ("poor sanitation", "waste", "contamination", "food storage", "hygiene"),
        "weight": 0.1,
    },
    "response_signal": {
        "keywords": ("surveillance", "screening", "response team", "health officials", "isolation"),
        "weight": 0.07,
    },
}

NEGATION_TERMS = (
    "no outbreak",
    "contained",
    "under control",
    "false alarm",
    "not lassa",
    "denied",
)

AMPLIFIER_TERMS = (
    "rising",
    "increase",
    "increased",
    "rapid",
    "worsening",
    "elevated",
    "alert",
    "warning",
)


def analyze_news_text(
    *,
    title: str,
    content: str,
    source_name: str,
    verification_status: str,
    location: str | None = None,
    disease: str | None = None,
) -> dict:
    combined = f"{title}\n{content}".lower()
    matched_locations = _extract_locations(title, content, location)
    resolved_location = matched_locations[0] if matched_locations else (location or "Nigeria")
    resolved_disease = _detect_disease(combined, disease)
    source_trust = _source_trust(source_name, verification_status)

    matched_terms: list[str] = []
    matched_signal_types: list[str] = []
    weighted_hits = 0.0
    for signal_type, config in SIGNAL_PATTERNS.items():
        keywords = config["keywords"]
        hits = [keyword for keyword in keywords if keyword in combined]
        if hits:
            matched_signal_types.append(signal_type)
            weighted_hits += config["weight"]
            for keyword in hits:
                if keyword not in matched_terms:
                    matched_terms.append(keyword)

    negation_hits = [term for term in NEGATION_TERMS if term in combined]
    amplifier_hits = [term for term in AMPLIFIER_TERMS if term in combined]
    signal_type = _primary_signal_type(matched_signal_types, combined)
    confidence = _confidence_score(
        resolved_disease=resolved_disease,
        matched_locations=matched_locations,
        matched_signal_types=matched_signal_types,
        source_trust=source_trust,
        verification_status=verification_status,
        weighted_hits=weighted_hits,
        negation_hits=negation_hits,
        amplifier_hits=amplifier_hits,
    )
    classification, risk_factor = _classification_from_confidence(confidence, matched_signal_types)
    should_generate_signal = confidence >= 0.42 and bool(matched_signal_types)
    summary = _summary_text(
        resolved_location=resolved_location,
        resolved_disease=resolved_disease,
        source_trust=source_trust,
        matched_terms=matched_terms,
        classification=classification,
        amplifier_hits=amplifier_hits,
        negation_hits=negation_hits,
    )

    return {
        "location": resolved_location,
        "disease": resolved_disease,
        "source_trust": source_trust,
        "matched_locations": matched_locations,
        "matched_terms": matched_terms,
        "signal_type": signal_type,
        "classification": classification,
        "risk_factor": risk_factor,
        "confidence": confidence,
        "signal_strength": _signal_strength(confidence),
        "summary": summary,
        "signal_title": f"NLP extracted risk signal from news: {title}",
        "should_generate_signal": should_generate_signal,
    }


def _extract_locations(title: str, content: str, fallback_location: str | None) -> list[str]:
    combined = f"{title}\n{content}"
    found: list[str] = []
    for location in NIGERIA_LOCATIONS:
        pattern = rf"\b{re.escape(location)}\b"
        if re.search(pattern, combined, flags=re.IGNORECASE):
            normalized = LOCATION_ALIASES.get(location, location)
            if normalized not in found:
                found.append(normalized)
    for alias, normalized in LOCATION_ALIASES.items():
        if re.search(rf"\b{re.escape(alias)}\b", combined, flags=re.IGNORECASE) and normalized not in found:
            found.append(normalized)
    if not found and fallback_location:
        found.append(fallback_location.strip())
    return found


def _detect_disease(combined: str, fallback_disease: str | None) -> str:
    for disease, keywords in DISEASE_TERMS.items():
        if any(keyword in combined for keyword in keywords):
            return disease
    return fallback_disease or "Lassa fever"


def _source_trust(source_name: str, verification_status: str) -> str:
    lowered = source_name.lower()
    for hint, trust in TRUSTED_SOURCE_HINTS.items():
        if hint in lowered:
            return trust
    if verification_status == "Verified":
        return "Medium"
    if verification_status == "Review":
        return "Watch"
    return "Low"


def _confidence_score(
    *,
    resolved_disease: str,
    matched_locations: list[str],
    matched_signal_types: list[str],
    source_trust: str,
    verification_status: str,
    weighted_hits: float,
    negation_hits: list[str],
    amplifier_hits: list[str],
) -> float:
    score = 0.18 if resolved_disease else 0.0
    score += min(len(matched_locations) * 0.08, 0.16)
    score += min(weighted_hits, 0.45)
    score += min(len(matched_signal_types) * 0.04, 0.16)
    score += SOURCE_TRUST_SCORES.get(source_trust, 0.0)
    score += {"Verified": 0.08, "Review": 0.03, "Unverified": 0.0}.get(verification_status, 0.0)
    score += min(len(amplifier_hits) * 0.03, 0.09)
    score -= min(len(negation_hits) * 0.18, 0.36)
    return round(min(score, 0.96), 2)


def _classification_from_confidence(confidence: float, signal_types: list[str]) -> tuple[str, str]:
    high_risk = any(item in signal_types for item in ("rodent_risk", "fatality_signal", "outbreak_signal", "suspected_cases"))
    if confidence >= 0.72 or (high_risk and confidence >= 0.58):
        return "Red", "HIGH"
    if confidence >= 0.42:
        return "Amber", "MEDIUM"
    return "Green", "LOW"


def _summary_text(
    *,
    resolved_location: str,
    resolved_disease: str,
    source_trust: str,
    matched_terms: list[str],
    classification: str,
    amplifier_hits: list[str],
    negation_hits: list[str],
) -> str:
    terms = ", ".join(matched_terms[:5]) if matched_terms else "general health-watch language"
    modifiers: list[str] = []
    if amplifier_hits:
        modifiers.append(f"escalation wording included {', '.join(amplifier_hits[:3])}")
    if negation_hits:
        modifiers.append(f"dampening wording included {', '.join(negation_hits[:2])}")
    modifier_text = f" {'; '.join(modifiers)}." if modifiers else ""
    return (
        f"{classification} NLP signal for {resolved_disease} in {resolved_location}. "
        f"Source trust is {source_trust.lower()} and the strongest matched terms were {terms}.{modifier_text}"
    )


def _primary_signal_type(signal_types: list[str], combined: str) -> str:
    if not signal_types:
        return "general_health_watch"
    ranked = sorted(
        signal_types,
        key=lambda item: (
            SIGNAL_PATTERNS[item]["weight"],
            sum(1 for keyword in SIGNAL_PATTERNS[item]["keywords"] if keyword in combined),
        ),
        reverse=True,
    )
    return ranked[0]


def _signal_strength(confidence: float) -> str:
    if confidence >= 0.72:
        return "high"
    if confidence >= 0.42:
        return "medium"
    return "low"
