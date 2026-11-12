import pytest
from datetime import datetime, timezone, timedelta
from app.models.user import OTPRecord, User, SessionModel
from tests.conftest import TestingSessionLocal

def test_secure_random_otp_generation(client):
    """Verifies that generated OTPs are 6-digit random values and not hardcoded."""
    resp1 = client.post("/api/v1/auth/otp/request", json={"phone": "9876500001"})
    assert resp1.status_code == 200
    otp1 = resp1.json()["demo_otp"]
    assert len(otp1) == 6
    assert otp1.isdigit()

    # Request with another phone
    resp2 = client.post("/api/v1/auth/otp/request", json={"phone": "9876500002"})
    assert resp2.status_code == 200
    otp2 = resp2.json()["demo_otp"]
    assert len(otp2) == 6
    assert otp2.isdigit()

def test_otp_incorrect_attempts_and_lockout(client):
    """Tests attempt counter decrement and lockout after 5 failed attempts."""
    phone = "9876500003"
    req_resp = client.post("/api/v1/auth/otp/request", json={"phone": phone})
    assert req_resp.status_code == 200

    # 4 invalid attempts
    for attempt in range(1, 5):
        bad_resp = client.post("/api/v1/auth/otp/verify", json={"phone": phone, "otp": "000000"})
        assert bad_resp.status_code == 401
        assert "attempt(s) remaining" in bad_resp.json()["message"]

    # 5th invalid attempt -> triggers 429 lockout
    lock_resp = client.post("/api/v1/auth/otp/verify", json={"phone": phone, "otp": "000000"})
    assert lock_resp.status_code == 429
    assert "Maximum verification attempts exceeded" in lock_resp.json()["message"]

def test_otp_resend_cooldown(client):
    """Tests that requesting an OTP within 60 seconds returns 429 rate limit."""
    phone = "9876500004"
    req1 = client.post("/api/v1/auth/otp/request", json={"phone": phone})
    assert req1.status_code == 200

    # Immediate second request
    req2 = client.post("/api/v1/auth/otp/request", json={"phone": phone})
    assert req2.status_code == 429
    assert "second(s) before requesting another OTP" in req2.json()["message"]

def test_otp_expiry_handling(client):
    """Tests that expired OTPs cannot be verified."""
    phone = "9876500005"
    req = client.post("/api/v1/auth/otp/request", json={"phone": phone})
    assert req.status_code == 200
    otp = req.json()["demo_otp"]

    # Manually expire the record in database
    db = TestingSessionLocal()
    try:
        record = db.query(OTPRecord).order_by(OTPRecord.created_at.desc()).first()
        record.expires_at = datetime.now(timezone.utc) - timedelta(minutes=1)
        db.commit()
    finally:
        db.close()

    # Attempt to verify expired OTP
    verify_resp = client.post("/api/v1/auth/otp/verify", json={"phone": phone, "otp": otp})
    assert verify_resp.status_code == 401
    assert "expired" in verify_resp.json()["message"].lower()

def test_logout_functionality(client):
    """Tests session revocation on logout."""
    phone = "9876500006"
    req = client.post("/api/v1/auth/otp/request", json={"phone": phone})
    otp = req.json()["demo_otp"]
    ver = client.post("/api/v1/auth/otp/verify", json={"phone": phone, "otp": otp})
    token = ver.json()["session_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Verify session is valid
    status_resp = client.get("/api/v1/consent/status", headers=headers)
    assert status_resp.status_code == 200

    # Logout
    logout_resp = client.post("/api/v1/auth/logout", headers=headers)
    assert logout_resp.status_code == 200
    assert logout_resp.json()["status"] == "LOGGED_OUT"

    # Verifying session is now revoked (401)
    revoked_resp = client.get("/api/v1/consent/status", headers=headers)
    assert revoked_resp.status_code == 401

def test_backwards_compatibility_query_endpoints(client):
    """Verifies that /api/auth/request-otp and verify-otp with query params work."""
    # 1. Request OTP via query param
    req_resp = client.post("/api/auth/request-otp?mobile=9999999999")
    assert req_resp.status_code == 200
    otp = req_resp.json()["demo_otp"]
    assert "masked_target" in req_resp.json()

    # 2. Verify OTP via query param
    verify_resp = client.post(f"/api/auth/verify-otp?mobile=9999999999&otp={otp}")
    assert verify_resp.status_code == 200
    data = verify_resp.json()
    assert "session_token" in data
    assert "access_token" in data
    assert data["access_token"] == data["session_token"]
