"""
FormFix Hackathon Demo Controller
Provides pre-configured synthetic test scenarios for live evaluators, judges, and testing.
Allows testing deterministic rules and bilingual explanations without uploading real documents.
"""

import json
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session as DBSession

from app.models.database import get_db
from app.models.user import SessionModel, User, AuditLog, Consent
from app.models.document import UploadedDocument
from app.core.security import get_current_session, log_audit_event
from app.services.explanation.engine import ExplanationEngine

router = APIRouter(prefix="/demo", tags=["Hackathon Demo Mode"])

class ScenarioMeta(BaseModel):
    id: str
    title: str
    subtitle: str
    target_form: str
    expected_status: str
    description_en: str
    description_hi: str
    planted_issues: List[str]

class LoadScenarioRequest(BaseModel):
    scenario_id: str
    form_type: Optional[str] = "up_post_matric"

DEMO_SCENARIOS = {
    "clean_pass": ScenarioMeta(
        id="clean_pass",
        title="Priya Sharma — 100% Clean Pass",
        subtitle="Flawless UP Post-Matric Scholarship Candidate",
        target_form="UP Post-Matric Scholarship (Dashmesh/OBC)",
        expected_status="PASS",
        description_en="All 5 documents match perfectly: valid income, student's own active bank account, verified Aadhaar & marksheet.",
        description_hi="सभी 5 दस्तावेज़ पूरी तरह सुसंगत हैं: वैध आय प्रमाण पत्र, स्वयं का बैंक खाता, सत्यापित आधार व अंकपत्र।",
        planted_issues=[]
    ),
    "name_mismatch": ScenarioMeta(
        id="name_mismatch",
        title="Rahul Verma — Name Spelling Discrepancy",
        subtitle="Aadhaar vs Marksheet Identity Conflict",
        target_form="UP Post-Matric Scholarship",
        expected_status="NEEDS_REVIEW",
        description_en="Aadhaar displays 'Rahul Kumar Verma' while 10th Marksheet shows 'Rahul Verma'. Triggers RapidFuzz fuzzy alert.",
        description_hi="आधार कार्ड में 'Rahul Kumar Verma' और 10वीं मार्कशीट में 'Rahul Verma' है। नाम मिलान त्रुटि उत्पन्न होगी।",
        planted_issues=["Name mismatch between Aadhaar and Marksheet", "High rejection risk at district scholarship committee"]
    ),
    "expired_income": ScenarioMeta(
        id="expired_income",
        title="Amit Patel — Expired Income Certificate",
        subtitle="Certificate > 3 Years Old & Income Over Limit",
        target_form="UP Pre-Matric / Post-Matric Scholarship",
        expected_status="REJECT",
        description_en="Income certificate was issued in 2020 (> 3 year validity limit) and declared income exceeds the Rs 2.5L threshold.",
        description_hi="आय प्रमाण पत्र 3 वर्ष से अधिक पुराना (अमान्य) है और वार्षिक आय 2.5 लाख की सीमा से अधिक है।",
        planted_issues=["Income certificate validity expired (> 3 years old)", "Family income exceeds prescribed portal limit"]
    ),
    "father_bank_account": ScenarioMeta(
        id="father_bank_account",
        title="Sunita Devi — Father's Bank Account Linked",
        subtitle="Third-Party Bank Account Rejection Cause",
        target_form="UP Post-Matric Scholarship",
        expected_status="REJECT",
        description_en="Bank passbook holder is 'Rameshwar Devi' (Father) instead of the student. DBT transfers will be rejected by PFMS.",
        description_hi="बैंक पासबुक छात्रा के बजाय पिता (रामेश्वर देवी) के नाम पर है। PFMS प्रणाली द्वारा छात्रवृत्ति खारिज हो जाएगी।",
        planted_issues=["Bank account holder is not the student", "Strict PFMS DBT rule violation"]
    )
}

SYNTHETIC_DATASETS = {
    "clean_pass": [
        {
            "document_type": "aadhaar",
            "original_filename": "DEMO_Aadhaar_Priya_Sharma.pdf",
            "file_size_kb": 142.5,
            "overall_confidence": 0.98,
            "fields": {
                "name": {"value": "Priya Sharma", "confidence": 0.99, "normalized_value": "PRIYA SHARMA"},
                "dob": {"value": "15/07/2005", "confidence": 0.98, "normalized_value": "2005-07-15"},
                "gender": {"value": "Female", "confidence": 0.99, "normalized_value": "FEMALE"},
                "aadhaar_number": {"value": "999988887779", "confidence": 0.98, "normalized_value": "999988887779"}
            }
        },
        {
            "document_type": "marksheet",
            "original_filename": "DEMO_Class10_Marksheet_Priya.pdf",
            "file_size_kb": 185.0,
            "overall_confidence": 0.97,
            "fields": {
                "student_name": {"value": "Priya Sharma", "confidence": 0.98, "normalized_value": "PRIYA SHARMA"},
                "roll_number": {"value": "UP202278912", "confidence": 0.99, "normalized_value": "UP202278912"},
                "passing_year": {"value": "2022", "confidence": 0.97, "normalized_value": "2022"},
                "board": {"value": "UP Board", "confidence": 0.98, "normalized_value": "UP Board"},
                "father_name": {"value": "Ramesh Sharma", "confidence": 0.98, "normalized_value": "RAMESH SHARMA"},
                "percentage": {"value": "82.5", "confidence": 0.96, "normalized_value": "82.5"},
                "dob": {"value": "15/07/2005", "confidence": 0.98, "normalized_value": "2005-07-15"}
            }
        },
        {
            "document_type": "income_certificate",
            "original_filename": "DEMO_Income_Cert_2025.pdf",
            "file_size_kb": 160.2,
            "overall_confidence": 0.96,
            "fields": {
                "applicant_name": {"value": "Priya Sharma", "confidence": 0.98, "normalized_value": "PRIYA SHARMA"},
                "certificate_number": {"value": "INC/UP/2025/98124", "confidence": 0.99, "normalized_value": "INC/UP/2025/98124"},
                "annual_income": {"value": "120000", "confidence": 0.97, "normalized_value": "120000"},
                "issue_date": {"value": "10/01/2025", "confidence": 0.96, "normalized_value": "2025-01-10"}
            }
        },
        {
            "document_type": "caste_certificate",
            "original_filename": "DEMO_Caste_Cert_OBC.pdf",
            "file_size_kb": 135.8,
            "overall_confidence": 0.95,
            "fields": {
                "applicant_name": {"value": "Priya Sharma", "confidence": 0.98, "normalized_value": "PRIYA SHARMA"},
                "certificate_number": {"value": "CST/UP/2023/45120", "confidence": 0.99, "normalized_value": "CST/UP/2023/45120"},
                "caste_category": {"value": "OBC", "confidence": 0.95, "normalized_value": "OBC"}
            }
        },
        {
            "document_type": "bank_passbook",
            "original_filename": "DEMO_SBI_Passbook_Priya.pdf",
            "file_size_kb": 210.4,
            "overall_confidence": 0.96,
            "fields": {
                "account_holder_name": {"value": "Priya Sharma", "confidence": 0.98, "normalized_value": "PRIYA SHARMA"},
                "account_number": {"value": "5010045892147", "confidence": 0.99, "normalized_value": "5010045892147"},
                "ifsc_code": {"value": "SBIN0001234", "confidence": 0.97, "normalized_value": "SBIN0001234"}
            }
        },
        {
            "document_type": "application",
            "original_filename": "DEMO_UP_Scholarship_Application.pdf",
            "file_size_kb": 190.0,
            "overall_confidence": 0.99,
            "fields": {
                "applicant_name": {"value": "Priya Sharma", "confidence": 0.99, "normalized_value": "PRIYA SHARMA"},
                "dob": {"value": "15/07/2005", "confidence": 0.99, "normalized_value": "2005-07-15"},
                "father_name": {"value": "Ramesh Sharma", "confidence": 0.98, "normalized_value": "RAMESH SHARMA"},
                "aadhaar_number": {"value": "999988887779", "confidence": 0.99, "normalized_value": "999988887779"},
                "account_number": {"value": "5010045892147", "confidence": 0.99, "normalized_value": "5010045892147"},
                "ifsc_code": {"value": "SBIN0001234", "confidence": 0.98, "normalized_value": "SBIN0001234"}
            }
        }
    ],
    "name_mismatch": [
        {
            "document_type": "aadhaar",
            "original_filename": "DEMO_Aadhaar_Rahul_Kumar_Verma.pdf",
            "file_size_kb": 145.0,
            "overall_confidence": 0.96,
            "fields": {
                "name": {"value": "Rahul Kumar Verma", "confidence": 0.98, "normalized_value": "RAHUL KUMAR VERMA"},
                "dob": {"value": "2003-08-20", "confidence": 0.97, "normalized_value": "2003-08-20"},
                "gender": {"value": "Male", "confidence": 0.99, "normalized_value": "MALE"},
                "aadhaar_number": {"value": "654123987012", "confidence": 0.98, "normalized_value": "654123987012"}
            }
        },
        {
            "document_type": "marksheet",
            "original_filename": "DEMO_Class10_Rahul_Verma.pdf",
            "file_size_kb": 178.0,
            "overall_confidence": 0.95,
            "fields": {
                "student_name": {"value": "Rahul Verma", "confidence": 0.97, "normalized_value": "RAHUL VERMA"},
                "roll_number": {"value": "UP202155421", "confidence": 0.98, "normalized_value": "UP202155421"},
                "passing_year": {"value": "2021", "confidence": 0.96, "normalized_value": "2021"},
                "percentage": {"value": "76.4", "confidence": 0.95, "normalized_value": "76.4"},
                "dob": {"value": "2003-08-20", "confidence": 0.97, "normalized_value": "2003-08-20"}
            }
        },
        {
            "document_type": "income_certificate",
            "original_filename": "DEMO_Income_Rahul.pdf",
            "file_size_kb": 150.0,
            "overall_confidence": 0.94,
            "fields": {
                "applicant_name": {"value": "Rahul Verma", "confidence": 0.96, "normalized_value": "RAHUL VERMA"},
                "certificate_number": {"value": "INC/UP/2024/77412", "confidence": 0.98, "normalized_value": "INC/UP/2024/77412"},
                "annual_income": {"value": "95000", "confidence": 0.96, "normalized_value": "95000"},
                "issue_date": {"value": "2024-01-15", "confidence": 0.95, "normalized_value": "2024-01-15"}
            }
        },
        {
            "document_type": "bank_passbook",
            "original_filename": "DEMO_Bank_Passbook_Rahul.pdf",
            "file_size_kb": 195.0,
            "overall_confidence": 0.93,
            "fields": {
                "account_holder_name": {"value": "Rahul Kumar Verma", "confidence": 0.95, "normalized_value": "RAHUL KUMAR VERMA"},
                "account_number": {"value": "30981245678", "confidence": 0.98, "normalized_value": "30981245678"},
                "ifsc_code": {"value": "PUNB0124500", "confidence": 0.96, "normalized_value": "PUNB0124500"}
            }
        }
    ],
    "expired_income": [
        {
            "document_type": "aadhaar",
            "original_filename": "DEMO_Aadhaar_Amit_Patel.pdf",
            "file_size_kb": 140.0,
            "overall_confidence": 0.97,
            "fields": {
                "name": {"value": "Amit Patel", "confidence": 0.98, "normalized_value": "AMIT PATEL"},
                "dob": {"value": "2002-11-04", "confidence": 0.97, "normalized_value": "2002-11-04"},
                "gender": {"value": "Male", "confidence": 0.99, "normalized_value": "MALE"},
                "aadhaar_number": {"value": "784512369014", "confidence": 0.98, "normalized_value": "784512369014"}
            }
        },
        {
            "document_type": "marksheet",
            "original_filename": "DEMO_Class10_Amit.pdf",
            "file_size_kb": 180.0,
            "overall_confidence": 0.96,
            "fields": {
                "student_name": {"value": "Amit Patel", "confidence": 0.98, "normalized_value": "AMIT PATEL"},
                "roll_number": {"value": "UP202088451", "confidence": 0.99, "normalized_value": "UP202088451"},
                "passing_year": {"value": "2020", "confidence": 0.97, "normalized_value": "2020"},
                "percentage": {"value": "69.0", "confidence": 0.96, "normalized_value": "69.0"},
                "dob": {"value": "2002-11-04", "confidence": 0.97, "normalized_value": "2002-11-04"}
            }
        },
        {
            "document_type": "income_certificate",
            "original_filename": "DEMO_Old_Income_Amit_2020.pdf",
            "file_size_kb": 162.0,
            "overall_confidence": 0.95,
            "fields": {
                "applicant_name": {"value": "Amit Patel", "confidence": 0.97, "normalized_value": "AMIT PATEL"},
                "certificate_number": {"value": "INC/UP/2020/12489", "confidence": 0.98, "normalized_value": "INC/UP/2020/12489"},
                "annual_income": {"value": "320000", "confidence": 0.96, "normalized_value": "320000"},
                "issue_date": {"value": "2020-02-10", "confidence": 0.95, "normalized_value": "2020-02-10"}
            }
        },
        {
            "document_type": "bank_passbook",
            "original_filename": "DEMO_Passbook_Amit.pdf",
            "file_size_kb": 205.0,
            "overall_confidence": 0.95,
            "fields": {
                "account_holder_name": {"value": "Amit Patel", "confidence": 0.98, "normalized_value": "AMIT PATEL"},
                "account_number": {"value": "60241589721", "confidence": 0.98, "normalized_value": "60241589721"},
                "ifsc_code": {"value": "BARB0LUCKNO", "confidence": 0.96, "normalized_value": "BARB0LUCKNO"}
            }
        }
    ],
    "father_bank_account": [
        {
            "document_type": "aadhaar",
            "original_filename": "DEMO_Aadhaar_Sunita_Devi.pdf",
            "file_size_kb": 144.0,
            "overall_confidence": 0.98,
            "fields": {
                "name": {"value": "Sunita Devi", "confidence": 0.99, "normalized_value": "SUNITA DEVI"},
                "dob": {"value": "2005-02-18", "confidence": 0.98, "normalized_value": "2005-02-18"},
                "gender": {"value": "Female", "confidence": 0.99, "normalized_value": "FEMALE"},
                "aadhaar_number": {"value": "895623147852", "confidence": 0.98, "normalized_value": "895623147852"}
            }
        },
        {
            "document_type": "marksheet",
            "original_filename": "DEMO_Marksheet_Sunita.pdf",
            "file_size_kb": 175.0,
            "overall_confidence": 0.97,
            "fields": {
                "student_name": {"value": "Sunita Devi", "confidence": 0.98, "normalized_value": "SUNITA DEVI"},
                "roll_number": {"value": "UP202399120", "confidence": 0.99, "normalized_value": "UP202399120"},
                "passing_year": {"value": "2023", "confidence": 0.97, "normalized_value": "2023"},
                "percentage": {"value": "88.2", "confidence": 0.96, "normalized_value": "88.2"},
                "dob": {"value": "2005-02-18", "confidence": 0.98, "normalized_value": "2005-02-18"}
            }
        },
        {
            "document_type": "income_certificate",
            "original_filename": "DEMO_Income_Sunita.pdf",
            "file_size_kb": 155.0,
            "overall_confidence": 0.96,
            "fields": {
                "applicant_name": {"value": "Sunita Devi", "confidence": 0.98, "normalized_value": "SUNITA DEVI"},
                "certificate_number": {"value": "INC/UP/2024/66321", "confidence": 0.99, "normalized_value": "INC/UP/2024/66321"},
                "annual_income": {"value": "80000", "confidence": 0.97, "normalized_value": "80000"},
                "issue_date": {"value": "2024-03-25", "confidence": 0.96, "normalized_value": "2024-03-25"}
            }
        },
        {
            "document_type": "bank_passbook",
            "original_filename": "DEMO_Father_Account_Rameshwar.pdf",
            "file_size_kb": 220.0,
            "overall_confidence": 0.97,
            "fields": {
                "account_holder_name": {"value": "Rameshwar Devi", "confidence": 0.98, "normalized_value": "RAMESHWAR DEVI"},
                "account_number": {"value": "908812345678", "confidence": 0.99, "normalized_value": "908812345678"},
                "ifsc_code": {"value": "SBIN0005432", "confidence": 0.97, "normalized_value": "SBIN0005432"}
            }
        }
    ]
}

@router.get("/scenarios", response_model=List[ScenarioMeta])
def list_demo_scenarios():
    """
    Returns available hackathon test scenarios with full bilingual descriptions.
    """
    return list(DEMO_SCENARIOS.values())

@router.post("/load")
def load_demo_scenario(
    payload: LoadScenarioRequest,
    session: SessionModel = Depends(get_current_session),
    db: DBSession = Depends(get_db)
):
    """
    FR-05 & Phase 7: Automatically populates the active session with synthetic OCR data
    and documents for 1-click evaluation by judges.
    """
    scenario_id = payload.scenario_id.lower().strip()
    if scenario_id not in DEMO_SCENARIOS:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown scenario '{payload.scenario_id}'. Available: {list(DEMO_SCENARIOS.keys())}"
        )

    # 1. Clean previous documents in this session
    existing_docs = db.query(UploadedDocument).filter(UploadedDocument.session_id == session.id).all()
    for doc in existing_docs:
        db.delete(doc)
    db.commit()

    # 2. Automatically grant consent in DB if not yet recorded (demo convenience)
    existing_consent = db.query(Consent).filter(Consent.user_id == session.user_id).first()
    if not existing_consent:
        demo_consent = Consent(
            user_id=session.user_id,
            policy_version="v2.0-dpdp-formfix-2026",
            accepted_at=datetime.now(timezone.utc),
            ip_hash="127.0.0.1"
        )
        db.add(demo_consent)
        db.commit()

    # 3. Insert synthetic documents
    dataset = SYNTHETIC_DATASETS.get(scenario_id, [])
    created_docs = []

    for item in dataset:
        doc = UploadedDocument(
            session_id=session.id,
            user_id=session.user_id,
            form_type=payload.form_type or "up_post_matric",
            document_type=item["document_type"],
            original_filename=f"[DEMO] {item['original_filename']}",
            file_path=f"demo://ephemeral/{item['document_type']}.pdf",
            file_size_kb=item["file_size_kb"],
            mime_type="application/pdf",
            format_status="PASSED",
            extracted_data=json.dumps(item["fields"]),
            overall_confidence=item["overall_confidence"],
            is_encrypted=True
        )
        db.add(doc)
        created_docs.append(doc)

    db.commit()

    # 4. Run instant audit check to prepare results
    engine = ExplanationEngine(session_id=session.id, db=db)
    audit_summary = engine.run_full_audit()

    # 5. Log audit event
    log_audit_event(
        db=db,
        user_id=session.user_id,
        action="DEMO_SCENARIO_LOADED",
        resource_type="scenario",
        resource_id=scenario_id,
        details=f"Loaded demo scenario '{scenario_id}' with {len(created_docs)} documents"
    )

    return {
        "status": "success",
        "message": f"Successfully loaded scenario: {DEMO_SCENARIOS[scenario_id].title}",
        "scenario": DEMO_SCENARIOS[scenario_id],
        "documents_loaded": len(created_docs),
        "audit_preview": {
            "overall_status": audit_summary["overall_status"],
            "overall_score": audit_summary["overall_score"],
            "total_checks": len(audit_summary["rule_results"]) + len(audit_summary["cross_verifications"]),
            "flagged_issues": len(audit_summary.get("fix_checklist", []))
        }
    }
