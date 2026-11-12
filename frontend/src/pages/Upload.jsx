import React, { useState, useEffect } from 'react';
import api from '../services/api';
import { useNavigate, Link } from 'react-router-dom';
import { isLoggedIn } from '../services/auth';

function Upload() {
  const [file, setFile] = useState(null);
  const [docType, setDocType] = useState('aadhaar');
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState(null);
  const [msgType, setMsgType] = useState('info');
  const [hasConsented, setHasConsented] = useState(true);
  const [showConsentModal, setShowConsentModal] = useState(false);
  const [uploadedDocs, setUploadedDocs] = useState([]);
  const [fetchingDocs, setFetchingDocs] = useState(false);
  const navigate = useNavigate();

  const docTypes = [
    { value: 'aadhaar', label: '🪪 Aadhaar Card (Max 200 KB)', limitKb: 200 },
    { value: 'marksheet', label: '📊 High School / Inter Marksheet (Max 200 KB)', limitKb: 200 },
    { value: 'bank_passbook', label: '🏦 Bank Passbook Copy (Max 200 KB)', limitKb: 200 },
    { value: 'income_certificate', label: '💰 Income Certificate (Max 200 KB)', limitKb: 200 },
    { value: 'caste_certificate', label: '📜 Caste Certificate (Max 200 KB)', limitKb: 200 },
    { value: 'application', label: '📝 UP Scholarship Application Form (Max 200 KB)', limitKb: 200 },
  ];

  // Check login and consent on mount
  useEffect(() => {
    if (!isLoggedIn()) {
      navigate('/login');
      return;
    }
    checkConsentAndFetchDocs();
  }, []);

  const checkConsentAndFetchDocs = async () => {
    try {
      const consentResp = await api.get('/consent/status');
      if (!consentResp.data.has_consented) {
        setHasConsented(false);
        setShowConsentModal(true);
      } else {
        setHasConsented(true);
      }
    } catch (err) {
      console.warn('Could not check consent status:', err);
    }
    fetchUploadedDocs();
  };

  const fetchUploadedDocs = async () => {
    setFetchingDocs(true);
    try {
      const resp = await api.get('/documents');
      setUploadedDocs(resp.data.documents || []);
    } catch (err) {
      console.warn('Could not fetch existing documents:', err);
    } finally {
      setFetchingDocs(false);
    }
  };

  const handleAcceptConsent = async () => {
    try {
      await api.post('/consent', { accept: true });
      setHasConsented(true);
      setShowConsentModal(false);
      setMessage('✅ DPDP Act 2023 Consent recorded. You may now upload your documents.');
      setMsgType('success');
    } catch (err) {
      alert('Failed to record consent. Please try again.');
    }
  };

  const handleFileChange = (e) => {
    const selected = e.target.files[0];
    if (!selected) return;

    const currentTypeConfig = docTypes.find((d) => d.value === docType);
    const maxKb = currentTypeConfig ? currentTypeConfig.limitKb : 200;
    const fileKb = selected.size / 1024;

    if (fileKb > maxKb) {
      setMessage(`⚠️ Selected file is ${fileKb.toFixed(1)} KB, which exceeds the UP portal limit of ${maxKb} KB.`);
      setMsgType('error');
      setFile(null);
      return;
    }

    setFile(selected);
    setMessage(null);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!hasConsented) {
      setShowConsentModal(true);
      return;
    }
    if (!file) {
      setMessage('Please select a file first.');
      setMsgType('error');
      return;
    }
    setLoading(true);
    setMessage(null);
    try {
      const formData = new FormData();
      formData.append('file', file);
      formData.append('document_type', docType);
      
      const resp = await api.post('/documents', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });

      setMessage(`🎉 Successfully uploaded ${resp.data.original_filename}! OCR extraction completed.`);
      setMsgType('success');
      setFile(null);
      fetchUploadedDocs();
    } catch (err) {
      const errorMsg =
        err.response?.data?.message ||
        err.response?.data?.detail ||
        err.message ||
        'Upload failed.';
      const hint = err.response?.data?.hint ? ` (${err.response.data.hint})` : '';
      setMessage(`❌ ${errorMsg}${hint}`);
      setMsgType('error');
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async (docId) => {
    if (!window.confirm('Delete this document?')) return;
    try {
      await api.delete(`/documents/${docId}`);
      fetchUploadedDocs();
      setMessage('🗑️ Document deleted successfully.');
      setMsgType('info');
    } catch (err) {
      alert('Failed to delete document.');
    }
  };

  return (
    <div className="page-container">
      {/* DPDP Act Consent Modal */}
      {showConsentModal && (
        <div
          style={{
            position: 'fixed',
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            background: 'rgba(0,0,0,0.6)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            zIndex: 1000,
            padding: '1rem',
          }}
        >
          <div
            className="card"
            style={{
              maxWidth: '540px',
              width: '100%',
              background: '#fff',
              boxShadow: '0 20px 25px -5px rgba(0, 0, 0, 0.2)',
            }}
          >
            <div style={{ fontSize: '2.5rem', textAlign: 'center', marginBottom: '0.5rem' }}>🛡️</div>
            <h2 style={{ color: 'var(--primary)', textAlign: 'center', margin: '0 0 0.5rem 0' }}>
              DPDP Act 2023 Consent
            </h2>
            <p style={{ fontSize: '0.9rem', color: 'var(--text-light)', textAlign: 'center', marginBottom: '1rem' }}>
              डिजिटल व्यक्तिगत डेटा संरक्षण अधिनियम 2023 सहमति
            </p>
            <div
              style={{
                background: '#f7fafc',
                border: '1px solid var(--border)',
                borderRadius: '8px',
                padding: '1rem',
                fontSize: '0.88rem',
                lineHeight: '1.6',
                maxHeight: '220px',
                overflowY: 'auto',
                marginBottom: '1.25rem',
              }}
            >
              <p><b>1. Purpose of Processing:</b> FormFix processes your documents solely to perform pre-submission error checking and cross-document verification for Uttar Pradesh scholarship portals.</p>
              <p><b>2. Privacy & Encryption:</b> All ephemeral files are encrypted at rest using AES-128 Fernet. Sensitive identifiers like your 12-digit Aadhaar number and Bank Account number are automatically masked (`XXXX XXXX 1234`).</p>
              <p><b>3. Short Retention Window:</b> Your uploaded files are stored ephemerally and automatically purged after 30 minutes of inactivity.</p>
              <p><b>4. Right to Erasure:</b> You may permanently delete your uploaded files and data at any time under DPDP Act 2023.</p>
            </div>
            <div style={{ display: 'flex', gap: '0.75rem', justifyContent: 'flex-end' }}>
              <button
                type="button"
                className="btn btn-outline"
                onClick={() => navigate('/')}
              >
                Decline & Exit
              </button>
              <button
                type="button"
                className="btn btn-primary"
                onClick={handleAcceptConsent}
              >
                ✅ I Understand & Agree
              </button>
            </div>
          </div>
        </div>
      )}

      <div className="page-header">
        <h1>📤 Upload Supporting Documents</h1>
        <p>Upload your application documents. We validate portal file constraints and extract values via bilingual OCR.</p>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr', gap: '2rem' }}>
        <div className="card" style={{ maxWidth: '680px' }}>
          <form onSubmit={handleSubmit}>
            {/* Document Type */}
            <div className="form-group">
              <label className="form-label">📋 Document Category</label>
              <select
                className="form-select"
                value={docType}
                onChange={(e) => setDocType(e.target.value)}
              >
                {docTypes.map((dt) => (
                  <option key={dt.value} value={dt.value}>
                    {dt.label}
                  </option>
                ))}
              </select>
            </div>

            {/* File Upload Area */}
            <div className="form-group">
              <label className="form-label">📎 Choose Document File</label>
              <div
                className="file-upload-area"
                onClick={() => document.getElementById('file-input').click()}
              >
                <div className="icon">📄</div>
                <p>Click or drag to select file</p>
                <p style={{ fontSize: '0.85rem' }}>Accepted: PDF, JPG, PNG (Max 200 KB per UP Portal rules)</p>
                {file && (
                  <div className="selected-file">
                    ✅ Selected: {file.name} ({(file.size / 1024).toFixed(1)} KB)
                  </div>
                )}
              </div>
              <input
                id="file-input"
                type="file"
                accept=".pdf,.png,.jpg,.jpeg"
                onChange={handleFileChange}
                style={{ display: 'none' }}
              />
            </div>

            {/* Submit Button */}
            <button
              type="submit"
              className="btn btn-primary"
              disabled={loading}
              style={{ width: '100%', justifyContent: 'center' }}
            >
              {loading ? (
                <>
                  <span className="spinner"></span> Processing & OCR Extracting...
                </>
              ) : (
                '📤 Upload & Extract'
              )}
            </button>
          </form>

          {/* Message Alert */}
          {message && (
            <div className={`alert alert-${msgType}`} style={{ marginTop: '1rem' }}>
              {message}
            </div>
          )}
        </div>

        {/* Uploaded Documents List */}
        <div className="card" style={{ maxWidth: '680px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
            <h3 style={{ margin: 0 }}>📁 Uploaded Documents ({uploadedDocs.length})</h3>
            {uploadedDocs.length > 0 && (
              <Link to="/review" className="btn btn-accent" style={{ fontSize: '0.9rem', padding: '0.4rem 1rem' }}>
                Go to Review Grid →
              </Link>
            )}
          </div>

          {fetchingDocs ? (
            <p>Loading documents...</p>
          ) : uploadedDocs.length === 0 ? (
            <div className="empty-state">
              <div className="icon">📂</div>
              <p>No documents uploaded yet. Upload Aadhaar, Marksheet, and Passbook above to begin.</p>
            </div>
          ) : (
            <div className="docs-list">
              {uploadedDocs.map((doc) => (
                <div key={doc.id} className="doc-card">
                  <div className="doc-type-badge">{doc.document_type}</div>
                  <div className="doc-info">
                    <h3>{doc.original_filename}</h3>
                    <div className="confidence">
                      Status: <b>{doc.format_status}</b> | Size: {doc.file_size_kb.toFixed(1)} KB | OCR Confidence:{' '}
                      {(doc.overall_confidence * 100).toFixed(0)}%
                    </div>
                  </div>
                  <button
                    className="btn btn-outline"
                    style={{ color: 'var(--error)', borderColor: '#fed7d7', padding: '0.3rem 0.6rem' }}
                    onClick={() => handleDelete(doc.id)}
                  >
                    🗑️
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default Upload;
