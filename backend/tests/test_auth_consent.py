import pytest

def test_health_check(client):
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"

def test_otp_flow_and_session_creation(client):
    # 1. Request OTP
    req_resp = client.post("/api/v1/auth/otp/request", json={"phone": "9876543210"})
    assert req_resp.status_code == 200
    assert req_resp.json()["status"] == "OTP_SENT"
    assert req_resp.json()["masked_target"] == "XXXXXX3210"
    demo_otp = req_resp.json()["demo_otp"]

    # 2. Verify with invalid OTP
    bad_resp = client.post("/api/v1/auth/otp/verify", json={"phone": "9876543210", "otp": "000000"})
    assert bad_resp.status_code == 401
    assert bad_resp.json()["code"] == "AUTH_INVALID_SESSION"

    # 3. Verify with correct OTP
    verify_resp = client.post("/api/v1/auth/otp/verify", json={"phone": "9876543210", "otp": demo_otp})
    assert verify_resp.status_code == 200
    data = verify_resp.json()
    assert "session_token" in data
    assert data["consent_required"] is True
    assert data["masked_identifier"] == "XXXXXX3210"

    token = data["session_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 4. Check consent status (should be false before accepting)
    status_resp = client.get("/api/v1/consent/status", headers=headers)
    assert status_resp.status_code == 200
    assert status_resp.json()["has_consented"] is False

    # 5. Accept consent
    consent_resp = client.post("/api/v1/consent", json={"accept": True}, headers=headers)
    assert consent_resp.status_code == 200
    assert consent_resp.json()["status"] == "CONSENT_RECORDED"

    # 6. Check consent status again (should be true)
    status_resp_after = client.get("/api/v1/consent/status", headers=headers)
    assert status_resp_after.status_code == 200
    assert status_resp_after.json()["has_consented"] is True

    # 7. User wipes data (FR-12)
    del_resp = client.delete("/api/v1/me/data", headers=headers)
    assert del_resp.status_code == 200
    assert del_resp.json()["status"] == "DATA_DELETED"

    # 8. Verifying session is now invalidated
    after_del = client.get("/api/v1/consent/status", headers=headers)
    assert after_del.status_code == 401
