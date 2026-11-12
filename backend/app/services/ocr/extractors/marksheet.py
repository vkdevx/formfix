import re
from typing import Dict
from app.services.ocr.extractors.base import ExtractedField, DocumentExtractionResult, CONFIDENCE_THRESHOLD

def extract_marksheet_fields(raw_text: str, base_confidence: float = 0.95) -> DocumentExtractionResult:
    """
    Extracts Candidate Name, Father/Guardian Name, DOB, Roll Number, Board, and Year
    from academic marksheets (Class 10 / High School / Intermediate).
    """
    fields: Dict[str, ExtractedField] = {}
    lines = [l.strip() for l in raw_text.splitlines() if l.strip()]

    # 1. Candidate Name
    cand_match = re.search(r"(?:Candidate(?:'s)?\s*Name|Student(?:'s)?\s*Name|परीक्षार्थी\s*का\s*नाम|Name)[:\s]+([A-Za-z\s]+?)(?=(?:\s+Father|\s+Mother|\s+DOB|\s+Roll|\n|$))", raw_text, re.IGNORECASE)
    cand_name = cand_match.group(1).strip().split("\n")[0].strip() if cand_match else ""
    if cand_name:
        cand_name = re.sub(r"^(Shri|Km\.|Kumari|Mr\.)\s*", "", cand_name, flags=re.IGNORECASE).strip()

    fields["candidate_name"] = ExtractedField(
        field_name="candidate_name",
        value=cand_name,
        raw_value=cand_name,
        confidence=base_confidence if cand_name else 0.0,
        is_low_confidence=not cand_name or base_confidence < CONFIDENCE_THRESHOLD,
        validation_passed=bool(cand_name),
        hint="Candidate name verified from marksheet" if cand_name else "Candidate name not detected"
    )

    # 2. Father / Guardian Name
    father_match = re.search(r"(?:Father(?:'s)?\s*Name|Guardian(?:'s)?\s*Name|पिता\s*का\s*नाम)[:\s]+([A-Za-z\s]+?)(?=(?:\s+Mother|\s+DOB|\s+Roll|\n|$))", raw_text, re.IGNORECASE)
    father_name = father_match.group(1).strip().split("\n")[0].strip() if father_match else ""
    if father_name:
        father_name = re.sub(r"^(Shri|Mr\.)\s*", "", father_name, flags=re.IGNORECASE).strip()

    fields["father_name"] = ExtractedField(
        field_name="father_name",
        value=father_name,
        raw_value=father_name,
        confidence=base_confidence if father_name else 0.0,
        is_low_confidence=not father_name or base_confidence < CONFIDENCE_THRESHOLD,
        validation_passed=bool(father_name),
        hint="Father/Guardian name extracted" if father_name else "Father/Guardian name not detected"
    )

    # 3. Date of Birth (DOB)
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
        validation_passed=bool(dob_val),
        hint="DOB detected" if dob_val else "DOB not detected on marksheet"
    )

    # 4. Roll Number
    roll_match = re.search(r"(?:Roll\s*(?:No|Number)|अनुक्रमांक)[:\s]*([A-Za-z0-9]+)", raw_text, re.IGNORECASE)
    roll_val = roll_match.group(1).strip() if roll_match else ""
    fields["roll_number"] = ExtractedField(
        field_name="roll_number",
        value=roll_val,
        raw_value=roll_val,
        confidence=base_confidence if roll_val else 0.0,
        is_low_confidence=not roll_val or base_confidence < CONFIDENCE_THRESHOLD,
        validation_passed=bool(roll_val)
    )

    # 5. Board
    board_val = "UP Board"
    if "cbse" in raw_text.lower():
        board_val = "CBSE"
    elif "icse" in raw_text.lower() or "cisce" in raw_text.lower():
        board_val = "CISCE"
    elif "madhyamik" in raw_text.lower() or "upmsp" in raw_text.lower() or "uttar pradesh" in raw_text.lower():
        board_val = "UP Board"

    fields["board"] = ExtractedField(
        field_name="board",
        value=board_val,
        raw_value=board_val,
        confidence=base_confidence,
        is_low_confidence=False,
        validation_passed=True
    )

    # 6. Passing Year
    year_match = re.search(r"\b(20[12]\d)\b", raw_text)
    year_val = year_match.group(1) if year_match else ""
    fields["passing_year"] = ExtractedField(
        field_name="passing_year",
        value=year_val,
        raw_value=year_val,
        confidence=base_confidence if year_val else 0.0,
        is_low_confidence=not year_val or base_confidence < CONFIDENCE_THRESHOLD,
        validation_passed=bool(year_val)
    )

    conf_scores = [f.confidence for f in fields.values()]
    overall = sum(conf_scores) / len(conf_scores) if conf_scores else 0.0

    return DocumentExtractionResult(
        document_type="marksheet",
        fields=fields,
        overall_confidence=overall,
        raw_text=raw_text
    )
