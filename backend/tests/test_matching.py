import pytest
from app.services.matching.normalise import normalize_name, normalize_date_to_iso
from app.services.matching.transliterate import (
    is_devanagari,
    transliterate_devanagari_to_roman,
    generate_phonetic_variations
)
from app.services.matching.compare import (
    compare_names,
    compare_dobs,
    run_cross_verification
)

def test_name_normalization():
    # Honorific stripping
    assert normalize_name("Shri Rajesh Sharma") == "rajesh sharma"
    assert normalize_name("Km. Sunita Devi") == "sunita devi"
    assert normalize_name("Mr. Mohd Imran") == "mohammad imran"
    assert normalize_name("श्रीमती सुनीता देवी") == "सुनीता देवी"
    assert normalize_name("Md. Arif Khan") == "mohammad arif khan"
    assert normalize_name("  Sunita   Devi  ") == "sunita devi"

def test_date_normalization_to_iso():
    assert normalize_date_to_iso("15/07/2005") == "2005-07-15"
    assert normalize_date_to_iso("15-07-2005") == "2005-07-15"
    assert normalize_date_to_iso("2005/07/15") == "2005-07-15"
    assert normalize_date_to_iso("invalid date") is None

def test_devanagari_detection_and_transliteration():
    assert is_devanagari("सुनीता देवी") is True
    assert is_devanagari("Sunita Devi") is False

    trans = transliterate_devanagari_to_roman("सुनीता देवी")
    assert "suneeta" in trans or "sunita" in trans

    vars_sunita = generate_phonetic_variations("sunita")
    assert "suneeta" in vars_sunita

def test_fuzzy_name_matching_bands():
    # 1. Exact Match (>= 95%)
    res_exact = compare_names("Sunita Devi", "Sunita Devi")
    assert res_exact.status == "match"
    assert res_exact.score == 100

    # 2. Token Order Differences (handled by RapidFuzz token sorting)
    res_order = compare_names("Sunita Devi", "Devi Sunita")
    assert res_order.status == "match"
    assert res_order.score >= 95

    # 3. Abbreviation expansion (Mohd -> Mohammad)
    res_abbr = compare_names("Mohd Imran", "Mohammad Imran")
    assert res_abbr.status == "match"
    assert res_abbr.score >= 95

    # 4. Phonetic / Minor Spelling Variation (Needs Review band: 80% - 94% or Match)
    res_typo = compare_names("Sunita Devi", "Suneeta Devi")
    assert res_typo.status in ["match", "needs_review"]
    assert res_typo.score >= 80

    # 5. Cross-Script: Hindi Devanagari vs Roman
    res_hindi = compare_names("सुनीता देवी", "Sunita Devi")
    assert res_hindi.status in ["match", "needs_review"]
    assert res_hindi.score >= 80

    # 6. Complete Mismatch (< 80%)
    res_mismatch = compare_names("Sunita Devi", "Pooja Verma")
    assert res_mismatch.status == "mismatch"
    assert res_mismatch.score < 80

def test_dob_comparison():
    # Exact match across formats
    res_ok = compare_dobs("15/07/2005", "15-07-2005")
    assert res_ok.status == "match"
    assert res_ok.score == 100

    # DOB mismatch
    res_bad = compare_dobs("15/07/2005", "20/08/2005")
    assert res_bad.status == "mismatch"
    assert res_bad.score == 0
    assert "mismatch" in res_bad.reason_en.lower()

def test_run_cross_verification_clean_and_planted_errors():
    # 1. Clean documents dataset: everything should match
    clean_docs = {
        "application": {
            "applicant_name": {"value": "Sunita Devi", "raw_value": "Sunita Devi"},
            "dob": {"value": "15/07/2005", "raw_value": "15/07/2005"},
            "father_name": {"value": "Ramesh Sharma", "raw_value": "Ramesh Sharma"},
            "account_number": {"value": "XXXXXX9012", "raw_value": "123456789012"}
        },
        "aadhaar": {
            "applicant_name": {"value": "Sunita Devi", "raw_value": "Sunita Devi"},
            "dob": {"value": "15/07/2005", "raw_value": "15/07/2005"}
        },
        "marksheet": {
            "candidate_name": {"value": "Sunita Devi", "raw_value": "Sunita Devi"},
            "dob": {"value": "15/07/2005", "raw_value": "15/07/2005"},
            "father_name": {"value": "Ramesh Sharma", "raw_value": "Ramesh Sharma"}
        },
        "bank_passbook": {
            "account_holder_name": {"value": "Sunita Devi", "raw_value": "Sunita Devi"},
            "account_number": {"value": "XXXXXX9012", "raw_value": "123456789012"}
        }
    }

    clean_issues = run_cross_verification(clean_docs)
    for issue in clean_issues:
        assert issue.status == "match", f"Expected match for {issue.check_id}, got {issue.status}"

    # 2. Planted errors dataset:
    # - Name variation between Aadhaar and Marksheet (Sunita vs Suneeta) -> Needs Review
    # - DOB mismatch between Aadhaar and Marksheet (15/07/2005 vs 18/09/2005) -> Mismatch
    # - Bank account holder name is father instead of student -> Mismatch
    planted_docs = {
        "application": {
            "applicant_name": {"value": "Sunita Devi", "raw_value": "Sunita Devi"},
            "dob": {"value": "15/07/2005", "raw_value": "15/07/2005"},
            "father_name": {"value": "Ramesh Sharma", "raw_value": "Ramesh Sharma"},
            "account_number": {"value": "XXXXXX9012", "raw_value": "123456789012"}
        },
        "aadhaar": {
            "applicant_name": {"value": "Sunita Devi", "raw_value": "Sunita Devi"},
            "dob": {"value": "15/07/2005", "raw_value": "15/07/2005"}
        },
        "marksheet": {
            "candidate_name": {"value": "Suneeta Devi", "raw_value": "Suneeta Devi"},  # Variation
            "dob": {"value": "18/09/2005", "raw_value": "18/09/2005"},  # Planted DOB mismatch
            "father_name": {"value": "Ramesh Sharma", "raw_value": "Ramesh Sharma"}
        },
        "bank_passbook": {
            "account_holder_name": {"value": "Ramesh Sharma", "raw_value": "Ramesh Sharma"},  # Account in father's name
            "account_number": {"value": "XXXXXX9012", "raw_value": "123456789012"}
        }
    }

    planted_issues = run_cross_verification(planted_docs)
    issue_map = {i.check_id: i for i in planted_issues}

    # Verify planted errors are flagged
    assert issue_map["CROSS_DOB_AADHAAR_MARKSHEET"].status == "mismatch"
    assert issue_map["CROSS_BANK_HOLDER_MATCH"].status == "mismatch"
    assert issue_map["CROSS_NAME_AADHAAR_MARKSHEET"].status in ["match", "needs_review"]
