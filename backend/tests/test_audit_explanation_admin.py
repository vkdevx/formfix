import pytest
import pymupdf
from app.models.user import User
from tests.conftest import TestingSessionLocal
from app.config import settings

def create_sample_pdf_with_text(text: str) -> bytes:
    doc = pymupdf.open()
    page = doc.new_page(width=595, height=842)
    page.insert_text((50, 72), text, fontsize=11)
    pdf_bytes = doc.tobytes()
    doc.close()
    return pdf_bytes

def test_full_audit_and_pdf_generation(client):
    # 1. Login & DPDP Consent
    phone = "9876511111"
    req_resp = client.post("/api/v1/auth/otp/request", json={"phone": phone})
    otp = req_resp.json()["demo_otp"]
    ver = client.post("/api/v1/auth/otp/verify", json={"phone": phone, "otp": otp})
    token = ver.json()["session_token"]
    headers = {"Authorization": f"Bearer {token}"}
    client.post("/api/v1/consent", json={"accept": True}, headers=headers)

    # 2. Upload Aadhaar & Marksheet
    aadhaar_pdf = create_sample_pdf_with_text(
        "GOVERNMENT OF INDIA\nSunita Devi\nDOB: 15/07/2005\nFemale\n9999 8888 7779"
    )
    marksheet_pdf = create_sample_pdf_with_text(
        "UP BOARD\nCandidate's Name: Sunita Devi\nFather's Name: Ramesh Sharma\nDOB: 15/07/2005\nRoll Number: 998877"
    )
    client.post(
        "/api/v1/documents",
        headers=headers,
        data={"document_type": "aadhaar"},
        files={"file": ("aadhaar.pdf", aadhaar_pdf, "application/pdf")}
    )
    client.post(
        "/api/v1/documents",
        headers=headers,
        data={"document_type": "marksheet"},
        files={"file": ("marksheet.pdf", marksheet_pdf, "application/pdf")}
    )

    # 3. GET /explanations/current
    audit_resp = client.get("/api/v1/explanations/current", headers=headers)
    assert audit_resp.status_code == 200
    data = audit_resp.json()
    assert "overall_status" in data
    assert "overall_score" in data
    assert "explanations" in data
    assert "fix_checklist" in data
    assert data["summary"]["total_documents"] == 2

    # 4. Download PDF audit report
    pdf_resp = client.get("/api/v1/explanations/current/pdf", headers=headers)
    assert pdf_resp.status_code == 200
    assert pdf_resp.headers["content-type"] == "application/pdf"
    assert len(pdf_resp.content) > 500  # Non-trivial PDF generated

def test_admin_panel_api(client):
    # 1. Access without admin authorization -> 403
    forbidden_resp = client.get("/api/v1/admin/stats")
    assert forbidden_resp.status_code == 403

    # 2. Access with X-Admin-Key bootstrap
    admin_headers = {"X-Admin-Key": settings.SECRET_KEY}
    stats_resp = client.get("/api/v1/admin/stats", headers=admin_headers)
    assert stats_resp.status_code == 200
    assert "stats" in stats_resp.json()
    assert "total_users" in stats_resp.json()["stats"]

    # 3. List users
    users_resp = client.get("/api/v1/admin/users", headers=admin_headers)
    assert users_resp.status_code == 200
    assert isinstance(users_resp.json(), list)

    # 4. Reseed rules
    reseed_resp = client.post("/api/v1/admin/rules/reseed", headers=admin_headers)
    assert reseed_resp.status_code == 200
    assert reseed_resp.json()["status"] == "RESEEDED"

    # 5. List rules
    rules_resp = client.get("/api/v1/admin/rules", headers=admin_headers)
    assert rules_resp.status_code == 200
    assert len(rules_resp.json()) >= 8
