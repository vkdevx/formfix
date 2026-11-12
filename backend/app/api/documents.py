import os
import json
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException, status
from sqlalchemy.orm import Session as DBSession
from typing import List, Dict

from app.models.database import get_db
from app.models.user import SessionModel
from app.models.document import UploadedDocument
from app.schemas.document import (
    DocumentResponse,
    DocumentListResponse,
    DocumentFormatResult,
    FieldDetailSchema,
    DocumentExtractionResponse
)
from app.core.security import get_current_session, require_consent
from app.core.errors import ValidationError, NotFoundError
from app.services.ingestion import validate_document_format, PORTAL_LIMITS
from app.services.lifecycle import save_ephemeral_file, delete_single_file, purge_session_files, cleanup_expired_sessions_and_files
from app.services.ocr.extractors import extract_document

router = APIRouter(prefix="/documents", tags=["Document Ingestion & OCR"])

@router.post("", response_model=DocumentResponse)
async def upload_document(
    file: UploadFile = File(..., description="Uploaded PDF or image document"),
    document_type: str = Form(..., description="Document type: application, aadhaar, marksheet, bank_passbook, income_certificate, caste_certificate"),
    form_type: str = Form("up_post_matric", description="Target government form type"),
    session: SessionModel = Depends(get_current_session),
    _consent = Depends(require_consent),
    db: DBSession = Depends(get_db)
):
    """
    FR-03, FR-04, FR-05: Upload document, validate portal format constraints,
    save to temporary storage, and extract fields via OCR with confidence scores.
    """
    clean_type = document_type.strip().lower()
    if clean_type not in PORTAL_LIMITS:
        allowed = ", ".join(PORTAL_LIMITS.keys())
        raise ValidationError(
            message=f"Invalid document type '{document_type}'. Allowed: {allowed}",
            hint="Select a valid document category (e.g., aadhaar, marksheet, bank_passbook)"
        )

    content = await file.read()
    if not content:
        raise ValidationError(
            message="Uploaded file is empty (0 bytes)",
            hint="Please select a valid non-empty document"
        )

    # 1. Format & magic-byte check against UP portal limits
    check_result = validate_document_format(
        content=content,
        document_type=clean_type,
        original_filename=file.filename or "unknown"
    )

    if not check_result.passed:
        raise ValidationError(
            message=check_result.error_reason_en or "Document failed portal format requirements",
            hint=check_result.error_reason_hi or "Please check file size, format, and resolution"
        )

    # 2. Ephemeral storage save
    saved_path = save_ephemeral_file(
        session_id=session.id,
        original_filename=file.filename or f"{clean_type}.bin",
        content=content
    )

    # Remove existing document of the same type for this session (replace)
    existing_doc = db.query(UploadedDocument).filter(
        UploadedDocument.session_id == session.id,
        UploadedDocument.document_type == clean_type
    ).first()

    if existing_doc:
        delete_single_file(existing_doc.file_path)
        db.delete(existing_doc)
        db.commit()

    # 3. Perform OCR field extraction (FR-05)
    extracted_json = None
    overall_conf = 0.0
    try:
        extraction_res = extract_document(clean_type, saved_path, check_result.mime_type)
        extracted_dict = extraction_res.to_dict()
        extracted_json = json.dumps(extracted_dict.get("fields", {}))
        overall_conf = extraction_res.overall_confidence
    except Exception:
        # Graceful degradation per PRD 7: user can still enter values manually in Review Grid
        extracted_json = json.dumps({})
        overall_conf = 0.0

    # 4. Save document record
    doc_record = UploadedDocument(
        session_id=session.id,
        user_id=session.user_id,
        form_type=form_type,
        document_type=clean_type,
        original_filename=file.filename or f"{clean_type}",
        file_path=saved_path,
        file_size_kb=check_result.file_size_kb,
        mime_type=check_result.mime_type,
        width_px=check_result.width_px,
        height_px=check_result.height_px,
        format_status="PASSED",
        error_message=None,
        extracted_data=extracted_json,
        overall_confidence=overall_conf,
        is_encrypted=True
    )
    db.add(doc_record)
    db.commit()
    db.refresh(doc_record)

    return DocumentResponse(
        id=doc_record.id,
        document_type=doc_record.document_type,
        original_filename=doc_record.original_filename,
        file_size_kb=doc_record.file_size_kb,
        mime_type=doc_record.mime_type,
        format_status=doc_record.format_status,
        error_message=doc_record.error_message,
        overall_confidence=doc_record.overall_confidence,
        created_at=doc_record.created_at.isoformat()
    )

@router.get("", response_model=DocumentListResponse)
def list_session_documents(
    session: SessionModel = Depends(get_current_session),
    _consent = Depends(require_consent),
    db: DBSession = Depends(get_db)
):
    """Lists all documents currently held in temporary storage for this session."""
    docs = db.query(UploadedDocument).filter(
        UploadedDocument.session_id == session.id
    ).all()

    formatted_docs = [
        DocumentResponse(
            id=d.id,
            document_type=d.document_type,
            original_filename=d.original_filename,
            file_size_kb=d.file_size_kb,
            mime_type=d.mime_type,
            format_status=d.format_status,
            error_message=d.error_message,
            overall_confidence=d.overall_confidence,
            created_at=d.created_at.isoformat()
        )
        for d in docs
    ]

    all_passed = all(d.format_status == "PASSED" for d in docs) if docs else False

    return DocumentListResponse(
        total_uploaded=len(docs),
        all_passed=all_passed,
        documents=formatted_docs
    )

@router.get("/{document_id}/fields", response_model=DocumentExtractionResponse)
def get_extracted_fields(
    document_id: str,
    session: SessionModel = Depends(get_current_session),
    _consent = Depends(require_consent),
    db: DBSession = Depends(get_db)
):
    """
    FR-05 & FR-09: Retrieve extracted fields with confidence scores.
    Sensitive identifiers are masked; fields below confidence threshold are flagged.
    """
    doc = db.query(UploadedDocument).filter(
        UploadedDocument.id == document_id,
        UploadedDocument.session_id == session.id
    ).first()

    if not doc:
        raise NotFoundError(message="Document not found", hint="Check document ID")

    # If extracted_data is empty, run extraction on demand
    if not doc.extracted_data or doc.extracted_data == "{}":
        try:
            extraction_res = extract_document(doc.document_type, doc.file_path, doc.mime_type)
            extracted_dict = extraction_res.to_dict()
            doc.extracted_data = json.dumps(extracted_dict.get("fields", {}))
            doc.overall_confidence = extraction_res.overall_confidence
            db.commit()
        except Exception:
            doc.extracted_data = "{}"

    fields_dict: Dict[str, Any] = json.loads(doc.extracted_data or "{}")

    # Build response schema
    field_schemas = {
        name: FieldDetailSchema(
            field_name=info["field_name"],
            value=info["value"],
            confidence=info["confidence"],
            is_low_confidence=info.get("is_low_confidence", False),
            validation_passed=info.get("validation_passed", True),
            hint=info.get("hint")
        )
        for name, info in fields_dict.items()
    }

    return DocumentExtractionResponse(
        document_id=doc.id,
        document_type=doc.document_type,
        overall_confidence=round(doc.overall_confidence or 0.0, 2),
        fields=field_schemas,
        extracted_at=doc.created_at.isoformat()
    )

@router.delete("/{document_id}")
def delete_document(
    document_id: str,
    session: SessionModel = Depends(get_current_session),
    db: DBSession = Depends(get_db)
):
    """Deletes a specific document from temporary storage and database."""
    doc = db.query(UploadedDocument).filter(
        UploadedDocument.id == document_id,
        UploadedDocument.session_id == session.id
    ).first()

    if not doc:
        raise NotFoundError(message="Document not found", hint="Check document ID")

    delete_single_file(doc.file_path)
    db.delete(doc)
    db.commit()

    return {
        "status": "DOCUMENT_DELETED",
        "document_id": document_id
    }

@router.post("/cleanup-expired")
def trigger_expired_cleanup(db: DBSession = Depends(get_db)):
    """Scheduled maintenance worker endpoint to purge inactive sessions and ephemeral files."""
    return cleanup_expired_sessions_and_files(db)
