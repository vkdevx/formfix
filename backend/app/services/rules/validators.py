import re
from datetime import datetime, date
from typing import List, Optional, Any, Tuple
from app.services.ocr.extractors.aadhaar import validate_verhoeff
from app.services.ocr.extractors.bank import validate_ifsc

Tuple_Result = Tuple[bool, str]

def parse_date_dmy(date_str: str) -> Optional[date]:
    """Parses DD/MM/YYYY or DD-MM-YYYY string into a datetime.date object."""
    if not date_str:
        return None
    clean = date_str.replace("-", "/").strip()
    match = re.match(r"^([0-3]?\d)/([0-1]?\d)/(\d{4})$", clean)
    if not match:
        return None
    try:
        day, month, year = int(match.group(1)), int(match.group(2)), int(match.group(3))
        return date(year, month, day)
    except ValueError:
        return None

def validate_required(value: Any) -> bool:
    """Verifies that a mandatory field is non-empty."""
    if value is None:
        return False
    if isinstance(value, str):
        return len(value.strip()) > 0
    return True

def validate_regex_pattern(value: str, pattern: str) -> bool:
    """Evaluates regex pattern match against value."""
    if not value or not pattern:
        return False
    return bool(re.match(pattern, str(value).strip()))

def validate_allowed(value: str, allowed: List[str]) -> bool:
    """Verifies that value is in allowed list (case-insensitive)."""
    if not value or not allowed:
        return False
    val_clean = str(value).strip().lower()
    return any(val_clean == str(a).strip().lower() for a in allowed)

def validate_student_age(
    dob_str: str,
    min_age: int = 14,
    max_age: int = 35,
    ref_date: Optional[date] = None
) -> Tuple_Result:
    """
    Verifies that the student's age at application time falls within the required range (e.g. 14 to 35).
    """
    d = parse_date_dmy(dob_str)
    if not d:
        return False, "Invalid DOB format"
    ref = ref_date or date.today()
    age = ref.year - d.year - ((ref.month, ref.day) < (d.month, d.day))
    if min_age <= age <= max_age:
        return True, f"Age is {age} years (within eligible {min_age}-{max_age} range)"
    return False, f"Age is {age} years, outside allowed scholarship range ({min_age}-{max_age} years)"

def validate_certificate_validity(
    issue_date_str: str,
    max_age_years: int = 3,
    ref_date: Optional[date] = None
) -> Tuple_Result:
    """
    UP Revenue income certificates are valid for 3 years from date of issue.
    """
    d = parse_date_dmy(issue_date_str)
    if not d:
        return False, "Invalid certificate issue date format"
    ref = ref_date or date.today()
    diff_days = (ref - d).days
    max_days = max_age_years * 365 + 1  # Leap year tolerance
    if diff_days < 0:
        return False, "Certificate issue date is in the future"
    if diff_days <= max_days:
        return True, f"Certificate is valid (issued on {d.strftime('%d/%m/%Y')})"
    return False, f"Certificate expired. Issued {diff_days // 365} years ago (must be within {max_age_years} years)"

def validate_numeric_limit(value: Any, max_limit: float) -> Tuple_Result:
    """Verifies numeric value does not exceed maximum allowable cap."""
    if value is None:
        return False, "Missing numeric value"
    digits = re.sub(r"\D", "", str(value))
    if not digits:
        return False, "Non-numeric value"
    val_num = float(digits)
    if val_num <= max_limit:
        return True, f"Amount ₹{int(val_num):,} is within portal limit of ₹{int(max_limit):,}"
    return False, f"Amount ₹{int(val_num):,} exceeds maximum portal limit of ₹{int(max_limit):,}"
