import uuid
from datetime import datetime, timezone, date
from sqlalchemy import Column, String, DateTime, ForeignKey, Integer, Boolean, Text, Date
from sqlalchemy.orm import relationship
from app.models.database import Base

def generate_uuid() -> str:
    return str(uuid.uuid4())

class FormTemplate(Base):
    __tablename__ = "form_templates"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    name = Column(String(100), unique=True, nullable=False)  # "UP_SCHOLARSHIP_POSTMATRIC"
    state = Column(String(50), nullable=False, default="Uttar Pradesh")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    rule_sets = relationship("RuleSet", back_populates="template", cascade="all, delete-orphan")

class RuleSet(Base):
    __tablename__ = "rule_sets"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    template_id = Column(String(36), ForeignKey("form_templates.id", ondelete="CASCADE"), nullable=False, index=True)
    version = Column(Integer, nullable=False, index=True)
    is_active = Column(Boolean, default=True)
    reviewed_on = Column(Date, default=date.today)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    template = relationship("FormTemplate", back_populates="rule_sets")
    rules = relationship("Rule", back_populates="rule_set", cascade="all, delete-orphan")

class Rule(Base):
    __tablename__ = "rules"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    rule_set_id = Column(String(36), ForeignKey("rule_sets.id", ondelete="CASCADE"), nullable=False, index=True)
    rule_id = Column(String(64), nullable=False, index=True)  # e.g. "AADHAAR_VERHOEFF", "IFSC_FORMAT"
    scope = Column(String(32), nullable=False)  # "aadhaar", "marksheet", "bank_passbook", "income_certificate", "global"
    rule_type = Column(String(32), nullable=False)  # "required", "regex", "checksum", "allowed_values", "date_logic", "document_presence"
    params = Column(Text, nullable=True)  # JSON-serialized parameters
    severity = Column(String(16), nullable=False, default="error")  # "error", "warning", "info"
    message_key = Column(String(100), nullable=False)

    rule_set = relationship("RuleSet", back_populates="rules")
