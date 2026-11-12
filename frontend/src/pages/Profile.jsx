import React, { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import api from "../services/api";
import { getUserName, getUserRole, getUserIdentifier, logout, isLoggedIn } from "../services/auth";

export default function Profile() {
  const navigate = useNavigate();
  const [profile, setProfile] = useState(null);
  const [loading, setLoading] = useState(true);
  const [msg, setMsg] = useState("");
  const [msgType, setMsgType] = useState("info");
  const [deleting, setDeleting] = useState(false);

  useEffect(() => {
    if (!isLoggedIn()) {
      navigate("/login");
      return;
    }

    api.get("/auth/me")
      .then((res) => setProfile(res.data))
      .catch((err) => {
        setMsg("Could not fetch profile details: " + err.message);
        setMsgType("error");
      })
      .finally(() => setLoading(false));
  }, [navigate]);

  const handleDeleteAllData = async () => {
    const confirmed = window.confirm(
      "⚠️ DPDP Act 2023 Right to Erasure:\n\nAre you sure you want to permanently erase all your uploaded documents, OCR records, and user session from the server?\n\nThis action cannot be undone."
    );
    if (!confirmed) return;

    setDeleting(true);
    try {
      await api.delete("/me/data");
      alert("✅ All personal identifiers, files, and sessions have been permanently purged.");
      await logout();
      navigate("/login");
    } catch (err) {
      alert("Failed to delete data: " + (err.response?.data?.message || err.message));
    } finally {
      setDeleting(false);
    }
  };

  return (
    <div style={{ maxWidth: "800px", margin: "2rem auto", padding: "0 1.5rem" }}>
      <h1 style={{ fontSize: "1.75rem", fontWeight: 800, color: "#0f172a", marginBottom: "0.5rem" }}>
        User Profile &amp; Data Privacy
      </h1>
      <p style={{ color: "#64748b", fontSize: "0.95rem", marginBottom: "2rem" }}>
        Manage your FormFix account, cryptographic security settings, and DPDP Act 2023 rights.
      </p>

      {msg && (
        <div style={{
          padding: "0.75rem 1rem",
          borderRadius: "8px",
          marginBottom: "1.5rem",
          background: msgType === "error" ? "#fef2f2" : "#f0fdf4",
          color: msgType === "error" ? "#991b1b" : "#166534",
          border: `1px solid ${msgType === "error" ? "#fecaca" : "#bbf7d0"}`
        }}>
          {msg}
        </div>
      )}

      {/* Account Info Card */}
      <div style={{ background: "#ffffff", border: "1px solid #e2e8f0", borderRadius: "14px", padding: "1.75rem", marginBottom: "2rem" }}>
        <h3 style={{ margin: "0 0 1.25rem 0", fontSize: "1.15rem", fontWeight: 700, color: "#0f172a" }}>
          Account Details
        </h3>
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "1.25rem" }}>
          <div>
            <div style={{ fontSize: "0.8rem", color: "#64748b", fontWeight: 600 }}>Full Name</div>
            <div style={{ fontSize: "1rem", fontWeight: 700, color: "#1e293b", marginTop: "2px" }}>
              {profile?.full_name || getUserName()}
            </div>
          </div>
          <div>
            <div style={{ fontSize: "0.8rem", color: "#64748b", fontWeight: 600 }}>Account Role</div>
            <div style={{ fontSize: "1rem", fontWeight: 700, color: "#2563eb", marginTop: "2px" }}>
              {(profile?.role || getUserRole()).toUpperCase()}
            </div>
          </div>
          <div>
            <div style={{ fontSize: "0.8rem", color: "#64748b", fontWeight: 600 }}>Email Address</div>
            <div style={{ fontSize: "0.95rem", color: "#1e293b", marginTop: "2px" }}>
              {profile?.email || getUserIdentifier() || "N/A"}
            </div>
          </div>
          <div>
            <div style={{ fontSize: "0.8rem", color: "#64748b", fontWeight: 600 }}>Mobile Number</div>
            <div style={{ fontSize: "0.95rem", color: "#1e293b", marginTop: "2px" }}>
              {profile?.phone || "N/A"}
            </div>
          </div>
        </div>
      </div>

      {/* Privacy & DPDP Compliance Card */}
      <div style={{ background: "#ffffff", border: "1px solid #e2e8f0", borderRadius: "14px", padding: "1.75rem", marginBottom: "2rem" }}>
        <div style={{ display: "flex", alignItems: "center", gap: "0.5rem", marginBottom: "0.75rem" }}>
          <span style={{ fontSize: "1.35rem" }}>🛡️</span>
          <h3 style={{ margin: 0, fontSize: "1.15rem", fontWeight: 700, color: "#0f172a" }}>
            DPDP Act 2023 Compliance Status
          </h3>
        </div>
        <p style={{ fontSize: "0.85rem", color: "#475569", lineHeight: 1.5, marginBottom: "1.25rem" }}>
          FormFix enforces rigorous data minimization principles. Ephemeral document files are encrypted at rest using AES-128 Fernet and automatically wiped from disk after 30 minutes of inactivity.
        </p>

        <div style={{ background: "#f8fafc", borderRadius: "10px", padding: "1rem", border: "1px solid #e2e8f0", marginBottom: "1.5rem" }}>
          <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "0.5rem", fontSize: "0.85rem" }}>
            <span style={{ color: "#64748b" }}>Encryption at Rest:</span>
            <span style={{ color: "#166534", fontWeight: 700 }}>AES-128 Fernet Active</span>
          </div>
          <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "0.5rem", fontSize: "0.85rem" }}>
            <span style={{ color: "#64748b" }}>Ephemeral Retention:</span>
            <span style={{ color: "#1e293b", fontWeight: 600 }}>30-Minute Auto-Purge Worker</span>
          </div>
          <div style={{ display: "flex", justifyContent: "space-between", fontSize: "0.85rem" }}>
            <span style={{ color: "#64748b" }}>Sensitive Masking:</span>
            <span style={{ color: "#166534", fontWeight: 700 }}>Aadhaar &amp; Bank Account Redaction</span>
          </div>
        </div>

        {/* Right to Erasure */}
        <div style={{ borderTop: "1px solid #f1f5f9", paddingTop: "1.25rem" }}>
          <h4 style={{ margin: "0 0 0.35rem 0", fontSize: "0.95rem", fontWeight: 700, color: "#be123c" }}>
            Right to Erasure (Data Wiping)
          </h4>
          <p style={{ fontSize: "0.85rem", color: "#64748b", margin: "0 0 1rem 0" }}>
            Under Section 12 of the DPDP Act 2023, you can immediately and irreversibly delete all uploaded documents, extracted metadata, and your account.
          </p>
          <button
            type="button"
            disabled={deleting}
            onClick={handleDeleteAllData}
            style={{
              background: "#ef4444",
              color: "#ffffff",
              border: "none",
              padding: "0.65rem 1.25rem",
              borderRadius: "8px",
              fontWeight: 700,
              fontSize: "0.85rem",
              cursor: deleting ? "not-allowed" : "pointer"
            }}
          >
            {deleting ? "Purging All Data..." : "🗑️ Permanently Delete All My Data"}
          </button>
        </div>
      </div>
    </div>
  );
}
