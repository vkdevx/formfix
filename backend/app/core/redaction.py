import re
from typing import Any, Dict, List, Union

def mask_aadhaar(aadhaar: str) -> str:
    """
    Masks a 12-digit Aadhaar number to format 'XXXX XXXX 1234'.
    Per Architecture Section 11 & FR-09.
    """
    if not aadhaar:
        return ""
    # Strip spaces and dashes
    digits = re.sub(r"\D", "", str(aadhaar))
    if len(digits) == 12:
        return f"XXXX XXXX {digits[-4:]}"
    elif len(digits) > 4:
        return f"XXXX XXXX {digits[-4:]}"
    return "XXXX XXXX XXXX"

def mask_bank_account(account: str) -> str:
    """
    Masks bank account number to show only last 4 digits: 'XXXXXX7890'.
    Per Architecture Section 11.
    """
    if not account:
        return ""
    clean = re.sub(r"\s+", "", str(account))
    if len(clean) > 4:
        return f"XXXXXX{clean[-4:]}"
    return "XXXXXX"

def mask_phone(phone: str) -> str:
    """
    Masks phone number to show only last 4 digits: 'XXXXXX1234'.
    Per Architecture Section 11.
    """
    if not phone:
        return ""
    digits = re.sub(r"\D", "", str(phone))
    if len(digits) >= 10:
        return f"XXXXXX{digits[-4:]}"
    elif len(digits) > 4:
        return f"XXXXXX{digits[-4:]}"
    return "XXXXXX"

def mask_text(text: str) -> str:
    """
    Detects and masks 12-digit Aadhaar patterns within any arbitrary text or log message.
    """
    if not text:
        return ""
    # Matches patterns like 1234 5678 9012 or 123456789012
    pattern = r"\b(\d{4})[\s-]?(\d{4})[\s-](\d{4})\b"
    text = re.sub(pattern, r"XXXX XXXX \3", text)
    
    # 12 continuous digits
    cont_pattern = r"\b\d{8}(\d{4})\b"
    text = re.sub(cont_pattern, r"XXXX XXXX \1", text)
    return text

def sanitize_dict_or_list(data: Union[Dict, List, Any]) -> Any:
    """
    Recursively sanitizes dictionary or list structures, masking sensitive fields
    so raw identity info never escapes in API responses or logs.
    """
    if isinstance(data, dict):
        sanitized = {}
        for k, v in data.items():
            k_lower = str(k).lower()
            if "aadhaar" in k_lower or "uidai" in k_lower:
                sanitized[k] = mask_aadhaar(str(v)) if v else v
            elif "account" in k_lower and ("bank" in k_lower or "num" in k_lower or "no" in k_lower):
                sanitized[k] = mask_bank_account(str(v)) if v else v
            elif "phone" in k_lower or "mobile" in k_lower:
                sanitized[k] = mask_phone(str(v)) if v else v
            else:
                sanitized[k] = sanitize_dict_or_list(v)
        return sanitized
    elif isinstance(data, list):
        return [sanitize_dict_or_list(item) for item in data]
    elif isinstance(data, str):
        return mask_text(data)
    return data
