from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from rapidfuzz import fuzz

from app.services.matching.normalise import normalize_name, normalize_date_to_iso
from app.services.matching.transliterate import (
    is_devanagari,
    transliterate_devanagari_to_roman,
    generate_phonetic_variations
)
from app.core.redaction import mask_aadhaar, mask_bank_account

# Three-band thresholds per PRD Section 8.2 & Architecture Section 8
MATCH_THRESHOLD = 95
NEEDS_REVIEW_THRESHOLD = 80

@dataclass
class MatchResult:
    status: str  # "match", "needs_review", "mismatch"
    score: int
    raw_val_a: str
    raw_val_b: str
    normalized_a: str
    normalized_b: str
    reason_en: str
    reason_hi: str

def classify_score_band(score: int) -> str:
    """Classifies match score into 3 bands: 'match', 'needs_review', 'mismatch'."""
    if score >= MATCH_THRESHOLD:
        return "match"
    elif score >= NEEDS_REVIEW_THRESHOLD:
        return "needs_review"
    return "mismatch"

def compare_names(name_a: str, name_b: str) -> MatchResult:
    """
    Performs fuzzy comparison of two Indian names using:
    1. Honorific and abbreviation normalization
    2. Devanagari to Roman transliteration
    3. Phonetic spelling variation expansion (e.g. Sunita vs Suneeta)
    4. RapidFuzz token sorting (handling word order differences)
    5. Three-band classification (Match >=95%, Needs Review 80-94%, Mismatch <80%)
    """
    if not name_a or not name_b:
        return MatchResult(
            status="mismatch",
            score=0,
            raw_val_a=name_a or "",
            raw_val_b=name_b or "",
            normalized_a="",
            normalized_b="",
            reason_en="One or both names are missing.",
            reason_hi="एक या दोनों नाम अनुपलब्ध हैं।"
        )

    # 1. Transliterate if Hindi
    norm_a = transliterate_devanagari_to_roman(name_a) if is_devanagari(name_a) else name_a
    norm_b = transliterate_devanagari_to_roman(name_b) if is_devanagari(name_b) else name_b

    # 2. Normalize honorifics, punctuation, and abbreviations
    clean_a = normalize_name(norm_a)
    clean_b = normalize_name(norm_b)

    # Exact match after normalization
    if clean_a == clean_b:
        return MatchResult(
            status="match",
            score=100,
            raw_val_a=name_a,
            raw_val_b=name_b,
            normalized_a=clean_a,
            normalized_b=clean_b,
            reason_en=f"Names are an exact match ('{name_a}').",
            reason_hi=f"नाम पूरी तरह मेल खाते हैं ('{name_a}')।"
        )

    # 3. Generate phonetic variations and calculate RapidFuzz scores
    vars_a = generate_phonetic_variations(clean_a)
    vars_b = generate_phonetic_variations(clean_b)

    best_score = 0
    for va in vars_a:
        for vb in vars_b:
            s_token_sort = fuzz.token_sort_ratio(va, vb)
            s_token_set = fuzz.token_set_ratio(va, vb)
            s_ratio = fuzz.ratio(va, vb)
            candidate_max = max(s_token_sort, s_token_set, s_ratio)
            if candidate_max > best_score:
                best_score = int(candidate_max)

    status = classify_score_band(best_score)

    if status == "match":
        reason_en = f"Names match with {best_score}% similarity ('{name_a}' vs '{name_b}')."
        reason_hi = f"नाम {best_score}% समानता के साथ मेल खाते हैं ('{name_a}' बनाम '{name_b}')।"
    elif status == "needs_review":
        reason_en = f"Minor spelling difference detected ({best_score}% similarity): '{name_a}' vs '{name_b}'. Please confirm if this is the same person."
        reason_hi = f"वर्तनी में थोड़ा अंतर मिला ({best_score}% समानता): '{name_a}' बनाम '{name_b}'। कृपया पुष्टि करें कि यह वही व्यक्ति है।"
    else:
        reason_en = f"Significant name mismatch ({best_score}% similarity): '{name_a}' vs '{name_b}'. This is a frequent rejection reason."
        reason_hi = f"नाम में गंभीर विसंगति ({best_score}% समानता): '{name_a}' बनाम '{name_b}'। यह आवेदन खारिज होने का प्रमुख कारण बनता है।"

    return MatchResult(
        status=status,
        score=best_score,
        raw_val_a=name_a,
        raw_val_b=name_b,
        normalized_a=clean_a,
        normalized_b=clean_b,
        reason_en=reason_en,
        reason_hi=reason_hi
    )

def compare_dobs(dob_a: str, dob_b: str) -> MatchResult:
    """
    Compares two dates of birth. Requires exact match after ISO normalization.
    """
    iso_a = normalize_date_to_iso(dob_a)
    iso_b = normalize_date_to_iso(dob_b)

    if not iso_a or not iso_b:
        return MatchResult(
            status="mismatch",
            score=0,
            raw_val_a=dob_a or "",
            raw_val_b=dob_b or "",
            normalized_a=iso_a or "",
            normalized_b=iso_b or "",
            reason_en="Invalid or missing date of birth in one of the documents.",
            reason_hi="एक दस्तावेज़ में जन्म तिथि अमान्य या अनुपलब्ध है।"
        )

    if iso_a == iso_b:
        return MatchResult(
            status="match",
            score=100,
            raw_val_a=dob_a,
            raw_val_b=dob_b,
            normalized_a=iso_a,
            normalized_b=iso_b,
            reason_en=f"Date of birth matches exactly across documents ({dob_a}).",
            reason_hi=f"दस्तावेजों में जन्म तिथि पूरी तरह मेल खाती है ({dob_a})।"
        )
    else:
        return MatchResult(
            status="mismatch",
            score=0,
            raw_val_a=dob_a,
            raw_val_b=dob_b,
            normalized_a=iso_a,
            normalized_b=iso_b,
            reason_en=f"Date of birth mismatch: '{dob_a}' does not match '{dob_b}'. Government portals strictly reject DOB mismatches.",
            reason_hi=f"जन्म तिथि में विसंगति: '{dob_a}' और '{dob_b}' मेल नहीं खाते। पोर्टल जन्म तिथि में अंतर तुरंत खारिज करता है।"
        )

@dataclass
class CrossVerificationIssue:
    check_id: str
    status: str  # "match", "needs_review", "mismatch"
    severity: str  # "error", "warning", "info"
    doc_a: str
    field_a: str
    doc_b: str
    field_b: str
    score: int
    masked_value_a: str
    masked_value_b: str
    message_key: str
    reason_en: str
    reason_hi: str

def run_cross_verification(doc_map: Dict[str, Dict[str, Any]]) -> List[CrossVerificationIssue]:
    """
    FR-08 & PRD 8.3: Executes full cross-document fuzzy comparisons across:
    1. Applicant name: Aadhaar vs Marksheet
    2. Applicant name: Application Form vs Aadhaar
    3. Bank account holder vs Applicant Name
    4. DOB: Aadhaar vs Marksheet
    5. DOB: Application vs Marksheet
    6. Father/Guardian Name: Marksheet vs Application Form
    7. Bank Account Number: Passbook vs Application Form
    """
    issues: List[CrossVerificationIssue] = []

    def get_field(doc_type: str, *field_names: str) -> tuple[str, str]:
        d = doc_map.get(doc_type, {})
        for fname in field_names:
            f = d.get(fname)
            if isinstance(f, dict):
                val = f.get("value", "")
                if val:
                    return str(val), str(f.get("raw_value", val))
            elif f is not None and str(f).strip():
                return str(f), str(f)
        return "", ""

    # Check 1: Applicant Name: Aadhaar vs Marksheet
    if "aadhaar" in doc_map and "marksheet" in doc_map:
        name_a, raw_a = get_field("aadhaar", "applicant_name", "name")
        name_m, raw_m = get_field("marksheet", "candidate_name", "student_name", "name")
        res = compare_names(name_a, name_m)
        issues.append(CrossVerificationIssue(
            check_id="CROSS_NAME_AADHAAR_MARKSHEET",
            status=res.status,
            severity="error" if res.status == "mismatch" else ("warning" if res.status == "needs_review" else "info"),
            doc_a="aadhaar",
            field_a="applicant_name",
            doc_b="marksheet",
            field_b="candidate_name",
            score=res.score,
            masked_value_a=name_a,
            masked_value_b=name_m,
            message_key="cross.name_aadhaar_marksheet",
            reason_en=res.reason_en,
            reason_hi=res.reason_hi
        ))

    # Check 2: Applicant Name: Application vs Aadhaar
    if "application" in doc_map and "aadhaar" in doc_map:
        name_app, _ = get_field("application", "applicant_name", "name")
        name_a, _ = get_field("aadhaar", "applicant_name", "name")
        res = compare_names(name_app, name_a)
        issues.append(CrossVerificationIssue(
            check_id="CROSS_NAME_APP_AADHAAR",
            status=res.status,
            severity="error" if res.status == "mismatch" else ("warning" if res.status == "needs_review" else "info"),
            doc_a="application",
            field_a="applicant_name",
            doc_b="aadhaar",
            field_b="applicant_name",
            score=res.score,
            masked_value_a=name_app,
            masked_value_b=name_a,
            message_key="cross.name_app_aadhaar",
            reason_en=res.reason_en,
            reason_hi=res.reason_hi
        ))

    # Check 3: Bank Account Holder vs Applicant Name
    target_partner = "application" if "application" in doc_map else ("aadhaar" if "aadhaar" in doc_map else None)
    if "bank_passbook" in doc_map and target_partner:
        holder_name, _ = get_field("bank_passbook", "account_holder_name", "name")
        app_name, _ = get_field(target_partner, "applicant_name", "name")
        res = compare_names(holder_name, app_name)
        issues.append(CrossVerificationIssue(
            check_id="CROSS_BANK_HOLDER_MATCH",
            status=res.status,
            severity="error" if res.status == "mismatch" else ("warning" if res.status == "needs_review" else "info"),
            doc_a="bank_passbook",
            field_a="account_holder_name",
            doc_b=target_partner,
            field_b="applicant_name",
            score=res.score,
            masked_value_a=holder_name,
            masked_value_b=app_name,
            message_key="cross.bank_holder_match",
            reason_en="Bank account holder name matches applicant name." if res.status == "match" else f"Bank account holder ('{holder_name}') differs from applicant ('{app_name}'). Passbook must be in student's name.",
            reason_hi="बैंक खाताधारक का नाम आवेदक से मेल खाता है।" if res.status == "match" else f"बैंक खाताधारक ('{holder_name}') आवेदक ('{app_name}') से भिन्न है। बैंक खाता छात्र के नाम पर ही होना चाहिए।"
        ))

    # Check 4: DOB: Aadhaar vs Marksheet
    if "aadhaar" in doc_map and "marksheet" in doc_map:
        dob_a, _ = get_field("aadhaar", "dob")
        dob_m, _ = get_field("marksheet", "dob")
        res_dob = compare_dobs(dob_a, dob_m)
        issues.append(CrossVerificationIssue(
            check_id="CROSS_DOB_AADHAAR_MARKSHEET",
            status=res_dob.status,
            severity="error" if res_dob.status == "mismatch" else "info",
            doc_a="aadhaar",
            field_a="dob",
            doc_b="marksheet",
            field_b="dob",
            score=res_dob.score,
            masked_value_a=dob_a,
            masked_value_b=dob_m,
            message_key="cross.dob_aadhaar_marksheet",
            reason_en=res_dob.reason_en,
            reason_hi=res_dob.reason_hi
        ))

    # Check 5: Father / Guardian Name: Marksheet vs Application Form
    if "marksheet" in doc_map and "application" in doc_map:
        father_m, _ = get_field("marksheet", "father_name")
        father_app, _ = get_field("application", "father_name")
        res_father = compare_names(father_m, father_app)
        issues.append(CrossVerificationIssue(
            check_id="CROSS_GUARDIAN_NAME_MATCH",
            status=res_father.status,
            severity="error" if res_father.status == "mismatch" else ("warning" if res_father.status == "needs_review" else "info"),
            doc_a="marksheet",
            field_a="father_name",
            doc_b="application",
            field_b="father_name",
            score=res_father.score,
            masked_value_a=father_m,
            masked_value_b=father_app,
            message_key="cross.guardian_name_match",
            reason_en=res_father.reason_en,
            reason_hi=res_father.reason_hi
        ))

    # Check 6: Bank Account Number: Passbook vs Application Form
    if "bank_passbook" in doc_map and "application" in doc_map:
        _, raw_acct_p = get_field("bank_passbook", "account_number")
        _, raw_acct_app = get_field("application", "account_number")
        is_same = (raw_acct_p == raw_acct_app) and bool(raw_acct_p)
        issues.append(CrossVerificationIssue(
            check_id="CROSS_BANK_ACCOUNT_MATCH",
            status="match" if is_same else "mismatch",
            severity="info" if is_same else "error",
            doc_a="bank_passbook",
            field_a="account_number",
            doc_b="application",
            field_b="account_number",
            score=100 if is_same else 0,
            masked_value_a=mask_bank_account(raw_acct_p),
            masked_value_b=mask_bank_account(raw_acct_app),
            message_key="cross.bank_account_match",
            reason_en="Bank account numbers match across application and passbook." if is_same else "Bank account number in application does not match bank passbook copy.",
            reason_hi="आवेदन और पासबुक में बैंक खाता संख्या मेल खाती है।" if is_same else "आवेदन में दर्ज बैंक खाता संख्या बैंक पासबुक से मेल नहीं खाती।"
        ))

    return issues
