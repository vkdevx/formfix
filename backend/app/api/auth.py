import json
import hashlib
import secrets
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional
from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session as DBSession

from app.models.database import get_db
from app.models.user import User, SessionModel, Consent, OTPRecord, AuditLog
from app.schemas.auth import (
    OTPRequest,
    OTPRequestResponse,
    OTPVerify,
    SessionResponse,
    UserRegisterRequest,
    UserRegisterVerifyRequest,
    UserLoginRequest,
    ForgotPasswordRequest,
    ResetPasswordRequest,
    DemoLoginRequest,
    UserProfileResponse,
)
from app.core.security import (
    hash_identifier,
    hash_password,
    verify_password,
    generate_session_token,
    hash_session_token,
    get_session_expiry,
    get_current_session,
    log_audit_event,
)
from app.core.redaction import mask_phone
from app.core.errors import ValidationError, AuthenticationError, RateLimitError, NotFoundError
from app.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["Authentication & Registration"])

OTP_EXPIRY_MINUTES = 10
RESEND_COOLDOWN_SECONDS = 60
MAX_ATTEMPTS = 5
MAX_HOURLY_REQUESTS = 10

def mask_email(email: str) -> str:
    if not email or "@" not in email:
        return ""
    name, domain = email.split("@", 1)
    masked_name = name[0] + "***" if len(name) > 1 else name + "***"
    return f"{masked_name}@{domain}"

def _clean_phone(phone: str) -> str:
    digits = "".join(ch for ch in phone.strip() if ch.isdigit())
    if len(digits) == 12 and digits.startswith("91"):
        digits = digits[2:]
    return digits

# --- Registration Workflows ---

@router.post("/register", response_model=OTPRequestResponse)
def register_user(payload: UserRegisterRequest, request: Request, db: DBSession = Depends(get_db)):
    """
    Phase 3: New user registration.
    Validates credentials, checks for existing duplicate accounts,
    and sends a verification OTP before account creation.
    """
    if payload.password != payload.confirm_password:
        raise ValidationError(message="Passwords do not match", hint="Ensure Password and Confirm Password match")

    clean_email = payload.email.strip().lower()
    if "@" not in clean_email or "." not in clean_email.split("@")[-1]:
        raise ValidationError(message="Invalid email address format", hint="Enter a valid email (e.g. student@example.com)")

    clean_ph = _clean_phone(payload.phone)
    if len(clean_ph) != 10:
        raise ValidationError(message="Invalid mobile number format", hint="Enter a 10-digit Indian phone number")

    email_hash = hash_identifier(clean_email)
    phone_hash = hash_identifier(clean_ph)

    # Check for existing accounts
    existing_user = db.query(User).filter(
        (User.email_hash == email_hash) | (User.phone_hash == phone_hash)
    ).first()

    if existing_user:
        raise ValidationError(
            message="An account with this email address or mobile number already exists",
            hint="Please log in with your password or use Forgot Password"
        )

    # Hash password with PBKDF2-HMAC-SHA256
    pw_hash, pw_salt = hash_password(payload.password)

    now = datetime.now(timezone.utc)
    id_hash = email_hash  # Use email hash as primary registration key

    # Check rate limit cooldown
    recent_otp = db.query(OTPRecord).filter(
        OTPRecord.identifier_hash == id_hash,
        OTPRecord.is_used == False,
        OTPRecord.expires_at > now
    ).order_by(OTPRecord.created_at.desc()).first()

    if recent_otp and recent_otp.resend_cooldown_until:
        cooldown_target = recent_otp.resend_cooldown_until
        if cooldown_target.tzinfo is None:
            cooldown_target = cooldown_target.replace(tzinfo=timezone.utc)
        if now < cooldown_target:
            rem = int((cooldown_target - now).total_seconds())
            raise RateLimitError(message=f"Please wait {rem} seconds before requesting another code", hint="Wait for cooldown timer")

    # Invalidate previous unused registration OTPs for this email
    db.query(OTPRecord).filter(
        OTPRecord.identifier_hash == id_hash,
        OTPRecord.is_used == False
    ).update({"is_used": True})
    db.commit()

    # Generate secure 6-digit random OTP
    otp_code = f"{secrets.randbelow(900000) + 100000:06d}"
    salt = secrets.token_hex(16)
    otp_hash = hashlib.sha256(f"{salt}:{otp_code}".encode("utf-8")).hexdigest()

    pending_payload = json.dumps({
        "full_name": payload.full_name.strip(),
        "email": clean_email,
        "phone": clean_ph,
        "email_hash": email_hash,
        "phone_hash": phone_hash,
        "password_hash": pw_hash,
        "password_salt": pw_salt
    })

    record = OTPRecord(
        identifier_hash=id_hash,
        otp_hash=otp_hash,
        salt=salt,
        purpose="registration",
        payload_data=pending_payload,
        attempts=0,
        is_used=False,
        expires_at=now + timedelta(minutes=OTP_EXPIRY_MINUTES),
        resend_cooldown_until=now + timedelta(seconds=RESEND_COOLDOWN_SECONDS)
    )
    db.add(record)
    db.commit()

    log_audit_event(db, None, "USER_REGISTER_INITIATED", details=f"Registration OTP sent to {mask_email(clean_email)}")

    return OTPRequestResponse(
        status="OTP_SENT",
        message="Registration verification code sent to your email",
        masked_target=mask_email(clean_email),
        cooldown_seconds=RESEND_COOLDOWN_SECONDS,
        demo_otp=otp_code
    )

@router.post("/verify-registration", response_model=SessionResponse)
def verify_registration(payload: UserRegisterVerifyRequest, db: DBSession = Depends(get_db)):
    """
    Phase 3: Verifies registration OTP, creates the User record in database,
    and returns a secure session token.
    """
    raw_id = payload.identifier.strip().lower()
    clean_id = _clean_phone(raw_id) if "@" not in raw_id else raw_id
    id_hash = hash_identifier(clean_id)

    now = datetime.now(timezone.utc)
    record = db.query(OTPRecord).filter(
        OTPRecord.identifier_hash == id_hash,
        OTPRecord.purpose == "registration",
        OTPRecord.is_used == False
    ).order_by(OTPRecord.created_at.desc()).first()

    if not record or not record.payload_data:
        raise AuthenticationError(message="No pending registration found for this email/phone", hint="Please complete the registration form")

    rec_exp = record.expires_at
    if rec_exp.tzinfo is None:
        rec_exp = rec_exp.replace(tzinfo=timezone.utc)

    if now > rec_exp:
        record.is_used = True
        db.commit()
        raise AuthenticationError(message="Verification code has expired. Please register again.", hint="Code valid for 10 minutes")

    if record.attempts >= MAX_ATTEMPTS:
        record.is_used = True
        db.commit()
        raise RateLimitError(message="Maximum attempts exceeded. Please register again.", hint="Brute-force protection triggered")

    clean_otp = payload.otp.strip()
    provided_hash = hashlib.sha256(f"{record.salt}:{clean_otp}".encode("utf-8")).hexdigest()

    if provided_hash != record.otp_hash:
        record.attempts += 1
        db.commit()
        rem = max(0, MAX_ATTEMPTS - record.attempts)
        raise AuthenticationError(message=f"Invalid verification code. {rem} attempt(s) remaining.", hint="Check your 6-digit code")

    # Success: Mark OTP as used
    record.is_used = True

    data = json.loads(record.payload_data)
    user = User(
        full_name=data["full_name"],
        email=data["email"],
        phone=data["phone"],
        email_hash=data["email_hash"],
        phone_hash=data["phone_hash"],
        password_hash=data["password_hash"],
        password_salt=data["password_salt"],
        role="citizen",
        is_verified=True
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    # Create session
    raw_token = generate_session_token()
    token_hash = hash_session_token(raw_token)
    session_expiry = get_session_expiry()

    session_rec = SessionModel(
        user_id=user.id,
        token_hash=token_hash,
        expires_at=session_expiry,
        is_active=True
    )
    db.add(session_rec)
    db.commit()

    log_audit_event(db, user.id, "USER_REGISTER_COMPLETED", details="User registered and verified account")

    return SessionResponse(
        session_token=raw_token,
        access_token=raw_token,
        user_id=user.id,
        full_name=user.full_name,
        role=user.role,
        expires_at=session_expiry.isoformat(),
        consent_required=True,
        masked_identifier=mask_email(user.email)
    )

# --- Password-Based Login ---

@router.post("/login", response_model=SessionResponse)
def login_with_password(payload: UserLoginRequest, db: DBSession = Depends(get_db)):
    """
    Phase 3: Existing user login using Email or Phone + Password.
    """
    raw_id = payload.identifier.strip().lower()
    clean_id = _clean_phone(raw_id) if "@" not in raw_id else raw_id
    id_hash = hash_identifier(clean_id)

    user = db.query(User).filter(
        (User.email_hash == id_hash) | (User.phone_hash == id_hash)
    ).first()

    if not user or not user.password_hash or not user.password_salt:
        raise AuthenticationError(
            message="Invalid credentials entered",
            hint="Check your email/phone and password, or use OTP login"
        )

    # Verify password
    if not verify_password(payload.password, user.password_hash, user.password_salt):
        log_audit_event(db, user.id, "LOGIN_FAILED", details="Incorrect password attempt")
        raise AuthenticationError(
            message="Invalid credentials entered",
            hint="Incorrect password. Check your password or use Forgot Password"
        )

    # Create active session
    raw_token = generate_session_token()
    token_hash = hash_session_token(raw_token)
    session_expiry = get_session_expiry()

    session_rec = SessionModel(
        user_id=user.id,
        token_hash=token_hash,
        expires_at=session_expiry,
        is_active=True
    )
    db.add(session_rec)
    db.commit()

    consent = db.query(Consent).filter(
        Consent.user_id == user.id,
        Consent.policy_version == settings.CONSENT_POLICY_VERSION
    ).first()

    masked = mask_email(user.email) if user.email else mask_phone(user.phone or "")
    log_audit_event(db, user.id, "USER_LOGIN_SUCCESS", details="Password login successful")

    return SessionResponse(
        session_token=raw_token,
        access_token=raw_token,
        user_id=user.id,
        full_name=user.full_name,
        role=user.role,
        expires_at=session_expiry.isoformat(),
        consent_required=consent is None,
        masked_identifier=masked
    )

# --- Forgot & Reset Password ---

@router.post("/forgot-password", response_model=OTPRequestResponse)
def forgot_password(payload: ForgotPasswordRequest, db: DBSession = Depends(get_db)):
    """Sends a password reset code to the registered email or mobile."""
    raw_id = payload.identifier.strip().lower()
    clean_id = _clean_phone(raw_id) if "@" not in raw_id else raw_id
    id_hash = hash_identifier(clean_id)

    user = db.query(User).filter(
        (User.email_hash == id_hash) | (User.phone_hash == id_hash)
    ).first()

    if not user:
        raise NotFoundError(message="No registered account found with this identifier", hint="Check your email or phone number")

    now = datetime.now(timezone.utc)
    otp_code = f"{secrets.randbelow(900000) + 100000:06d}"
    salt = secrets.token_hex(16)
    otp_hash = hashlib.sha256(f"{salt}:{otp_code}".encode("utf-8")).hexdigest()

    record = OTPRecord(
        identifier_hash=id_hash,
        otp_hash=otp_hash,
        salt=salt,
        purpose="password_reset",
        attempts=0,
        is_used=False,
        expires_at=now + timedelta(minutes=OTP_EXPIRY_MINUTES),
        resend_cooldown_until=now + timedelta(seconds=RESEND_COOLDOWN_SECONDS)
    )
    db.add(record)
    db.commit()

    masked = mask_email(user.email) if user.email else mask_phone(user.phone or "")
    return OTPRequestResponse(
        status="OTP_SENT",
        message="Password reset verification code sent",
        masked_target=masked,
        cooldown_seconds=RESEND_COOLDOWN_SECONDS,
        demo_otp=otp_code
    )

@router.post("/reset-password")
def reset_password(payload: ResetPasswordRequest, db: DBSession = Depends(get_db)):
    """Verifies reset code and updates account password."""
    if payload.new_password != payload.confirm_password:
        raise ValidationError(message="New passwords do not match", hint="Ensure new password matches confirmation")

    raw_id = payload.identifier.strip().lower()
    clean_id = _clean_phone(raw_id) if "@" not in raw_id else raw_id
    id_hash = hash_identifier(clean_id)

    user = db.query(User).filter(
        (User.email_hash == id_hash) | (User.phone_hash == id_hash)
    ).first()

    if not user:
        raise NotFoundError(message="User account not found", hint="Check your identifier")

    now = datetime.now(timezone.utc)
    record = db.query(OTPRecord).filter(
        OTPRecord.identifier_hash == id_hash,
        OTPRecord.purpose == "password_reset",
        OTPRecord.is_used == False
    ).order_by(OTPRecord.created_at.desc()).first()

    if not record:
        raise AuthenticationError(message="No active password reset request found", hint="Request a reset code first")

    clean_otp = payload.otp.strip()
    provided_hash = hashlib.sha256(f"{record.salt}:{clean_otp}".encode("utf-8")).hexdigest()

    if provided_hash != record.otp_hash:
        record.attempts += 1
        db.commit()
        raise AuthenticationError(message="Invalid password reset code", hint="Check the 6-digit code and try again")

    record.is_used = True
    new_hash, new_salt = hash_password(payload.new_password)
    user.password_hash = new_hash
    user.password_salt = new_salt
    db.commit()

    log_audit_event(db, user.id, "PASSWORD_RESET_SUCCESS", details="Password reset completed successfully")

    return {"status": "SUCCESS", "message": "Password updated successfully. You can now log in with your new password."}

# --- 1-Click Hackathon Demo Login ---

@router.post("/demo-login", response_model=SessionResponse)
def demo_login(payload: DemoLoginRequest, db: DBSession = Depends(get_db)):
    """
    Phase 7: Instant Demo Login for Hackathon Presentations!
    Provides 1-click access as Student or Administrator with synthetic mock data.
    """
    role = payload.role.strip().lower()
    now = datetime.now(timezone.utc)

    if role == "admin":
        user = db.query(User).filter(User.role == "admin").first()
        if not user:
            user = User(
                full_name="FormFix Administrator",
                email="admin@formfix.gov.in",
                phone="9999900001",
                email_hash=hash_identifier("admin@formfix.gov.in"),
                phone_hash=hash_identifier("9999900001"),
                role="admin",
                is_verified=True
            )
            db.add(user)
            db.commit()
            db.refresh(user)
    else:
        user = db.query(User).filter(User.email == "demo.student@formfix.in").first()
        if not user:
            user = User(
                full_name="Sunita Devi (Demo Student)",
                email="demo.student@formfix.in",
                phone="9876543210",
                email_hash=hash_identifier("demo.student@formfix.in"),
                phone_hash=hash_identifier("9876543210"),
                role="student",
                is_verified=True
            )
            db.add(user)
            db.commit()
            db.refresh(user)

    # Create active session
    raw_token = generate_session_token()
    token_hash = hash_session_token(raw_token)
    session_expiry = get_session_expiry()

    session_rec = SessionModel(
        user_id=user.id,
        token_hash=token_hash,
        expires_at=session_expiry,
        is_active=True
    )
    db.add(session_rec)
    db.commit()

    # Automatically grant DPDP consent for the demo student
    consent = db.query(Consent).filter(
        Consent.user_id == user.id,
        Consent.policy_version == settings.CONSENT_POLICY_VERSION
    ).first()

    if not consent:
        consent = Consent(
            user_id=user.id,
            policy_version=settings.CONSENT_POLICY_VERSION,
            accepted_at=now,
            ip_hash="demo-session"
        )
        db.add(consent)
        db.commit()

    log_audit_event(db, user.id, "DEMO_LOGIN", details=f"Demo login as {role}")

    return SessionResponse(
        session_token=raw_token,
        access_token=raw_token,
        user_id=user.id,
        full_name=user.full_name,
        role=user.role,
        expires_at=session_expiry.isoformat(),
        consent_required=False,
        masked_identifier=mask_email(user.email or "demo@formfix.in")
    )

# --- User Profile ---

@router.get("/me", response_model=UserProfileResponse)
def get_user_profile(
    session: SessionModel = Depends(get_current_session),
    db: DBSession = Depends(get_db)
):
    """Retrieves profile and DPDP status for the currently authenticated user."""
    user = session.user
    if not user:
        raise NotFoundError(message="User not found", hint="Session may be invalid")

    consent = db.query(Consent).filter(
        Consent.user_id == user.id,
        Consent.policy_version == settings.CONSENT_POLICY_VERSION
    ).first()

    return UserProfileResponse(
        id=user.id,
        full_name=user.full_name or "Registered Citizen",
        email=user.email,
        phone=mask_phone(user.phone or ""),
        role=user.role,
        created_at=user.created_at.isoformat() if user.created_at else None,
        has_consent=consent is not None
    )

# --- Legacy & Backwards Compatible OTP Routes ---

def _process_otp_request(phone: Optional[str], email: Optional[str], db: DBSession) -> OTPRequestResponse:
    if not phone and not email:
        raise ValidationError(message="Either phone number or email address is required", hint="Provide phone or email")

    now = datetime.now(timezone.utc)
    if phone:
        digits = _clean_phone(phone)
        if len(digits) != 10:
            raise ValidationError(message="Invalid mobile number format", hint="Enter 10-digit phone number")
        masked = mask_phone(digits)
        id_hash = hash_identifier(digits)
    else:
        clean_em = email.strip().lower()
        masked = mask_email(clean_em)
        id_hash = hash_identifier(clean_em)

    # Check cooldown
    active_recent_otp = db.query(OTPRecord).filter(
        OTPRecord.identifier_hash == id_hash,
        OTPRecord.is_used == False,
        OTPRecord.expires_at > now
    ).order_by(OTPRecord.created_at.desc()).first()

    if active_recent_otp and active_recent_otp.resend_cooldown_until:
        cooldown_target = active_recent_otp.resend_cooldown_until
        if cooldown_target.tzinfo is None:
            cooldown_target = cooldown_target.replace(tzinfo=timezone.utc)
        if now < cooldown_target:
            rem = int((cooldown_target - now).total_seconds())
            raise RateLimitError(message=f"Please wait {rem} second(s) before requesting another OTP", hint="Wait for cooldown")

    # Invalidate previous unused OTPs
    db.query(OTPRecord).filter(
        OTPRecord.identifier_hash == id_hash,
        OTPRecord.is_used == False
    ).update({"is_used": True})
    db.commit()

    otp_code = f"{secrets.randbelow(900000) + 100000:06d}"
    salt = secrets.token_hex(16)
    otp_hash = hashlib.sha256(f"{salt}:{otp_code}".encode("utf-8")).hexdigest()

    rec = OTPRecord(
        identifier_hash=id_hash,
        otp_hash=otp_hash,
        salt=salt,
        purpose="auth",
        attempts=0,
        is_used=False,
        expires_at=now + timedelta(minutes=OTP_EXPIRY_MINUTES),
        resend_cooldown_until=now + timedelta(seconds=RESEND_COOLDOWN_SECONDS)
    )
    db.add(rec)
    db.commit()

    return OTPRequestResponse(
        status="OTP_SENT",
        message="Verification OTP sent successfully",
        masked_target=masked,
        cooldown_seconds=RESEND_COOLDOWN_SECONDS,
        demo_otp=otp_code
    )

def _process_otp_verify(phone: Optional[str], email: Optional[str], otp: str, db: DBSession) -> SessionResponse:
    if not phone and not email:
        raise ValidationError(message="Either phone or email must be provided", hint="Provide phone or email")

    now = datetime.now(timezone.utc)
    if phone:
        digits = _clean_phone(phone)
        masked = mask_phone(digits)
        id_hash = hash_identifier(digits)
        user_filter = User.phone_hash == id_hash
    else:
        clean_em = email.strip().lower()
        masked = mask_email(clean_em)
        id_hash = hash_identifier(clean_em)
        user_filter = User.email_hash == id_hash

    record = db.query(OTPRecord).filter(
        OTPRecord.identifier_hash == id_hash,
        OTPRecord.is_used == False
    ).order_by(OTPRecord.created_at.desc()).first()

    if not record:
        raise AuthenticationError(message="No active OTP found. Please request an OTP first.", hint="Click Request OTP")

    rec_exp = record.expires_at
    if rec_exp.tzinfo is None:
        rec_exp = rec_exp.replace(tzinfo=timezone.utc)

    if now > rec_exp:
        record.is_used = True
        db.commit()
        raise AuthenticationError(message="OTP has expired. Please request a new OTP.", hint="Valid for 10 minutes")

    if record.attempts >= MAX_ATTEMPTS:
        record.is_used = True
        db.commit()
        raise RateLimitError(message="Maximum verification attempts exceeded.", hint="Please request a new OTP")

    clean_otp = otp.strip()
    provided_hash = hashlib.sha256(f"{record.salt}:{clean_otp}".encode("utf-8")).hexdigest()

    if provided_hash != record.otp_hash:
        record.attempts += 1
        db.commit()
        rem = max(0, MAX_ATTEMPTS - record.attempts)
        if rem == 0:
            record.is_used = True
            db.commit()
            raise RateLimitError(message="Maximum verification attempts exceeded.", hint="Please request a new OTP")
        raise AuthenticationError(message=f"Invalid OTP code entered. {rem} attempt(s) remaining.", hint="Check the 6-digit code")

    record.is_used = True
    db.commit()

    user = db.query(User).filter(user_filter).first()
    if not user:
        user = User(
            phone_hash=id_hash if phone else None,
            email_hash=id_hash if email else None,
            role="citizen",
            is_verified=True
        )
        db.add(user)
        db.commit()
        db.refresh(user)

    raw_token = generate_session_token()
    token_hash = hash_session_token(raw_token)
    session_expiry = get_session_expiry()

    session_rec = SessionModel(
        user_id=user.id,
        token_hash=token_hash,
        expires_at=session_expiry,
        is_active=True
    )
    db.add(session_rec)
    db.commit()

    consent = db.query(Consent).filter(
        Consent.user_id == user.id,
        Consent.policy_version == settings.CONSENT_POLICY_VERSION
    ).first()

    return SessionResponse(
        session_token=raw_token,
        access_token=raw_token,
        user_id=user.id,
        full_name=user.full_name,
        role=user.role,
        expires_at=session_expiry.isoformat(),
        consent_required=consent is None,
        masked_identifier=masked
    )

@router.post("/otp/request", response_model=OTPRequestResponse)
def request_otp_json(payload: OTPRequest, db: DBSession = Depends(get_db)):
    return _process_otp_request(payload.phone, payload.email, db)

@router.post("/request-otp", response_model=OTPRequestResponse)
def request_otp_query(
    mobile: Optional[str] = Query(None),
    phone: Optional[str] = Query(None),
    email: Optional[str] = Query(None),
    db: DBSession = Depends(get_db)
):
    target_phone = mobile or phone
    return _process_otp_request(target_phone, email, db)

@router.post("/otp/verify", response_model=SessionResponse)
def verify_otp_json(payload: OTPVerify, db: DBSession = Depends(get_db)):
    return _process_otp_verify(payload.phone, payload.email, payload.otp, db)

@router.post("/verify-otp", response_model=SessionResponse)
def verify_otp_query(
    mobile: Optional[str] = Query(None),
    phone: Optional[str] = Query(None),
    email: Optional[str] = Query(None),
    otp: str = Query(...),
    db: DBSession = Depends(get_db)
):
    target_phone = mobile or phone
    return _process_otp_verify(target_phone, email, otp, db)

@router.post("/logout")
def logout(
    session: SessionModel = Depends(get_current_session),
    db: DBSession = Depends(get_db)
):
    session.is_active = False
    db.commit()
    log_audit_event(db, session.user_id, "USER_LOGOUT", details="Session logged out")
    return {"status": "LOGGED_OUT", "message": "Session invalidated successfully."}
