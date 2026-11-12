import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import api from './services/api';
import { isLoggedIn } from './services/auth';

function App() {
  const [audit, setAudit] = useState(null);
  const [manualSessionId, setManualSessionId] = useState('');
  const [loading, setLoading] = useState(true);
  const [downloading, setDownloading] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (isLoggedIn()) {
      fetchCurrentAudit();
    } else {
      setLoading(false);
    }
  }, []);

  const fetchCurrentAudit = async () => {
    setLoading(true);
    setError(null);
    try {
      const resp = await api.get('/explanations/current');
      setAudit(resp.data);
    } catch (err) {
      const msg = err.response?.data?.message || err.response?.data?.detail || err.message;
      setError(msg);
    } finally {
      setLoading(false);
    }
  };

  const fetchBySessionId = async () => {
    if (!manualSessionId.trim()) return;
    setLoading(true);
    setError(null);
    try {
      const resp = await api.get(`/explanations/${manualSessionId.trim()}`);
      setAudit(resp.data);
    } catch (err) {
      const msg = err.response?.data?.message || err.response?.data?.detail || err.message;
      setError(msg);
    } finally {
      setLoading(false);
    }
  };

  const handleDownloadPdf = async () => {
    setDownloading(true);
    try {
      const endpoint = audit?.session_id
        ? `/explanations/${audit.session_id}/pdf`
        : '/explanations/current/pdf';
      const resp = await api.get(endpoint, { responseType: 'blob' });
      
      const blobUrl = window.URL.createObjectURL(new Blob([resp.data], { type: 'application/pdf' }));
      const link = document.createElement('a');
      link.href = blobUrl;
      link.setAttribute('download', `FormFix_Audit_Report_${(audit?.session_id || 'session').slice(0, 8)}.pdf`);
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(blobUrl);
    } catch (err) {
      alert('Failed to download PDF report. Ensure audit was generated.');
    } finally {
      setDownloading(false);
    }
  };

  const getStatusColor = (status) => {
    if (status === 'PASS' || status === 'passed' || status === 'match') return 'var(--success)';
    if (status === 'NEEDS_REVIEW' || status === 'needs_review' || status === 'warning') return 'var(--accent)';
    return 'var(--error)';
  };

  return (
    <div className="page-container">
      {/* Header */}
      <div className="page-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '1rem' }}>
        <div>
          <h1>💡 AI Bilingual Explanations & Audit Report</h1>
          <p>
            Bilingual (English & Hindi) feedback grounded directly in deterministic portal rules and cross-document verification.
          </p>
        </div>
        {audit && (
          <button
            onClick={handleDownloadPdf}
            className="btn btn-primary"
            disabled={downloading}
            style={{ padding: '0.75rem 1.5rem' }}
          >
            {downloading ? 'Generating PDF...' : '📥 Download Official PDF Report'}
          </button>
        )}
      </div>

      {/* Manual lookup fallback */}
      <div
        className="card"
        style={{
          padding: '0.75rem 1rem',
          marginBottom: '1.5rem',
          display: 'flex',
          alignItems: 'center',
          gap: '0.75rem',
          flexWrap: 'wrap',
          background: '#f7fafc',
        }}
      >
        <span style={{ fontSize: '0.85rem', color: 'var(--text-light)', fontWeight: '600' }}>
          🔍 Lookup by Session ID:
        </span>
        <input
          type="text"
          className="form-input"
          placeholder="Paste Session UUID..."
          value={manualSessionId}
          onChange={(e) => setManualSessionId(e.target.value)}
          style={{ maxWidth: '320px', padding: '0.4rem 0.8rem', fontSize: '0.9rem' }}
        />
        <button
          onClick={fetchBySessionId}
          className="btn btn-outline"
          style={{ padding: '0.4rem 1rem', fontSize: '0.85rem' }}
          disabled={loading}
        >
          View Audit
        </button>
        {isLoggedIn() && (
          <button
            onClick={fetchCurrentAudit}
            className="btn btn-outline"
            style={{ padding: '0.4rem 1rem', fontSize: '0.85rem' }}
            disabled={loading}
          >
            🔄 Refresh My Current Audit
          </button>
        )}
      </div>

      {loading && (
        <div style={{ textAlign: 'center', padding: '3rem' }}>
          <div className="spinner spinner-dark" style={{ width: '40px', height: '40px' }}></div>
          <p style={{ marginTop: '1rem', color: 'var(--text-light)' }}>
            Evaluating deterministic rules and cross-document matches...
          </p>
        </div>
      )}

      {error && (
        <div className="alert alert-error" style={{ marginBottom: '1.5rem' }}>
          ❌ {error}
        </div>
      )}

      {!loading && !audit && (
        <div className="card empty-state">
          <div className="icon">📋</div>
          <h3>No Audit Results Yet</h3>
          <p>Upload your application documents and confirm the verification grid to generate a full audit report.</p>
          <div style={{ display: 'flex', gap: '1rem', justifyContent: 'center', marginTop: '1rem' }}>
            <Link to="/upload" className="btn btn-primary">
              📤 Upload Documents
            </Link>
            <Link to="/review" className="btn btn-accent">
              📝 Go to Review Grid
            </Link>
          </div>
        </div>
      )}

      {audit && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '2rem' }}>
          {/* Executive Verdict Banner */}
          <div
            className="card"
            style={{
              borderLeft: `8px solid ${getStatusColor(audit.overall_status)}`,
              background: '#fff',
            }}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '1rem' }}>
              <div>
                <span
                  style={{
                    fontSize: '0.85rem',
                    textTransform: 'uppercase',
                    letterSpacing: '1px',
                    fontWeight: 'bold',
                    color: getStatusColor(audit.overall_status),
                  }}
                >
                  PRE-SUBMISSION VERDICT
                </span>
                <h2 style={{ fontSize: '2rem', margin: '0.2rem 0', color: 'var(--primary)' }}>
                  {audit.overall_status === 'PASS' && '✅ PASSED — Ready for Submission'}
                  {audit.overall_status === 'NEEDS_REVIEW' && '⚠️ NEEDS REVIEW — Minor Discrepancies'}
                  {audit.overall_status === 'FAIL' && '❌ REJECT RISK — Critical Errors Detected'}
                </h2>
                <p style={{ margin: 0, color: 'var(--text-light)', fontSize: '0.95rem' }}>
                  Audited against Uttar Pradesh Post-Matric & Pre-Matric Scholarship Portal Deterministic Rules (v1.0).
                </p>
              </div>

              <div
                style={{
                  textAlign: 'center',
                  background: '#f7fafc',
                  padding: '1rem 1.5rem',
                  borderRadius: '12px',
                  border: '1px solid var(--border)',
                  minWidth: '150px',
                }}
              >
                <div style={{ fontSize: '0.8rem', color: 'var(--text-light)', fontWeight: 'bold' }}>
                  READINESS SCORE
                </div>
                <div style={{ fontSize: '2.5rem', fontWeight: '800', color: getStatusColor(audit.overall_status) }}>
                  {audit.overall_score}
                  <span style={{ fontSize: '1rem', color: 'var(--text-light)' }}>/100</span>
                </div>
              </div>
            </div>
          </div>

          {/* Actionable Fix Checklist */}
          {audit.fix_checklist && audit.fix_checklist.length > 0 && (
            <div className="card" style={{ border: '1px solid #fbd38d', background: '#fffaf0' }}>
              <h3 style={{ color: '#c05621', marginTop: 0, display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                📋 Student Action Checklist ({audit.fix_checklist.length} Fixes Required)
              </h3>
              <p style={{ fontSize: '0.9rem', color: '#744210' }}>
                Correct these items before submitting your application to the cyber-cafe or official UP scholarship portal:
              </p>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem', marginTop: '1rem' }}>
                {audit.fix_checklist.map((item, idx) => (
                  <div
                    key={idx}
                    style={{
                      background: '#fff',
                      padding: '0.85rem 1rem',
                      borderRadius: '8px',
                      border: '1px solid #feebc8',
                    }}
                  >
                    <div style={{ fontWeight: '600', color: 'var(--primary)', marginBottom: '0.25rem' }}>
                      {idx + 1}. {item.issue}
                    </div>
                    <div style={{ fontSize: '0.9rem', color: '#2d3748' }}>
                      🇬🇧 <b>Action:</b> {item.action_en}
                    </div>
                    <div style={{ fontSize: '0.9rem', color: '#2d3748', marginTop: '0.15rem' }}>
                      🇮🇳 <b>सुधार:</b> {item.action_hi}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Cross-Document Fuzzy Verification Grid */}
          <div className="card">
            <h3 style={{ marginTop: 0, color: 'var(--primary)' }}>
              🔍 Cross-Document Verification (FR-08)
            </h3>
            <p style={{ fontSize: '0.9rem', color: 'var(--text-light)' }}>
              Fuzzy matching comparing Aadhaar, Marksheets, and Bank Passbook records to prevent cyber-cafe rejection.
            </p>

            <div style={{ overflowX: 'auto', marginTop: '1rem' }}>
              <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left' }}>
                <thead>
                  <tr style={{ background: '#f7fafc', borderBottom: '2px solid var(--border)' }}>
                    <th style={{ padding: '0.6rem 0.8rem', fontSize: '0.85rem' }}>CHECK NAME</th>
                    <th style={{ padding: '0.6rem 0.8rem', fontSize: '0.85rem' }}>DOCUMENTS COMPARED</th>
                    <th style={{ padding: '0.6rem 0.8rem', fontSize: '0.85rem' }}>VALUES COMPARED</th>
                    <th style={{ padding: '0.6rem 0.8rem', fontSize: '0.85rem' }}>SIMILARITY</th>
                    <th style={{ padding: '0.6rem 0.8rem', fontSize: '0.85rem' }}>STATUS</th>
                  </tr>
                </thead>
                <tbody>
                  {audit.cross_verifications?.map((c) => (
                    <tr key={c.check_id} style={{ borderBottom: '1px solid var(--border)' }}>
                      <td style={{ padding: '0.75rem 0.8rem', fontWeight: '600' }}>
                        {c.check_id.replace('CROSS_', '').replace(/_/g, ' ')}
                      </td>
                      <td style={{ padding: '0.75rem 0.8rem', fontSize: '0.85rem' }}>
                        {c.doc_a} ({c.field_a}) <br />vs {c.doc_b} ({c.field_b})
                      </td>
                      <td style={{ padding: '0.75rem 0.8rem', fontSize: '0.9rem', fontFamily: 'monospace' }}>
                        "{c.masked_a}" vs "{c.masked_b}"
                      </td>
                      <td style={{ padding: '0.75rem 0.8rem', fontWeight: 'bold' }}>
                        {c.score}%
                      </td>
                      <td style={{ padding: '0.75rem 0.8rem' }}>
                        <span
                          style={{
                            fontSize: '0.75rem',
                            fontWeight: 'bold',
                            padding: '0.2rem 0.6rem',
                            borderRadius: '12px',
                            background: c.status === 'match' ? '#c6f6d5' : (c.status === 'needs_review' ? '#feebc8' : '#fed7d7'),
                            color: c.status === 'match' ? '#22543d' : (c.status === 'needs_review' ? '#744210' : '#742a2a'),
                          }}
                        >
                          {c.status.toUpperCase()}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {/* Bilingual Explanations Feed */}
          <div className="card">
            <h3 style={{ marginTop: 0, color: 'var(--primary)' }}>
              💬 Grounded Bilingual Explanations (FR-10)
            </h3>
            <p style={{ fontSize: '0.9rem', color: 'var(--text-light)' }}>
              Every issue explained in simple Hindi and English, grounded strictly in rule engine results.
            </p>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem', marginTop: '1rem' }}>
              {audit.explanations?.map((exp, idx) => (
                <div key={idx} className="explanation-item">
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.5rem' }}>
                    <span style={{ fontWeight: 'bold', fontSize: '0.85rem', color: 'var(--teal)' }}>
                      {exp.category} — {exp.id}
                    </span>
                    <span
                      style={{
                        fontSize: '0.75rem',
                        fontWeight: 'bold',
                        padding: '0.15rem 0.5rem',
                        borderRadius: '4px',
                        background: exp.status === 'passed' ? '#c6f6d5' : (exp.status === 'needs_review' ? '#feebc8' : '#fed7d7'),
                        color: exp.status === 'passed' ? '#22543d' : (exp.status === 'needs_review' ? '#744210' : '#742a2a'),
                      }}
                    >
                      {exp.status.toUpperCase()}
                    </span>
                  </div>

                  <p>
                    <span className="lang-label lang-en">EN</span>
                    {exp.en}
                  </p>
                  <p>
                    <span className="lang-label lang-hi">HI</span>
                    {exp.hi}
                  </p>
                </div>
              ))}
            </div>
          </div>

          {/* Action Footer */}
          <div style={{ textAlign: 'center', padding: '1rem 0 3rem 0' }}>
            <button
              onClick={handleDownloadPdf}
              className="btn btn-primary"
              disabled={downloading}
              style={{ padding: '0.85rem 2rem', fontSize: '1.05rem' }}
            >
              {downloading ? 'Downloading PDF...' : '📥 Download Official PDF Audit Checklist'}
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

export default App;
