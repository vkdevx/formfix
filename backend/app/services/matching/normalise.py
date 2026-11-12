import re
from typing import Optional

# Honorifics & Prefixes to strip before name comparison
HONORIFICS_EN = [
    r"\bshri\b", r"\bsri\b", r"\bsmt\b", r"\bsrimati\b",
    r"\bmr\b", r"\bmrs\b", r"\bms\b", r"\bmiss\b",
    r"\bkm\b", r"\bkumari\b", r"\bkumar\b",
    r"\bdr\b", r"\blate\b"
]

HONORIFICS_HI = [
    r"श्रीमान", r"श्रीमती", r"सुश्री", r"कुमारी",
    r"श्री", r"डॉ\."
]

# Standard abbreviations in Indian names
ABBREVIATIONS = {
    r"\bmohd\b": "mohammad",
    r"\bmd\b": "mohammad",
    r"\bch\b": "chaudhary",
    r"\bkr\b": "kumar",
    r"\bpt\b": "pandit"
}

def normalize_name(name: str) -> str:
    """
    Normalizes a name string for fuzzy matching (PRD 8.2 & Architecture Section 8):
    1. Strip whitespace and convert to lowercase
    2. Remove punctuation and special characters
    3. Remove honorific titles/prefixes (Shri, Smt, Km, etc.)
    4. Expand common Indian name abbreviations (Mohd -> Mohammad)
    5. Collapse multiple spaces
    """
    if not name:
        return ""

    text = name.strip().lower()

    # Remove punctuation
    text = re.sub(r"[\.,\-_\'\"/()]+", " ", text)

    # Remove English honorifics
    for pattern in HONORIFICS_EN:
        text = re.sub(pattern, " ", text, flags=re.IGNORECASE)

    # Remove Hindi honorifics
    for pattern in HONORIFICS_HI:
        text = re.sub(pattern, " ", text)

    # Expand abbreviations
    for abbr, expansion in ABBREVIATIONS.items():
        text = re.sub(abbr, expansion, text, flags=re.IGNORECASE)

    # Collapse redundant whitespace
    text = re.sub(r"\s+", " ", text).strip()
    return text

def normalize_date_to_iso(date_str: str) -> Optional[str]:
    """
    Normalizes DD/MM/YYYY, DD-MM-YYYY, or YYYY-MM-DD into a standard ISO YYYY-MM-DD string.
    DOB cross-checking requires exact match after normalization (PRD 8.3 & Architecture Section 8).
    """
    if not date_str:
        return None

    clean = date_str.strip().replace("-", "/")

    # Matches DD/MM/YYYY
    match_dmy = re.match(r"^([0-3]?\d)/([0-1]?\d)/(\d{4})$", clean)
    if match_dmy:
        day, month, year = int(match_dmy.group(1)), int(match_dmy.group(2)), int(match_dmy.group(3))
        if 1 <= day <= 31 and 1 <= month <= 12:
            return f"{year:04d}-{month:02d}-{day:02d}"

    # Matches YYYY/MM/DD
    match_ymd = re.match(r"^(\d{4})/([0-1]?\d)/([0-3]?\d)$", clean)
    if match_ymd:
        year, month, day = int(match_ymd.group(1)), int(match_ymd.group(2)), int(match_ymd.group(3))
        if 1 <= day <= 31 and 1 <= month <= 12:
            return f"{year:04d}-{month:02d}-{day:02d}"

    return None
