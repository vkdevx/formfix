import os
import json
import pytest
from datetime import date
from sqlalchemy.orm import Session

from app.services.rules.validators import (
    validate_required,
    validate_regex_pattern,
    validate_allowed,
    validate_student_age,
    validate_certificate_validity,
    validate_numeric_limit
)
from app.services.rules.engine import (
    RulesEngine,
    seed_rules_from_file,
    RuleEvaluationResult
)
from app.models.rules import FormTemplate, RuleSet, Rule

def test_deterministic_validators():
    # 1. Student Age Validation (reference year 2026)
    ref = date(2026, 11, 10)
    ok_age, msg_ok = validate_student_age("15/07/2005", min_age=14, max_age=35, ref_date=ref)
    assert ok_age is True
    assert "within eligible" in msg_ok

    bad_young, msg_young = validate_student_age("15/07/2018", min_age=14, max_age=35, ref_date=ref)
    assert bad_young is False
    assert "outside allowed" in msg_young

    bad_old, _ = validate_student_age("15/07/1980", min_age=14, max_age=35, ref_date=ref)
    assert bad_old is False

    # 2. Certificate Validity (UP 3-year rule)
    ok_cert, msg_cert = validate_certificate_validity("10/01/2025", max_age_years=3, ref_date=ref)
    assert ok_cert is True
    assert "Certificate is valid" in msg_cert

    expired_cert, msg_exp = validate_certificate_validity("10/01/2021", max_age_years=3, ref_date=ref)
    assert expired_cert is False
    assert "Certificate expired" in msg_exp

    future_cert, msg_fut = validate_certificate_validity("10/01/2028", max_age_years=3, ref_date=ref)
    assert future_cert is False
    assert "in the future" in msg_fut

    # 3. Numeric Income Limit
    ok_inc, _ = validate_numeric_limit("72000", max_limit=250000)
    assert ok_inc is True

    bad_inc, msg_bad_inc = validate_numeric_limit("350000", max_limit=250000)
    assert bad_inc is False
    assert "exceeds maximum portal limit" in msg_bad_inc

    # 4. Regex Pattern Matching
    assert validate_regex_pattern("SBIN0001234", r"^[A-Z]{4}0[A-Z0-9]{6}$") is True
    assert validate_regex_pattern("SBINX001234", r"^[A-Z]{4}0[A-Z0-9]{6}$") is False

def test_rules_engine_seeding_and_evaluation(setup_test_db):
    from tests.conftest import TestingSessionLocal
    db: Session = TestingSessionLocal()
    try:
        # Seed rules into database
        rule_set = seed_rules_from_file(db)
        assert rule_set is not None
        assert rule_set.version == 1

        engine = RulesEngine(db)
        rules = engine.load_active_rules(version=1)
        assert len(rules) >= 8

        # 1. Clean valid applicant dataset
        clean_docs = {
            "application": {
                "applicant_name": {"value": "Sunita Devi", "raw_value": "Sunita Devi"},
                "dob": {"value": "15/07/2005", "raw_value": "15/07/2005"}
            },
            "aadhaar": {
                "applicant_name": {"value": "Sunita Devi", "raw_value": "Sunita Devi"},
                "aadhaar_number": {"value": "XXXX XXXX 7779", "raw_value": "999988887779"}
            },
            "marksheet": {
                "candidate_name": {"value": "Sunita Devi", "raw_value": "Sunita Devi"},
                "dob": {"value": "15/07/2005", "raw_value": "15/07/2005"},
                "board": {"value": "UP Board", "raw_value": "UP Board"}
            },
            "bank_passbook": {
                "account_holder_name": {"value": "Sunita Devi", "raw_value": "Sunita Devi"},
                "account_number": {"value": "XXXXXX9012", "raw_value": "123456789012"},
                "ifsc_code": {"value": "SBIN0001234", "raw_value": "SBIN0001234"}
            },
            "income_certificate": {
                "applicant_name": {"value": "Sunita Devi", "raw_value": "Sunita Devi"},
                "annual_income": {"value": "72000", "raw_value": "72000"},
                "issue_date": {"value": "10/01/2026", "raw_value": "10/01/2026"}
            }
        }

        # Evaluate all rules
        results = [engine.evaluate_rule(r, clean_docs) for r in rules]
        failed = [r for r in results if r.status == "failed"]
        assert len(failed) == 0, f"Expected 0 failures in clean dataset, got: {failed}"

        # 2. Planted Error Dataset: Bad Aadhaar Checksum, Expired Certificate, Missing Bank Passbook
        corrupt_docs = {
            "application": {
                "applicant_name": {"value": "Sunita Devi", "raw_value": "Sunita Devi"}
            },
            "aadhaar": {
                "aadhaar_number": {"value": "XXXX XXXX 7770", "raw_value": "999988887770"}  # Invalid Verhoeff
            },
            "marksheet": {
                "candidate_name": {"value": "Sunita Devi", "raw_value": "Sunita Devi"},
                "dob": {"value": "15/07/2005", "raw_value": "15/07/2005"},
                "board": {"value": "UP Board", "raw_value": "UP Board"}
            },
            "income_certificate": {
                "annual_income": {"value": "72000", "raw_value": "72000"},
                "issue_date": {"value": "10/01/2019", "raw_value": "10/01/2019"}  # Expired
            }
            # bank_passbook intentionally omitted
        }

        corrupt_results = [engine.evaluate_rule(r, corrupt_docs) for r in rules]
        corrupt_map = {r.rule_id: r for r in corrupt_results}

        # Assert specific planted errors are caught deterministically
        assert corrupt_map["AADHAAR_CHECKSUM"].status == "failed"
        assert corrupt_map["MANDATORY_DOCUMENTS"].status == "failed"
        assert corrupt_map["INCOME_CERT_VALIDITY"].status == "failed"
    finally:
        db.close()
