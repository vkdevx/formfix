# FormSaathi: System Architecture

**Based on:** PRD v2.2 (Hackathon Edition) | **Scope:** UP Scholarship pre-submission audit | **Status:** Draft v1.0

FormSaathi is a pre-submission assistant. Users upload a filled application and supporting documents. The system extracts data with OCR, lets the user correct it, validates it with a deterministic rules engine, cross-verifies it across documents, and explains problems in Hindi and English.

---

## 1. Architecture Principles
1. **Rules decide, LLM explains:** Only the Python rules engine produces verdicts.
2. **Human in the loop:** Every OCR value is editable before validation.
3. **Privacy by design:** Mask on output, store nothing longer than needed, never store the full Aadhaar.
4. **Rules are data, not code:** Versioned rules in the database.
5. **Graceful degradation:** If OCR or LLM fails, manual entry and rule checks still work.
6. **MVP first:** Build the core pipeline; cyber-cafe mode is future scope.

---

## 2. Tech Stack
- **Frontend (PWA):** React.js, Tailwind CSS, Service Worker
- **Backend:** Python with FastAPI
- **OCR:** OpenCV, PyMuPDF, EasyOCR / Tesseract
- **Matching:** RapidFuzz, Transliteration library
- **Rules Engine:** Pure deterministic Python
- **Database:** PostgreSQL (with SQLite for local development)
- **Temporary Storage:** Encrypted local disk / memory with 30-minute TTL
