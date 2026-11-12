import re
from typing import Dict, Any
from app.services.ocr.extractors.base import ExtractedField, DocumentExtractionResult, CONFIDENCE_THRESHOLD
from app.core.redaction import mask_aadhaar

def validate_verhoeff(num: str) -> bool:
    """
    Verhoeff algorithm implementation for official 12-digit Aadhaar checksum validation.
    """
    d = [
        [0, 1, 2, 3, 4, 5, 6, 7, 8, 9],
        [1, 2, 3, 4, 0, 6, 7, 8, 9, 5],
        [2, 3, 4, 0, 1, 7, 8, 9, 5, 6],
        [3, 4, 0, 1, 2, 8, 9, 5, 6, 7],
        [4, 0, 1, 2, 3, 9, 5, 6, 7, 8],
        [5, 9, 8, 7, 6, 0, 4, 3, 2, 1],
        [6, 5, 9, 8, 7, 1, 0, 4, 3, 2],
        [7, 6, 5, 9, 8, 2, 1, 0, 4, 3],
        [8, 7, 6, 5, 9, 3, 2, 1, 0, 4],
        [9, 8, 7, 6, 5, 4, 3, 2, 1, 0]
    ]
    p = [
        [0, 1, 2, 3, 4, 5, 6, 7, 8, 9],
        [1, 5, 7, 6, 2, 8, 3, 0, 9, 4],
        [5, 8, 0, 3, 7, 9, 6, 1, 4, 2],
        [8, 9, 1, 6, 0, 4, 3, 5, 2, 7],
        [9, 4, 5, 3, 1, 2, 6, 8, 7, 0],
        [4, 2, 8, 6, 5, 7, 3, 9, 0, 1],
        [2, 7, 9, 3, 8, 0, 6, 4, 1, 5],
        [7, 0, 4, 6, 9, 1, 3, 2, 5, 8]
    ]
    inv = [0, 4, 3, 2, 1, 5, 6, 7, 8, 9]

    digits = [int(c) for c in str(num) if c.isdigit()]
    if len(digits) != 12:
        return False
    c = 0
    for i, item in enumerate(reversed(digits)):
        c = d[c][p[i % 8][item]]
    return c == 0

def extract_aadhaar_fields(raw_text: str, base_confidence: float = 0.95) -> DocumentExtractionResult:
    """
    Extracts name, DOB, gender, and Aadhaar number from raw text.
    Sensitive Aadhaar number is masked in output (FR-09).
    """
    fields: Dict[str, ExtractedField] = {}
    lines = [l.strip() for l in raw_text.splitlines() if l.strip()]

    # 1. Aadhaar Number (12 digits, often formatted as 4-4-4)
    aadhaar_match = re.search(r"\b(\d{4})[\s-](\d{4})[\s-](\d{4})\b", raw_text)
    if not aadhaar_match:
        aadhaar_match = re.search(r"\b\d{12}\b", raw_text)

    if aadhaar_match:
        raw_num = re.sub(r"\D", "", aadhaar_match.group(0))
        is_valid_chk = validate_verhoeff(raw_num)
        masked_val = mask_aadhaar(raw_num)
        conf = base_confidence if is_valid_chk else min(base_confidence, 0.65)
        fields["aadhaar_number"] = ExtractedField(
            field_name="aadhaar_number",
            value=masked_val,
            raw_value=raw_num,
            confidence=conf,
            is_low_confidence=conf < CONFIDENCE_THRESHOLD,
            validation_passed=is_valid_chk,
            hint="Aadhaar number format and Verhoeff checksum valid" if is_valid_chk else "Invalid Verhoeff checksum"
        )
    else:
        fields["aadhaar_number"] = ExtractedField(
            field_name="aadhaar_number",
            value="",
            raw_value="",
            confidence=0.0,
            is_low_confidence=True,
            validation_passed=False,
            hint="Could not detect 12-digit Aadhaar number"
        )

    # 2. Date of Birth (DOB)
    dob_match = re.search(r"(?:DOB|D\.O\.B|जन्म\s*तिथि|Date\s*of\s*Birth)[:\s]*([0-3]?\d[/-][0-1]?\d[/-]\d{4})", raw_text, re.IGNORECASE)
    if not dob_match:
        # Search standalone date pattern
        dob_match = re.search(r"\b([0-3]\d/[0-1]\d/\d{4})\b", raw_text)

    if dob_match:
        dob_val = dob_match.group(1).replace("-", "/")
        fields["dob"] = ExtractedField(
            field_name="dob",
            value=dob_val,
            raw_value=dob_val,
            confidence=base_confidence,
            is_low_confidence=base_confidence < CONFIDENCE_THRESHOLD,
            validation_passed=True
        )
    else:
        fields["dob"] = ExtractedField(
            field_name="dob",
            value="",
            raw_value="",
            confidence=0.0,
            is_low_confidence=True,
            validation_passed=False,
            hint="Date of birth not found"
        )

    # 3. Gender
    gender_match = re.search(r"\b(FEMALE|MALE|TRANSGENDER|महिला|पुरुष)\b", raw_text, re.IGNORECASE)
    if gender_match:
        g_raw = gender_match.group(1).upper()
        g_norm = "FEMALE" if g_raw in ["FEMALE", "महिला"] else "MALE"
        fields["gender"] = ExtractedField(
            field_name="gender",
            value=g_norm,
            raw_value=gender_match.group(1),
            confidence=base_confidence,
            is_low_confidence=False,
            validation_passed=True
        )
    else:
        fields["gender"] = ExtractedField(
            field_name="gender",
            value="",
            raw_value="",
            confidence=0.0,
            is_low_confidence=True,
            validation_passed=False
        )

    # 4. Name extraction heuristics
    name_val = ""
    # Look for name label if present
    name_label_match = re.search(r"(?:Name|नाम)[:\s]+([A-Za-z\s]+)", raw_text, re.IGNORECASE)
    if name_label_match:
        name_val = name_label_match.group(1).strip().split("\n")[0].strip()

    if not name_val:
        # Look for English words appearing before the DOB line
        for i, line in enumerate(lines):
            if any(term in line.lower() for term in ["dob", "birth", "जन्म", "year of birth"]):
                if i > 0:
                    cand = lines[i - 1].strip()
                    if not any(k in cand.lower() for k in ["government", "india", "आधार", "aadhaar", "authority"]):
                        name_val = cand
                        break

    if name_val:
        # Clean honorifics or junk
        name_clean = re.sub(r"^(Mr\.|Ms\.|Mrs\.|Shri|Smt\.)\s*", "", name_val, flags=re.IGNORECASE).strip()
        fields["applicant_name"] = ExtractedField(
            field_name="applicant_name",
            value=name_clean,
            raw_value=name_val,
            confidence=base_confidence,
            is_low_confidence=base_confidence < CONFIDENCE_THRESHOLD,
            validation_passed=len(name_clean) > 2
        )
    else:
        fields["applicant_name"] = ExtractedField(
            field_name="applicant_name",
            value="",
            raw_value="",
            confidence=0.0,
            is_low_confidence=True,
            validation_passed=False,
            hint="Applicant name not clearly detected"
        )

    # Calculate overall confidence
    conf_scores = [f.confidence for f in fields.values()]
    overall = sum(conf_scores) / len(conf_scores) if conf_scores else 0.0

    return DocumentExtractionResult(
        document_type="aadhaar",
        fields=fields,
        overall_confidence=overall,
        raw_text=raw_text
    )
