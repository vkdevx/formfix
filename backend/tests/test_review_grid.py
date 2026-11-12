import pytest
import pymupdf

from app.services.review import get_confidence_badge, validate_and_format_field

def create_sample_pdf_with_text(text: str) -> bytes:
    doc = pymupdf.open()
    page = doc.new_page(width=595, height=842)
    page.insert_text((50, 72), text, fontsize=11)
    pdf_bytes = doc.tobytes()
    doc.close()
    return pdf_bytes

def test_confidence_badges():
    assert get_confidence_badge(0.95) == "high"
    assert get_confidence_badge(0.85) == "high"
    assert get_confidence_badge(0.75) == "medium"
    assert get_confidence_badge(0.60) == "low"
    assert get_confidence_badge(0.0) == "low"

def test_validate_and_format_field():
    # Valid Aadhaar Verhoeff
    disp, raw, valid, hint = validate_and_format_field("aadhaar_number", "999988887779")
    assert disp == "XXXX XXXX 7779"
    assert raw == "999988887779"
    assert valid is True

    # Invalid Aadhaar Verhoeff
    disp_bad, raw_bad, valid_bad, hint_bad = validate_and_format_field("aadhaar_number", "999988887770")
    assert valid_bad is False
    assert "checksum failed" in hint_bad.lower()

    # Valid IFSC
    disp_ifsc, raw_ifsc, valid_ifsc, _ = validate_and_format_field("ifsc_code", "sbin0001234")
    assert disp_ifsc == "SBIN0001234"
    assert valid_ifsc is True

    # Invalid IFSC (5th character not 0)
    _, _, valid_bad_ifsc, _ = validate_and_format_field("ifsc_code", "SBIN9001234")
    assert valid_bad_ifsc is False

    # Valid DOB
    disp_dob, _, valid_dob, _ = validate_and_format_field("dob", "15-07-2005")
    assert disp_dob == "15/07/2005"
    assert valid_dob is True

    # Invalid DOB
    _, _, valid_bad_dob, _ = validate_and_format_field("dob", "35/14/2005")
    assert valid_bad_dob is False

def test_review_grid_api_lifecycle(client):
    # 1. Login & DPDP Consent
    req_resp = client.post("/api/v1/auth/otp/request", json={"phone": "9876543210"})
    demo_otp = req_resp.json()["demo_otp"]
    verify_resp = client.post("/api/v1/auth/otp/verify", json={"phone": "9876543210", "otp": demo_otp})
    token = verify_resp.json()["session_token"]
    headers = {"Authorization": f"Bearer {token}"}
    client.post("/api/v1/consent", json={"accept": True}, headers=headers)

    # 2. Upload Aadhaar PDF
    aadhaar_pdf = create_sample_pdf_with_text(
        "GOVERNMENT OF INDIA\nSunita Devi\nDOB: 15/07/2005\nFemale\n9999 8888 7779"
    )
    up1 = client.post(
        "/api/v1/documents",
        headers=headers,
        data={"document_type": "aadhaar"},
        files={"file": ("aadhaar.pdf", aadhaar_pdf, "application/pdf")}
    )
    assert up1.status_code == 200
    aadhaar_doc_id = up1.json()["id"]

    # 3. Upload Marksheet PDF (with slight typo in name: Suneeta Devi)
    marksheet_pdf = create_sample_pdf_with_text(
        "UP BOARD\nCandidate's Name: Suneeta Devi\nFather's Name: Ramesh Sharma\nDOB: 15/07/2005\nRoll Number: 998877"
    )
    up2 = client.post(
        "/api/v1/documents",
        headers=headers,
        data={"document_type": "marksheet"},
        files={"file": ("marksheet.pdf", marksheet_pdf, "application/pdf")}
    )
    assert up2.status_code == 200
    marksheet_doc_id = up2.json()["id"]

    # 4. GET /review/grid
    grid_resp = client.get("/api/v1/review/grid", headers=headers)
    assert grid_resp.status_code == 200
    grid_data = grid_resp.json()
    assert len(grid_data["documents"]) == 2
    assert grid_data["total_fields"] >= 6
    assert grid_data["corrected_count"] == 0

    # 5. User corrects candidate_name on Marksheet via PUT /review/documents/{id}/fields
    correction_resp = client.put(
        f"/api/v1/review/documents/{marksheet_doc_id}/fields",
        headers=headers,
        json={"corrections": {"candidate_name": "Sunita Devi"}}
    )
    assert correction_resp.status_code == 200
    updated_fields = correction_resp.json()["fields"]
    assert updated_fields["candidate_name"]["value"] == "Sunita Devi"
    assert updated_fields["candidate_name"]["confidence"] == 1.0
    assert updated_fields["candidate_name"]["is_low_confidence"] is False

    # 6. Verify review grid reflects the correction (FR-06)
    grid_resp_after = client.get("/api/v1/review/grid", headers=headers)
    grid_data_after = grid_resp_after.json()
    assert grid_data_after["corrected_count"] >= 1

    # Find marksheet doc group
    marksheet_group = next(d for d in grid_data_after["documents"] if d["document_id"] == marksheet_doc_id)
    assert marksheet_group["has_corrections"] is True
    assert marksheet_group["fields"]["candidate_name"]["value"] == "Sunita Devi"
    assert marksheet_group["fields"]["candidate_name"]["is_user_corrected"] is True
    assert marksheet_group["fields"]["candidate_name"]["confidence_badge"] == "high"

    # 7. Confirm Review Grid
    confirm_resp = client.post("/api/v1/review/confirm", headers=headers)
    assert confirm_resp.status_code == 200
    assert confirm_resp.json()["status"] == "REVIEW_CONFIRMED"
    assert confirm_resp.json()["ready_for_audit"] is True
    assert "aadhaar" in confirm_resp.json()["document_types_present"]
    assert "marksheet" in confirm_resp.json()["document_types_present"]
