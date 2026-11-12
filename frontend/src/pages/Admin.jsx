import React, { useState, useEffect } from 'react';
import api from '../services/api';
import { getUserRole, isLoggedIn } from '../services/auth';

export default function Admin() {
  const [stats, setStats] = useState(null);
  const [users, setUsers] = useState([]);
  const [rules, setRules] = useState([]);
  const [documents, setDocuments] = useState([]);
  const [adminKey, setAdminKey] = useState('');
  const [loading, setLoading] = useState(true);
  const [actionMsg, setActionMsg] = useState('');
  const [error, setError] = useState('');

  const headers = adminKey ? { 'X-Admin-Key': adminKey } : {};

  useEffect(() => {
    fetchAdminData();
  }, []);

  const fetchAdminData = async () => {
    setLoading(true);
    setError('');
    try {
      const statsResp = await api.get('/admin/stats', { headers });
      setStats(statsResp.data.stats);

      const usersResp = await api.get('/admin/users', { headers });
      setUsers(usersResp.data || []);

      const rulesResp = await api.get('/admin/rules', { headers });
      setRules(rulesResp.data || []);

      const docsResp = await api.get('/admin/documents', { headers });
      setDocuments(docsResp.data || []);
    } catch (err) {
      const msg = err.response?.data?.message || err.response?.data?.detail || err.message;
      setError(`Access restricted: ${msg}. Enter Admin Key below if required.`);
    } finally {
      setLoading(false);
    }
  };

  const handleReseedRules = async () => {
    try {
      const resp = await api.post('/admin/rules/reseed', null, { headers });
      setActionMsg(`✅ Rules reseeded successfully! Total active rules: ${resp.data.rules_count}`);
      fetchAdminData();
    } catch (err) {
      alert('Failed to reseed rules.');
    }
  };

  const handleCleanupExpired = async () => {
    try {
      const resp = await api.post('/documents/cleanup-expired', null, { headers });
      setActionMsg(`✅ Maintenance complete! Purged ${resp.data.purged_sessions_count} expired sessions and ephemeral files.`);
      fetchAdminData();
    } catch (err) {
      alert('Cleanup failed.');
    }
  };

  const handleRoleToggle = async (userId, currentRole) => {
    const newRole = currentRole === 'admin' ? 'citizen' : 'admin';
    try {
      await api.put(`/admin/users/${userId}/role?role=${newRole}`, null, { headers });
      setActionMsg(`✅ User ${userId.slice(0, 8)}... role updated to ${newRole}`);
      fetchAdminData();
    } catch (err) {
      alert('Failed to update role.');
    }
  };

  return (
    <div className="page-container">
      <div className="page-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '1rem' }}>
        <div>
          <h1>🛠️ FormFix Admin &amp; Oversight Console</h1>
          <p>System metrics, user management, deterministic rules versioning, and DPDP compliance logs.</p>
        </div>
        <div style={{ display: 'flex', gap: '0.5rem' }}>
          <button onClick={handleReseedRules} className="btn btn-outline" style={{ fontSize: '0.85rem' }}>
            🔄 Reseed Rules Engine
          </button>
          <button onClick={handleCleanupExpired} className="btn btn-primary" style={{ fontSize: '0.85rem' }}>
            🧹 Purge Expired Storage
          </button>
        </div>
      </div>

      {actionMsg && <div className="alert alert-success">{actionMsg}</div>}
      {error && <div className="alert alert-error">{error}</div>}

      {/* Admin Key authorization fallback */}
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
          🔑 Admin Key / Bootstrap Key:
        </span>
        <input
          type="password"
          className="form-input"
          placeholder="Enter System Secret Key..."
          value={adminKey}
          onChange={(e) => setAdminKey(e.target.value)}
          style={{ maxWidth: '320px', padding: '0.4rem 0.8rem', fontSize: '0.9rem' }}
        />
        <button
          onClick={fetchAdminData}
          className="btn btn-accent"
          style={{ padding: '0.4rem 1rem', fontSize: '0.85rem' }}
        >
          Authenticate Key
        </button>
      </div>

      {loading ? (
        <div style={{ textAlign: 'center', padding: '3rem' }}>
          <div className="spinner spinner-dark"></div>
          <p style={{ marginTop: '0.5rem', color: 'var(--text-light)' }}>Loading admin statistics...</p>
        </div>
      ) : stats ? (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '2rem' }}>
          {/* Metrics KPIs */}
          <div
            style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))',
              gap: '1rem',
            }}
          >
            <div className="card">
              <div style={{ color: 'var(--text-light)', fontSize: '0.8rem', fontWeight: 'bold' }}>TOTAL REGISTERED USERS</div>
              <div style={{ fontSize: '1.8rem', fontWeight: '800', color: 'var(--primary)' }}>{stats.total_users}</div>
            </div>
            <div className="card">
              <div style={{ color: 'var(--text-light)', fontSize: '0.8rem', fontWeight: 'bold' }}>ACTIVE SESSIONS</div>
              <div style={{ fontSize: '1.8rem', fontWeight: '800', color: 'var(--teal)' }}>{stats.active_sessions}</div>
            </div>
            <div className="card">
              <div style={{ color: 'var(--text-light)', fontSize: '0.8rem', fontWeight: 'bold' }}>TOTAL DOCUMENTS</div>
              <div style={{ fontSize: '1.8rem', fontWeight: '800', color: 'var(--accent)' }}>{stats.total_documents}</div>
            </div>
            <div className="card">
              <div style={{ color: 'var(--text-light)', fontSize: '0.8rem', fontWeight: 'bold' }}>DOCS PASSED FORMAT</div>
              <div style={{ fontSize: '1.8rem', fontWeight: '800', color: 'var(--success)' }}>{stats.documents_passed}</div>
            </div>
            <div className="card">
              <div style={{ color: 'var(--text-light)', fontSize: '0.8rem', fontWeight: 'bold' }}>ACTIVE RULES IN ENGINE</div>
              <div style={{ fontSize: '1.8rem', fontWeight: '800', color: 'var(--primary)' }}>{stats.total_rules}</div>
            </div>
          </div>

          {/* User Management */}
          <div className="card">
            <h3 style={{ marginTop: 0, color: 'var(--primary)' }}>👥 User Accounts & Access Control</h3>
            <div style={{ overflowX: 'auto', marginTop: '1rem' }}>
              <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left' }}>
                <thead>
                  <tr style={{ background: '#f7fafc', borderBottom: '2px solid var(--border)' }}>
                    <th style={{ padding: '0.6rem 0.8rem', fontSize: '0.85rem' }}>USER ID (HASHED)</th>
                    <th style={{ padding: '0.6rem 0.8rem', fontSize: '0.85rem' }}>ROLE</th>
                    <th style={{ padding: '0.6rem 0.8rem', fontSize: '0.85rem' }}>ACTIVE SESSIONS</th>
                    <th style={{ padding: '0.6rem 0.8rem', fontSize: '0.85rem' }}>DPDP CONSENT</th>
                    <th style={{ padding: '0.6rem 0.8rem', fontSize: '0.85rem', textAlign: 'right' }}>ACTION</th>
                  </tr>
                </thead>
                <tbody>
                  {users.map((u) => (
                    <tr key={u.id} style={{ borderBottom: '1px solid var(--border)' }}>
                      <td style={{ padding: '0.6rem 0.8rem', fontFamily: 'monospace' }}>{u.id}</td>
                      <td style={{ padding: '0.6rem 0.8rem' }}>
                        <span
                          style={{
                            padding: '0.2rem 0.6rem',
                            borderRadius: '12px',
                            fontSize: '0.75rem',
                            fontWeight: 'bold',
                            background: u.role === 'admin' ? '#fed7aa' : '#e2e8f0',
                            color: u.role === 'admin' ? '#9a3412' : '#2d3748',
                          }}
                        >
                          {u.role.toUpperCase()}
                        </span>
                      </td>
                      <td style={{ padding: '0.6rem 0.8rem' }}>{u.active_sessions}</td>
                      <td style={{ padding: '0.6rem 0.8rem' }}>{u.has_consent ? '✅ Consented' : '❌ Pending'}</td>
                      <td style={{ padding: '0.6rem 0.8rem', textAlign: 'right' }}>
                        <button
                          className="btn btn-outline"
                          style={{ padding: '0.2rem 0.6rem', fontSize: '0.75rem' }}
                          onClick={() => handleRoleToggle(u.id, u.role)}
                        >
                          {u.role === 'admin' ? 'Demote to Citizen' : 'Promote to Admin'}
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {/* Rules Engine Configuration */}
          <div className="card">
            <h3 style={{ marginTop: 0, color: 'var(--primary)' }}>⚖️ Deterministic Rules Engine (UP Scholarship v1.0)</h3>
            <div style={{ overflowX: 'auto', marginTop: '1rem' }}>
              <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left' }}>
                <thead>
                  <tr style={{ background: '#f7fafc', borderBottom: '2px solid var(--border)' }}>
                    <th style={{ padding: '0.6rem 0.8rem', fontSize: '0.85rem' }}>RULE ID</th>
                    <th style={{ padding: '0.6rem 0.8rem', fontSize: '0.85rem' }}>SCOPE</th>
                    <th style={{ padding: '0.6rem 0.8rem', fontSize: '0.85rem' }}>RULE TYPE</th>
                    <th style={{ padding: '0.6rem 0.8rem', fontSize: '0.85rem' }}>SEVERITY</th>
                    <th style={{ padding: '0.6rem 0.8rem', fontSize: '0.85rem' }}>MESSAGE KEY</th>
                  </tr>
                </thead>
                <tbody>
                  {rules.map((r) => (
                    <tr key={r.id} style={{ borderBottom: '1px solid var(--border)' }}>
                      <td style={{ padding: '0.6rem 0.8rem', fontWeight: 'bold' }}>{r.rule_id}</td>
                      <td style={{ padding: '0.6rem 0.8rem' }}>{r.scope}</td>
                      <td style={{ padding: '0.6rem 0.8rem' }}>{r.rule_type}</td>
                      <td style={{ padding: '0.6rem 0.8rem' }}>
                        <span style={{ color: r.severity === 'error' ? 'var(--error)' : 'var(--accent)', fontWeight: 'bold', fontSize: '0.85rem' }}>
                          {r.severity.toUpperCase()}
                        </span>
                      </td>
                      <td style={{ padding: '0.6rem 0.8rem', fontSize: '0.85rem', color: 'var(--text-light)' }}>{r.message_key}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {/* Document Ingestion Logs */}
          <div className="card">
            <h3 style={{ marginTop: 0, color: 'var(--primary)' }}>📑 Ephemeral Document Ingestion Registry</h3>
            <div style={{ overflowX: 'auto', marginTop: '1rem' }}>
              <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left' }}>
                <thead>
                  <tr style={{ background: '#f7fafc', borderBottom: '2px solid var(--border)' }}>
                    <th style={{ padding: '0.6rem 0.8rem', fontSize: '0.85rem' }}>CATEGORY</th>
                    <th style={{ padding: '0.6rem 0.8rem', fontSize: '0.85rem' }}>FILE</th>
                    <th style={{ padding: '0.6rem 0.8rem', fontSize: '0.85rem' }}>SIZE</th>
                    <th style={{ padding: '0.6rem 0.8rem', fontSize: '0.85rem' }}>MIME</th>
                    <th style={{ padding: '0.6rem 0.8rem', fontSize: '0.85rem' }}>STATUS</th>
                    <th style={{ padding: '0.6rem 0.8rem', fontSize: '0.85rem' }}>CONFIDENCE</th>
                  </tr>
                </thead>
                <tbody>
                  {documents.map((d) => (
                    <tr key={d.id} style={{ borderBottom: '1px solid var(--border)' }}>
                      <td style={{ padding: '0.6rem 0.8rem', fontWeight: '600' }}>{d.document_type}</td>
                      <td style={{ padding: '0.6rem 0.8rem' }}>{d.original_filename}</td>
                      <td style={{ padding: '0.6rem 0.8rem' }}>{d.file_size_kb.toFixed(1)} KB</td>
                      <td style={{ padding: '0.6rem 0.8rem', fontSize: '0.85rem' }}>{d.mime_type}</td>
                      <td style={{ padding: '0.6rem 0.8rem' }}>
                        <span style={{ color: d.format_status === 'PASSED' ? 'var(--success)' : 'var(--error)', fontWeight: 'bold' }}>
                          {d.format_status}
                        </span>
                      </td>
                      <td style={{ padding: '0.6rem 0.8rem' }}>{(d.overall_confidence * 100).toFixed(0)}%</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      ) : null}
    </div>
  );
}
