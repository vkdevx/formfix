import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_user_registration_and_verification_flow():
    # 1. Register new user
    reg_payload = {
        "full_name": "Aarav Sharma",
        "email": "aarav.sharma@example.com",
        "phone": "9811223344",
        "password": "StrongPassword123!",
        "confirm_password": "StrongPassword123!"
    }
    reg_resp = client.post("/api/v1/auth/register", json=reg_payload)
    assert reg_resp.status_code == 200, reg_resp.text
    data = reg_resp.json()
    assert data["status"] == "OTP_SENT"
    demo_otp = data.get("demo_otp")
    assert demo_otp is not None, "Demo OTP should be returned in testing environment"

    # 2. Verify registration OTP
    verify_payload = {
        "identifier": "aarav.sharma@example.com",
        "otp": demo_otp
    }
    verify_resp = client.post("/api/v1/auth/verify-registration", json=verify_payload)
    assert verify_resp.status_code == 200, verify_resp.text
    session_data = verify_resp.json()
    assert "session_token" in session_data
    assert session_data["role"] == "citizen"

    # 3. Password Login
    login_resp = client.post("/api/v1/auth/login", json={
        "identifier": "aarav.sharma@example.com",
        "password": "StrongPassword123!"
    })
    assert login_resp.status_code == 200, login_resp.text
    login_data = login_resp.json()
    token = login_data["session_token"]
    assert token

    # 4. Access protected profile /auth/me
    me_resp = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me_resp.status_code == 200, me_resp.text
    me_data = me_resp.json()
    assert me_data["email"] == "aarav.sharma@example.com"
    assert me_data["full_name"] == "Aarav Sharma"

def test_demo_login_and_scenarios():
    # 1. 1-Click Demo Login as Student
    demo_resp = client.post("/api/v1/auth/demo-login", json={"role": "student"})
    assert demo_resp.status_code == 200, demo_resp.text
    demo_data = demo_resp.json()
    token = demo_data["session_token"]
    assert token

    headers = {"Authorization": f"Bearer {token}", "X-Session-Token": token}

    # 2. List demo scenarios
    scenarios_resp = client.get("/api/v1/demo/scenarios")
    assert scenarios_resp.status_code == 200
    scenarios = scenarios_resp.json()
    assert len(scenarios) >= 4
    scenario_ids = [s["id"] for s in scenarios]
    assert "clean_pass" in scenario_ids
    assert "name_mismatch" in scenario_ids
    assert "expired_income" in scenario_ids
    assert "father_bank_account" in scenario_ids

    # 3. Load clean_pass scenario
    load_resp = client.post("/api/v1/demo/load", json={"scenario_id": "clean_pass"}, headers=headers)
    assert load_resp.status_code == 200, load_resp.text
    load_data = load_resp.json()
    assert load_data["status"] == "success"
    assert load_data["documents_loaded"] == 6

    # 4. Inspect review grid
    grid_resp = client.get("/api/v1/review/grid", headers=headers)
    assert grid_resp.status_code == 200, grid_resp.text
    grid_data = grid_resp.json()
    assert len(grid_data["documents"]) == 6

    # 5. Execute Explanation Audit
    audit_resp = client.get("/api/v1/explanations/current", headers=headers)
    assert audit_resp.status_code == 200, audit_resp.text
    audit_data = audit_resp.json()
    assert audit_data["overall_status"] == "PASS"
    assert audit_data["overall_score"] == 100
    assert len(audit_data["cross_verifications"]) > 0

    # 6. Stream Masked PDF report
    pdf_resp = client.get("/api/v1/explanations/current/pdf", headers=headers)
    assert pdf_resp.status_code == 200
    assert pdf_resp.headers["content-type"] == "application/pdf"
    assert len(pdf_resp.content) > 1000

def test_planted_error_scenarios():
    # 1. Demo Login
    demo_resp = client.post("/api/v1/auth/demo-login", json={"role": "student"})
    token = demo_resp.json()["session_token"]
    headers = {"Authorization": f"Bearer {token}", "X-Session-Token": token}

    # 2. Load name_mismatch scenario
    load_resp = client.post("/api/v1/demo/load", json={"scenario_id": "name_mismatch"}, headers=headers)
    assert load_resp.status_code == 200
    audit_resp = client.get("/api/v1/explanations/current", headers=headers)
    audit = audit_resp.json()
    # Should flag warning / discrepancy
    assert audit["overall_score"] < 100

    # 3. Load expired_income scenario
    load_resp2 = client.post("/api/v1/demo/load", json={"scenario_id": "expired_income"}, headers=headers)
    assert load_resp2.status_code == 200
    audit_resp2 = client.get("/api/v1/explanations/current", headers=headers)
    audit2 = audit_resp2.json()
    # Income cert is expired so score drops
    assert audit2["overall_score"] < 100

def test_dpdp_right_to_erasure():
    # 1. Demo Login
    demo_resp = client.post("/api/v1/auth/demo-login", json={"role": "student"})
    token = demo_resp.json()["session_token"]
    headers = {"Authorization": f"Bearer {token}", "X-Session-Token": token}

    # 2. Delete data
    del_resp = client.delete("/api/v1/me/data", headers=headers)
    assert del_resp.status_code == 200
    del_data = del_resp.json()
    assert del_data["status"] == "DATA_DELETED"
