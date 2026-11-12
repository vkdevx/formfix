import re
from typing import Dict
from app.services.ocr.extractors.base import ExtractedField, DocumentExtractionResult, CONFIDENCE_THRESHOLD
from app.services.ocr.extractors.aadhaar import validate_verhoeff
from app.core.redaction import mask_aadhaar, mask_bank_account

def extract_application_fields(raw_text: str, base_confidence: float = 0.98) -> DocumentExtractionResult:
    """
    Extracts all candidate, academic, and banking information from the filled UP Scholarship Application Form.
    """
    fields: Dict[str, ExtractedField] = {}

    # 1. Registration Number
    reg_match = re.search(r"(?:Registration\s*(?:No|Number)|पंजीकरण\s*संख्या)[:\s]*([A-Za-z0-9]+)", raw_text, re.IGNORECASE)
    reg_no = reg_match.group(1).strip() if reg_match else ""
    fields["registration_no"] = ExtractedField(
        field_name="registration_no",
        value=reg_no,
        raw_value=reg_no,
        confidence=base_confidence if reg_no else 0.0,
        is_low_confidence=not reg_no or base_confidence < CONFIDENCE_THRESHOLD,
        validation_passed=bool(reg_no)
    )

    # 2. Applicant Name
    name_match = re.search(r"(?:Applicant(?:'s)?\s*Name|Candidate(?:'s)?\s*Name|छात्र/छात्रा\s*का\s*नाम)[:\s]+([A-Za-z\s]+)", raw_text, re.IGNORECASE)
    app_name = name_match.group(1).strip().split("\n")[0].strip() if name_match else ""
    if app_name:
        app_name = re.sub(r"^(Shri|Km\.|Kumari|Mr\.)\s*", "", app_name, flags=re.IGNORECASE).strip()

    fields["applicant_name"] = ExtractedField(
        field_name="applicant_name",
        value=app_name,
        raw_value=app_name,
        confidence=base_confidence if app_name else 0.0,
        is_low_confidence=not app_name or base_confidence < CONFIDENCE_THRESHOLD,
        validation_passed=bool(app_name)
    )

    # 3. Father / Guardian Name
    father_match = re.search(r"(?:Father(?:'s)?\s*Name|Guardian(?:'s)?\s*Name|पिता\s*का\s*नाम)[:\s]+([A-Za-z\s]+)", raw_text, re.IGNORECASE)
    father_name = father_match.group(1).strip().split("\n")[0].strip() if father_match else ""
    if father_name:
        father_name = re.sub(r"^(Shri|Mr\.)\s*", "", father_name, flags=re.IGNORECASE).strip()

    fields["father_name"] = ExtractedField(
        field_name="father_name",
        value=father_name,
        raw_value=father_name,
        confidence=base_confidence if father_name else 0.0,
        is_low_confidence=not father_name or base_confidence < CONFIDENCE_THRESHOLD,
        validation_passed=bool(father_name)
    )

    # 4. Date of Birth (DOB)
    dob_match = re.search(r"(?:DOB|D\.O\.B|जन्म\s*तिथि|Date\s*of\s*Birth)[:\s]*([0-3]?\d[/-][0-1]?\d[/-]\d{4})", raw_text, re.IGNORECASE)
    if not dob_match:
        dob_match = re.search(r"\b([0-3]\d/[0-1]\d/\d{4})\b", raw_text)

    dob_val = dob_match.group(1).replace("-", "/") if dob_match else ""
    fields["dob"] = ExtractedField(
        field_name="dob",
        value=dob_val,
        raw_value=dob_val,
        confidence=base_confidence if dob_val else 0.0,
        is_low_confidence=not dob_val or base_confidence < CONFIDENCE_THRESHOLD,
        validation_passed=bool(dob_val)
    )

    # 5. Aadhaar Number (Masked)
    aadhaar_match = re.search(r"(?:Aadhaar|UIDAI|आधार)?\s*(?:No|Number)?[:\s]*(\d{4}[\s-]?\d{4}[\s-]?\d{4}|\d{12})\b", raw_text, re.IGNORECASE)
    if aadhaar_match:
        raw_aadhaar = re.sub(r"\D", "", aadhaar_match.group(1))
        is_valid = validate_verhoeff(raw_aadhaar)
        fields["aadhaar_number"] = ExtractedField(
            field_name="aadhaar_number",
            value=mask_aadhaar(raw_aadhaar),
            raw_value=raw_aadhaar,
            confidence=base_confidence if is_valid else 0.65,
            is_low_confidence=not is_valid or base_confidence < CONFIDENCE_THRESHOLD,
            validation_passed=is_valid,
            hint="Aadhaar format valid" if is_valid else "Aadhaar checksum failed"
        )
    else:
        fields["aadhaar_number"] = ExtractedField(
            field_name="aadhaar_number",
            value="",
            raw_value="",
            confidence=0.0,
            is_low_confidence=True,
            validation_passed=False
        )

    # 6. Bank Account Number (Masked)
    acct_match = re.search(r"(?:Bank\s*A/?C|Account|खाता|A/?C)\s*(?:No\.?|Number|संख्या)?[:\s]*(\d{9,18})\b", raw_text, re.IGNORECASE)
    if acct_match:
        raw_acct = acct_match.group(1)
        fields["account_number"] = ExtractedField(
            field_name="account_number",
            value=mask_bank_account(raw_acct),
            raw_value=raw_acct,
            confidence=base_confidence,
            is_low_confidence=base_confidence < CONFIDENCE_THRESHOLD,
            validation_passed=True
        )
    else:
        fields["account_number"] = ExtractedField(
            field_name="account_number",
            value="",
            raw_value="",
            confidence=0.0,
            is_low_confidence=True,
            validation_passed=False
        )

    # 7. IFSC Code
    ifsc_match = re.search(r"\b([A-Z]{4}0[A-Z0-9]{6})\b", raw_text)
    ifsc_val = ifsc_match.group(1) if ifsc_match else ""
    fields["ifsc_code"] = ExtractedField(
        field_name="ifsc_code",
        value=ifsc_val,
        raw_value=ifsc_val,
        confidence=base_confidence if ifsc_val else 0.0,
        is_low_confidence=not ifsc_val or base_confidence < CONFIDENCE_THRESHOLD,
        validation_passed=bool(ifsc_val)
    )

    conf_scores = [f.confidence for f in fields.values()]
    overall = sum(conf_scores) / len(conf_scores) if conf_scores else 0.0

    return DocumentExtractionResult(
        document_type="application",
        fields=fields,
        overall_confidence=overall,
        raw_text=raw_text
    )
