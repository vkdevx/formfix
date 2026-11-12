import os
import shutil
import uuid
import logging
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy.orm import Session as DBSession
from cryptography.fernet import Fernet

from app.config import settings
from app.models.user import SessionModel
from app.models.document import UploadedDocument

logger = logging.getLogger(__name__)

# Initialize Fernet cipher for encryption-at-rest
try:
    _cipher = Fernet(settings.STORAGE_ENCRYPTION_KEY.encode("utf-8") if isinstance(settings.STORAGE_ENCRYPTION_KEY, str) else settings.STORAGE_ENCRYPTION_KEY)
except Exception as e:
    logger.warning(f"Failed to initialize Fernet with configured key, generating ephemeral fallback: {e}")
    _cipher = Fernet(Fernet.generate_key())

def get_session_dir(session_id: str) -> str:
    """Returns the isolated ephemeral folder path for a given session."""
    path = os.path.join(settings.TEMP_STORAGE_DIR, session_id)
    os.makedirs(path, exist_ok=True)
    return path

def save_ephemeral_file(session_id: str, original_filename: str, content: bytes, encrypt: bool = True) -> str:
    """
    Saves an uploaded document into the session's isolated temporary directory
    using a randomized filename.
    Per Phase 4: Encrypts files at rest with AES-128 authenticated encryption (Fernet).
    """
    session_dir = get_session_dir(session_id)
    ext = os.path.splitext(original_filename)[1].lower()
    random_filename = f"{uuid.uuid4().hex[:12]}{ext}"
    file_path = os.path.join(session_dir, random_filename)

    payload_to_write = _cipher.encrypt(content) if encrypt else content

    with open(file_path, "wb") as f:
        f.write(payload_to_write)

    return file_path

def read_ephemeral_file(file_path: str) -> bytes:
    """
    Reads an ephemeral file from disk and decrypts it in-memory.
    If decryption fails or file is not encrypted, falls back safely to raw bytes.
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")

    with open(file_path, "rb") as f:
        raw_bytes = f.read()

    try:
        decrypted = _cipher.decrypt(raw_bytes)
        return decrypted
    except Exception:
        # File may have been stored unencrypted
        return raw_bytes

def delete_single_file(file_path: str) -> bool:
    """Deletes a single file from temporary storage if it exists."""
    try:
        if file_path and os.path.exists(file_path):
            os.remove(file_path)
            return True
    except OSError:
        pass
    return False

def purge_session_files(session_id: str) -> int:
    """
    Deletes all temporary files and the folder for a given session.
    Called on session expiry, audit completion, or explicit user deletion (FR-12).
    """
    session_dir = os.path.join(settings.TEMP_STORAGE_DIR, session_id)
    count = 0
    if os.path.exists(session_dir):
        for root, dirs, files in os.walk(session_dir):
            count += len(files)
        shutil.rmtree(session_dir, ignore_errors=True)
    return count

def cleanup_expired_sessions_and_files(db: DBSession) -> dict:
    """
    Worker function to purge expired sessions (> 30 mins) and wipe their disk storage.
    Per DPDP Act 2023 & FormFix storage retention policy.
    """
    now = datetime.now(timezone.utc)
    expired_sessions = db.query(SessionModel).filter(
        (SessionModel.expires_at < now) | (SessionModel.is_active == False)
    ).all()

    purged_count = 0
    for sess in expired_sessions:
        purge_session_files(sess.id)
        sess.is_active = False
        purged_count += 1

    db.commit()
    return {
        "status": "PURGE_COMPLETE",
        "purged_sessions_count": purged_count,
        "timestamp": now.isoformat()
    }
