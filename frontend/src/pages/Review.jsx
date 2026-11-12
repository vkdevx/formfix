import React, { useEffect, useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import api from '../services/api';
import { isLoggedIn } from '../services/auth';

function Review() {
  const [grid, setGrid] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [confirmMsg, setConfirmMsg] = useState(null);
  const [confirming, setConfirming] = useState(false);
  const [editingField, setEditingField] = useState(null); // { docId, fieldName, value }
  const [savingEdit, setSavingEdit] = useState(false);
  const navigate = useNavigate();

  useEffect(() => {
    if (!isLoggedIn()) {
      navigate('/login');
      return;
    }
    fetchGrid();
  }, []);

  const fetchGrid = async () => {
    setLoading(true);
    setError(null);
    try {
      const resp = await api.get('/review/grid');
      setGrid(resp.data);
    } catch (err) {
      const msg = err.response?.data?.message || err.response?.data?.detail || err.message;
      setError(msg);
    } finally {
      setLoading(false);
    }
  };

  const handleEditClick = (docId, fieldName, currentValue) => {
    setEditingField({ docId, fieldName, value: currentValue });
  };

  const handleSaveCorrection = async () => {
    if (!editingField) return;
    setSavingEdit(true);
    try {
      await api.put(`/review/documents/${editingField.docId}/fields`, {
        corrections: {
          [editingField.fieldName]: editingField.value,
        },
      });
      setEditingField(null);
      await fetchGrid();
    } catch (err) {
      alert(err.response?.data?.message || 'Failed to save correction.');
    } finally {
      setSavingEdit(false);
    }
  };

  const handleConfirm = async () => {
    setConfirming(true);
    setConfirmMsg(null);
    try {
      const resp = await api.post('/review/confirm');
      setConfirmMsg('✅ Verification grid confirmed! Running deterministic audit...');
      setTimeout(() => {
        navigate('/explanations');
      }, 1000);
    } catch (err) {
      const msg = err.response?.data?.message || err.response?.data?.detail || err.message;
      setConfirmMsg(`❌ ${msg}`);
    } finally {
      setConfirming(false);
    }
  };

  const getBadgeStyle = (badge) => {
    if (badge === 'high') {
      return { background: '#c6f6d5', color: '#22543d', border: '1px solid #9ae6b4' };
    } else if (badge === 'medium') {
      return { background: '#feebc8', color: '#744210', border: '1px solid #fbd38d' };
    }
    return { background: '#fed7d7', color: '#742a2a', border: '1px solid #feb2b2' };
  };

  if (loading) {
    return (
      <div className="page-container" style={{ textAlign: 'center', padding: '4rem' }}>
        <div className="spinner spinner-dark" style={{ width: '40px', height: '40px' }}></div>
        <p style={{ marginTop: '1rem', color: 'var(--text-light)' }}>
          Loading extracted document verification grid...
        </p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="page-container">
        <div className="alert alert-error">❌ {error}</div>
        <Link to="/upload" className="btn btn-primary">
          ← Return to Upload Page
        </Link>
      </div>
    );
  }

  const docs = grid?.documents || [];

  return (
    <div className="page-container">
      <div className="page-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '1rem' }}>
        <div>
          <h1>📝 Interactive Verification Grid</h1>
          <p>
            Human-in-the-Loop review: verify and correct OCR extracted fields before running portal rules.
          </p>
        </div>
        {docs.length > 0 && (
          <button
            onClick={handleConfirm}
            className="btn btn-accent"
            disabled={confirming}
            style={{ padding: '0.75rem 1.75rem', fontSize: '1rem' }}
          >
            {confirming ? 'Auditing...' : '🚀 Confirm & Run Rules Audit →'}
          </button>
        )}
      </div>

      {confirmMsg && (
        <div className={`alert ${confirmMsg.startsWith('✅') ? 'alert-success' : 'alert-error'}`}>
          {confirmMsg}
        </div>
      )}

      {/* Summary KPI Cards */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
          gap: '1rem',
          marginBottom: '2rem',
        }}
      >
        <div className="card" style={{ padding: '1rem' }}>
          <div style={{ color: 'var(--text-light)', fontSize: '0.85rem' }}>Total Documents</div>
          <div style={{ fontSize: '1.75rem', fontWeight: 'bold', color: 'var(--primary)' }}>
            {docs.length}
          </div>
        </div>
        <div className="card" style={{ padding: '1rem' }}>
          <div style={{ color: 'var(--text-light)', fontSize: '0.85rem' }}>Total Fields Verified</div>
          <div style={{ fontSize: '1.75rem', fontWeight: 'bold', color: 'var(--teal)' }}>
            {grid?.total_fields || 0}
          </div>
        </div>
        <div className="card" style={{ padding: '1rem' }}>
          <div style={{ color: 'var(--text-light)', fontSize: '0.85rem' }}>User Corrections</div>
          <div style={{ fontSize: '1.75rem', fontWeight: 'bold', color: 'var(--accent)' }}>
            {grid?.corrected_count || 0}
          </div>
        </div>
        <div className="card" style={{ padding: '1rem' }}>
          <div style={{ color: 'var(--text-light)', fontSize: '0.85rem' }}>Low Confidence Fields</div>
          <div
            style={{
              fontSize: '1.75rem',
              fontWeight: 'bold',
              color: (grid?.low_confidence_count || 0) > 0 ? 'var(--error)' : 'var(--success)',
            }}
          >
            {grid?.low_confidence_count || 0}
          </div>
        </div>
      </div>

      {docs.length === 0 ? (
        <div className="card empty-state">
          <div className="icon">📂</div>
          <h3>No documents ready for review</h3>
          <p>Please upload your application documents first to view the extracted verification grid.</p>
          <Link to="/upload" className="btn btn-primary" style={{ marginTop: '1rem' }}>
            📤 Upload Documents Now
          </Link>
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '2rem' }}>
          {docs.map((doc) => {
            const fieldKeys = Object.keys(doc.fields || {});
            return (
              <div key={doc.document_id} className="card">
                <div
                  style={{
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center',
                    borderBottom: '1px solid var(--border)',
                    paddingBottom: '0.75rem',
                    marginBottom: '1rem',
                    flexWrap: 'wrap',
                    gap: '0.5rem',
                  }}
                >
                  <div>
                    <h2 style={{ margin: 0, fontSize: '1.2rem', color: 'var(--primary)' }}>
                      {doc.document_label_en} ({doc.document_label_hi})
                    </h2>
                    <span style={{ fontSize: '0.85rem', color: 'var(--text-light)' }}>
                      File: {doc.original_filename}
                    </span>
                  </div>
                  <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
                    {doc.has_corrections && (
                      <span
                        style={{
                          fontSize: '0.75rem',
                          padding: '0.2rem 0.5rem',
                          background: '#e6fffa',
                          color: '#234e52',
                          borderRadius: '4px',
                          border: '1px solid #b2f5ea',
                        }}
                      >
                        ✏️ Corrected
                      </span>
                    )}
                    <span
                      style={{
                        fontSize: '0.85rem',
                        fontWeight: '600',
                        padding: '0.25rem 0.6rem',
                        borderRadius: '4px',
                        ...getBadgeStyle(doc.overall_confidence >= 0.85 ? 'high' : 'medium'),
                      }}
                    >
                      OCR Confidence: {(doc.overall_confidence * 100).toFixed(0)}%
                    </span>
                  </div>
                </div>

                {fieldKeys.length === 0 ? (
                  <p style={{ color: 'var(--text-light)', fontStyle: 'italic' }}>
                    No fields extracted for this document. You may enter values manually.
                  </p>
                ) : (
                  <div style={{ overflowX: 'auto' }}>
                    <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left' }}>
                      <thead>
                        <tr style={{ background: '#f7fafc', borderBottom: '2px solid var(--border)' }}>
                          <th style={{ padding: '0.6rem 0.8rem', fontSize: '0.85rem', color: 'var(--text-light)' }}>FIELD NAME</th>
                          <th style={{ padding: '0.6rem 0.8rem', fontSize: '0.85rem', color: 'var(--text-light)' }}>EXTRACTED VALUE</th>
                          <th style={{ padding: '0.6rem 0.8rem', fontSize: '0.85rem', color: 'var(--text-light)' }}>CONFIDENCE</th>
                          <th style={{ padding: '0.6rem 0.8rem', fontSize: '0.85rem', color: 'var(--text-light)' }}>STATUS</th>
                          <th style={{ padding: '0.6rem 0.8rem', fontSize: '0.85rem', color: 'var(--text-light)', textAlign: 'right' }}>ACTION</th>
                        </tr>
                      </thead>
                      <tbody>
                        {fieldKeys.map((fname) => {
                          const f = doc.fields[fname];
                          const isEditing =
                            editingField &&
                            editingField.docId === doc.document_id &&
                            editingField.fieldName === fname;

                          return (
                            <tr key={fname} style={{ borderBottom: '1px solid var(--border)' }}>
                              <td style={{ padding: '0.75rem 0.8rem' }}>
                                <div style={{ fontWeight: '600', color: 'var(--text)' }}>{f.label_en}</div>
                                <div style={{ fontSize: '0.8rem', color: 'var(--text-light)' }}>{f.label_hi}</div>
                              </td>

                              <td style={{ padding: '0.75rem 0.8rem' }}>
                                {isEditing ? (
                                  <input
                                    type="text"
                                    className="form-input"
                                    value={editingField.value}
                                    onChange={(e) =>
                                      setEditingField({ ...editingField, value: e.target.value })
                                    }
                                    style={{ padding: '0.3rem 0.6rem', fontSize: '0.9rem' }}
                                    autoFocus
                                  />
                                ) : (
                                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                                    <span style={{ fontWeight: '500', fontSize: '0.95rem' }}>
                                      {f.value || <span style={{ color: '#a0aec0', fontStyle: 'italic' }}>[Empty]</span>}
                                    </span>
                                    {f.is_masked && (
                                      <span
                                        style={{
                                          fontSize: '0.7rem',
                                          background: '#edf2f7',
                                          padding: '2px 6px',
                                          borderRadius: '4px',
                                          color: '#4a5568',
                                        }}
                                      >
                                        🔒 Masked
                                      </span>
                                    )}
                                  </div>
                                )}
                              </td>

                              <td style={{ padding: '0.75rem 0.8rem' }}>
                                <span
                                  style={{
                                    fontSize: '0.75rem',
                                    fontWeight: '700',
                                    padding: '0.2rem 0.6rem',
                                    borderRadius: '12px',
                                    ...getBadgeStyle(f.confidence_badge),
                                  }}
                                >
                                  {(f.confidence * 100).toFixed(0)}% ({f.confidence_badge.toUpperCase()})
                                </span>
                              </td>

                              <td style={{ padding: '0.75rem 0.8rem' }}>
                                {f.validation_passed ? (
                                  <span style={{ color: 'var(--success)', fontSize: '0.85rem' }}>✓ Valid</span>
                                ) : (
                                  <span style={{ color: 'var(--error)', fontSize: '0.85rem', title: f.hint }}>
                                    ⚠️ {f.hint || 'Check format'}
                                  </span>
                                )}
                              </td>

                              <td style={{ padding: '0.75rem 0.8rem', textAlign: 'right' }}>
                                {isEditing ? (
                                  <div style={{ display: 'flex', gap: '0.4rem', justifyContent: 'flex-end' }}>
                                    <button
                                      type="button"
                                      className="btn btn-primary"
                                      style={{ padding: '0.25rem 0.6rem', fontSize: '0.8rem' }}
                                      disabled={savingEdit}
                                      onClick={handleSaveCorrection}
                                    >
                                      Save
                                    </button>
                                    <button
                                      type="button"
                                      className="btn btn-outline"
                                      style={{ padding: '0.25rem 0.6rem', fontSize: '0.8rem' }}
                                      onClick={() => setEditingField(null)}
                                    >
                                      Cancel
                                    </button>
                                  </div>
                                ) : (
                                  <button
                                    type="button"
                                    className="btn btn-outline"
                                    style={{ padding: '0.25rem 0.6rem', fontSize: '0.8rem' }}
                                    onClick={() => handleEditClick(doc.document_id, fname, f.value)}
                                  >
                                    ✏️ Edit
                                  </button>
                                )}
                              </td>
                            </tr>
                          );
                        })}
                      </tbody>
                    </table>
                  </div>
                )}
              </div>
            );
          })}

          <div style={{ textAlign: 'center', marginTop: '1rem', paddingBottom: '2rem' }}>
            <button
              onClick={handleConfirm}
              className="btn btn-accent"
              disabled={confirming}
              style={{ padding: '0.85rem 2.5rem', fontSize: '1.1rem' }}
            >
              {confirming ? 'Executing Audit...' : '🚀 Confirm Verification & Run Audit'}
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

export default Review;
