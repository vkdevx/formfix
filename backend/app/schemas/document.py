from pydantic import BaseModel, Field
from typing import Optional, List, Dict

class DocumentFormatResult(BaseModel):
    status: str = Field(..., description="PASSED or FAILED")
    mime_type: str
    file_size_kb: float
    width_px: Optional[int] = None
    height_px: Optional[int] = None
    page_count: Optional[int] = None
    error_reason_en: Optional[str] = None
    error_reason_hi: Optional[str] = None

class DocumentResponse(BaseModel):
    id: str
    document_type: str
    original_filename: str
    file_size_kb: float
    mime_type: str
    format_status: str
    error_message: Optional[str] = None
    overall_confidence: Optional[float] = 0.0
    created_at: str

class DocumentListResponse(BaseModel):
    total_uploaded: int
    all_passed: bool
    documents: List[DocumentResponse]

class FieldDetailSchema(BaseModel):
    field_name: str
    value: str
    confidence: float
    is_low_confidence: bool
    validation_passed: bool = True
    hint: Optional[str] = None

class DocumentExtractionResponse(BaseModel):
    document_id: str
    document_type: str
    overall_confidence: float
    fields: Dict[str, FieldDetailSchema]
    extracted_at: str
