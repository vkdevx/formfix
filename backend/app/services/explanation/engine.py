"""
Explanation & Audit Engine (Bilingual English & Hindi)
Performs complete pre-submission audit analysis and generates downloadable PDF checklist reports.
"""

import io
import json
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
from sqlalchemy.orm import Session as DBSession

from app.models.document import UploadedDocument
from app.services.rules.engine import RulesEngine, RuleEvaluationResult
from app.services.matching.compare import run_cross_verification, CrossVerificationIssue
from app.core.redaction import mask_aadhaar, mask_bank_account

from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    HRFlowable,
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

logger = logging.getLogger(__name__)

class ExplanationEngine:
    """
    Evaluates session documents against the deterministic rules engine and
    cross-document matching engine to produce grounded bilingual explanations
    and downloadable PDF audit reports.
    """

    def __init__(self, session_id: str, db: DBSession):
        self.session_id = session_id
        self.db = db

    def _load_documents(self) -> List[UploadedDocument]:
        return self.db.query(UploadedDocument).filter(
            UploadedDocument.session_id == self.session_id
        ).all()

    def _build_doc_map(self, docs: List[UploadedDocument]) -> Dict[str, Dict[str, Any]]:
        doc_map = {}
        for d in docs:
            try:
                extracted = json.loads(d.extracted_data or "{}")
            except Exception:
                extracted = {}
            doc_map[d.document_type] = extracted
        return doc_map

    def run_full_audit(self) -> Dict[str, Any]:
        """
        Executes both the deterministic rules engine and the cross-document matching engine.
        Returns a unified audit dictionary with bilingual explanations and fix checklist.
        """
        docs = self._load_documents()
        doc_map = self._build_doc_map(docs)

        # 1. Run deterministic rules engine
        rules_engine = RulesEngine(self.db)
        rule_results: List[RuleEvaluationResult] = rules_engine.run_session_audit(self.session_id)

        # 2. Run fuzzy cross-document verification
        match_issues: List[CrossVerificationIssue] = run_cross_verification(doc_map)

        # 3. Compile statistics
        total_rules = len(rule_results)
        rules_passed = sum(1 for r in rule_results if r.status == "passed")
        rules_failed = sum(1 for r in rule_results if r.status == "failed")
        rules_review = sum(1 for r in rule_results if r.status == "needs_review")

        match_matches = sum(1 for m in match_issues if m.status == "match")
        match_mismatches = sum(1 for m in match_issues if m.status == "mismatch")
        match_review = sum(1 for m in match_issues if m.status == "needs_review")

        # 4. Generate bilingual explanations and fix checklist
        explanations: List[Dict[str, Any]] = []
        fix_checklist: List[Dict[str, str]] = []

        # Process rule results
        for r in rule_results:
            if r.status != "passed":
                explanations.append({
                    "id": r.rule_id,
                    "category": "Portal Requirement Rule",
                    "status": r.status,
                    "severity": r.severity,
                    "fields": r.fields,
                    "en": r.reason_en,
                    "hi": r.reason_hi
                })
                fix_checklist.append({
                    "issue": r.reason_en,
                    "action_en": f"Correct {', '.join(r.fields)} before submission to UP Scholarship portal.",
                    "action_hi": f"यूपी छात्रवृत्ति पोर्टल पर जमा करने से पहले {', '.join(r.fields)} को ठीक करें।"
                })

        # Process cross-document match issues
        for m in match_issues:
            if m.status != "match":
                explanations.append({
                    "id": m.check_id,
                    "category": "Cross-Document Discrepancy",
                    "status": m.status,
                    "severity": m.severity,
                    "fields": [f"{m.doc_a}.{m.field_a}", f"{m.doc_b}.{m.field_b}"],
                    "en": m.reason_en,
                    "hi": m.reason_hi
                })
                fix_checklist.append({
                    "issue": m.reason_en,
                    "action_en": f"Align {m.field_a} on {m.doc_a} with {m.field_b} on {m.doc_b}.",
                    "action_hi": f"{m.doc_a} पर {m.field_a} को {m.doc_b} पर {m.field_b} के साथ समान करें।"
                })

        # Determine overall status and score
        if rules_failed > 0 or match_mismatches > 0:
            overall_status = "FAIL"
            deductions = (rules_failed * 25) + (match_mismatches * 20) + (rules_review * 5) + (match_review * 5)
            overall_score = max(10, 100 - deductions)
        elif rules_review > 0 or match_review > 0:
            overall_status = "NEEDS_REVIEW"
            deductions = (rules_review * 10) + (match_review * 10)
            overall_score = max(70, 100 - deductions)
        else:
            overall_status = "PASS"
            overall_score = 100
            explanations.append({
                "id": "AUDIT_CLEAN",
                "category": "Overall Status",
                "status": "passed",
                "severity": "info",
                "fields": [],
                "en": "All portal validation rules and cross-document checks passed successfully.",
                "hi": "सभी पोर्टल सत्यापन नियम और अंतर-दस्तावेज़ जाँच सफलतापूर्वक उत्तीर्ण हुए।"
            })

        # Document summary with masked info
        doc_summaries = []
        for d in docs:
            doc_summaries.append({
                "id": d.id,
                "document_type": d.document_type,
                "original_filename": d.original_filename,
                "format_status": d.format_status,
                "overall_confidence": round(d.overall_confidence or 0.0, 2),
                "file_size_kb": d.file_size_kb
            })

        return {
            "session_id": self.session_id,
            "overall_status": overall_status,
            "overall_score": overall_score,
            "audited_at": datetime.now(timezone.utc).isoformat(),
            "summary": {
                "total_documents": len(docs),
                "rules_evaluated": total_rules,
                "rules_passed": rules_passed,
                "rules_failed": rules_failed,
                "rules_needs_review": rules_review,
                "cross_checks_total": len(match_issues),
                "cross_checks_matched": match_matches,
                "cross_checks_mismatched": match_mismatches,
                "cross_checks_needs_review": match_review
            },
            "documents": doc_summaries,
            "rule_results": [
                {
                    "rule_id": r.rule_id,
                    "status": r.status,
                    "severity": r.severity,
                    "score": r.score,
                    "reason_en": r.reason_en,
                    "reason_hi": r.reason_hi,
                    "fields": r.fields,
                    "values_masked": r.values_masked
                }
                for r in rule_results
            ],
            "cross_verifications": [
                {
                    "check_id": m.check_id,
                    "status": m.status,
                    "severity": m.severity,
                    "score": m.score,
                    "doc_a": m.doc_a,
                    "field_a": m.field_a,
                    "doc_b": m.doc_b,
                    "field_b": m.field_b,
                    "masked_a": m.masked_value_a,
                    "masked_b": m.masked_value_b,
                    "reason_en": m.reason_en,
                    "reason_hi": m.reason_hi
                }
                for m in match_issues
            ],
            "explanations": explanations,
            "fix_checklist": fix_checklist
        }

    def generate_pdf_report(self, audit_data: Optional[Dict[str, Any]] = None) -> bytes:
        """
        Generates a PDF audit report per FR-11 with pass/review/fail summary,
        masked identifiers, and a clear fix checklist.
        """
        if audit_data is None:
            audit_data = self.run_full_audit()

        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=letter,
            rightMargin=36,
            leftMargin=36,
            topMargin=36,
            bottomMargin=36
        )

        styles = getSampleStyleSheet()

        # Custom Typography
        title_style = ParagraphStyle(
            "DocTitle",
            parent=styles["Heading1"],
            fontSize=18,
            leading=22,
            textColor=colors.HexColor("#1a365d"),
            spaceAfter=4
        )
        subtitle_style = ParagraphStyle(
            "DocSubTitle",
            parent=styles["Normal"],
            fontSize=10,
            leading=14,
            textColor=colors.HexColor("#4a5568"),
            spaceAfter=12
        )
        h2_style = ParagraphStyle(
            "Heading2Custom",
            parent=styles["Heading2"],
            fontSize=12,
            leading=16,
            textColor=colors.HexColor("#2b6cb0"),
            spaceBefore=10,
            spaceAfter=6
        )
        body_style = ParagraphStyle(
            "BodyCustom",
            parent=styles["Normal"],
            fontSize=9,
            leading=13,
            textColor=colors.HexColor("#2d3748")
        )
        disclaimer_style = ParagraphStyle(
            "Disclaimer",
            parent=styles["Italic"],
            fontSize=8,
            leading=11,
            textColor=colors.HexColor("#718096"),
            spaceAfter=10
        )

        elements = []

        # 1. Header & Title
        elements.append(Paragraph("FormFix (फॉर्म फिक्स) - Pre-Submission Audit Report", title_style))
        elements.append(Paragraph("AI-Powered Smart Government Form Assistant & Verification Engine | Advisory Checklist", subtitle_style))
        elements.append(Paragraph(
            "<b>Disclaimer:</b> FormFix is an independent pre-submission assistive tool. "
            "It is not affiliated with the Government of Uttar Pradesh or scholarship portals. "
            "Results are advisory and do not guarantee approval.",
            disclaimer_style
        ))
        elements.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#cbd5e0"), spaceAfter=10))

        # 2. Executive Summary Box
        status_color = "#38a169" if audit_data["overall_status"] == "PASS" else ("#dd6b20" if audit_data["overall_status"] == "NEEDS_REVIEW" else "#e53e3e")
        summary_data = [
            [
                Paragraph(f"<b>Overall Audit Status:</b> <font color='{status_color}'><b>{audit_data['overall_status']}</b></font>", body_style),
                Paragraph(f"<b>Audit Readiness Score:</b> <b>{audit_data['overall_score']} / 100</b>", body_style),
            ],
            [
                Paragraph(f"<b>Session ID:</b> {audit_data['session_id'][:8]}...", body_style),
                Paragraph(f"<b>Audit Date:</b> {audit_data['audited_at'][:19]} UTC", body_style),
            ]
        ]
        summary_table = Table(summary_data, colWidths=[270, 270])
        summary_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f7fafc")),
            ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#e2e8f0")),
            ("PADDING", (0, 0), (-1, -1), 6),
        ]))
        elements.append(summary_table)
        elements.append(Spacer(1, 10))

        # 3. Documents Table
        elements.append(Paragraph("1. Uploaded Document Verification", h2_style))
        doc_rows = [["Document Category", "Original File", "Size", "Format Status", "OCR Confidence"]]
        for d in audit_data["documents"]:
            doc_rows.append([
                d["document_type"].replace("_", " ").title(),
                d["original_filename"][:20],
                f"{d['file_size_kb']:.1f} KB",
                d["format_status"],
                f"{d['overall_confidence'] * 100:.0f}%"
            ])
        doc_table = Table(doc_rows, colWidths=[130, 150, 70, 90, 100])
        doc_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#edf2f7")),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
            ("PADDING", (0, 0), (-1, -1), 4),
        ]))
        elements.append(doc_table)
        elements.append(Spacer(1, 10))

        # 4. Cross-Document & Rule Check Results
        elements.append(Paragraph("2. Deterministic Rules & Cross-Verification Findings", h2_style))
        check_rows = [["Check ID", "Status", "Masked Values Checked", "Reason / Finding"]]
        for r in audit_data["rule_results"]:
            check_rows.append([
                r["rule_id"],
                r["status"].upper(),
                ", ".join(str(v) for v in r["values_masked"]) if r["values_masked"] else "N/A",
                Paragraph(r["reason_en"], body_style)
            ])
        for c in audit_data["cross_verifications"]:
            check_rows.append([
                c["check_id"],
                c["status"].upper(),
                f"{c['masked_a']} vs {c['masked_b']}",
                Paragraph(c["reason_en"], body_style)
            ])
        check_table = Table(check_rows, colWidths=[120, 70, 140, 210])
        check_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#edf2f7")),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
            ("PADDING", (0, 0), (-1, -1), 4),
        ]))
        elements.append(check_table)
        elements.append(Spacer(1, 10))

        # 5. Fix Checklist
        elements.append(Paragraph("3. Actionable Fix Checklist (Before Portal Submission)", h2_style))
        if audit_data["fix_checklist"]:
            for idx, item in enumerate(audit_data["fix_checklist"], start=1):
                elements.append(Paragraph(f"<b>{idx}. {item['issue']}</b>", body_style))
                elements.append(Paragraph(f"&nbsp;&nbsp;&nbsp;&nbsp;<b>Fix (EN):</b> {item['action_en']}", body_style))
                elements.append(Paragraph(f"&nbsp;&nbsp;&nbsp;&nbsp;<b>सुधार (HI):</b> {item['action_hi']}", body_style))
                elements.append(Spacer(1, 4))
        else:
            elements.append(Paragraph("✅ <b>No fixes required!</b> All checks passed.", body_style))

        elements.append(Spacer(1, 15))
        elements.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#cbd5e0"), spaceAfter=6))
        elements.append(Paragraph("FormSaathi Pre-Submission Assistant | Built for Indian Citizens & Students", disclaimer_style))

        doc.build(elements)
        buffer.seek(0)
        return buffer.getvalue()
