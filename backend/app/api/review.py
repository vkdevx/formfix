from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session as DBSession
from typing import Dict

from app.models.database import get_db
from app.models.user import SessionModel
from app.models.document import UploadedDocument
from app.schemas.review import (
    ReviewGridResponse,
    FieldCorrectionPayload,
    BatchCorrectionPayload,
    ReviewConfirmResponse
)
from app.schemas.document import DocumentExtractionResponse, FieldDetailSchema
from app.core.security import get_current_session, require_consent
from app.core.errors import NotFoundError, ValidationError
from app.services.review import (
    build_session_review_grid,
    apply_field_corrections
)

router = APIRouter(prefix="/review", tags=["Editable Verification Grid"])

@router.get("/grid", response_model=ReviewGridResponse)
def get_review_grid(
    session: SessionModel = Depends(get_current_session),
    _consent = Depends(require_consent),
    db: DBSession = Depends(get_db)
):
    """
    FR-06: Retrieves the complete multi-document verification grid for human review.
    Shows confidence badges (Green, Amber, Red), field values, and user corrections.
    """
    return build_session_review_grid(session.id, db)

@router.put("/grid", response_model=ReviewGridResponse)
def batch_update_review_grid(
    payload: BatchCorrectionPayload,
    session: SessionModel = Depends(get_current_session),
    _consent = Depends(require_consent),
    db: DBSession = Depends(get_db)
):
    """
    FR-06: Batch updates corrections across multiple documents simultaneously.
    """
    for doc_id, corrections in payload.document_corrections.items():
        doc = db.query(UploadedDocument).filter(
            UploadedDocument.id == doc_id,
            UploadedDocument.session_id == session.id
        ).first()

        if doc:
            apply_field_corrections(doc, corrections, db)

    return build_session_review_grid(session.id, db)

@router.put("/documents/{document_id}/fields", response_model=DocumentExtractionResponse)
def update_document_fields(
    document_id: str,
    payload: FieldCorrectionPayload,
    session: SessionModel = Depends(get_current_session),
    _consent = Depends(require_consent),
    db: DBSession = Depends(get_db)
):
    """
    FR-06: Updates specific fields for a document in the review grid.
    Corrected values are saved with 100% confidence and become authoritative for all subsequent checks.
    """
    doc = db.query(UploadedDocument).filter(
        UploadedDocument.id == document_id,
        UploadedDocument.session_id == session.id
    ).first()

    if not doc:
        raise NotFoundError(message="Document not found", hint="Check document ID")

    updated_data = apply_field_corrections(doc, payload.corrections, db)

    field_schemas = {
        name: FieldDetailSchema(
            field_name=info["field_name"],
            value=info["value"],
            confidence=info["confidence"],
            is_low_confidence=info.get("is_low_confidence", False),
            validation_passed=info.get("validation_passed", True),
            hint=info.get("hint")
        )
        for name, info in updated_data.items()
    }

    return DocumentExtractionResponse(
        document_id=doc.id,
        document_type=doc.document_type,
        overall_confidence=round(doc.overall_confidence or 0.0, 2),
        fields=field_schemas,
        extracted_at=doc.created_at.isoformat()
    )

@router.post("/confirm", response_model=ReviewConfirmResponse)
def confirm_review_grid(
    session: SessionModel = Depends(get_current_session),
    _consent = Depends(require_consent),
    db: DBSession = Depends(get_db)
):
    """
    Confirms review completion before executing the deterministic rules engine audit.
    """
    grid = build_session_review_grid(session.id, db)
    doc_types = [d.document_type for d in grid.documents]

    return ReviewConfirmResponse(
        status="REVIEW_CONFIRMED",
        ready_for_audit=len(grid.documents) > 0,
        document_types_present=doc_types,
        total_fields_reviewed=grid.total_fields,
        message_en="Verification grid confirmed. Ready to run deterministic rules engine audit.",
        message_hi="सत्यापन ग्रिड की पुष्टि हो गई है। नियम इंजन ऑडिट चलाने के लिए तैयार।"
    )
