import os
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session as DBSession

from app.models.database import get_db
from app.models.user import User, SessionModel
from app.models.document import UploadedDocument
from app.core.security import get_current_session
from app.services.lifecycle import purge_session_files

router = APIRouter(prefix="/me", tags=["Privacy & DPDP"])

@router.delete("/data")
def delete_user_data(
    session: SessionModel = Depends(get_current_session),
    db: DBSession = Depends(get_db)
):
    """
    FR-12: The user can delete their data at any time.
    Permanently wipes user sessions, consents, uploaded document records,
    and ephemeral files from disk.
    """
    user_id = session.user_id

    # 1. Clean up ephemeral disk files and document records for all sessions of this user
    user_sessions = db.query(SessionModel).filter(SessionModel.user_id == user_id).all()
    for s in user_sessions:
        purge_session_files(s.id)
        db.query(UploadedDocument).filter(UploadedDocument.session_id == s.id).delete()

    # 2. Delete user database record (cascades sessions and consents)
    user = db.query(User).filter(User.id == user_id).first()
    if user:
        db.delete(user)
        db.commit()

    return {
        "status": "DATA_DELETED",
        "message": "All personal identifiers, active sessions, and temporary files have been permanently erased.",
        "user_id": user_id
    }
