import io
from typing import Tuple, Optional
from dataclasses import dataclass
from PIL import Image
import fitz  # PyMuPDF

# UP Scholarship Portal Official Format Constraints
PORTAL_LIMITS = {
    "application": {
        "max_size_kb": 1024.0,  # 1 MB for application PDF
        "allowed_mimes": ["application/pdf"],
        "label": "Scholarship Application Form"
    },
    "aadhaar": {
        "max_size_kb": 200.0,
        "allowed_mimes": ["application/pdf", "image/jpeg", "image/png"],
        "label": "Aadhaar Card"
    },
    "marksheet": {
        "max_size_kb": 200.0,
        "allowed_mimes": ["application/pdf", "image/jpeg", "image/png"],
        "label": "Academic Marksheet"
    },
    "bank_passbook": {
        "max_size_kb": 200.0,
        "allowed_mimes": ["application/pdf", "image/jpeg", "image/png"],
        "label": "Bank Passbook"
    },
    "income_certificate": {
        "max_size_kb": 200.0,
        "allowed_mimes": ["application/pdf", "image/jpeg", "image/png"],
        "label": "Income Certificate"
    },
    "caste_certificate": {
        "max_size_kb": 200.0,
        "allowed_mimes": ["application/pdf", "image/jpeg", "image/png"],
        "label": "Caste Certificate"
    }
}

MIN_IMAGE_WIDTH = 300
MIN_IMAGE_HEIGHT = 200

@dataclass
class FormatValidationResult:
    passed: bool
    mime_type: str
    file_size_kb: float
    width_px: Optional[int] = None
    height_px: Optional[int] = None
    page_count: Optional[int] = None
    error_reason_en: Optional[str] = None
    error_reason_hi: Optional[str] = None

def detect_mime_type_from_bytes(content: bytes) -> str:
    """
    Detects true MIME type using magic byte header inspection.
    Prevents file extension spoofing attacks.
    """
    if len(content) < 8:
        return "application/octet-stream"

    if content.startswith(b"%PDF-"):
        return "application/pdf"
    elif content.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    elif content.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    return "application/octet-stream"

def validate_document_format(
    content: bytes,
    document_type: str,
    original_filename: str
) -> FormatValidationResult:
    """
    FR-04: Checks file type, size, and image resolution against official portal limits.
    Immediately flags failures with plain-language bilingual reasons.
    """
    doc_type_clean = document_type.strip().lower()
    limits = PORTAL_LIMITS.get(doc_type_clean)
    if not limits:
        return FormatValidationResult(
            passed=False,
            mime_type="unknown",
            file_size_kb=len(content) / 1024.0,
            error_reason_en=f"Unsupported document type '{document_type}'. Allowed: {', '.join(PORTAL_LIMITS.keys())}",
            error_reason_hi=f"अमान्य दस्तावेज़ प्रकार '{document_type}'।"
        )

    file_size_kb = round(len(content) / 1024.0, 2)
    mime_type = detect_mime_type_from_bytes(content)

    # 1. MIME type validation
    if mime_type not in limits["allowed_mimes"]:
        allowed_str = ", ".join([m.split("/")[-1].upper() for m in limits["allowed_mimes"]])
        return FormatValidationResult(
            passed=False,
            mime_type=mime_type,
            file_size_kb=file_size_kb,
            error_reason_en=f"Invalid file format ({mime_type}). {limits['label']} must be {allowed_str}.",
            error_reason_hi=f"अमान्य फ़ाइल प्रारूप ({mime_type})। कृपया {allowed_str} फ़ाइल ही अपलोड करें।"
        )

    # 2. File size validation against portal limits
    max_size = limits["max_size_kb"]
    if file_size_kb > max_size:
        return FormatValidationResult(
            passed=False,
            mime_type=mime_type,
            file_size_kb=file_size_kb,
            error_reason_en=f"File size ({file_size_kb} KB) exceeds the portal limit of {int(max_size)} KB. Please compress your file.",
            error_reason_hi=f"फ़ाइल का आकार ({file_size_kb} KB) पोर्टल सीमा {int(max_size)} KB से अधिक है। कृपया फ़ाइल को कंप्रेस करें।"
        )

    # 3. Resolution and structure checks
    width_px = None
    height_px = None
    page_count = None

    if mime_type == "application/pdf":
        try:
            doc = fitz.open(stream=content, filetype="pdf")
            page_count = len(doc)
            if page_count == 0:
                return FormatValidationResult(
                    passed=False,
                    mime_type=mime_type,
                    file_size_kb=file_size_kb,
                    error_reason_en="Uploaded PDF file is empty or corrupted.",
                    error_reason_hi="अपलोड की गई PDF फ़ाइल खाली या दूषित है।"
                )
            doc.close()
        except Exception:
            return FormatValidationResult(
                passed=False,
                mime_type=mime_type,
                file_size_kb=file_size_kb,
                error_reason_en="Unable to read PDF file. The file may be password protected or corrupted.",
                error_reason_hi="PDF फ़ाइल पढ़ने में असमर्थ। फ़ाइल पासवर्ड-सुरक्षित या दूषित हो सकती है।"
            )
    elif mime_type in ["image/jpeg", "image/png"]:
        try:
            with Image.open(io.BytesIO(content)) as img:
                width_px, height_px = img.size
                if width_px < MIN_IMAGE_WIDTH or height_px < MIN_IMAGE_HEIGHT:
                    return FormatValidationResult(
                        passed=False,
                        mime_type=mime_type,
                        file_size_kb=file_size_kb,
                        width_px=width_px,
                        height_px=height_px,
                        error_reason_en=f"Image resolution too low ({width_px}x{height_px}px). Minimum required is {MIN_IMAGE_WIDTH}x{MIN_IMAGE_HEIGHT}px for readable OCR.",
                        error_reason_hi=f"फ़ोटो का रिज़ॉल्यूशन बहुत कम है ({width_px}x{height_px}px)। स्पष्टता हेतु कम से कम {MIN_IMAGE_WIDTH}x{MIN_IMAGE_HEIGHT}px आवश्यक है।"
                    )
        except Exception:
            return FormatValidationResult(
                passed=False,
                mime_type=mime_type,
                file_size_kb=file_size_kb,
                error_reason_en="Invalid or unreadable image file.",
                error_reason_hi="अमान्य या अपठनीय फोटो फ़ाइल।"
            )

    return FormatValidationResult(
        passed=True,
        mime_type=mime_type,
        file_size_kb=file_size_kb,
        width_px=width_px,
        height_px=height_px,
        page_count=page_count
    )
