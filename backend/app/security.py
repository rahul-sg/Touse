"""
JWT security helpers + FastAPI auth dependency.

Deliberately dependency-free (no imports from app.api.*) so both auth.py and the
route modules can import it without circular-import problems.
"""
import os
from datetime import datetime, timedelta, timezone

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError

SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-change-in-prod")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_DAYS = 30
EMAIL_TOKEN_EXPIRE_DAYS = 3

# auto_error=True → a missing/blank Authorization header yields a 403 automatically.
_bearer = HTTPBearer(auto_error=True)


def create_access_token(user_id: int) -> str:
    """Mint a signed JWT carrying the user id in the `sub` claim."""
    expire = datetime.now(timezone.utc) + timedelta(days=ACCESS_TOKEN_EXPIRE_DAYS)
    return jwt.encode({"sub": str(user_id), "exp": expire}, SECRET_KEY, algorithm=ALGORITHM)


def get_current_user_id(
    creds: HTTPAuthorizationCredentials = Depends(_bearer),
) -> int:
    """FastAPI dependency: decode the Bearer token, return the authenticated user id.

    Raises 401 if the token is missing a subject, malformed, or expired.
    """
    try:
        payload = jwt.decode(creds.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        sub = payload.get("sub")
        if sub is None:
            raise JWTError("token missing 'sub' claim")
        return int(sub)
    except (JWTError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired session — please sign in again.",
            headers={"WWW-Authenticate": "Bearer"},
        )


def require_self(path_user_id: int, current_user_id: int) -> None:
    """Raise 403 unless the user id in the URL matches the authenticated user."""
    if path_user_id != current_user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorized to access this account.",
        )


def create_email_token(user_id: int) -> str:
    """Mint a short-lived signed token used in email-verification links."""
    expire = datetime.now(timezone.utc) + timedelta(days=EMAIL_TOKEN_EXPIRE_DAYS)
    return jwt.encode(
        {"sub": str(user_id), "purpose": "email_verify", "exp": expire},
        SECRET_KEY,
        algorithm=ALGORITHM,
    )


def decode_email_token(token: str) -> int | None:
    """Return the user id from a valid email-verification token, else None."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        if payload.get("purpose") != "email_verify":
            return None
        return int(payload["sub"])
    except (JWTError, ValueError, KeyError):
        return None
