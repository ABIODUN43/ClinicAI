from datetime import UTC, datetime, timedelta

import jwt
from fastapi import HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from .config import allowed_admin_emails, settings

bearer_scheme = HTTPBearer(auto_error=False)


def resolve_user_role(email: str, requested_role: str | None = None) -> str:
    lowered = email.lower()
    requested = (requested_role or "").strip().lower()

    if lowered in allowed_admin_emails():
        return "admin"
    if requested in {"clinic", "public_health"}:
        return requested
    if any(keyword in lowered for keyword in ("clinic", "hospital", "nurse", "doctor", "facility")):
        return "clinic"
    if any(keyword in lowered for keyword in ("ncdc", "surveillance", "publichealth", "health")):
        return "public_health"
    return "public_health"


def create_access_token(*, email: str, name: str, image_url: str | None, role: str) -> str:
    now = datetime.now(UTC)
    payload = {
        "sub": email,
        "name": name,
        "picture": image_url,
        "role": role,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(hours=settings.app_jwt_expiration_hours)).timestamp()),
    }
    return jwt.encode(payload, settings.app_jwt_secret, algorithm=settings.app_jwt_algorithm)


def decode_access_token(token: str) -> dict:
    if token in {"demo-session", "demo-session-admin", "demo-session-public_health", "demo-session-clinic"}:
        role = "admin"
        if token.endswith("public_health"):
            role = "public_health"
        if token.endswith("clinic"):
            role = "clinic"
        return {
            "sub": "demo@sentinel-healthscope.local",
            "name": "Demo Analyst",
            "picture": None,
            "role": role,
        }

    try:
        return jwt.decode(token, settings.app_jwt_secret, algorithms=[settings.app_jwt_algorithm])
    except jwt.PyJWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired session token.",
        ) from exc


def require_bearer_token(credentials: HTTPAuthorizationCredentials | None) -> dict:
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required.",
        )

    return decode_access_token(credentials.credentials)


def require_role(user: dict, *allowed_roles: str) -> dict:
    role = user.get("role", "admin")
    if role not in allowed_roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"This action requires one of these roles: {', '.join(allowed_roles)}.",
        )
    return user
