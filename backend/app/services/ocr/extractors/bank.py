import re
from typing import Dict
from app.services.ocr.extractors.base import ExtractedField, DocumentExtractionResult, CONFIDENCE_THRESHOLD
from app.core.redaction import mask_bank_account

IFSC_REGEX = r"\b([A-Z]{4}0[A-Z0-9]{6})\b"

def validate_ifsc(ifsc: str) -> bool:
    """Verifies that an IFSC code adheres to the RBI standard: 4 letters, 0, 6 alphanumerics."""
    return bool(re.match(r"^[A-Z]{4}0[A-Z0-9]{6}$", ifsc))

def extract_bank_fields(raw_text: str, base_confidence: float = 0.95) -> DocumentExtractionResult:
    """
    Extracts Account Holder Name, Bank Account Number, IFSC Code, and Bank Name.
    Account number is masked on output (FR-09).
    """
    fields: Dict[str, ExtractedField] = {}

    # 1. IFSC Code
    ifsc_match = re.search(IFSC_REGEX, raw_text, re.IGNORECASE)
    if ifsc_match:
        ifsc_val = ifsc_match.group(1).upper()
        is_valid = validate_ifsc(ifsc_val)
        fields["ifsc_code"] = ExtractedField(
            field_name="ifsc_code",
            value=ifsc_val,
            raw_value=ifsc_val,
            confidence=base_confidence if is_valid else 0.6,
            is_low_confidence=not is_valid or base_confidence < CONFIDENCE_THRESHOLD,
            validation_passed=is_valid,
            hint="Valid RBI IFSC format" if is_valid else "IFSC 5th character must be '0'"
        )
    else:
        fields["ifsc_code"] = ExtractedField(
            field_name="ifsc_code",
            value="",
            raw_value="",
            confidence=0.0,
            is_low_confidence=True,
            validation_passed=False,
            hint="IFSC code not found on passbook"
        )

    # 2. Account Number (9 to 18 digits)
    acct_match = re.search(r"(?:A/C|Account|खाता)?\s*(?:No|Number|संख्या)?[:\s]*(\d{9,18})\b", raw_text, re.IGNORECASE)
    if acct_match:
        raw_acct = acct_match.group(1).strip()
        masked_acct = mask_bank_account(raw_acct)
        fields["account_number"] = ExtractedField(
            field_name="account_number",
            value=masked_acct,
            raw_value=raw_acct,
            confidence=base_confidence,
            is_low_confidence=base_confidence < CONFIDENCE_THRESHOLD,
            validation_passed=True
        )
    else:
        fields["account_number"] = ExtractedField(
            field_name="account_number",
            value="",
            raw_value="",
            confidence=0.0,
            is_low_confidence=True,
            validation_passed=False,
            hint="Bank account number not found"
        )

    # 3. Account Holder Name
    holder_match = re.search(r"(?:Name|Account\s*Holder|खाताधारक)[:\s]+([A-Za-z\s]+)", raw_text, re.IGNORECASE)
    holder_name = holder_match.group(1).strip().split("\n")[0].strip() if holder_match else ""
    if holder_name:
        holder_name = re.sub(r"^(Shri|Smt\.|Mr\.|Mrs\.)\s*", "", holder_name, flags=re.IGNORECASE).strip()

    fields["account_holder_name"] = ExtractedField(
        field_name="account_holder_name",
        value=holder_name,
        raw_value=holder_name,
        confidence=base_confidence if holder_name else 0.0,
        is_low_confidence=not holder_name or base_confidence < CONFIDENCE_THRESHOLD,
        validation_passed=bool(holder_name),
        hint="Account holder name detected" if holder_name else "Holder name not found on passbook"
    )

    # 4. Bank Name detection
    bank_name = "State Bank of India"
    for b in ["State Bank of India", "Punjab National Bank", "Bank of Baroda", "Canara Bank", "Union Bank", "HDFC Bank", "ICICI Bank"]:
        if b.lower() in raw_text.lower():
            bank_name = b
            break

    fields["bank_name"] = ExtractedField(
        field_name="bank_name",
        value=bank_name,
        raw_value=bank_name,
        confidence=base_confidence,
        is_low_confidence=False,
        validation_passed=True
    )

    conf_scores = [f.confidence for f in fields.values()]
    overall = sum(conf_scores) / len(conf_scores) if conf_scores else 0.0

    return DocumentExtractionResult(
        document_type="bank_passbook",
        fields=fields,
        overall_confidence=overall,
        raw_text=raw_text
    )
