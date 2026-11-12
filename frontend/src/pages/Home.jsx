import React from 'react';
import { Link } from 'react-router-dom';
import Logo from '../components/Logo';

function Home() {
  return (
    <div style={{ maxWidth: '1200px', margin: '0 auto', padding: '2rem 1.5rem', fontFamily: "'Inter', sans-serif" }}>
      {/* Hero Section */}
      <div style={{
        textAlign: 'center',
        padding: '3.5rem 1rem 3rem 1rem',
        background: 'radial-gradient(circle at center, #eff6ff 0%, #f8fafc 100%)',
        borderRadius: '20px',
        border: '1px solid #e2e8f0',
        marginBottom: '3rem'
      }}>
        <div style={{ display: 'inline-flex', marginBottom: '1.25rem' }}>
          <Logo size="xl" withTagline={false} />
        </div>

        <h1 style={{
          fontSize: '2.5rem',
          fontWeight: 800,
          color: '#0f172a',
          margin: '0 0 0.75rem 0',
          letterSpacing: '-0.03em',
          lineHeight: 1.2
        }}>
          Stop Government Form Rejections <br />
          <span style={{ color: '#2563eb' }}>Before You Hit Submit</span>
        </h1>

        <p style={{
          fontSize: '1.2rem',
          color: '#475569',
          fontWeight: 500,
          margin: '0 0 0.5rem 0'
        }}>
          सटीक दस्तावेज़ सत्यापन और पूर्व-जमा ऑडिट इंजन
        </p>

        <p style={{
          maxWidth: '650px',
          margin: '0 auto 2rem auto',
          color: '#64748b',
          fontSize: '1rem',
          lineHeight: 1.6
        }}>
          FormFix catches cross-document discrepancies, expired certificates, name mismatches, and portal constraint errors before they lead to painful scholarship rejection.
        </p>

        <div style={{ display: 'flex', justifyContent: 'center', gap: '1rem', flexWrap: 'wrap' }}>
          <Link
            to="/dashboard"
            style={{
              background: '#2563eb',
              color: '#ffffff',
              padding: '0.85rem 1.75rem',
              borderRadius: '10px',
              fontWeight: 700,
              fontSize: '1rem',
              textDecoration: 'none',
              boxShadow: '0 4px 12px rgba(37, 99, 235, 0.25)',
              display: 'inline-flex',
              alignItems: 'center',
              gap: '8px'
            }}
          >
            ⚡ 1-Click Demo Scenarios →
          </Link>

          <Link
            to="/upload"
            style={{
              background: '#ffffff',
              color: '#1e293b',
              border: '1px solid #cbd5e1',
              padding: '0.85rem 1.5rem',
              borderRadius: '10px',
              fontWeight: 600,
              fontSize: '1rem',
              textDecoration: 'none'
            }}
          >
            📤 Upload Documents
          </Link>

          <Link
            to="/login"
            style={{
              background: '#f1f5f9',
              color: '#334155',
              padding: '0.85rem 1.5rem',
              borderRadius: '10px',
              fontWeight: 600,
              fontSize: '1rem',
              textDecoration: 'none'
            }}
          >
            🔐 Sign In / Register
          </Link>
        </div>
      </div>

      {/* Feature Cards Grid */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))',
        gap: '1.5rem',
        marginBottom: '3rem'
      }}>
        <div style={{
          background: '#ffffff',
          borderRadius: '14px',
          border: '1px solid #e2e8f0',
          padding: '1.75rem',
          boxShadow: '0 2px 4px rgba(0,0,0,0.03)'
        }}>
          <div style={{ fontSize: '2rem', marginBottom: '0.75rem' }}>🎯</div>
          <h3 style={{ fontSize: '1.15rem', fontWeight: 700, color: '#0f172a', margin: '0 0 0.5rem 0' }}>
            Deterministic Rule Engine
          </h3>
          <p style={{ color: '#64748b', fontSize: '0.9rem', lineHeight: 1.5, margin: 0 }}>
            No hallucinations. Every check runs against codified government requirements: income ceilings, validity time windows, and mandatory certificate rules.
          </p>
        </div>

        <div style={{
          background: '#ffffff',
          borderRadius: '14px',
          border: '1px solid #e2e8f0',
          padding: '1.75rem',
          boxShadow: '0 2px 4px rgba(0,0,0,0.03)'
        }}>
          <div style={{ fontSize: '2rem', marginBottom: '0.75rem' }}>🔄</div>
          <h3 style={{ fontSize: '1.15rem', fontWeight: 700, color: '#0f172a', margin: '0 0 0.5rem 0' }}>
            Cross-Document Matching
          </h3>
          <p style={{ color: '#64748b', fontSize: '0.9rem', lineHeight: 1.5, margin: 0 }}>
            RapidFuzz token-sort matching checks Aadhaar, Marksheets, and Passbooks for subtle name spelling variations and date of birth discrepancies.
          </p>
        </div>

        <div style={{
          background: '#ffffff',
          borderRadius: '14px',
          border: '1px solid #e2e8f0',
          padding: '1.75rem',
          boxShadow: '0 2px 4px rgba(0,0,0,0.03)'
        }}>
          <div style={{ fontSize: '2rem', marginBottom: '0.75rem' }}>🇮🇳</div>
          <h3 style={{ fontSize: '1.15rem', fontWeight: 700, color: '#0f172a', margin: '0 0 0.5rem 0' }}>
            Bilingual Action Checklists
          </h3>
          <p style={{ color: '#64748b', fontSize: '0.9rem', lineHeight: 1.5, margin: 0 }}>
            Every detected problem is explained in clear Hindi and English with step-by-step resolution advice, plus downloadable masked PDF reports.
          </p>
        </div>

        <div style={{
          background: '#ffffff',
          borderRadius: '14px',
          border: '1px solid #e2e8f0',
          padding: '1.75rem',
          boxShadow: '0 2px 4px rgba(0,0,0,0.03)'
        }}>
          <div style={{ fontSize: '2rem', marginBottom: '0.75rem' }}>🔒</div>
          <h3 style={{ fontSize: '1.15rem', fontWeight: 700, color: '#0f172a', margin: '0 0 0.5rem 0' }}>
            DPDP Act 2023 Compliant
          </h3>
          <p style={{ color: '#64748b', fontSize: '0.9rem', lineHeight: 1.5, margin: 0 }}>
            AES-128 Fernet encryption at rest, automatic 30-minute ephemeral purge worker, sensitive identifier masking, and 1-click Right to Erasure.
          </p>
        </div>
      </div>

      {/* 4-Step How It Works Banner */}
      <div style={{
        background: '#ffffff',
        borderRadius: '16px',
        border: '1px solid #e2e8f0',
        padding: '2.5rem 2rem',
        textAlign: 'center',
        marginBottom: '3rem'
      }}>
        <h2 style={{ fontSize: '1.45rem', fontWeight: 800, color: '#0f172a', margin: '0 0 2rem 0' }}>
          How FormFix Works
        </h2>

        <div style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))',
          gap: '2rem'
        }}>
          <div>
            <div style={{ fontSize: '2rem', marginBottom: '0.5rem' }}>1️⃣</div>
            <div style={{ fontWeight: 700, color: '#0f172a', marginBottom: '0.35rem' }}>Upload or Demo</div>
            <p style={{ color: '#64748b', fontSize: '0.85rem', margin: 0 }}>
              Upload your documents or load a pre-set test scenario in 1 click.
            </p>
          </div>

          <div>
            <div style={{ fontSize: '2rem', marginBottom: '0.5rem' }}>2️⃣</div>
            <div style={{ fontWeight: 700, color: '#0f172a', marginBottom: '0.35rem' }}>OCR &amp; Extraction</div>
            <p style={{ color: '#64748b', fontSize: '0.85rem', margin: 0 }}>
              Encrypted OCR extracts fields with color-coded confidence indicators.
            </p>
          </div>

          <div>
            <div style={{ fontSize: '2rem', marginBottom: '0.5rem' }}>3️⃣</div>
            <div style={{ fontWeight: 700, color: '#0f172a', marginBottom: '0.35rem' }}>Verification Grid</div>
            <p style={{ color: '#64748b', fontSize: '0.85rem', margin: 0 }}>
              Inspect and correct any OCR errors with 100% human-in-the-loop authority.
            </p>
          </div>

          <div>
            <div style={{ fontSize: '2rem', marginBottom: '0.5rem' }}>4️⃣</div>
            <div style={{ fontWeight: 700, color: '#0f172a', marginBottom: '0.35rem' }}>Download PDF Report</div>
            <p style={{ color: '#64748b', fontSize: '0.85rem', margin: 0 }}>
              Download official pre-submission checklist with bilingual recommendations.
            </p>
          </div>
        </div>
      </div>

      {/* Footer */}
      <footer style={{
        textAlign: 'center',
        padding: '2rem 1rem',
        borderTop: '1px solid #e2e8f0',
        color: '#64748b',
        fontSize: '0.875rem'
      }}>
        <div style={{ marginBottom: '0.5rem', fontWeight: 600, color: '#334155' }}>
          FormFix — Smart Government Form Assistant &amp; Verification Engine
        </div>
        <div>
          Advisory pre-submission tool • DPDP Act 2023 Compliant • Ephemeral 30-Minute Storage
        </div>
      </footer>
    </div>
  );
}

export default Home;
