# backend/app/services/document.py
"""Utility helpers for document‑related DB queries.

This module provides a thin wrapper around the SQLAlchemy session to fetch
`UploadedDocument` records for a given session ID. It is deliberately kept
lightweight so that other services (e.g., the ExplanationEngine) can import it
without pulling in FastAPI dependencies.
"""

from typing import List

from app.models.document import UploadedDocument
from app.models.database import SessionLocal


def get_documents_for_session(session_id: str) -> List[UploadedDocument]:
    """Return all `UploadedDocument` rows belonging to *session_id*.

    The function creates a short‑lived SQLAlchemy session, queries the table,
    and closes the connection. It is safe to call from background code or
    FastAPI dependencies.
    """
    db = SessionLocal()
    try:
        return (
            db.query(UploadedDocument)
            .filter(UploadedDocument.session_id == session_id)
            .all()
        )
    finally:
        db.close()
