import io
import pytest
from PIL import Image
import pymupdf

from app.services.ocr.preprocess import preprocess_image_for_ocr, deskew_image
from app.services.ocr.extractors.aadhaar import extract_aadhaar_fields, validate_verhoeff
from app.services.ocr.extractors.marksheet import extract_marksheet_fields
from app.services.ocr.extractors.bank import extract_bank_fields, validate_ifsc
from app.services.ocr.extractors.certificates import extract_certificate_fields
from app.services.ocr.extractors.application import extract_application_fields
from app.services.ocr.extractors import extract_document

def create_sample_pdf_with_text(text: str) -> bytes:
    doc = pymupdf.open()
    page = doc.new_page(width=595, height=842)
    page.insert_text((50, 72), text, fontsize=11)
    pdf_bytes = doc.tobytes()
    doc.close()
    return pdf_bytes

def test_opencv_preprocessing():
    # Create an RGB image
    img = Image.new("RGB", (400, 300), color=(255, 255, 255))
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    raw_bytes = buf.getvalue()

    processed_np, meta = preprocess_image_for_ocr(raw_bytes)
    assert processed_np is not None
    assert len(processed_np.shape) == 2  # Grayscale image (single channel)
    assert meta["original_width"] == 400
    assert meta["original_height"] == 300
    assert "deskew_angle" in meta

def test_aadhaar_extractor_valid_and_masked():
    raw_aadhaar_text = """
    GOVERNMENT OF INDIA
    भारत सरकार
    Sunita Devi
    DOB: 15/07/2005
    Female / महिला
    9999 8888 7779
    """
    res = extract_aadhaar_fields(raw_aadhaar_text)
    assert res.document_type == "aadhaar"
    assert res.fields["applicant_name"].value == "Sunita Devi"
    assert res.fields["dob"].value == "15/07/2005"
    assert res.fields["gender"].value == "FEMALE"
    # Ensure sensitive Aadhaar number is masked in the output value (FR-09)
    assert res.fields["aadhaar_number"].value == "XXXX XXXX 7779"
    assert res.fields["aadhaar_number"].validation_passed is True

def test_aadhaar_extractor_invalid_checksum():
    # 9999 8888 7770 has an invalid Verhoeff checksum
    raw_bad_aadhaar = """
    Government of India
    Riya Sharma
    DOB: 20/08/2006
    Female
    9999 8888 7770
    """
    res = extract_aadhaar_fields(raw_bad_aadhaar)
    assert res.fields["aadhaar_number"].validation_passed is False
    assert res.fields["aadhaar_number"].is_low_confidence is True
    assert "Invalid Verhoeff checksum" in res.fields["aadhaar_number"].hint

def test_marksheet_extractor():
    raw_marksheet = """
    UTTAR PRADESH MADHYAMIK SHIKSHA PARISHAD
    HIGH SCHOOL EXAMINATION - 2023
    Candidate's Name: Sunita Devi
    Father's Name: Ramesh Sharma
    Date of Birth: 15/07/2005
    Roll Number: 2104567
    """
    res = extract_marksheet_fields(raw_marksheet)
    assert res.document_type == "marksheet"
    assert res.fields["candidate_name"].value == "Sunita Devi"
    assert res.fields["father_name"].value == "Ramesh Sharma"
    assert res.fields["dob"].value == "15/07/2005"
    assert res.fields["roll_number"].value == "2104567"
    assert res.fields["board"].value == "UP Board"
    assert res.overall_confidence >= 0.80

def test_bank_passbook_extractor():
    raw_bank = """
    STATE BANK OF INDIA
    LUCKNOW BRANCH
    Account Holder: Sunita Devi
    Account No: 123456789012
    IFSC: SBIN0001234
    """
    res = extract_bank_fields(raw_bank)
    assert res.document_type == "bank_passbook"
    assert res.fields["account_holder_name"].value == "Sunita Devi"
    assert res.fields["account_number"].value == "XXXXXX9012"
    assert res.fields["ifsc_code"].value == "SBIN0001234"
    assert res.fields["ifsc_code"].validation_passed is True
    assert res.fields["bank_name"].value == "State Bank of India"

def test_bank_passbook_invalid_ifsc():
    # 5th character of IFSC must be '0', here it is 'X'
    raw_bad_bank = """
    State Bank of India
    Account Holder: Sunita Devi
    Account No: 123456789012
    IFSC: SBINX001234
    """
    res = extract_bank_fields(raw_bad_bank)
    assert res.fields["ifsc_code"].validation_passed is False
    assert res.fields["ifsc_code"].is_low_confidence is True

def test_certificate_extractor():
    raw_income = """
    उत्तर प्रदेश सरकार - राजस्व विभाग
    आय प्रमाण पत्र (INCOME CERTIFICATE)
    Certificate No: UP/INC/2026/98765
    प्रमाणित किया जाता है कि Sunita Devi
    पिता का नाम: Ramesh Sharma
    वार्षिक आय: ₹ 72,000
    Issue Date: 12/01/2026
    """
    res = extract_certificate_fields(raw_income, doc_type="income_certificate")
    assert res.document_type == "income_certificate"
    assert res.fields["applicant_name"].value == "Sunita Devi"
    assert res.fields["father_name"].value == "Ramesh Sharma"
    assert res.fields["annual_income"].value == "72000"
    assert res.fields["certificate_no"].value == "UP/INC/2026/98765"

def test_application_extractor():
    raw_app = """
    UTTAR PRADESH SCHOLARSHIP & FEE REIMBURSEMENT SYSTEM
    Registration Number: 2026UP102948
    Applicant's Name: Sunita Devi
    Father's Name: Ramesh Sharma
    DOB: 15/07/2005
    Aadhaar Number: 9999 8888 7779
    Bank A/C No: 123456789012
    IFSC: SBIN0001234
    """
    res = extract_application_fields(raw_app)
    assert res.document_type == "application"
    assert res.fields["applicant_name"].value == "Sunita Devi"
    assert res.fields["father_name"].value == "Ramesh Sharma"
    assert res.fields["dob"].value == "15/07/2005"
    assert res.fields["registration_no"].value == "2026UP102948"
    assert res.fields["aadhaar_number"].value == "XXXX XXXX 7779"
    assert res.fields["account_number"].value == "XXXXXX9012"

def test_api_upload_and_get_extracted_fields(client):
    # 1. Login & Consent
    req_resp = client.post("/api/v1/auth/otp/request", json={"phone": "9876543210"})
    demo_otp = req_resp.json()["demo_otp"]
    verify_resp = client.post("/api/v1/auth/otp/verify", json={"phone": "9876543210", "otp": demo_otp})
    token = verify_resp.json()["session_token"]
    headers = {"Authorization": f"Bearer {token}"}
    client.post("/api/v1/consent", json={"accept": True}, headers=headers)

    # 2. Upload digital PDF marksheet
    marksheet_pdf = create_sample_pdf_with_text(
        "UTTAR PRADESH BOARD\nCandidate's Name: Riya Sharma\nFather's Name: Rajesh Sharma\nDOB: 10/05/2006\nRoll Number: 554433"
    )
    upload_resp = client.post(
        "/api/v1/documents",
        headers=headers,
        data={"document_type": "marksheet"},
        files={"file": ("marksheet.pdf", marksheet_pdf, "application/pdf")}
    )
    assert upload_resp.status_code == 200
    doc_id = upload_resp.json()["id"]

    # 3. Call GET /documents/{id}/fields to fetch extracted data with confidence
    fields_resp = client.get(f"/api/v1/documents/{doc_id}/fields", headers=headers)
    assert fields_resp.status_code == 200
    fields_data = fields_resp.json()
    assert fields_data["document_id"] == doc_id
    assert fields_data["document_type"] == "marksheet"
    assert fields_data["fields"]["candidate_name"]["value"] == "Riya Sharma"
    assert fields_data["fields"]["father_name"]["value"] == "Rajesh Sharma"
    assert fields_data["fields"]["dob"]["value"] == "10/05/2006"
    assert fields_data["fields"]["candidate_name"]["confidence"] >= 0.80
