import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, DateTime, ForeignKey, Boolean, Integer, Text
from sqlalchemy.orm import relationship
from app.models.database import Base

def generate_uuid() -> str:
    return str(uuid.uuid4())

class User(Base):
    __tablename__ = "users"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    full_name = Column(String(100), nullable=True)
    email = Column(String(120), nullable=True, index=True)
    phone = Column(String(20), nullable=True, index=True)
    phone_hash = Column(String(64), nullable=True, index=True)
    email_hash = Column(String(64), nullable=True, index=True)
    password_hash = Column(String(256), nullable=True)
    password_salt = Column(String(64), nullable=True)
    role = Column(String(20), default="citizen", nullable=False)  # citizen, student, admin
    is_verified = Column(Boolean, default=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    sessions = relationship("SessionModel", back_populates="user", cascade="all, delete-orphan")
    consents = relationship("Consent", back_populates="user", cascade="all, delete-orphan")

class SessionModel(Base):
    __tablename__ = "sessions"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    token_hash = Column(String(64), unique=True, nullable=False, index=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    expires_at = Column(DateTime, nullable=False)
    is_active = Column(Boolean, default=True)

    user = relationship("User", back_populates="sessions")

class Consent(Base):
    __tablename__ = "consents"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    policy_version = Column(String(32), nullable=False)
    accepted_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    ip_hash = Column(String(64), nullable=True)

    user = relationship("User", back_populates="consents")

class OTPRecord(Base):
    __tablename__ = "otp_records"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    identifier_hash = Column(String(64), nullable=False, index=True)
    otp_hash = Column(String(64), nullable=False)
    salt = Column(String(32), nullable=False)
    purpose = Column(String(32), default="auth", nullable=False)  # "auth", "registration", "password_reset"
    payload_data = Column(Text, nullable=True)  # encrypted or temporary JSON data for pending registration
    attempts = Column(Integer, default=0, nullable=False)
    is_used = Column(Boolean, default=False, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    resend_cooldown_until = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(36), nullable=True, index=True)
    action = Column(String(64), nullable=False)  # USER_REGISTER, USER_LOGIN, DOCUMENT_UPLOAD, FIELD_CORRECTION, AUDIT_RUN, PDF_DOWNLOAD, DATA_PURGE
    resource_type = Column(String(32), nullable=True)
    resource_id = Column(String(64), nullable=True)
    details = Column(String(255), nullable=True)
    ip_hash = Column(String(64), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
