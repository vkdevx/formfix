import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, DateTime, ForeignKey, Float, Integer, Text, Boolean
from sqlalchemy.orm import relationship
from app.models.database import Base

def generate_uuid() -> str:
    return str(uuid.uuid4())

class UploadedDocument(Base):
    __tablename__ = "uploaded_documents"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    session_id = Column(String(36), ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(String(36), nullable=True, index=True)
    form_type = Column(String(64), default="UP_SCHOLARSHIP_POSTMATRIC", nullable=False)
    document_type = Column(String(32), nullable=False)  # application, aadhaar, marksheet, bank_passbook, income_cert, caste_cert
    original_filename = Column(String(255), nullable=False)
    file_path = Column(String(512), nullable=False)
    file_size_kb = Column(Float, nullable=False)
    mime_type = Column(String(64), nullable=False)
    width_px = Column(Integer, nullable=True)
    height_px = Column(Integer, nullable=True)
    format_status = Column(String(16), nullable=False, default="PASSED")  # PASSED, FAILED
    error_message = Column(Text, nullable=True)
    extracted_data = Column(Text, nullable=True)  # JSON-serialized fields
    overall_confidence = Column(Float, default=0.0)
    has_corrections = Column(Boolean, default=False)
    is_encrypted = Column(Boolean, default=True)
    reviewed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    session = relationship("SessionModel", backref="documents")
