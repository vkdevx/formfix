import json
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone, date
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session as DBSession

from app.models.rules import FormTemplate, RuleSet, Rule
from app.models.document import UploadedDocument
from app.core.redaction import mask_aadhaar, mask_bank_account
from app.services.rules.validators import (
    validate_required,
    validate_regex_pattern,
    validate_allowed,
    validate_student_age,
    validate_certificate_validity,
    validate_numeric_limit,
    validate_verhoeff
)

@dataclass
class RuleEvaluationResult:
    rule_id: str
    status: str  # "passed", "failed", "needs_review"
    severity: str  # "error", "warning", "info"
    fields: List[str]
    score: int
    values_masked: List[str]
    message_key: str
    reason_en: str
    reason_hi: str

def seed_rules_from_file(db: DBSession, seed_path: Optional[str] = None) -> RuleSet:
    """
    Seeds Version 1 UP Scholarship rules from JSON file into PostgreSQL/SQLite if not already present.
    Per Architecture Section 7.1 & Principle 4.
    """
    if seed_path is None:
        curr = os.path.abspath(__file__)
        # Walk up to find 'rules/up_scholarship_v1.json'
        for _ in range(6):
            candidate = os.path.join(curr, "rules", "up_scholarship_v1.json")
            if os.path.exists(candidate):
                seed_path = candidate
                break
            curr = os.path.dirname(curr)

    if not seed_path or not os.path.exists(seed_path):
        raise FileNotFoundError(f"Cannot locate rules seed file at {seed_path}")

    with open(seed_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    template_name = data["template_name"]
    template = db.query(FormTemplate).filter(FormTemplate.name == template_name).first()
    if not template:
        template = FormTemplate(name=template_name, state=data.get("state", "Uttar Pradesh"))
        db.add(template)
        db.commit()
        db.refresh(template)

    ver = data["version"]
    existing_set = db.query(RuleSet).filter(
        RuleSet.template_id == template.id,
        RuleSet.version == ver
    ).first()

    if not existing_set:
        rule_set = RuleSet(
            template_id=template.id,
            version=ver,
            is_active=True,
            reviewed_on=date.fromisoformat(data.get("reviewed_on", "2026-11-10"))
        )
        db.add(rule_set)
        db.commit()
        db.refresh(rule_set)

        for r in data["rules"]:
            rule_entry = Rule(
                rule_set_id=rule_set.id,
                rule_id=r["rule_id"],
                scope=r["scope"],
                rule_type=r["rule_type"],
                params=json.dumps(r.get("params", {})),
                severity=r.get("severity", "error"),
                message_key=r.get("message_key", f"rule.{r['rule_id'].lower()}")
            )
            db.add(rule_entry)
        db.commit()
        return rule_set

    return existing_set

class RulesEngine:
    """
    Pure deterministic Python rules engine (Architecture Section 1 Principle 1).
    Evaluates versioned rules against extracted/user-corrected form data.
    """

    def __init__(self, db: DBSession):
        self.db = db

    def load_active_rules(self, version: int = 1) -> List[Rule]:
        """Loads versioned rules from the database."""
        seed_rules_from_file(self.db)
        rule_set = self.db.query(RuleSet).filter(
            RuleSet.version == version,
            RuleSet.is_active == True
        ).first()

        if not rule_set:
            raise ValueError(f"No active rule set found for version {version}")

        return self.db.query(Rule).filter(Rule.rule_set_id == rule_set.id).all()

    def evaluate_rule(
        self,
        rule: Rule,
        doc_map: Dict[str, Dict[str, Any]]
    ) -> RuleEvaluationResult:
        """Evaluates an individual rule deterministically against the document data map."""
        params = json.loads(rule.params or "{}")
        rtype = rule.rule_type
        scope = rule.scope

        # 1. Document Presence Check
        if rtype == "document_presence":
            required_docs = params.get("required_documents", [])
            missing = [d for d in required_docs if d not in doc_map]
            present = [d for d in required_docs if d in doc_map]
            if not missing:
                return RuleEvaluationResult(
                    rule_id=rule.rule_id,
                    status="passed",
                    severity=rule.severity,
                    fields=["documents"],
                    score=100,
                    values_masked=present,
                    message_key=rule.message_key,
                    reason_en="All required scholarship documents are uploaded.",
                    reason_hi="सभी आवश्यक छात्रवृत्ति दस्तावेज़ अपलोड कर दिए गए हैं।"
                )
            else:
                missing_str = ", ".join(missing)
                return RuleEvaluationResult(
                    rule_id=rule.rule_id,
                    status="failed",
                    severity=rule.severity,
                    fields=["documents"],
                    score=0,
                    values_masked=present,
                    message_key=rule.message_key,
                    reason_en=f"Missing mandatory documents: {missing_str}.",
                    reason_hi=f"आवश्यक दस्तावेज़ गायब हैं: {missing_str}।"
                )

        # Retrieve target document fields
        doc_fields = doc_map.get(scope, {})
        target_field = params.get("field")
        field_info = doc_fields.get(target_field, {})
        val = field_info.get("value", "")
        raw_val = field_info.get("raw_value", val)

        masked_val = val
        if "aadhaar" in target_field:
            masked_val = mask_aadhaar(raw_val)
        elif "account" in target_field:
            masked_val = mask_bank_account(raw_val)

        # 2. Checksum (Aadhaar Verhoeff)
        if rtype == "checksum":
            is_valid = validate_verhoeff(raw_val)
            if is_valid:
                return RuleEvaluationResult(
                    rule_id=rule.rule_id,
                    status="passed",
                    severity=rule.severity,
                    fields=[f"{scope}.{target_field}"],
                    score=100,
                    values_masked=[masked_val],
                    message_key=rule.message_key,
                    reason_en="Aadhaar 12-digit format and Verhoeff checksum validated successfully.",
                    reason_hi="आधार 12-अंकीय प्रारूप और वेरहोफ चेकसम सफलतापूर्वक मान्य हुआ।"
                )
            return RuleEvaluationResult(
                rule_id=rule.rule_id,
                status="failed",
                severity=rule.severity,
                fields=[f"{scope}.{target_field}"],
                score=0,
                values_masked=[masked_val],
                message_key=rule.message_key,
                reason_en="Aadhaar number failed 12-digit Verhoeff checksum validation.",
                reason_hi="आधार संख्या 12-अंकीय वेरहोफ चेकसम सत्यापन में विफल रही।"
            )

        # 3. Regex Pattern Validation
        if rtype == "regex":
            pattern = params.get("pattern", "")
            is_match = validate_regex_pattern(raw_val, pattern)
            if is_match:
                return RuleEvaluationResult(
                    rule_id=rule.rule_id,
                    status="passed",
                    severity=rule.severity,
                    fields=[f"{scope}.{target_field}"],
                    score=100,
                    values_masked=[masked_val],
                    message_key=rule.message_key,
                    reason_en=f"{target_field.replace('_', ' ').title()} format is valid.",
                    reason_hi=f"{target_field.replace('_', ' ').title()} प्रारूप सही है।"
                )
            return RuleEvaluationResult(
                rule_id=rule.rule_id,
                status="failed",
                severity=rule.severity,
                fields=[f"{scope}.{target_field}"],
                score=0,
                values_masked=[masked_val],
                message_key=rule.message_key,
                reason_en=f"Invalid {target_field.replace('_', ' ')} format: '{masked_val}'.",
                reason_hi=f"अमान्य {target_field.replace('_', ' ')} प्रारूप: '{masked_val}'।"
            )

        # 4. Date Logic Validation (Student Age or Certificate Validity)
        if rtype == "date_logic":
            if "min_age" in params:
                ok, msg = validate_student_age(
                    val,
                    min_age=params.get("min_age", 14),
                    max_age=params.get("max_age", 35)
                )
                status = "passed" if ok else "failed"
                return RuleEvaluationResult(
                    rule_id=rule.rule_id,
                    status=status,
                    severity=rule.severity,
                    fields=[f"{scope}.{target_field}"],
                    score=100 if ok else 0,
                    values_masked=[val],
                    message_key=rule.message_key,
                    reason_en=msg,
                    reason_hi="छात्र की आयु छात्रवृत्ति पात्रता सीमा में है।" if ok else "छात्र की आयु छात्रवृत्ति पात्रता सीमा से बाहर है।"
                )
            elif "max_age_years" in params:
                ok, msg = validate_certificate_validity(
                    val,
                    max_age_years=params.get("max_age_years", 3)
                )
                status = "passed" if ok else "failed"
                return RuleEvaluationResult(
                    rule_id=rule.rule_id,
                    status=status,
                    severity=rule.severity,
                    fields=[f"{scope}.{target_field}"],
                    score=100 if ok else 0,
                    values_masked=[val],
                    message_key=rule.message_key,
                    reason_en=msg,
                    reason_hi="प्रमाण पत्र वैध अवधि में है।" if ok else "प्रमाण पत्र की 3 वर्ष की वैधता अवधि समाप्त हो चुकी है।"
                )

        # 5. Numeric Limit (Income Cap)
        if rtype == "numeric_limit":
            max_lim = float(params.get("max_limit", 250000))
            ok, msg = validate_numeric_limit(val, max_lim)
            return RuleEvaluationResult(
                rule_id=rule.rule_id,
                status="passed" if ok else "failed",
                severity=rule.severity,
                fields=[f"{scope}.{target_field}"],
                score=100 if ok else 0,
                values_masked=[val],
                message_key=rule.message_key,
                reason_en=msg,
                reason_hi="पारिवारिक आय सीमा पोर्टल पात्रता के अनुसार है।" if ok else "पारिवारिक आय अधिकतम पात्रता सीमा से अधिक है।"
            )

        # 6. Allowed Values
        if rtype == "allowed_values":
            allowed = params.get("allowed", [])
            ok = validate_allowed(val, allowed)
            return RuleEvaluationResult(
                rule_id=rule.rule_id,
                status="passed" if ok else "needs_review",
                severity=rule.severity,
                fields=[f"{scope}.{target_field}"],
                score=100 if ok else 50,
                values_masked=[val],
                message_key=rule.message_key,
                reason_en=f"Board '{val}' is recognized." if ok else f"Unrecognized board '{val}'. Please confirm.",
                reason_hi=f"बोर्ड '{val}' मान्य है।" if ok else f"अपरिचित बोर्ड '{val}', कृपया जांच लें।"
            )

        # Default fallback
        return RuleEvaluationResult(
            rule_id=rule.rule_id,
            status="passed",
            severity="info",
            fields=[f"{scope}.{target_field or ''}"],
            score=100,
            values_masked=[val],
            message_key=rule.message_key,
            reason_en="Rule passed.",
            reason_hi="नियम मान्य हुआ।"
        )

    def run_session_audit(
        self,
        session_id: str,
        version: int = 1
    ) -> List[RuleEvaluationResult]:
        """
        Executes all rules for the active rule version against the session's documents.
        Uses corrected values from the review grid as ground truth (FR-06 & FR-07).
        """
        rules = self.load_active_rules(version=version)

        # Load session documents
        docs = self.db.query(UploadedDocument).filter(
            UploadedDocument.session_id == session_id
        ).all()

        # Build document data map
        doc_map = {}
        for d in docs:
            extracted = json.loads(d.extracted_data or "{}")
            doc_map[d.document_type] = extracted

        results = []
        for rule in rules:
            res = self.evaluate_rule(rule, doc_map)
            results.append(res)

        return results
