import pytest
from app.core.redaction import (
    mask_aadhaar,
    mask_bank_account,
    mask_phone,
    mask_text,
    sanitize_dict_or_list
)

def test_mask_aadhaar():
    # 12 digits raw
    assert mask_aadhaar("123456789012") == "XXXX XXXX 9012"
    # 12 digits with spaces
    assert mask_aadhaar("1234 5678 9012") == "XXXX XXXX 9012"
    # 12 digits with hyphens
    assert mask_aadhaar("1234-5678-9012") == "XXXX XXXX 9012"
    # Empty or short
    assert mask_aadhaar("") == ""
    assert mask_aadhaar("12") == "XXXX XXXX XXXX"

def test_mask_bank_account():
    assert mask_bank_account("1234567890") == "XXXXXX7890"
    assert mask_bank_account("98765432101234") == "XXXXXX1234"
    assert mask_bank_account("") == ""

def test_mask_phone():
    assert mask_phone("9876543210") == "XXXXXX3210"
    assert mask_phone("+919876543210") == "XXXXXX3210"
    assert mask_phone("") == ""

def test_mask_text():
    sample = "User Aadhaar is 1234 5678 9012 registered in UP"
    masked = mask_text(sample)
    assert "1234 5678" not in masked
    assert "XXXX XXXX 9012" in masked

def test_sanitize_dict_or_list():
    payload = {
        "user": {
            "name": "Riya Sharma",
            "aadhaar_number": "999988887777",
            "phone": "9876543210",
            "bank_account_no": "112233445566"
        },
        "notes": "Verified Aadhaar 9999 8888 7777 successfully"
    }

    sanitized = sanitize_dict_or_list(payload)

    # Assert raw sensitive numbers are NEVER present
    assert "999988887777" not in str(sanitized)
    assert "9876543210" not in str(sanitized)
    assert "112233445566" not in str(sanitized)

    # Assert masked formats are present
    assert sanitized["user"]["aadhaar_number"] == "XXXX XXXX 7777"
    assert sanitized["user"]["phone"] == "XXXXXX3210"
    assert sanitized["user"]["bank_account_no"] == "XXXXXX5566"
    assert "XXXX XXXX 7777" in sanitized["notes"]
