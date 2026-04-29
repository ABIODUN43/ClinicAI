import json
import sys

import requests


def main() -> int:
    if len(sys.argv) != 3:
        print("Usage: python backend/scripts/submit_clinic_report.py <api-base-url> <bearer-token>")
        return 1

    api_base_url = sys.argv[1].rstrip("/")
    token = sys.argv[2]

    payload = {
        "facility_name": "Lokoja Community Clinic",
        "location": "Kogi",
        "disease": "Lassa fever",
        "symptom_summary": "Fever, weakness, and sore throat clustering across recent walk-in patients.",
        "patient_count": 5,
        "severity": "Medium",
        "notes": "Example clinic report submission for testing the ingestion workflow.",
        "reported_by": "Clinic operations lead",
    }

    response = requests.post(
        f"{api_base_url}/api/clinic-reports",
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
