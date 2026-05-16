import json
import os
import sys
import urllib.error
import urllib.request


def main() -> int:
    automation_url = os.environ.get(
        "AUTOMATION_URL",
        "https://clinicai-sentinel-api.onrender.com/api/automation/daily-cycle",
    )
    automation_secret = os.environ.get("AUTOMATION_SECRET", "").strip()

    if not automation_secret:
        print("AUTOMATION_SECRET is not configured.", file=sys.stderr)
        return 1

    request = urllib.request.Request(
        automation_url,
        data=b"",
        method="POST",
        headers={
            "X-ClinicAI-Automation-Key": automation_secret,
        },
    )

    try:
        with urllib.request.urlopen(request, timeout=300) as response:
            payload = response.read().decode("utf-8")
            print(payload)
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        print(
            json.dumps(
                {
                    "status": "http_error",
                    "code": exc.code,
                    "reason": exc.reason,
                    "body": body,
                },
                indent=2,
            ),
            file=sys.stderr,
        )
        return 1
    except urllib.error.URLError as exc:
        print(
            json.dumps(
                {
                    "status": "url_error",
                    "reason": str(exc.reason),
                },
                indent=2,
            ),
            file=sys.stderr,
        )
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
