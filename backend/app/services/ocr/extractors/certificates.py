import re
from typing import Dict
from app.services.ocr.extractors.base import ExtractedField, DocumentExtractionResult, CONFIDENCE_THRESHOLD

def extract_certificate_fields(raw_text: str, doc_type: str = "income_certificate", base_confidence: float = 0.95) -> DocumentExtractionResult:
    """
    Extracts fields from UP Government Revenue Department Income / Caste Certificates.
    """
    fields: Dict[str, ExtractedField] = {}

    # 1. Certificate Number
    cert_match = re.search(r"(?:Certificate\s*No|प्रमाण\s*पत्र\s*क्रमांक)[:\s]*([A-Za-z0-9/-]+)", raw_text, re.IGNORECASE)
    cert_no = cert_match.group(1).strip() if cert_match else ""
    fields["certificate_no"] = ExtractedField(
        field_name="certificate_no",
        value=cert_no,
        raw_value=cert_no,
        confidence=base_confidence if cert_no else 0.0,
        is_low_confidence=not cert_no or base_confidence < CONFIDENCE_THRESHOLD,
        validation_passed=bool(cert_no)
    )

    # 2. Applicant Name
    name_match = re.search(r"(?:Name|नाम|प्रमाणित\s*किया\s*जाता\s*है\s*कि)[:\s]+([A-Za-z\s]+)", raw_text, re.IGNORECASE)
    app_name = name_match.group(1).strip().split("\n")[0].strip() if name_match else ""
    if app_name:
        app_name = re.sub(r"^(Shri|Smt\.|Km\.|Mr\.)\s*", "", app_name, flags=re.IGNORECASE).strip()

    fields["applicant_name"] = ExtractedField(
        field_name="applicant_name",
        value=app_name,
        raw_value=app_name,
        confidence=base_confidence if app_name else 0.0,
        is_low_confidence=not app_name or base_confidence < CONFIDENCE_THRESHOLD,
        validation_passed=bool(app_name)
    )

    # 3. Father's Name
    father_match = re.search(r"(?:Father(?:'s)?\s*Name|पिता\s*का\s*नाम|आत्मज)[:\s]+([A-Za-z\s]+)", raw_text, re.IGNORECASE)
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

    # 4. Issue Date
    date_match = re.search(r"(?:Issue\s*Date|दिनांक|जारी\s*दिनांक)[:\s]*([0-3]?\d[/-][0-1]?\d[/-]\d{4})", raw_text, re.IGNORECASE)
    if not date_match:
        date_match = re.search(r"\b([0-3]\d/[0-1]\d/\d{4})\b", raw_text)

    issue_date = date_match.group(1).replace("-", "/") if date_match else ""
    fields["issue_date"] = ExtractedField(
        field_name="issue_date",
        value=issue_date,
        raw_value=issue_date,
        confidence=base_confidence if issue_date else 0.0,
        is_low_confidence=not issue_date or base_confidence < CONFIDENCE_THRESHOLD,
        validation_passed=bool(issue_date),
        hint="Certificate issue date extracted" if issue_date else "Issue date not detected"
    )

    # 5. Type-specific fields
    if doc_type == "income_certificate":
        income_match = re.search(r"(?:Annual\s*Income|वार्षिक\s*आय)[:\s]*(?:Rs\.?|₹)?\s*([0-9,]+)", raw_text, re.IGNORECASE)
        income_val = re.sub(r"\D", "", income_match.group(1)) if income_match else ""
        fields["annual_income"] = ExtractedField(
            field_name="annual_income",
            value=income_val,
            raw_value=income_val,
            confidence=base_confidence if income_val else 0.0,
            is_low_confidence=not income_val or base_confidence < CONFIDENCE_THRESHOLD,
            validation_passed=bool(income_val)
        )
    elif doc_type == "caste_certificate":
        caste_match = re.search(r"\b(OBC|SC|ST|GENERAL|पिछड़ा\s*वर्ग|अनुसूचित\s*जाति|अनुसूचित\s*जनजाति)\b", raw_text, re.IGNORECASE)
        caste_val = caste_match.group(1).upper() if caste_match else ""
        if "पिछड़ा" in caste_val:
            caste_val = "OBC"
        elif "अनुसूचित जाति" in caste_val:
            caste_val = "SC"
        elif "अनुसूचित जनजाति" in caste_val:
            caste_val = "ST"

        fields["caste_category"] = ExtractedField(
            field_name="caste_category",
            value=caste_val,
            raw_value=caste_val,
            confidence=base_confidence if caste_val else 0.0,
            is_low_confidence=not caste_val or base_confidence < CONFIDENCE_THRESHOLD,
            validation_passed=bool(caste_val)
        )

    conf_scores = [f.confidence for f in fields.values()]
    overall = sum(conf_scores) / len(conf_scores) if conf_scores else 0.0

    return DocumentExtractionResult(
        document_type=doc_type,
        fields=fields,
        overall_confidence=overall,
        raw_text=raw_text
    )
