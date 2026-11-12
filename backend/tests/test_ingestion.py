import io
import pytest
from PIL import Image
import fitz  # PyMuPDF

from app.services.ingestion import validate_document_format, detect_mime_type_from_bytes, PORTAL_LIMITS

def create_sample_pdf_bytes(text="Sample FormSaathi Document", target_size_kb: int = 10) -> bytes:
    doc = fitz.open()
    page = doc.new_page(width=595, height=842)
    page.insert_text((50, 72), text, fontsize=12)
    # Add dummy padding if target_size_kb requested
    if target_size_kb > 20:
        padding = " " * (target_size_kb * 1024)
        page.insert_text((50, 100), padding[:500], fontsize=8)
    pdf_bytes = doc.tobytes()
    doc.close()
    if target_size_kb > 20 and len(pdf_bytes) < target_size_kb * 1024:
        pdf_bytes += b"\n% DUMMY PADDING " + b"X" * (target_size_kb * 1024 - len(pdf_bytes))
    return pdf_bytes

def create_sample_image_bytes(width: int = 400, height: int = 300, format: str = "JPEG") -> bytes:
    img = Image.new("RGB", (width, height), color=(240, 240, 240))
    buf = io.BytesIO()
    img.save(buf, format=format)
    return buf.getvalue()

# Unit tests for format validation
def test_detect_mime_type():
    pdf_bytes = create_sample_pdf_bytes()
    jpeg_bytes = create_sample_image_bytes(format="JPEG")
    png_bytes = create_sample_image_bytes(format="PNG")

    assert detect_mime_type_from_bytes(pdf_bytes) == "application/pdf"
    assert detect_mime_type_from_bytes(jpeg_bytes) == "image/jpeg"
    assert detect_mime_type_from_bytes(png_bytes) == "image/png"
    assert detect_mime_type_from_bytes(b"hello text") == "application/octet-stream"

def test_validate_valid_documents():
    pdf_bytes = create_sample_pdf_bytes("Aadhaar Card Copy", target_size_kb=50)
    result = validate_document_format(pdf_bytes, "aadhaar", "aadhaar.pdf")
    assert result.passed is True
    assert result.mime_type == "application/pdf"

    jpeg_bytes = create_sample_image_bytes(width=500, height=400, format="JPEG")
    res_img = validate_document_format(jpeg_bytes, "marksheet", "marksheet.jpg")
    assert res_img.passed is True
    assert res_img.mime_type == "image/jpeg"

def test_validate_oversized_document():
    # 350 KB exceeds 200 KB limit for Aadhaar
    big_pdf = create_sample_pdf_bytes(target_size_kb=350)
    result = validate_document_format(big_pdf, "aadhaar", "big_aadhaar.pdf")
    assert result.passed is False
    assert "exceeds the portal limit of 200 KB" in result.error_reason_en
    assert "पोर्टल सीमा" in result.error_reason_hi

def test_validate_low_resolution_image():
    # 100x100 is below 300x200 min resolution
    tiny_img = create_sample_image_bytes(width=100, height=100, format="JPEG")
    result = validate_document_format(tiny_img, "bank_passbook", "passbook.jpg")
    assert result.passed is False
    assert "resolution too low" in result.error_reason_en.lower()

def test_validate_spoofed_file():
    fake_pdf = b"Plain text trying to masquerade as a PDF"
    result = validate_document_format(fake_pdf, "marksheet", "test.pdf")
    assert result.passed is False
    assert "Invalid file format" in result.error_reason_en

# Integration tests for /api/v1/documents endpoints
def test_upload_flow_with_auth_and_consent(client):
    # 1. Login to get token
    req_resp = client.post("/api/v1/auth/otp/request", json={"phone": "9876543210"})
    demo_otp = req_resp.json()["demo_otp"]
    verify_resp = client.post("/api/v1/auth/otp/verify", json={"phone": "9876543210", "otp": demo_otp})
    token = verify_resp.json()["session_token"]
    headers = {"Authorization": f"Bearer {token}"}

    sample_img = create_sample_image_bytes(width=500, height=400)

    # 2. Upload without consent -> must return 403 CONSENT_REQUIRED
    resp_no_consent = client.post(
        "/api/v1/documents",
        headers=headers,
        data={"document_type": "aadhaar"},
        files={"file": ("aadhaar.jpg", sample_img, "image/jpeg")}
    )
    assert resp_no_consent.status_code == 403
    assert resp_no_consent.json()["code"] == "CONSENT_REQUIRED"

    # 3. Accept consent
    client.post("/api/v1/consent", json={"accept": True}, headers=headers)

    # 4. Upload valid document with consent
    upload_resp = client.post(
        "/api/v1/documents",
        headers=headers,
        data={"document_type": "aadhaar"},
        files={"file": ("aadhaar.jpg", sample_img, "image/jpeg")}
    )
    assert upload_resp.status_code == 200
    doc_data = upload_resp.json()
    assert doc_data["document_type"] == "aadhaar"
    assert doc_data["format_status"] == "PASSED"
    doc_id = doc_data["id"]

    # 5. List documents
    list_resp = client.get("/api/v1/documents", headers=headers)
    assert list_resp.status_code == 200
    assert list_resp.json()["total_uploaded"] == 1
    assert list_resp.json()["all_passed"] is True

    # 6. Upload oversized file -> rejects with 422
    big_bytes = create_sample_pdf_bytes(target_size_kb=300)
    oversized_resp = client.post(
        "/api/v1/documents",
        headers=headers,
        data={"document_type": "marksheet"},
        files={"file": ("marksheet.pdf", big_bytes, "application/pdf")}
    )
    assert oversized_resp.status_code == 422
    assert "exceeds the portal limit" in oversized_resp.json()["message"]

    # 7. Delete document
    del_resp = client.delete(f"/api/v1/documents/{doc_id}", headers=headers)
    assert del_resp.status_code == 200
    assert del_resp.json()["status"] == "DOCUMENT_DELETED"

    # 8. List documents should now be empty
    list_after_del = client.get("/api/v1/documents", headers=headers)
    assert list_after_del.json()["total_uploaded"] == 0
