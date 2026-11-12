import React, { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import Logo from "../components/Logo";
import {
  loginWithPassword,
  registerUser,
  verifyRegistration,
  demoLogin,
  forgotPassword,
  resetPassword,
  requestOtp,
  verifyOtp
} from "../services/auth";

export default function Login() {
  const navigate = useNavigate();

  // Active top-level mode: 'login' | 'register' | 'demo'
  const [activeTab, setActiveTab] = useState("login");
  const [loginMethod, setLoginMethod] = useState("password"); // 'password' | 'otp'

  // Login form state
  const [loginIdentifier, setLoginIdentifier] = useState("");
  const [loginPassword, setLoginPassword] = useState("");

  // Registration form state
  const [regFullName, setRegFullName] = useState("");
  const [regEmail, setRegEmail] = useState("");
  const [regPhone, setRegPhone] = useState("");
  const [regPassword, setRegPassword] = useState("");
  const [regConfirmPassword, setRegConfirmPassword] = useState("");

  // OTP Verification state (used for registration confirmation or OTP login)
  const [otpStage, setOtpStage] = useState(false); // boolean
  const [otpIdentifier, setOtpIdentifier] = useState("");
  const [otpValue, setOtpValue] = useState("");
  const [otpPurpose, setOtpPurpose] = useState("login"); // 'registration' | 'login' | 'reset'

  // Forgot Password modal state
  const [showForgotModal, setShowForgotModal] = useState(false);
  const [forgotStep, setForgotStep] = useState(1); // 1: request, 2: reset
  const [forgotIdentifier, setForgotIdentifier] = useState("");
  const [forgotOtp, setForgotOtp] = useState("");
  const [forgotNewPass, setForgotNewPass] = useState("");
  const [forgotConfirmPass, setForgotConfirmPass] = useState("");

  // Status and feedback
  const [msg, setMsg] = useState("");
  const [msgType, setMsgType] = useState("info"); // 'info' | 'success' | 'error'
  const [demoCode, setDemoCode] = useState("");
  const [loading, setLoading] = useState(false);
  const [cooldown, setCooldown] = useState(0);

  // Cooldown countdown
  useEffect(() => {
    let timer;
    if (cooldown > 0) {
      timer = setInterval(() => setCooldown((prev) => prev - 1), 1000);
    }
    return () => clearInterval(timer);
  }, [cooldown]);

  const clearMessages = () => {
    setMsg("");
    setDemoCode("");
  };

  // 1. Handle Password Login
  const handlePasswordLogin = async (e) => {
    e.preventDefault();
    if (!loginIdentifier.trim() || !loginPassword.trim()) {
      setMsg("Please enter both email/mobile and password.");
      setMsgType("error");
      return;
    }

    setLoading(true);
    clearMessages();
    try {
      await loginWithPassword(loginIdentifier, loginPassword);
      setMsg("🎉 Login successful! Redirecting to Dashboard...");
      setMsgType("success");
      setTimeout(() => navigate("/dashboard"), 700);
    } catch (err) {
      const errText = err.response?.data?.message || err.response?.data?.detail || "Invalid credentials. Please try again.";
      const hint = err.response?.data?.hint ? ` (${err.response.data.hint})` : "";
      setMsg(`❌ ${errText}${hint}`);
      setMsgType("error");
    } finally {
      setLoading(false);
    }
  };

  // 2. Handle OTP Login Request
  const handleOtpLoginRequest = async (e) => {
    e.preventDefault();
    if (!loginIdentifier.trim()) {
      setMsg("Please enter your registered mobile number or email.");
      setMsgType("error");
      return;
    }

    setLoading(true);
    clearMessages();
    try {
      const data = await requestOtp(loginIdentifier);
      setOtpIdentifier(loginIdentifier);
      setOtpPurpose("login");
      setOtpStage(true);
      if (data.demo_otp) setDemoCode(data.demo_otp);
      setCooldown(data.cooldown_seconds || 60);
      setMsg(`✅ OTP sent to ${data.masked_target || loginIdentifier}`);
      setMsgType("success");
    } catch (err) {
      const errText = err.response?.data?.message || err.response?.data?.detail || "Failed to send OTP.";
      setMsg(`❌ ${errText}`);
      setMsgType("error");
    } finally {
      setLoading(false);
    }
  };

  // 3. Handle Registration Submit
  const handleRegister = async (e) => {
    e.preventDefault();
    if (!regFullName.trim() || !regEmail.trim() || !regPhone.trim() || !regPassword.trim()) {
      setMsg("All fields are required for registration.");
      setMsgType("error");
      return;
    }

    if (regPassword !== regConfirmPassword) {
      setMsg("Passwords do not match. Please re-enter.");
      setMsgType("error");
      return;
    }

    if (regPassword.length < 8) {
      setMsg("Password must be at least 8 characters long.");
      setMsgType("error");
      return;
    }

    setLoading(true);
    clearMessages();
    try {
      const data = await registerUser({
        full_name: regFullName.trim(),
        email: regEmail.trim(),
        phone: regPhone.trim(),
        password: regPassword,
        confirm_password: regConfirmPassword
      });

      setOtpIdentifier(regEmail.trim());
      setOtpPurpose("registration");
      setOtpStage(true);
      if (data.demo_otp) setDemoCode(data.demo_otp);
      setCooldown(data.cooldown_seconds || 60);
      setMsg(`✅ Registration initiated! OTP sent to ${regEmail}.`);
      setMsgType("success");
    } catch (err) {
      const errText = err.response?.data?.message || err.response?.data?.detail || "Registration failed.";
      const hint = err.response?.data?.hint ? ` (${err.response.data.hint})` : "";
      setMsg(`❌ ${errText}${hint}`);
      setMsgType("error");
    } finally {
      setLoading(false);
    }
  };

  // 4. Verify OTP (Registration or Login)
  const handleVerifyOtp = async (e) => {
    e.preventDefault();
    if (!otpValue.trim() || otpValue.trim().length !== 6) {
      setMsg("Please enter a valid 6-digit verification code.");
      setMsgType("error");
      return;
    }

    setLoading(true);
    clearMessages();
    try {
      if (otpPurpose === "registration") {
        await verifyRegistration(otpIdentifier, otpValue);
        setMsg("🎉 Account verified & created successfully! Redirecting...");
      } else {
        await verifyOtp(otpIdentifier, otpValue);
        setMsg("🎉 OTP verified successfully! Redirecting...");
      }
      setMsgType("success");
      setTimeout(() => navigate("/dashboard"), 700);
    } catch (err) {
      const errText = err.response?.data?.message || err.response?.data?.detail || "Invalid OTP code.";
      setMsg(`❌ ${errText}`);
      setMsgType("error");
    } finally {
      setLoading(false);
    }
  };

  // 5. 1-Click Demo Login
  const handleDemoAccess = async (role) => {
    setLoading(true);
    clearMessages();
    try {
      const data = await demoLogin(role);
      setMsg(`⚡ Instant Demo Access granted (${role.toUpperCase()})! Opening Dashboard...`);
      setMsgType("success");
      setTimeout(() => navigate("/dashboard"), 500);
    } catch (err) {
      setMsg("Failed to start demo session. Please try again.");
      setMsgType("error");
    } finally {
      setLoading(false);
    }
  };

  // 6. Forgot Password Handlers
  const handleForgotRequest = async (e) => {
    e.preventDefault();
    if (!forgotIdentifier.trim()) {
      setMsg("Please enter your registered email or phone.");
      setMsgType("error");
      return;
    }
    setLoading(true);
    clearMessages();
    try {
      const data = await forgotPassword(forgotIdentifier);
      setForgotStep(2);
      if (data.demo_otp) setDemoCode(data.demo_otp);
      setMsg(`✅ Password reset OTP sent to ${forgotIdentifier}`);
      setMsgType("success");
    } catch (err) {
      setMsg(err.response?.data?.message || "Failed to send reset code.");
      setMsgType("error");
    } finally {
      setLoading(false);
    }
  };

  const handleForgotReset = async (e) => {
    e.preventDefault();
    if (!forgotOtp.trim() || !forgotNewPass.trim()) {
      setMsg("Please fill in all reset fields.");
      setMsgType("error");
      return;
    }
    if (forgotNewPass !== forgotConfirmPass) {
      setMsg("New passwords do not match.");
      setMsgType("error");
      return;
    }
    setLoading(true);
    clearMessages();
    try {
      await resetPassword(forgotIdentifier, forgotOtp, forgotNewPass, forgotConfirmPass);
      setMsg("🎉 Password updated successfully! Please log in with your new password.");
      setMsgType("success");
      setShowForgotModal(false);
      setForgotStep(1);
      setActiveTab("login");
      setLoginMethod("password");
    } catch (err) {
      setMsg(err.response?.data?.message || "Failed to reset password.");
      setMsgType("error");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{
      minHeight: "calc(100vh - 70px)",
      display: "flex",
      alignItems: "center",
      justifyContent: "center",
      padding: "2rem 1rem",
      background: "radial-gradient(circle at top right, #eff6ff 0%, #f8fafc 100%)"
    }}>
      <div style={{
        width: "100%",
        maxWidth: "520px",
        background: "#ffffff",
        borderRadius: "16px",
        boxShadow: "0 10px 25px -5px rgba(0, 0, 0, 0.08), 0 8px 10px -6px rgba(0, 0, 0, 0.04)",
        border: "1px solid #e2e8f0",
        padding: "2.5rem 2rem",
        position: "relative"
      }}>
        {/* Brand Header */}
        <div style={{ textAlign: "center", marginBottom: "1.75rem" }}>
          <Logo size="lg" withTagline={true} />
          <p style={{ color: "#64748b", fontSize: "0.95rem", marginTop: "0.5rem" }}>
            Secure AI-Powered Government Form Verification
          </p>
        </div>

        {/* Global Feedback Banner */}
        {msg && (
          <div style={{
            padding: "0.75rem 1rem",
            borderRadius: "8px",
            fontSize: "0.9rem",
            marginBottom: "1.25rem",
            background: msgType === "success" ? "#f0fdf4" : msgType === "error" ? "#fef2f2" : "#f0f9ff",
            color: msgType === "success" ? "#166534" : msgType === "error" ? "#991b1b" : "#075985",
            border: `1px solid ${msgType === "success" ? "#bbf7d0" : msgType === "error" ? "#fecaca" : "#bae6fd"}`
          }}>
            {msg}
          </div>
        )}

        {/* Test OTP Helper Box */}
        {demoCode && (
          <div style={{
            background: "#ecfdf5",
            border: "1px dashed #10b981",
            borderRadius: "8px",
            padding: "0.6rem 0.9rem",
            marginBottom: "1.25rem",
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            fontSize: "0.85rem",
            color: "#065f46"
          }}>
            <div>
              <span>⚡ <strong>Demo OTP:</strong> </span>
              <span style={{ fontFamily: "monospace", fontWeight: 700, fontSize: "1.05rem", letterSpacing: "1.5px" }}>
                {demoCode}
              </span>
            </div>
            <button
              type="button"
              onClick={() => {
                if (showForgotModal) setForgotOtp(demoCode);
                else setOtpValue(demoCode);
              }}
              style={{
                background: "#059669",
                color: "#ffffff",
                border: "none",
                borderRadius: "4px",
                padding: "3px 8px",
                fontSize: "0.75rem",
                cursor: "pointer",
                fontWeight: 600
              }}
            >
              Auto-fill
            </button>
          </div>
        )}

        {/* ---------------- OTP Verification Stage ---------------- */}
        {otpStage ? (
          <div>
            <div style={{ textAlign: "center", marginBottom: "1.5rem" }}>
              <div style={{ fontSize: "2rem", marginBottom: "0.25rem" }}>📲</div>
              <h3 style={{ fontSize: "1.25rem", fontWeight: 700, color: "#0f172a", margin: 0 }}>
                Enter Verification Code
              </h3>
              <p style={{ color: "#64748b", fontSize: "0.875rem", marginTop: "0.35rem" }}>
                We sent a 6-digit OTP code to <strong>{otpIdentifier}</strong>
              </p>
            </div>

            <form onSubmit={handleVerifyOtp}>
              <div style={{ marginBottom: "1.25rem" }}>
                <input
                  type="text"
                  maxLength={6}
                  value={otpValue}
                  onChange={(e) => setOtpValue(e.target.value.replace(/\D/g, ""))}
                  placeholder="• • • • • •"
                  style={{
                    width: "100%",
                    fontSize: "1.8rem",
                    letterSpacing: "0.5rem",
                    textAlign: "center",
                    fontWeight: 700,
                    padding: "0.75rem",
                    borderRadius: "10px",
                    border: "2px solid #cbd5e1",
                    color: "#1e293b",
                    outline: "none",
                    boxSizing: "border-box"
                  }}
                  required
                />
              </div>

              <button
                type="submit"
                disabled={loading}
                style={{
                  width: "100%",
                  padding: "0.85rem",
                  background: "#2563eb",
                  color: "#ffffff",
                  fontWeight: 600,
                  fontSize: "1rem",
                  borderRadius: "10px",
                  border: "none",
                  cursor: loading ? "not-allowed" : "pointer"
                }}
              >
                {loading ? "Verifying..." : "Verify & Continue →"}
              </button>

              <div style={{ display: "flex", justifyContent: "space-between", marginTop: "1rem", fontSize: "0.85rem" }}>
                <button
                  type="button"
                  onClick={() => { setOtpStage(false); clearMessages(); }}
                  style={{ background: "none", border: "none", color: "#64748b", cursor: "pointer", textDecoration: "underline" }}
                >
                  ← Go Back
                </button>
                <button
                  type="button"
                  disabled={cooldown > 0 || loading}
                  onClick={async () => {
                    if (cooldown > 0) return;
                    setLoading(true);
                    try {
                      const data = await requestOtp(otpIdentifier);
                      if (data.demo_otp) setDemoCode(data.demo_otp);
                      setCooldown(60);
                      setMsg("New OTP sent!");
                      setMsgType("success");
                    } catch (e) {
                      setMsg("Failed to resend OTP.");
                      setMsgType("error");
                    } finally {
                      setLoading(false);
                    }
                  }}
                  style={{
                    background: "none",
                    border: "none",
                    color: cooldown > 0 ? "#94a3b8" : "#2563eb",
                    cursor: cooldown > 0 ? "default" : "pointer",
                    fontWeight: 500
                  }}
                >
                  {cooldown > 0 ? `Resend OTP in ${cooldown}s` : "🔄 Resend OTP"}
                </button>
              </div>
            </form>
          </div>
        ) : (
          /* ---------------- Main Tabbed Auth Flow ---------------- */
          <div>
            {/* Nav Tabs: Log In | Create Account | 1-Click Demo */}
            <div style={{
              display: "grid",
              gridTemplateColumns: "1fr 1fr 1fr",
              background: "#f1f5f9",
              padding: "4px",
              borderRadius: "10px",
              marginBottom: "1.5rem"
            }}>
              <button
                type="button"
                onClick={() => { setActiveTab("login"); clearMessages(); }}
                style={{
                  padding: "0.6rem 0.4rem",
                  fontSize: "0.875rem",
                  fontWeight: 600,
                  borderRadius: "8px",
                  border: "none",
                  cursor: "pointer",
                  background: activeTab === "login" ? "#ffffff" : "transparent",
                  color: activeTab === "login" ? "#1e293b" : "#64748b",
                  boxShadow: activeTab === "login" ? "0 1px 3px rgba(0,0,0,0.1)" : "none",
                  transition: "all 0.15s ease"
                }}
              >
                Log In
              </button>
              <button
                type="button"
                onClick={() => { setActiveTab("register"); clearMessages(); }}
                style={{
                  padding: "0.6rem 0.4rem",
                  fontSize: "0.875rem",
                  fontWeight: 600,
                  borderRadius: "8px",
                  border: "none",
                  cursor: "pointer",
                  background: activeTab === "register" ? "#ffffff" : "transparent",
                  color: activeTab === "register" ? "#1e293b" : "#64748b",
                  boxShadow: activeTab === "register" ? "0 1px 3px rgba(0,0,0,0.1)" : "none",
                  transition: "all 0.15s ease"
                }}
              >
                Register
              </button>
              <button
                type="button"
                onClick={() => { setActiveTab("demo"); clearMessages(); }}
                style={{
                  padding: "0.6rem 0.4rem",
                  fontSize: "0.875rem",
                  fontWeight: 700,
                  borderRadius: "8px",
                  border: "none",
                  cursor: "pointer",
                  background: activeTab === "demo" ? "#ffffff" : "transparent",
                  color: activeTab === "demo" ? "#2563eb" : "#64748b",
                  boxShadow: activeTab === "demo" ? "0 1px 3px rgba(0,0,0,0.1)" : "none",
                  transition: "all 0.15s ease"
                }}
              >
                ⚡ 1-Click Demo
              </button>
            </div>

            {/* TAB 1: LOG IN */}
            {activeTab === "login" && (
              <div>
                {/* Method selector: Password vs OTP */}
                <div style={{ display: "flex", justifyContent: "flex-end", marginBottom: "0.75rem" }}>
                  <button
                    type="button"
                    onClick={() => setLoginMethod(loginMethod === "password" ? "otp" : "password")}
                    style={{
                      background: "none",
                      border: "none",
                      color: "#2563eb",
                      fontSize: "0.8rem",
                      fontWeight: 600,
                      cursor: "pointer"
                    }}
                  >
                    {loginMethod === "password" ? "Switch to OTP Login →" : "Switch to Password Login →"}
                  </button>
                </div>

                {loginMethod === "password" ? (
                  <form onSubmit={handlePasswordLogin}>
                    <div style={{ marginBottom: "1rem" }}>
                      <label style={{ display: "block", fontSize: "0.85rem", fontWeight: 600, color: "#334155", marginBottom: "0.4rem" }}>
                        Email Address or Mobile Number
                      </label>
                      <input
                        type="text"
                        value={loginIdentifier}
                        onChange={(e) => setLoginIdentifier(e.target.value)}
                        placeholder="e.g. rahul@example.com or 9876543210"
                        style={{
                          width: "100%",
                          padding: "0.75rem 0.85rem",
                          borderRadius: "8px",
                          border: "1px solid #cbd5e1",
                          fontSize: "0.95rem",
                          boxSizing: "border-box"
                        }}
                        required
                      />
                    </div>

                    <div style={{ marginBottom: "1rem" }}>
                      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "0.4rem" }}>
                        <label style={{ fontSize: "0.85rem", fontWeight: 600, color: "#334155" }}>
                          Password
                        </label>
                        <button
                          type="button"
                          onClick={() => { setShowForgotModal(true); setForgotStep(1); clearMessages(); }}
                          style={{
                            background: "none",
                            border: "none",
                            color: "#64748b",
                            fontSize: "0.8rem",
                            cursor: "pointer",
                            textDecoration: "underline"
                          }}
                        >
                          Forgot password?
                        </button>
                      </div>
                      <input
                        type="password"
                        value={loginPassword}
                        onChange={(e) => setLoginPassword(e.target.value)}
                        placeholder="••••••••••••"
                        style={{
                          width: "100%",
                          padding: "0.75rem 0.85rem",
                          borderRadius: "8px",
                          border: "1px solid #cbd5e1",
                          fontSize: "0.95rem",
                          boxSizing: "border-box"
                        }}
                        required
                      />
                    </div>

                    <button
                      type="submit"
                      disabled={loading}
                      style={{
                        width: "100%",
                        padding: "0.85rem",
                        background: "#2563eb",
                        color: "#ffffff",
                        fontWeight: 600,
                        fontSize: "1rem",
                        borderRadius: "10px",
                        border: "none",
                        cursor: loading ? "not-allowed" : "pointer",
                        marginTop: "0.5rem"
                      }}
                    >
                      {loading ? "Authenticating..." : "Log In →"}
                    </button>
                  </form>
                ) : (
                  <form onSubmit={handleOtpLoginRequest}>
                    <div style={{ marginBottom: "1.25rem" }}>
                      <label style={{ display: "block", fontSize: "0.85rem", fontWeight: 600, color: "#334155", marginBottom: "0.4rem" }}>
                        Mobile Number or Email
                      </label>
                      <input
                        type="text"
                        value={loginIdentifier}
                        onChange={(e) => setLoginIdentifier(e.target.value)}
                        placeholder="Enter 10-digit mobile or email"
                        style={{
                          width: "100%",
                          padding: "0.75rem 0.85rem",
                          borderRadius: "8px",
                          border: "1px solid #cbd5e1",
                          fontSize: "0.95rem",
                          boxSizing: "border-box"
                        }}
                        required
                      />
                    </div>

                    <button
                      type="submit"
                      disabled={loading}
                      style={{
                        width: "100%",
                        padding: "0.85rem",
                        background: "#2563eb",
                        color: "#ffffff",
                        fontWeight: 600,
                        fontSize: "1rem",
                        borderRadius: "10px",
                        border: "none",
                        cursor: loading ? "not-allowed" : "pointer"
                      }}
                    >
                      {loading ? "Sending Code..." : "Send Login OTP Code →"}
                    </button>
                  </form>
                )}
              </div>
            )}

            {/* TAB 2: REGISTER */}
            {activeTab === "register" && (
              <form onSubmit={handleRegister}>
                <div style={{ marginBottom: "0.85rem" }}>
                  <label style={{ display: "block", fontSize: "0.85rem", fontWeight: 600, color: "#334155", marginBottom: "0.3rem" }}>
                    Full Legal Name (as per Aadhaar/Class 10)
                  </label>
                  <input
                    type="text"
                    value={regFullName}
                    onChange={(e) => setRegFullName(e.target.value)}
                    placeholder="e.g. Priya Sharma"
                    style={{ width: "100%", padding: "0.7rem", borderRadius: "8px", border: "1px solid #cbd5e1", fontSize: "0.9rem", boxSizing: "border-box" }}
                    required
                  />
                </div>

                <div style={{ display: "grid", gridTemplateColumns: "1.1fr 0.9fr", gap: "0.75rem", marginBottom: "0.85rem" }}>
                  <div>
                    <label style={{ display: "block", fontSize: "0.85rem", fontWeight: 600, color: "#334155", marginBottom: "0.3rem" }}>
                      Email Address
                    </label>
                    <input
                      type="email"
                      value={regEmail}
                      onChange={(e) => setRegEmail(e.target.value)}
                      placeholder="priya@example.com"
                      style={{ width: "100%", padding: "0.7rem", borderRadius: "8px", border: "1px solid #cbd5e1", fontSize: "0.9rem", boxSizing: "border-box" }}
                      required
                    />
                  </div>
                  <div>
                    <label style={{ display: "block", fontSize: "0.85rem", fontWeight: 600, color: "#334155", marginBottom: "0.3rem" }}>
                      Mobile Number
                    </label>
                    <input
                      type="tel"
                      value={regPhone}
                      onChange={(e) => setRegPhone(e.target.value.replace(/\D/g, ""))}
                      placeholder="9876543210"
                      maxLength={10}
                      style={{ width: "100%", padding: "0.7rem", borderRadius: "8px", border: "1px solid #cbd5e1", fontSize: "0.9rem", boxSizing: "border-box" }}
                      required
                    />
                  </div>
                </div>

                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "0.75rem", marginBottom: "1.25rem" }}>
                  <div>
                    <label style={{ display: "block", fontSize: "0.85rem", fontWeight: 600, color: "#334155", marginBottom: "0.3rem" }}>
                      Password (min 8 chars)
                    </label>
                    <input
                      type="password"
                      value={regPassword}
                      onChange={(e) => setRegPassword(e.target.value)}
                      placeholder="••••••••"
                      style={{ width: "100%", padding: "0.7rem", borderRadius: "8px", border: "1px solid #cbd5e1", fontSize: "0.9rem", boxSizing: "border-box" }}
                      required
                    />
                  </div>
                  <div>
                    <label style={{ display: "block", fontSize: "0.85rem", fontWeight: 600, color: "#334155", marginBottom: "0.3rem" }}>
                      Confirm Password
                    </label>
                    <input
                      type="password"
                      value={regConfirmPassword}
                      onChange={(e) => setRegConfirmPassword(e.target.value)}
                      placeholder="••••••••"
                      style={{ width: "100%", padding: "0.7rem", borderRadius: "8px", border: "1px solid #cbd5e1", fontSize: "0.9rem", boxSizing: "border-box" }}
                      required
                    />
                  </div>
                </div>

                <button
                  type="submit"
                  disabled={loading}
                  style={{
                    width: "100%",
                    padding: "0.85rem",
                    background: "#2563eb",
                    color: "#ffffff",
                    fontWeight: 600,
                    fontSize: "1rem",
                    borderRadius: "10px",
                    border: "none",
                    cursor: loading ? "not-allowed" : "pointer"
                  }}
                >
                  {loading ? "Preparing Registration..." : "Continue to OTP Verification →"}
                </button>
              </form>
            )}

            {/* TAB 3: 1-CLICK HACKATHON DEMO ACCESS */}
            {activeTab === "demo" && (
              <div>
                <div style={{
                  background: "#eff6ff",
                  borderRadius: "10px",
                  padding: "1rem",
                  marginBottom: "1.25rem",
                  border: "1px solid #bfdbfe",
                  fontSize: "0.85rem",
                  color: "#1e3a8a",
                  lineHeight: 1.5
                }}>
                  🎯 <strong>Designed for Hackathon Judges &amp; Evaluators:</strong>
                  <br />
                  Bypass manual sign-up instantly. One click logs you into a fully operational testing session with encrypted ephemeral storage and verified DPDP compliance.
                </div>

                <div style={{ display: "flex", flexDirection: "column", gap: "0.85rem" }}>
                  <button
                    type="button"
                    disabled={loading}
                    onClick={() => handleDemoAccess("student")}
                    style={{
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "space-between",
                      padding: "1rem 1.25rem",
                      borderRadius: "10px",
                      background: "#ffffff",
                      border: "2px solid #2563eb",
                      color: "#1e40af",
                      fontWeight: 700,
                      fontSize: "0.95rem",
                      cursor: "pointer",
                      textAlign: "left"
                    }}
                  >
                    <div>
                      <div>🎓 Enter as Demo Student</div>
                      <div style={{ fontSize: "0.75rem", fontWeight: 400, color: "#64748b", marginTop: "2px" }}>
                        Priya Sharma • UP Post-Matric Applicant
                      </div>
                    </div>
                    <span style={{ fontSize: "1.25rem" }}>→</span>
                  </button>

                  <button
                    type="button"
                    disabled={loading}
                    onClick={() => handleDemoAccess("admin")}
                    style={{
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "space-between",
                      padding: "1rem 1.25rem",
                      borderRadius: "10px",
                      background: "#f8fafc",
                      border: "2px solid #64748b",
                      color: "#334155",
                      fontWeight: 700,
                      fontSize: "0.95rem",
                      cursor: "pointer",
                      textAlign: "left"
                    }}
                  >
                    <div>
                      <div>🛡️ Enter as Demo Administrator</div>
                      <div style={{ fontSize: "0.75rem", fontWeight: 400, color: "#64748b", marginTop: "2px" }}>
                        System Oversight • Rules Management • Audit Logs
                      </div>
                    </div>
                    <span style={{ fontSize: "1.25rem" }}>→</span>
                  </button>
                </div>
              </div>
            )}
          </div>
        )}

        {/* ---------------- Forgot Password Modal ---------------- */}
        {showForgotModal && (
          <div style={{
            position: "fixed",
            inset: 0,
            background: "rgba(15, 23, 42, 0.6)",
            backdropFilter: "blur(4px)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            zIndex: 9999,
            padding: "1rem"
          }}>
            <div style={{
              width: "100%",
              maxWidth: "440px",
              background: "#ffffff",
              borderRadius: "14px",
              padding: "2rem",
              boxShadow: "0 20px 25px -5px rgba(0, 0, 0, 0.2)"
            }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "1rem" }}>
                <h3 style={{ margin: 0, fontSize: "1.2rem", fontWeight: 700, color: "#0f172a" }}>
                  {forgotStep === 1 ? "Reset Password" : "Enter Reset OTP"}
                </h3>
                <button
                  onClick={() => setShowForgotModal(false)}
                  style={{ background: "none", border: "none", fontSize: "1.25rem", cursor: "pointer", color: "#64748b" }}
                >
                  ✕
                </button>
              </div>

              {forgotStep === 1 ? (
                <form onSubmit={handleForgotRequest}>
                  <p style={{ fontSize: "0.85rem", color: "#64748b", marginBottom: "1rem" }}>
                    Enter your registered email address or mobile number to receive a secure password reset code.
                  </p>
                  <input
                    type="text"
                    value={forgotIdentifier}
                    onChange={(e) => setForgotIdentifier(e.target.value)}
                    placeholder="email@example.com or mobile"
                    style={{ width: "100%", padding: "0.75rem", borderRadius: "8px", border: "1px solid #cbd5e1", fontSize: "0.95rem", boxSizing: "border-box", marginBottom: "1rem" }}
                    required
                  />
                  <button
                    type="submit"
                    disabled={loading}
                    style={{ width: "100%", padding: "0.75rem", background: "#2563eb", color: "#ffffff", border: "none", borderRadius: "8px", fontWeight: 600, cursor: "pointer" }}
                  >
                    {loading ? "Sending..." : "Send Reset Code"}
                  </button>
                </form>
              ) : (
                <form onSubmit={handleForgotReset}>
                  <p style={{ fontSize: "0.85rem", color: "#64748b", marginBottom: "1rem" }}>
                    Enter the 6-digit reset code sent to <strong>{forgotIdentifier}</strong> and your new password.
                  </p>
                  <input
                    type="text"
                    maxLength={6}
                    value={forgotOtp}
                    onChange={(e) => setForgotOtp(e.target.value.replace(/\D/g, ""))}
                    placeholder="6-digit OTP code"
                    style={{ width: "100%", padding: "0.75rem", borderRadius: "8px", border: "1px solid #cbd5e1", fontSize: "0.95rem", boxSizing: "border-box", marginBottom: "0.75rem", textAlign: "center", letterSpacing: "2px", fontWeight: 700 }}
                    required
                  />
                  <input
                    type="password"
                    value={forgotNewPass}
                    onChange={(e) => setForgotNewPass(e.target.value)}
                    placeholder="New password (min 8 characters)"
                    style={{ width: "100%", padding: "0.75rem", borderRadius: "8px", border: "1px solid #cbd5e1", fontSize: "0.95rem", boxSizing: "border-box", marginBottom: "0.75rem" }}
                    required
                  />
                  <input
                    type="password"
                    value={forgotConfirmPass}
                    onChange={(e) => setForgotConfirmPass(e.target.value)}
                    placeholder="Confirm new password"
                    style={{ width: "100%", padding: "0.75rem", borderRadius: "8px", border: "1px solid #cbd5e1", fontSize: "0.95rem", boxSizing: "border-box", marginBottom: "1.25rem" }}
                    required
                  />
                  <button
                    type="submit"
                    disabled={loading}
                    style={{ width: "100%", padding: "0.75rem", background: "#2563eb", color: "#ffffff", border: "none", borderRadius: "8px", fontWeight: 600, cursor: "pointer" }}
                  >
                    {loading ? "Resetting..." : "Save New Password"}
                  </button>
                </form>
              )}
            </div>
          </div>
        )}

      </div>
    </div>
  );
}
