from pydantic import BaseModel, Field
from typing import Dict, List, Optional

class ReviewFieldSchema(BaseModel):
    field_name: str
    label_en: str
    label_hi: str
    value: str
    confidence: float
    confidence_badge: str = Field(..., description="'high' (>=0.85), 'medium' (0.70-0.84), 'low' (<0.70)")
    is_user_corrected: bool = False
    is_masked: bool = False
    validation_passed: bool = True
    hint: Optional[str] = None

class DocumentReviewGroup(BaseModel):
    document_id: str
    document_type: str
    document_label_en: str
    document_label_hi: str
    original_filename: str
    has_corrections: bool = False
    overall_confidence: float
    fields: Dict[str, ReviewFieldSchema]

class ReviewGridResponse(BaseModel):
    session_id: str
    documents: List[DocumentReviewGroup]
    total_fields: int
    low_confidence_count: int
    corrected_count: int
    ready_for_audit: bool

class FieldCorrectionPayload(BaseModel):
    corrections: Dict[str, str] = Field(..., description="Key-value mapping of field_name to new user-corrected value")

class BatchCorrectionPayload(BaseModel):
    document_corrections: Dict[str, Dict[str, str]] = Field(
        ...,
        description="Nested mapping: document_id -> {field_name: new_value}"
    )

class ReviewConfirmResponse(BaseModel):
    status: str
    ready_for_audit: bool
    document_types_present: List[str]
    total_fields_reviewed: int
    message_en: str
    message_hi: str
