import hashlib
import secrets
from datetime import datetime, timezone, timedelta
from typing import Optional, Tuple
from fastapi import Header, Depends
from sqlalchemy.orm import Session as DBSession

from app.config import settings
from app.models.database import get_db
from app.models.user import User, SessionModel, Consent, AuditLog
from app.core.errors import AuthenticationError, ConsentRequiredError

PBKDF2_ITERATIONS = 100000

def hash_identifier(value: str) -> str:
    """
    Computes a salted SHA-256 hash of a normalized identifier (phone or email).
    Ensures that raw identity credentials are never persisted in the database
    (per Architecture Section 10.2 & DPDP Act 2023 principles).
    """
    if not value:
        return ""
    normalized = value.strip().lower()
    salted = f"{settings.SECRET_KEY}:{normalized}"
    return hashlib.sha256(salted.encode("utf-8")).hexdigest()

def hash_password(password: str) -> Tuple[str, str]:
    """
    Hashes a user password using PBKDF2-HMAC-SHA256 with a unique cryptographic salt.
    Returns: (password_hash_hex, salt_hex)
    """
    salt = secrets.token_hex(16)
    dk = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        PBKDF2_ITERATIONS
    )
    return dk.hex(), salt

def verify_password(password: str, password_hash: str, salt: str) -> bool:
    """
    Verifies a password against the stored PBKDF2 hash and salt using constant-time comparison.
    """
    if not password or not password_hash or not salt:
        return False
    dk = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        PBKDF2_ITERATIONS
    )
    return secrets.compare_digest(dk.hex(), password_hash)

def generate_session_token() -> str:
    """Generates a cryptographically secure random session token."""
    return secrets.token_urlsafe(32)

def hash_session_token(token: str) -> str:
    """Hashes a session token for storage and lookup in the database."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()

def get_session_expiry() -> datetime:
    """Returns the expiry timestamp for a new session (30 minutes of inactivity)."""
    return datetime.now(timezone.utc) + timedelta(minutes=settings.SESSION_EXPIRE_MINUTES)

def extract_token(authorization: Optional[str] = None, x_session_token: Optional[str] = None) -> Optional[str]:
    """Extracts session token from Bearer header or X-Session-Token header."""
    if x_session_token:
        return x_session_token.strip()
    if authorization and authorization.lower().startswith("bearer "):
        return authorization[7:].strip()
    return None

def get_current_session(
    authorization: Optional[str] = Header(None),
    x_session_token: Optional[str] = Header(None, alias="X-Session-Token"),
    db: DBSession = Depends(get_db)
) -> SessionModel:
    """
    Dependency that authenticates the session token, verifies expiry,
    and refreshes the 30-minute inactivity window.
    """
    token = extract_token(authorization, x_session_token)
    if not token:
        raise AuthenticationError(
            message="Missing authentication token",
            hint="Provide token via Authorization: Bearer <token> or X-Session-Token header"
        )
    
    token_hash = hash_session_token(token)
    session = db.query(SessionModel).filter(
        SessionModel.token_hash == token_hash,
        SessionModel.is_active == True
    ).first()

    if not session:
        raise AuthenticationError(message="Invalid or revoked session", hint="Please log in again")

    # Check expiration safely
    now = datetime.now(timezone.utc)
    expires_at = session.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)

    if expires_at < now:
        session.is_active = False
        db.commit()
        raise AuthenticationError(message="Session expired due to 30 minutes of inactivity", hint="Please log in again")

    # Sliding expiry window on activity
    session.expires_at = get_session_expiry()
    db.commit()
    return session

def require_consent(
    session: SessionModel = Depends(get_current_session),
    db: DBSession = Depends(get_db)
) -> Consent:
    """
    Ensures that the user has accepted the DPDP Act 2023 consent policy
    before proceeding to upload documents or run audits (FR-02).
    """
    consent = db.query(Consent).filter(
        Consent.user_id == session.user_id
    ).order_by(Consent.accepted_at.desc()).first()

    if not consent:
        raise ConsentRequiredError(
            message="Explicit DPDP Act 2023 consent is required before proceeding",
            hint="Submit consent via POST /api/v1/consent"
        )
    return consent

def log_audit_event(
    db: DBSession,
    user_id: Optional[str],
    action: str,
    resource_type: Optional[str] = None,
    resource_id: Optional[str] = None,
    details: Optional[str] = None,
    ip_hash: Optional[str] = None
) -> AuditLog:
    """Logs an audit entry for privacy and compliance oversight."""
    try:
        entry = AuditLog(
            user_id=user_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            details=details,
            ip_hash=ip_hash
        )
        db.add(entry)
        db.commit()
        return entry
    except Exception:
        db.rollback()
        return None
