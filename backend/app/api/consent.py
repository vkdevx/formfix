from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session as DBSession
from datetime import datetime, timezone
import hashlib

from app.models.database import get_db
from app.models.user import Consent, SessionModel
from app.schemas.consent import ConsentCreate, ConsentResponse, ConsentStatusResponse
from app.core.security import get_current_session
from app.core.errors import ValidationError
from app.config import settings

router = APIRouter(prefix="/consent", tags=["DPDP Consent"])

@router.post("", response_model=ConsentResponse)
def record_consent(
    payload: ConsentCreate,
    request: Request,
    session: SessionModel = Depends(get_current_session),
    db: DBSession = Depends(get_db)
):
    """
    FR-02: Record explicit DPDP Act 2023 user consent before any document upload.
    Stores policy version, timestamp, and anonymized client hash.
    """
    if not payload.accept:
        raise ValidationError(
            message="Consent must be affirmatively accepted to use FormSaathi pre-submission verification",
            hint="Set accept=True on the consent dialog"
        )

    policy_ver = payload.policy_version or settings.CONSENT_POLICY_VERSION

    # Hash client IP for auditing without storing raw IP address
    client_ip = request.client.host if request.client else "unknown"
    ip_hash = hashlib.sha256(client_ip.encode("utf-8")).hexdigest()[:16]

    # Check if consent already recorded for this user and version
    consent = db.query(Consent).filter(
        Consent.user_id == session.user_id,
        Consent.policy_version == policy_ver
    ).first()

    now = datetime.now(timezone.utc)
    if not consent:
        consent = Consent(
            user_id=session.user_id,
            policy_version=policy_ver,
            accepted_at=now,
            ip_hash=ip_hash
        )
        db.add(consent)
        db.commit()
        db.refresh(consent)

    return ConsentResponse(
        status="CONSENT_RECORDED",
        policy_version=consent.policy_version,
        accepted_at=consent.accepted_at.isoformat(),
        retention_period_minutes=settings.SESSION_EXPIRE_MINUTES,
        user_id=session.user_id
    )

@router.get("/status", response_model=ConsentStatusResponse)
def get_consent_status(
    session: SessionModel = Depends(get_current_session),
    db: DBSession = Depends(get_db)
):
    """
    Check whether active consent is present for the current user session.
    """
    consent = db.query(Consent).filter(
        Consent.user_id == session.user_id,
        Consent.policy_version == settings.CONSENT_POLICY_VERSION
    ).first()

    if consent:
        return ConsentStatusResponse(
            has_consented=True,
            policy_version=consent.policy_version,
            accepted_at=consent.accepted_at.isoformat(),
            retention_period_minutes=settings.SESSION_EXPIRE_MINUTES
        )
    return ConsentStatusResponse(
        has_consented=False,
        retention_period_minutes=settings.SESSION_EXPIRE_MINUTES
    )
