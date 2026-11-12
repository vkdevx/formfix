import React, { useState, useEffect } from "react";
import { useNavigate, Link } from "react-router-dom";
import api from "../services/api";
import { getUserName, getUserRole, getUserIdentifier, isLoggedIn } from "../services/auth";

export default function Dashboard() {
  const navigate = useNavigate();
  const [userName, setUserName] = useState("Scholarship Applicant");
  const [userRole, setUserRole] = useState("citizen");
  const [userIdentifier, setUserIdentifier] = useState("");
  const [scenarios, setScenarios] = useState([]);
  const [selectedForm, setSelectedForm] = useState("up_post_matric");
  const [loadingScenario, setLoadingScenario] = useState("");
  const [demoBanner, setDemoBanner] = useState(null);

  useEffect(() => {
    if (!isLoggedIn()) {
      navigate("/login");
      return;
    }
    setUserName(getUserName());
    setUserRole(getUserRole());
    setUserIdentifier(getUserIdentifier());

    // Fetch demo scenarios
    api.get("/demo/scenarios")
      .then((res) => setScenarios(res.data))
      .catch((err) => console.log("Demo scenarios fetch note:", err.message));
  }, [navigate]);

  const handleLoadDemoScenario = async (scenarioId) => {
    setLoadingScenario(scenarioId);
    setDemoBanner(null);
    try {
      const res = await api.post("/demo/load", {
        scenario_id: scenarioId,
        form_type: selectedForm
      });
      setDemoBanner({
        type: "success",
        title: res.data.message,
        preview: res.data.audit_preview
      });
    } catch (err) {
      setDemoBanner({
        type: "error",
        title: err.response?.data?.detail || "Failed to load test scenario."
      });
    } finally {
      setLoadingScenario("");
    }
  };

  return (
    <div style={{ maxWidth: "1200px", margin: "0 auto", padding: "2rem 1.5rem" }}>
      {/* Top Welcome Banner */}
      <div style={{
        background: "linear-gradient(135deg, #1e3a8a 0%, #2563eb 100%)",
        color: "#ffffff",
        borderRadius: "16px",
        padding: "2rem",
        boxShadow: "0 10px 20px -5px rgba(37, 99, 235, 0.25)",
        marginBottom: "2rem",
        display: "flex",
        flexWrap: "wrap",
        justifyContent: "space-between",
        alignItems: "center",
        gap: "1.5rem"
      }}>
        <div>
          <div style={{ display: "inline-block", background: "rgba(255,255,255,0.2)", padding: "4px 12px", borderRadius: "20px", fontSize: "0.8rem", fontWeight: 600, letterSpacing: "0.5px", marginBottom: "0.75rem" }}>
            {userRole === "admin" ? "🛡️ SYSTEM ADMINISTRATOR" : "🎓 CITIZEN APPLICANT"}
          </div>
          <h1 style={{ margin: "0 0 0.5rem 0", fontSize: "1.85rem", fontWeight: 800 }}>
            Welcome back, {userName}!
          </h1>
          <p style={{ margin: 0, opacity: 0.9, fontSize: "0.95rem" }}>
            Account: <strong>{userIdentifier || "Active Session"}</strong> • Ephemeral Storage: <span style={{ color: "#86efac", fontWeight: 600 }}>AES-128 Encrypted</span>
          </p>
        </div>

        <div style={{ display: "flex", gap: "0.75rem", flexWrap: "wrap" }}>
          <Link
            to="/upload"
            style={{
              background: "#ffffff",
              color: "#1e3a8a",
              padding: "0.75rem 1.25rem",
              borderRadius: "10px",
              fontWeight: 700,
              textDecoration: "none",
              fontSize: "0.95rem",
              boxShadow: "0 2px 4px rgba(0,0,0,0.1)"
            }}
          >
            + Upload My Documents
          </Link>
          <Link
            to="/review"
            style={{
              background: "rgba(255,255,255,0.15)",
              color: "#ffffff",
              border: "1px solid rgba(255,255,255,0.4)",
              padding: "0.75rem 1.25rem",
              borderRadius: "10px",
              fontWeight: 600,
              textDecoration: "none",
              fontSize: "0.95rem"
            }}
          >
            Review Grid
          </Link>
        </div>
      </div>

      {/* Target Government Scheme Selector */}
      <div style={{
        background: "#ffffff",
        borderRadius: "12px",
        padding: "1.25rem 1.5rem",
        border: "1px solid #e2e8f0",
        marginBottom: "2rem",
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        flexWrap: "wrap",
        gap: "1rem"
      }}>
        <div style={{ display: "flex", alignItems: "center", gap: "0.75rem" }}>
          <span style={{ fontSize: "1.5rem" }}>🏛️</span>
          <div>
            <div style={{ fontWeight: 700, color: "#0f172a", fontSize: "1rem" }}>
              Active Government Scheme Ruleset
            </div>
            <div style={{ fontSize: "0.85rem", color: "#64748b" }}>
              Deterministic verification rules will adapt to the requirements of the selected scholarship portal.
            </div>
          </div>
        </div>

        <select
          value={selectedForm}
          onChange={(e) => setSelectedForm(e.target.value)}
          style={{
            padding: "0.6rem 1rem",
            borderRadius: "8px",
            border: "1px solid #cbd5e1",
            fontWeight: 600,
            color: "#1e293b",
            background: "#f8fafc",
            fontSize: "0.9rem",
            cursor: "pointer",
            outline: "none"
          }}
        >
          <option value="up_post_matric">Uttar Pradesh Post-Matric Scholarship (General/OBC/SC/ST)</option>
          <option value="up_pre_matric">Uttar Pradesh Pre-Matric Scholarship (Class 9-10)</option>
          <option value="up_dashmesh">UP Dashmesh Post-Matric (Other than Intermediate)</option>
        </select>
      </div>

      {/* Live Feedback Banner for Demo Load */}
      {demoBanner && (
        <div style={{
          background: demoBanner.type === "success" ? "#f0fdf4" : "#fef2f2",
          border: `1px solid ${demoBanner.type === "success" ? "#bbf7d0" : "#fecaca"}`,
          borderRadius: "12px",
          padding: "1.25rem 1.5rem",
          marginBottom: "2rem"
        }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <div>
              <h4 style={{ margin: "0 0 0.25rem 0", color: demoBanner.type === "success" ? "#166534" : "#991b1b", fontSize: "1.1rem" }}>
                {demoBanner.title}
              </h4>
              {demoBanner.preview && (
                <p style={{ margin: 0, fontSize: "0.9rem", color: "#374151" }}>
                  Status: <strong>{demoBanner.preview.overall_status}</strong> •
                  Readiness Score: <strong>{demoBanner.preview.overall_score}/100</strong> •
                  Issues Flagged: <strong>{demoBanner.preview.flagged_issues}</strong>
                </p>
              )}
            </div>
            <div style={{ display: "flex", gap: "0.5rem" }}>
              <button
                onClick={() => navigate("/review")}
                style={{
                  background: "#2563eb",
                  color: "#ffffff",
                  border: "none",
                  padding: "0.5rem 1rem",
                  borderRadius: "6px",
                  fontWeight: 600,
                  fontSize: "0.85rem",
                  cursor: "pointer"
                }}
              >
                Inspect Review Grid →
              </button>
              <button
                onClick={() => navigate("/explanations")}
                style={{
                  background: "#059669",
                  color: "#ffffff",
                  border: "none",
                  padding: "0.5rem 1rem",
                  borderRadius: "6px",
                  fontWeight: 600,
                  fontSize: "0.85rem",
                  cursor: "pointer"
                }}
              >
                View Audit Report →
              </button>
            </div>
          </div>
        </div>
      )}

      {/* 🎯 Hackathon Showcase Scenarios Grid */}
      <div style={{ marginBottom: "2.5rem" }}>
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "1rem" }}>
          <div>
            <h2 style={{ margin: 0, fontSize: "1.35rem", fontWeight: 800, color: "#0f172a" }}>
              🎯 Live Pitch &amp; Evaluation Test Scenarios
            </h2>
            <p style={{ margin: "0.25rem 0 0 0", fontSize: "0.875rem", color: "#64748b" }}>
              1-click test datasets populated with synthetic documents for live hackathon jury testing.
            </p>
          </div>
        </div>

        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(270px, 1fr))", gap: "1.25rem" }}>
          {scenarios.map((sc) => {
            const isClean = sc.expected_status === "PASS";
            return (
              <div
                key={sc.id}
                style={{
                  background: "#ffffff",
                  border: isClean ? "2px solid #10b981" : "1px solid #e2e8f0",
                  borderRadius: "14px",
                  padding: "1.5rem",
                  display: "flex",
                  flexDirection: "column",
                  justifyContent: "space-between",
                  boxShadow: isClean ? "0 4px 12px rgba(16, 185, 129, 0.12)" : "0 2px 5px rgba(0,0,0,0.04)"
                }}
              >
                <div>
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "0.75rem" }}>
                    <span style={{
                      fontSize: "0.75rem",
                      fontWeight: 700,
                      padding: "3px 8px",
                      borderRadius: "6px",
                      background: isClean ? "#dcfce7" : sc.expected_status === "NEEDS_REVIEW" ? "#fef3c7" : "#fee2e2",
                      color: isClean ? "#15803d" : sc.expected_status === "NEEDS_REVIEW" ? "#b45309" : "#b91c1c"
                    }}>
                      {sc.expected_status}
                    </span>
                    <span style={{ fontSize: "0.8rem", color: "#64748b", fontWeight: 500 }}>
                      Synthetic Data
                    </span>
                  </div>

                  <h3 style={{ margin: "0 0 0.35rem 0", fontSize: "1.05rem", fontWeight: 700, color: "#0f172a" }}>
                    {sc.title}
                  </h3>
                  <div style={{ fontSize: "0.8rem", fontWeight: 600, color: "#2563eb", marginBottom: "0.75rem" }}>
                    {sc.subtitle}
                  </div>
                  <p style={{ fontSize: "0.85rem", color: "#475569", lineHeight: 1.45, margin: "0 0 1rem 0" }}>
                    {sc.description_en}
                  </p>

                  {sc.planted_issues.length > 0 && (
                    <div style={{ background: "#fff1f2", borderRadius: "8px", padding: "0.6rem 0.75rem", marginBottom: "1rem", border: "1px solid #ffe4e6" }}>
                      <div style={{ fontSize: "0.75rem", fontWeight: 700, color: "#be123c", marginBottom: "2px" }}>
                        Planted Test Traps:
                      </div>
                      <ul style={{ margin: 0, paddingLeft: "1.2rem", fontSize: "0.75rem", color: "#9f1239" }}>
                        {sc.planted_issues.map((issue, idx) => (
                          <li key={idx}>{issue}</li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>

                <button
                  type="button"
                  disabled={loadingScenario === sc.id}
                  onClick={() => handleLoadDemoScenario(sc.id)}
                  style={{
                    width: "100%",
                    padding: "0.7rem",
                    borderRadius: "8px",
                    border: "none",
                    background: isClean ? "#10b981" : "#0f172a",
                    color: "#ffffff",
                    fontWeight: 700,
                    fontSize: "0.875rem",
                    cursor: loadingScenario === sc.id ? "not-allowed" : "pointer"
                  }}
                >
                  {loadingScenario === sc.id ? "Loading Dataset..." : `⚡ Load Scenario`}
                </button>
              </div>
            );
          })}
        </div>
      </div>

      {/* Quick Navigation Cards */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(300px, 1fr))", gap: "1.5rem" }}>
        <div style={{ background: "#ffffff", border: "1px solid #e2e8f0", borderRadius: "12px", padding: "1.5rem" }}>
          <div style={{ fontSize: "1.5rem", marginBottom: "0.5rem" }}>📄</div>
          <h3 style={{ margin: "0 0 0.5rem 0", fontSize: "1.1rem", fontWeight: 700, color: "#0f172a" }}>
            1. Document Upload
          </h3>
          <p style={{ fontSize: "0.85rem", color: "#64748b", margin: "0 0 1rem 0", lineHeight: 1.5 }}>
            Upload Aadhaar, Marksheet, Income &amp; Caste Certificates, and Bank Passbook. Instant portal constraint validation and OCR field extraction.
          </p>
          <Link to="/upload" style={{ color: "#2563eb", fontWeight: 600, fontSize: "0.9rem", textDecoration: "none" }}>
            Open Document Upload →
          </Link>
        </div>

        <div style={{ background: "#ffffff", border: "1px solid #e2e8f0", borderRadius: "12px", padding: "1.5rem" }}>
          <div style={{ fontSize: "1.5rem", marginBottom: "0.5rem" }}>📊</div>
          <h3 style={{ margin: "0 0 0.5rem 0", fontSize: "1.1rem", fontWeight: 700, color: "#0f172a" }}>
            2. Editable Verification Grid
          </h3>
          <p style={{ fontSize: "0.85rem", color: "#64748b", margin: "0 0 1rem 0", lineHeight: 1.5 }}>
            Inspect extracted fields with color-coded confidence indicators (Green &gt;80%, Amber 50-80%, Red &lt;50%). Correct any OCR misreadings directly.
          </p>
          <Link to="/review" style={{ color: "#2563eb", fontWeight: 600, fontSize: "0.9rem", textDecoration: "none" }}>
            Open Verification Grid →
          </Link>
        </div>

        <div style={{ background: "#ffffff", border: "1px solid #e2e8f0", borderRadius: "12px", padding: "1.5rem" }}>
          <div style={{ fontSize: "1.5rem", marginBottom: "0.5rem" }}>🔍</div>
          <h3 style={{ margin: "0 0 0.5rem 0", fontSize: "1.1rem", fontWeight: 700, color: "#0f172a" }}>
            3. Bilingual Explanations &amp; PDF
          </h3>
          <p style={{ fontSize: "0.85rem", color: "#64748b", margin: "0 0 1rem 0", lineHeight: 1.5 }}>
            Deterministic cross-verification rules report exact discrepancies in Hindi and English with step-by-step resolution checklists and downloadable PDF reports.
          </p>
          <Link to="/explanations" style={{ color: "#2563eb", fontWeight: 600, fontSize: "0.9rem", textDecoration: "none" }}>
            View Explanations &amp; PDF →
          </Link>
        </div>
      </div>
    </div>
  );
}
