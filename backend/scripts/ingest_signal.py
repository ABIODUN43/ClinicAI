import json
import sys

import requests


def main() -> int:
    if len(sys.argv) != 3:
        print("Usage: python backend/scripts/ingest_signal.py <api-base-url> <bearer-token>")
        return 1

    api_base_url = sys.argv[1].rstrip("/")
    token = sys.argv[2]

    payload = {
        "title": "Community rodent exposure discussion rising in Nasarawa",
        "disease": "Lassa fever",
        "location": "Nasarawa",
        "source_type": "News crawl",
        "source_name": "Regional verified source",
        "classification": "Amber",
        "confidence": 0.74,
        "risk_factor": "MEDIUM",
        "summary": "Automated ingest example from crawler/NLP pipeline for ClinicAI Sentinel.",
    }

    response = requests.post(
        f"{api_base_url}/api/signals",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
        data=json.dumps(payload),
        timeout=30,
    )
    print(response.status_code)
    print(response.text)
    return 0 if response.ok else 2


if __name__ == "__main__":
    raise SystemExit(main())
