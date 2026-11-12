from dataclasses import dataclass, field
from typing import Dict, Any, Optional

CONFIDENCE_THRESHOLD = 0.80  # Fields below 0.80 are flagged for human review (FR-05)

@dataclass
class ExtractedField:
    field_name: str
    value: str
    raw_value: str
    confidence: float
    is_low_confidence: bool = False
    validation_passed: bool = True
    hint: Optional[str] = None

@dataclass
class DocumentExtractionResult:
    document_type: str
    fields: Dict[str, ExtractedField] = field(default_factory=dict)
    overall_confidence: float = 0.0
    raw_text: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "document_type": self.document_type,
            "overall_confidence": round(self.overall_confidence, 2),
            "fields": {
                name: {
                    "field_name": f.field_name,
                    "value": f.value,
                    "confidence": round(f.confidence, 2),
                    "is_low_confidence": f.is_low_confidence,
                    "validation_passed": f.validation_passed,
                    "hint": f.hint
                }
                for name, f in self.fields.items()
            }
        }
