from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy.orm import Session as DBSession
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any

from app.models.database import get_db
from app.models.user import User, SessionModel, Consent
from app.models.document import UploadedDocument
from app.models.rules import FormTemplate, RuleSet, Rule
from app.core.security import get_current_session
from app.core.errors import ForbiddenError, NotFoundError
from app.services.lifecycle import purge_session_files
from app.services.rules.engine import seed_rules_from_file
from app.config import settings

router = APIRouter(prefix="/admin", tags=["Admin Panel"])

def require_admin(
    authorization: Optional[str] = Header(None),
    x_session_token: Optional[str] = Header(None, alias="X-Session-Token"),
    x_admin_key: Optional[str] = Header(None, alias="X-Admin-Key"),
    db: DBSession = Depends(get_db)
) -> User:
    """
    Ensures the caller has administrative privileges via:
    1. An active session with role == 'admin'
    2. OR emergency/bootstrap X-Admin-Key header matching system SECRET_KEY
    """
    if x_admin_key and x_admin_key == settings.SECRET_KEY:
        admin = db.query(User).filter(User.role == "admin").first()
        if not admin:
            admin = User(role="admin")
            db.add(admin)
            db.commit()
            db.refresh(admin)
        return admin

    token = None
    if x_session_token:
        token = x_session_token.strip()
    elif authorization and authorization.lower().startswith("bearer "):
        token = authorization[7:].strip()

    if not token:
        raise ForbiddenError(
            message="Administrative authorization required",
            hint="You must be an admin user or provide a valid X-Admin-Key header"
        )

    from app.core.security import hash_session_token
    token_hash = hash_session_token(token)
    session = db.query(SessionModel).filter(
        SessionModel.token_hash == token_hash,
        SessionModel.is_active == True
    ).first()

    if not session or not session.user or session.user.role != "admin":
        raise ForbiddenError(
            message="Administrative privileges required",
            hint="Your account does not have admin permissions"
        )

    return session.user

@router.get("/stats")
def get_dashboard_stats(
    _admin: User = Depends(require_admin),
    db: DBSession = Depends(get_db)
) -> Dict[str, Any]:
    """Retrieves high-level platform health, usage, and audit statistics."""
    total_users = db.query(User).count()
    total_sessions = db.query(SessionModel).count()
    active_sessions = db.query(SessionModel).filter(SessionModel.is_active == True).count()
    total_documents = db.query(UploadedDocument).count()
    total_rules = db.query(Rule).count()
    total_consents = db.query(Consent).count()

    docs_passed = db.query(UploadedDocument).filter(UploadedDocument.format_status == "PASSED").count()
    docs_failed = db.query(UploadedDocument).filter(UploadedDocument.format_status != "PASSED").count()

    return {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "stats": {
            "total_users": total_users,
            "total_sessions": total_sessions,
            "active_sessions": active_sessions,
            "total_documents": total_documents,
            "documents_passed": docs_passed,
            "documents_failed": docs_failed,
            "total_rules": total_rules,
            "total_consents": total_consents,
        }
    }

@router.get("/users")
def list_users(
    _admin: User = Depends(require_admin),
    db: DBSession = Depends(get_db)
) -> List[Dict[str, Any]]:
    """Lists users with role and session status, protecting personal privacy."""
    users = db.query(User).all()
    result = []
    for u in users:
        active_sess_count = db.query(SessionModel).filter(
            SessionModel.user_id == u.id,
            SessionModel.is_active == True
        ).count()
        has_consent = db.query(Consent).filter(Consent.user_id == u.id).first() is not None

        result.append({
            "id": u.id,
            "role": u.role,
            "created_at": u.created_at.isoformat() if u.created_at else None,
            "active_sessions": active_sess_count,
            "has_consent": has_consent
        })
    return result

@router.put("/users/{user_id}/role")
def update_user_role(
    user_id: str,
    role: str,
    _admin: User = Depends(require_admin),
    db: DBSession = Depends(get_db)
):
    """Updates user role (e.g. promotes to 'admin' or resets to 'citizen')."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise NotFoundError(message="User not found", hint="Check user identifier")

    if role not in ["citizen", "student", "admin"]:
        raise HTTPException(status_code=400, detail="Invalid role. Must be 'citizen', 'student', or 'admin'.")

    user.role = role
    db.commit()
    return {"status": "SUCCESS", "user_id": user_id, "new_role": role}

@router.get("/rules")
def list_rules(
    _admin: User = Depends(require_admin),
    db: DBSession = Depends(get_db)
) -> List[Dict[str, Any]]:
    """Lists all configured validation rules."""
    rules = db.query(Rule).all()
    return [
        {
            "id": r.id,
            "rule_id": r.rule_id,
            "scope": r.scope,
            "rule_type": r.rule_type,
            "severity": r.severity,
            "message_key": r.message_key,
        }
        for r in rules
    ]

@router.post("/rules/reseed")
def reseed_rules(
    _admin: User = Depends(require_admin),
    db: DBSession = Depends(get_db)
):
    """Reseeds validation rules from the JSON rule definition."""
    rule_set = seed_rules_from_file(db)
    return {
        "status": "RESEEDED",
        "version": rule_set.version,
        "rules_count": len(rule_set.rules) if rule_set.rules else 0
    }

@router.get("/documents")
def list_recent_documents(
    _admin: User = Depends(require_admin),
    db: DBSession = Depends(get_db)
) -> List[Dict[str, Any]]:
    """Lists documents processed on the platform."""
    docs = db.query(UploadedDocument).order_by(UploadedDocument.created_at.desc()).limit(50).all()
    return [
        {
            "id": d.id,
            "session_id": d.session_id[:8] + "...",
            "document_type": d.document_type,
            "original_filename": d.original_filename,
            "mime_type": d.mime_type,
            "file_size_kb": d.file_size_kb,
            "format_status": d.format_status,
            "overall_confidence": round(d.overall_confidence or 0.0, 2),
            "created_at": d.created_at.isoformat() if d.created_at else None
        }
        for d in docs
    ]

@router.delete("/sessions/{session_id}")
def admin_revoke_session(
    session_id: str,
    _admin: User = Depends(require_admin),
    db: DBSession = Depends(get_db)
):
    """Admin action: revokes a session and cleans up disk files."""
    sess = db.query(SessionModel).filter(SessionModel.id == session_id).first()
    if not sess:
        raise NotFoundError(message="Session not found", hint="Check session ID")

    sess.is_active = False
    purge_session_files(session_id)
    db.commit()

    return {
        "status": "SESSION_REVOKED",
        "session_id": session_id
    }
