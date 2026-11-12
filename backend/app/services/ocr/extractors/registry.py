from typing import Dict, Any, Callable
from app.services.ocr.engine import ocr_engine, OCRResult
from app.services.ocr.extractors.base import DocumentExtractionResult, ExtractedField
from app.services.ocr.extractors.aadhaar import extract_aadhaar_fields
from app.services.ocr.extractors.marksheet import extract_marksheet_fields
from app.services.ocr.extractors.bank import extract_bank_fields
from app.services.ocr.extractors.certificates import extract_certificate_fields
from app.services.ocr.extractors.application import extract_application_fields

def get_extractor_for_type(document_type: str) -> Callable[[str, float], DocumentExtractionResult]:
    clean_type = document_type.strip().lower()
    if clean_type == "aadhaar":
        return extract_aadhaar_fields
    elif clean_type == "marksheet":
        return extract_marksheet_fields
    elif clean_type == "bank_passbook":
        return extract_bank_fields
    elif clean_type == "income_certificate":
        return lambda text, conf: extract_certificate_fields(text, doc_type="income_certificate", base_confidence=conf)
    elif clean_type == "caste_certificate":
        return lambda text, conf: extract_certificate_fields(text, doc_type="caste_certificate", base_confidence=conf)
    elif clean_type == "application":
        return extract_application_fields
    else:
        raise ValueError(f"Unknown document type: '{document_type}'")

def extract_document(document_type: str, file_path: str, mime_type: str) -> DocumentExtractionResult:
    """
    High-level extraction pipeline:
    1. Preprocesses and tokenizes document using ocr_engine
    2. Routes text to domain-specific field extractor
    3. Produces confidence scores and low-confidence flags (FR-05)
    """
    ocr_res = ocr_engine.extract_from_file(file_path, mime_type)
    extractor = get_extractor_for_type(document_type)

    base_conf = max(ocr_res.mean_confidence, 0.7) if ocr_res.full_text else 0.0
    extraction_result = extractor(ocr_res.full_text, base_conf)

    return extraction_result
