import io
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import pymupdf
from fastapi.testclient import TestClient
from app.main import app
from app.config import settings

def run_e2e_verification():
    client = TestClient(app)

    print("--- 1. Testing OTP Generation & Request ---")
    r = client.post("/api/auth/request-otp?mobile=9876543210")
    assert r.status_code == 200, f"OTP Request failed: {r.text}"
    otp_data = r.json()
    otp = otp_data["demo_otp"]
    print(f"OTP Sent to {otp_data['masked_target']}, code: {otp}")

    print("--- 2. Testing OTP Verification ---")
    r = client.post("/api/auth/otp/verify", json={"phone": "9876543210", "otp": otp})
    assert r.status_code == 200, f"OTP Verify failed: {r.text}"
    auth_data = r.json()
    token = auth_data["session_token"]
    headers = {"Authorization": f"Bearer {token}"}
    print(f"Session Token received: {token[:12]}..., role: {auth_data['role']}")

    print("--- 3. Testing DPDP Consent ---")
    r = client.get("/api/consent/status", headers=headers)
    assert r.status_code == 200
    r = client.post("/api/consent", json={"accept": True}, headers=headers)
    assert r.status_code == 200
    print("Consent recorded successfully.")

    print("--- 4. Testing Document Ingestion & Bilingual OCR ---")
    def make_pdf(txt):
        d = pymupdf.open()
        p = d.new_page(width=595, height=842)
        p.insert_text((50, 72), txt, fontsize=11)
        b = d.tobytes()
        d.close()
        return b

    aadhaar_pdf = make_pdf("GOVERNMENT OF INDIA\nSunita Devi\nDOB: 15/07/2005\nFemale\n9999 8888 7779")
    r = client.post(
        "/api/documents",
        headers=headers,
        data={"document_type": "aadhaar"},
        files={"file": ("aadhaar.pdf", aadhaar_pdf, "application/pdf")}
    )
    assert r.status_code == 200
    print(f"Aadhaar uploaded, format: {r.json()['format_status']}, OCR conf: {r.json()['overall_confidence']}")

    marksheet_pdf = make_pdf("UP BOARD\nCandidate's Name: Suneeta Devi\nFather's Name: Ramesh Sharma\nDOB: 15/07/2005\nRoll Number: 998877")
    r = client.post(
        "/api/documents",
        headers=headers,
        data={"document_type": "marksheet"},
        files={"file": ("marksheet.pdf", marksheet_pdf, "application/pdf")}
    )
    assert r.status_code == 200
    marksheet_id = r.json()["id"]
    print(f"Marksheet uploaded, ID: {marksheet_id}")

    print("--- 5. Testing Interactive Review Grid ---")
    r = client.get("/api/review/grid", headers=headers)
    assert r.status_code == 200
    grid = r.json()
    print(f"Grid loaded: {len(grid['documents'])} docs, {grid['total_fields']} fields.")

    print("--- 6. Testing Human-in-the-Loop Field Correction ---")
    r = client.put(
        f"/api/review/documents/{marksheet_id}/fields",
        headers=headers,
        json={"corrections": {"candidate_name": "Sunita Devi"}}
    )
    assert r.status_code == 200
    print(f"Corrected candidate_name to: {r.json()['fields']['candidate_name']['value']}")

    print("--- 7. Confirming Review Grid ---")
    r = client.post("/api/review/confirm", headers=headers)
    assert r.status_code == 200
    print("Review confirmed.")

    print("--- 8. Testing Deterministic Audit & Bilingual Explanations ---")
    r = client.get("/api/explanations/current", headers=headers)
    assert r.status_code == 200
    audit = r.json()
    print(f"Audit Verdict: {audit['overall_status']}, Score: {audit['overall_score']}/100")
    print(f"Explanations count: {len(audit['explanations'])}")
    for e in audit["explanations"][:2]:
        print(f"  - EN: {e['en']}")
        print(f"  - HI: {e['hi'].encode('ascii', 'replace').decode('ascii')}")

    print("--- 9. Testing Masked PDF Checklist Report Generation ---")
    r = client.get("/api/explanations/current/pdf", headers=headers)
    assert r.status_code == 200
    assert r.headers["content-type"] == "application/pdf"
    print(f"PDF Report generated successfully: {len(r.content)} bytes.")

    print("--- 10. Testing Admin Panel ---")
    admin_headers = {"X-Admin-Key": settings.SECRET_KEY}
    r = client.get("/api/admin/stats", headers=admin_headers)
    assert r.status_code == 200
    print(f"Admin Stats: {r.json()['stats']}")

    print("--- 11. Testing Logout ---")
    r = client.post("/api/auth/logout", headers=headers)
    assert r.status_code == 200
    print("User successfully logged out.")

    print("\n=======================================================")
    print("ALL 11 END-TO-END WORKFLOWS VERIFIED SUCCESSFULLY")
    print("=======================================================")

if __name__ == "__main__":
    run_e2e_verification()
