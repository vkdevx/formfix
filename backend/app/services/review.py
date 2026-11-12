import json
import re
from datetime import datetime, timezone
from typing import Dict, Any, Tuple, Optional
from sqlalchemy.orm import Session as DBSession

from app.models.document import UploadedDocument
from app.schemas.review import (
    ReviewFieldSchema,
    DocumentReviewGroup,
    ReviewGridResponse,
    ReviewConfirmResponse
)
from app.services.ocr.extractors.aadhaar import validate_verhoeff
from app.services.ocr.extractors.bank import validate_ifsc
from app.core.redaction import mask_aadhaar, mask_bank_account

# Bilingual Field Labels
FIELD_LABELS: Dict[str, Tuple[str, str]] = {
    "applicant_name": ("Applicant Name", "आवेदक का नाम"),
    "candidate_name": ("Candidate Name", "परीक्षार्थी का नाम"),
    "father_name": ("Father / Guardian Name", "पिता / अभिभावक का नाम"),
    "dob": ("Date of Birth", "जन्म तिथि"),
    "gender": ("Gender", "लिंग"),
    "aadhaar_number": ("Aadhaar Number", "आधार संख्या"),
    "account_number": ("Bank Account Number", "बैंक खाता संख्या"),
    "account_holder_name": ("Account Holder Name", "खाताधारक का नाम"),
    "ifsc_code": ("IFSC Code", "आईएफएससी कोड"),
    "bank_name": ("Bank Name", "बैंक का नाम"),
    "roll_number": ("Roll Number", "अनुक्रमांक"),
    "board": ("Education Board", "शिक्षा बोर्ड"),
    "passing_year": ("Passing Year", "उत्तीर्ण वर्ष"),
    "certificate_no": ("Certificate Number", "प्रमाण पत्र क्रमांक"),
    "issue_date": ("Issue Date", "जारी दिनांक"),
    "annual_income": ("Annual Family Income (₹)", "वार्षिक पारिवारिक आय (₹)"),
    "caste_category": ("Caste Category", "जाति श्रेणी"),
    "registration_no": ("Portal Registration Number", "पोर्टल पंजीकरण संख्या")
}

DOCUMENT_LABELS: Dict[str, Tuple[str, str]] = {
    "application": ("UP Scholarship Application Form", "छात्रवृत्ति आवेदन प्रपत्र"),
    "aadhaar": ("Aadhaar Card", "आधार कार्ड"),
    "marksheet": ("Academic Marksheet (High School / Inter)", "शैक्षणिक अंकपत्र"),
    "bank_passbook": ("Bank Passbook Copy", "बैंक पासबुक प्रति"),
    "income_certificate": ("Income Certificate", "आय प्रमाण पत्र"),
    "caste_certificate": ("Caste Certificate", "जाति प्रमाण पत्र")
}

def get_confidence_badge(conf: float) -> str:
    """Classifies confidence into high (green), medium (amber), or low (red)."""
    if conf >= 0.85:
        return "high"
    elif conf >= 0.70:
        return "medium"
    return "low"

def validate_and_format_field(field_name: str, new_value: str) -> Tuple[str, str, bool, Optional[str]]:
    """
    Validates a user-corrected value and applies masking if sensitive.
    Returns: (display_value, raw_value, validation_passed, hint)
    """
    val = new_value.strip()

    if field_name == "aadhaar_number":
        digits = re.sub(r"\D", "", val)
        if len(digits) == 12:
            is_valid = validate_verhoeff(digits)
            return mask_aadhaar(digits), digits, is_valid, "Aadhaar checksum valid" if is_valid else "Aadhaar Verhoeff checksum failed"
        elif len(digits) == 4:
            # User confirmed last 4 digits
            return f"XXXX XXXX {digits}", f"00000000{digits}", True, "Last 4 digits confirmed"
        return mask_aadhaar(digits), digits, False, "Aadhaar must be 12 digits"

    elif field_name == "account_number":
        digits = re.sub(r"\D", "", val)
        if 9 <= len(digits) <= 18:
            return mask_bank_account(digits), digits, True, "Bank account format valid"
        return mask_bank_account(digits), digits, False, "Account number must be between 9 and 18 digits"

    elif field_name == "ifsc_code":
        clean_ifsc = val.upper()
        is_valid = validate_ifsc(clean_ifsc)
        return clean_ifsc, clean_ifsc, is_valid, "Valid RBI IFSC format" if is_valid else "IFSC must be 11 characters and 5th character must be '0'"

    elif field_name in ["dob", "issue_date"]:
        val_clean = val.replace("-", "/")
        match = re.match(r"^([0-3]?\d)/([0-1]?\d)/(\d{4})$", val_clean)
        if match:
            day, month, year = int(match.group(1)), int(match.group(2)), int(match.group(3))
            if 1 <= day <= 31 and 1 <= month <= 12 and 1950 <= year <= 2030:
                formatted_date = f"{day:02d}/{month:02d}/{year:04d}"
                return formatted_date, formatted_date, True, "Valid date format"
        return val, val, False, "Date must follow DD/MM/YYYY format"

    elif field_name == "annual_income":
        digits = re.sub(r"\D", "", val)
        if digits and int(digits) > 0:
            return digits, digits, True, "Income format valid"
        return val, val, False, "Please enter numeric annual income"

    # Default text fields (names, etc.)
    return val, val, len(val) > 0, None

def apply_field_corrections(
    doc: UploadedDocument,
    corrections: Dict[str, str],
    db: DBSession
) -> Dict[str, Any]:
    """
    FR-06: Saves user corrections to the verification grid.
    User corrections become the authoritative source of truth for all subsequent rule checks.
    """
    data = json.loads(doc.extracted_data or "{}")

    for field_name, new_val in corrections.items():
        disp_val, raw_val, valid, hint = validate_and_format_field(field_name, new_val)

        data[field_name] = {
            "field_name": field_name,
            "value": disp_val,
            "raw_value": raw_val,
            "confidence": 1.0,  # User-confirmed values have 100% confidence
            "is_user_corrected": True,
            "is_low_confidence": False,
            "validation_passed": valid,
            "hint": hint or "Corrected by applicant"
        }

    doc.extracted_data = json.dumps(data)
    doc.has_corrections = True
    doc.reviewed_at = datetime.now(timezone.utc)

    # Recalculate overall confidence
    if data:
        conf_scores = [f.get("confidence", 0.0) for f in data.values()]
        doc.overall_confidence = sum(conf_scores) / len(conf_scores)

    db.commit()
    db.refresh(doc)
    return data

def build_session_review_grid(session_id: str, db: DBSession) -> ReviewGridResponse:
    """
    Assembles the complete interactive Review Grid across all uploaded documents.
    """
    docs = db.query(UploadedDocument).filter(
        UploadedDocument.session_id == session_id
    ).all()

    doc_groups = []
    total_fields = 0
    low_confidence_count = 0
    corrected_count = 0

    for doc in docs:
        extracted = json.loads(doc.extracted_data or "{}")
        field_schemas = {}

        for fname, finfo in extracted.items():
            total_fields += 1
            conf = float(finfo.get("confidence", 0.0))
            is_low = bool(finfo.get("is_low_confidence", False))
            is_corr = bool(finfo.get("is_user_corrected", False))

            if is_low:
                low_confidence_count += 1
            if is_corr:
                corrected_count += 1

            lbl_en, lbl_hi = FIELD_LABELS.get(fname, (fname.replace("_", " ").title(), fname))
            is_masked = fname in ["aadhaar_number", "account_number"]

            field_schemas[fname] = ReviewFieldSchema(
                field_name=fname,
                label_en=lbl_en,
                label_hi=lbl_hi,
                value=finfo.get("value", ""),
                confidence=conf,
                confidence_badge=get_confidence_badge(conf),
                is_user_corrected=is_corr,
                is_masked=is_masked,
                validation_passed=finfo.get("validation_passed", True),
                hint=finfo.get("hint")
            )

        doc_lbl_en, doc_lbl_hi = DOCUMENT_LABELS.get(
            doc.document_type,
            (doc.document_type.replace("_", " ").title(), doc.document_type)
        )

        doc_groups.append(DocumentReviewGroup(
            document_id=doc.id,
            document_type=doc.document_type,
            document_label_en=doc_lbl_en,
            document_label_hi=doc_lbl_hi,
            original_filename=doc.original_filename,
            has_corrections=bool(doc.has_corrections),
            overall_confidence=round(doc.overall_confidence or 0.0, 2),
            fields=field_schemas
        ))

    ready_for_audit = len(docs) > 0 and low_confidence_count == 0

    return ReviewGridResponse(
        session_id=session_id,
        documents=doc_groups,
        total_fields=total_fields,
        low_confidence_count=low_confidence_count,
        corrected_count=corrected_count,
        ready_for_audit=ready_for_audit
    )
