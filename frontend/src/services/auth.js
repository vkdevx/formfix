import axios from 'axios';

/**
 * FormFix Authentication & Session Management Service
 * Supports Full Registration, Password Login, OTP verification, 1-Click Demo Login,
 * Forgot Password, and DPDP-compliant session teardown.
 */

function storeAuthData(data) {
  const token = data.session_token || data.access_token;
  if (token) {
    localStorage.setItem('access_token', token);
    localStorage.setItem('session_token', token);
  }
  if (data.user_id) localStorage.setItem('user_id', data.user_id);
  if (data.role) localStorage.setItem('user_role', data.role);
  if (data.full_name) localStorage.setItem('user_name', data.full_name);
  if (data.email) localStorage.setItem('user_email', data.email);
  if (data.phone) localStorage.setItem('user_phone', data.phone);
  if (data.masked_identifier) localStorage.setItem('masked_identifier', data.masked_identifier);
  if (data.demo_otp) localStorage.setItem('demo_otp', data.demo_otp);
}

/**
 * Phase 3: Initiate user registration (Full Name, Email, Phone, Password).
 * Triggers OTP delivery.
 */
export async function registerUser(payload) {
  const resp = await axios.post('/api/auth/register', payload);
  return resp.data;
}

/**
 * Phase 3: Verify registration OTP and create account session.
 */
export async function verifyRegistration(identifier, otp) {
  const resp = await axios.post('/api/auth/verify-registration', {
    identifier: identifier.trim(),
    otp: otp.trim()
  });
  storeAuthData(resp.data);
  return resp.data;
}

/**
 * Phase 3: Standard login with email or phone + password.
 */
export async function loginWithPassword(identifier, password) {
  const resp = await axios.post('/api/auth/login', {
    identifier: identifier.trim(),
    password: password
  });
  storeAuthData(resp.data);
  return resp.data;
}

/**
 * Phase 3 & 7: 1-Click Demo Login for Hackathon Judges & Evaluators.
 * Instant access without typing credentials.
 */
export async function demoLogin(role = 'student') {
  const resp = await axios.post('/api/auth/demo-login', { role });
  storeAuthData(resp.data);
  return resp.data;
}

/**
 * Phase 3: Request password reset OTP.
 */
export async function forgotPassword(identifier) {
  const resp = await axios.post('/api/auth/forgot-password', {
    identifier: identifier.trim()
  });
  return resp.data;
}

/**
 * Phase 3: Reset password with OTP.
 */
export async function resetPassword(identifier, otp, newPassword, confirmPassword) {
  const resp = await axios.post('/api/auth/reset-password', {
    identifier: identifier.trim(),
    otp: otp.trim(),
    new_password: newPassword,
    confirm_password: confirmPassword
  });
  return resp.data;
}

/**
 * Legacy OTP Request.
 */
export async function requestOtp(identifier) {
  const isEmail = identifier.includes('@');
  const payload = isEmail ? { email: identifier.trim() } : { phone: identifier.trim() };
  const resp = await axios.post('/api/auth/otp/request', payload);
  return resp.data;
}

/**
 * Legacy OTP Verify.
 */
export async function verifyOtp(identifier, otp) {
  const isEmail = identifier.includes('@');
  const payload = isEmail
    ? { email: identifier.trim(), otp: otp.trim() }
    : { phone: identifier.trim(), otp: otp.trim() };

  const resp = await axios.post('/api/auth/otp/verify', payload);
  storeAuthData(resp.data);
  return resp.data;
}

/**
 * Retrieve current user profile.
 */
export async function getCurrentUser() {
  const token = getToken();
  if (!token) return null;
  const resp = await axios.get('/api/auth/me', {
    headers: { Authorization: `Bearer ${token}` }
  });
  return resp.data;
}

/** Stored token getter. */
export function getToken() {
  return localStorage.getItem('access_token') || localStorage.getItem('session_token');
}

/** User info getters. */
export function getUserRole() {
  return localStorage.getItem('user_role') || 'citizen';
}

export function getUserName() {
  return localStorage.getItem('user_name') || 'Scholarship Applicant';
}

export function getUserIdentifier() {
  return localStorage.getItem('masked_identifier') || localStorage.getItem('user_email') || '';
}

export function isLoggedIn() {
  return Boolean(getToken());
}

/**
 * Logout the user, revoke server-side session, and clear client storage.
 */
export async function logout() {
  const token = getToken();
  try {
    if (token) {
      await axios.post('/api/auth/logout', null, {
        headers: { Authorization: `Bearer ${token}` }
      });
    }
  } catch (err) {
    console.error('Logout error on server:', err);
  } finally {
    localStorage.removeItem('access_token');
    localStorage.removeItem('session_token');
    localStorage.removeItem('user_id');
    localStorage.removeItem('user_role');
    localStorage.removeItem('user_name');
    localStorage.removeItem('user_email');
    localStorage.removeItem('user_phone');
    localStorage.removeItem('masked_identifier');
    localStorage.removeItem('demo_otp');
  }
}
