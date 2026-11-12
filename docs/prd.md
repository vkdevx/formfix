# FormSaathi PRD v2.2
**AI-Powered Government Form Pre-Submission Assistant and Validation Engine (Hackathon Edition)**
- **Version:** 2.2 (supersedes v2.1)
- **Date:** 10 November 2026
- **Platform:** Responsive Web App and Progressive Web App (PWA)
- **Initial Scope:** Uttar Pradesh (UP) Scholarship Portal pre-submission audit

---

## 1. Executive Summary
Government form submissions in India, especially scholarship portals such as the UP Scholarship portal, see high rejection rates caused by small, preventable errors: spelling differences across identity documents, mismatched dates of birth, wrong file formats, and unclear guidelines.

FormSaathi is a pre-submission assistant. The applicant uploads a filled application and supporting documents. FormSaathi extracts the data with OCR, checks it against deterministic rules, cross-verifies it across documents, and explains every problem in simple Hindi and English. The goal is to **significantly reduce preventable rejections** and to save students repeated trips to cyber-cafes.

**Core value proposition:** help students and citizens check, correct, and prepare an error-free application before final submission, independently and at low cost.

**Important:** FormSaathi is not affiliated with any government portal. It does not submit forms and does not guarantee approval.

---

## 2. Problem Statement and Pain Points
- **Confusing guidelines:** complex terminology in portal notices leaves applicants unsure about mandatory fields.
- **Cross-document discrepancies:** small spelling variations, DOB mismatches, or different guardian names across Aadhaar, marksheets, and bank passbooks lead to rejection.
- **Format failures:** wrong image resolution, file size over the limit, or unreadable PDF scans.
- **Socio-economic overhead:** students in Tier-2 and Tier-3 regions lose time and money on repeated cyber-cafe visits for corrections.

---

## 3. Goals, Non-Goals, and Success Metrics

### 3.1 Goals
1. Detect the most common rejection causes before submission.
2. Explain each issue in plain bilingual language with a clear fix.
3. Protect user privacy by design (masking, short-lived storage, consent).
4. Keep the user in control: every extracted value can be reviewed and corrected.

### 3.2 Non-Goals (for this version)
- Auto-filling or submitting forms on the government portal.
- Verifying documents against government databases (UIDAI, DigiLocker, etc.).
- Guaranteeing scholarship approval or eligibility.
- Supporting states other than Uttar Pradesh.

### 3.3 Success Metrics
- OCR field accuracy on clean sample documents: 90% or higher
- Seeded errors detected in test set: 85% or higher
- False alarms per form: 2 or fewer
- Time to complete one full audit: Under 3 minutes
- Demo: planted mismatches caught live: All planted errors
- Usability: first-time user finishes audit unaided: 4 out of 5 testers

---

## 4. Personas and User Stories
- **Persona 1: Riya, class 12 student (Tier-2 town).** Applies for a scholarship on her own phone, has limited data, and is afraid of rejection.
  - As a student, I want to upload my documents and see what is wrong, so that I can fix it before submitting.
  - As a student, I want explanations in Hindi, so that I understand each problem.
  - As a student, I want my Aadhaar number hidden on screen, so that my data stays safe.
- **Persona 2: Manoj, cyber-cafe operator.** Fills dozens of forms daily for walk-in students and wants fewer repeat visits. (Future scope)

---

## 5. Functional Requirements
- **FR-01 (Must):** User can sign up and log in with phone OTP or email. Each session is isolated.
- **FR-02 (Must):** User must accept a consent screen (purpose, data used, retention period) before any upload.
- **FR-03 (Must):** Upload filled application PDF and supporting documents (Aadhaar, marksheet, income cert, caste cert, bank passbook).
- **FR-04 (Must):** Checks file type, size, and resolution against portal limits and flags failures immediately.
- **FR-05 (Must):** Extracts fields using OCR with confidence scores. Low-confidence fields highlighted.
- **FR-06 (Must):** Extracted values appear in an editable verification grid. Corrections are used for all later checks.
- **FR-07 (Must):** Deterministic rules engine validates mandatory fields, regex patterns, allowed values, and date logic.
- **FR-08 (Must):** Cross-document comparison using fuzzy matching (Match, Needs Review, Mismatch).
- **FR-09 (Must):** Sensitive identifiers (Aadhaar) masked in every screen and report, showing only last 4 digits.
- **FR-10 (Should):** Plain-language explanations in Hindi and English grounded only in rule results.
- **FR-11 (Should):** Downloadable audit report (PDF) with pass, review, fail summary and fix checklist.
- **FR-12 (Must):** User can delete their data at any time. All files removed on session expiry.
