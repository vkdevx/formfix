from fastapi import APIRouter, Depends, HTTPException, Response
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session as DBSession
from typing import Dict, Any, Optional
import io

from app.models.database import get_db
from app.models.user import SessionModel
from app.core.security import get_current_session, require_consent
from app.core.errors import NotFoundError, ValidationError
from app.services.explanation.engine import ExplanationEngine

router = APIRouter(prefix="/explanations", tags=["Audit Explanations & PDF Reports"])

@router.get("/current")
def get_current_session_audit(
    session: SessionModel = Depends(get_current_session),
    _consent = Depends(require_consent),
    db: DBSession = Depends(get_db)
):
    """
    Executes pre-submission audit on the current active session and returns
    full bilingual (English & Hindi) explanations, rules verdicts, and fix checklist.
    """
    engine = ExplanationEngine(session_id=session.id, db=db)
    return engine.run_full_audit()

@router.get("/current/pdf")
def download_current_session_pdf(
    session: SessionModel = Depends(get_current_session),
    _consent = Depends(require_consent),
    db: DBSession = Depends(get_db)
):
    """
    FR-11: Generates and streams downloadable masked PDF audit checklist
    for the current user session.
    """
    engine = ExplanationEngine(session_id=session.id, db=db)
    pdf_bytes = engine.generate_pdf_report()

    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"attachment; filename=FormFix_Audit_Report_{session.id[:8]}.pdf"
        }
    )

@router.get("/{session_id}")
def get_audit_by_session_id(
    session_id: str,
    db: DBSession = Depends(get_db)
):
    """
    Retrieves explanations and audit findings for a specific session ID.
    Used by frontend explanation viewer.
    """
    sess = db.query(SessionModel).filter(SessionModel.id == session_id).first()
    if not sess:
        raise NotFoundError(message="Audit session not found", hint="Check your session identifier")

    engine = ExplanationEngine(session_id=session_id, db=db)
    return engine.run_full_audit()

@router.get("/{session_id}/pdf")
def download_pdf_by_session_id(
    session_id: str,
    db: DBSession = Depends(get_db)
):
    """
    FR-11: Downloads masked PDF audit report by session ID.
    """
    sess = db.query(SessionModel).filter(SessionModel.id == session_id).first()
    if not sess:
        raise NotFoundError(message="Audit session not found", hint="Check your session identifier")

    engine = ExplanationEngine(session_id=session_id, db=db)
    pdf_bytes = engine.generate_pdf_report()

    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"attachment; filename=FormFix_Audit_Report_{session_id[:8]}.pdf"
        }
    )
