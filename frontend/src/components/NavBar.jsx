import React, { useState, useEffect } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import Logo from './Logo';
import { isLoggedIn, logout, getUserName, getUserRole } from '../services/auth';

function NavBar() {
  const location = useLocation();
  const navigate = useNavigate();
  const [loggedIn, setLoggedIn] = useState(isLoggedIn());
  const [userName, setUserName] = useState(getUserName());
  const [role, setRole] = useState(getUserRole());

  useEffect(() => {
    setLoggedIn(isLoggedIn());
    setUserName(getUserName());
    setRole(getUserRole());
  }, [location.pathname]);

  const isActive = (path) => location.pathname === path;

  const handleLogout = async () => {
    await logout();
    setLoggedIn(false);
    navigate('/login');
  };

  return (
    <nav style={{
      background: '#0f172a',
      borderBottom: '1px solid #1e293b',
      padding: '0.65rem 1.5rem',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'space-between',
      position: 'sticky',
      top: 0,
      zIndex: 1000
    }}>
      <Link to="/" style={{ textDecoration: 'none' }}>
        <Logo size="sm" theme="dark" />
      </Link>

      <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
        <Link
          to="/"
          style={{
            color: isActive('/') ? '#ffffff' : '#94a3b8',
            fontWeight: isActive('/') ? 700 : 500,
            textDecoration: 'none',
            fontSize: '0.9rem',
            padding: '0.4rem 0.6rem'
          }}
        >
          Home
        </Link>

        {loggedIn && (
          <Link
            to="/dashboard"
            style={{
              color: isActive('/dashboard') ? '#ffffff' : '#94a3b8',
              fontWeight: isActive('/dashboard') ? 700 : 500,
              textDecoration: 'none',
              fontSize: '0.9rem',
              padding: '0.4rem 0.6rem'
            }}
          >
            Dashboard
          </Link>
        )}

        <Link
          to="/upload"
          style={{
            color: isActive('/upload') ? '#ffffff' : '#94a3b8',
            fontWeight: isActive('/upload') ? 700 : 500,
            textDecoration: 'none',
            fontSize: '0.9rem',
            padding: '0.4rem 0.6rem'
          }}
        >
          Upload
        </Link>

        <Link
          to="/review"
          style={{
            color: isActive('/review') ? '#ffffff' : '#94a3b8',
            fontWeight: isActive('/review') ? 700 : 500,
            textDecoration: 'none',
            fontSize: '0.9rem',
            padding: '0.4rem 0.6rem'
          }}
        >
          Review Grid
        </Link>

        <Link
          to="/explanations"
          style={{
            color: isActive('/explanations') ? '#ffffff' : '#94a3b8',
            fontWeight: isActive('/explanations') ? 700 : 500,
            textDecoration: 'none',
            fontSize: '0.9rem',
            padding: '0.4rem 0.6rem'
          }}
        >
          Audit Report
        </Link>

        {role === 'admin' && (
          <Link
            to="/admin"
            style={{
              color: isActive('/admin') ? '#38bdf8' : '#7dd3fc',
              fontWeight: 700,
              textDecoration: 'none',
              fontSize: '0.9rem',
              padding: '0.4rem 0.6rem',
              background: 'rgba(56, 189, 248, 0.12)',
              borderRadius: '6px'
            }}
          >
            🛡️ Admin Panel
          </Link>
        )}

        {loggedIn ? (
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginLeft: '0.5rem' }}>
            <Link
              to="/profile"
              style={{
                textDecoration: 'none',
                fontSize: '0.825rem',
                color: '#e2e8f0',
                background: '#1e293b',
                padding: '0.35rem 0.75rem',
                borderRadius: '8px',
                border: '1px solid #334155',
                display: 'flex',
                alignItems: 'center',
                gap: '5px'
              }}
            >
              <span>👤</span>
              <span style={{ fontWeight: 600 }}>{userName}</span>
            </Link>

            <button
              onClick={handleLogout}
              style={{
                background: 'transparent',
                color: '#f87171',
                border: '1px solid #7f1d1d',
                padding: '0.35rem 0.75rem',
                fontSize: '0.825rem',
                borderRadius: '8px',
                cursor: 'pointer',
                fontWeight: 600
              }}
            >
              Sign Out
            </button>
          </div>
        ) : (
          <Link
            to="/login"
            style={{
              background: '#2563eb',
              color: '#ffffff',
              padding: '0.45rem 1rem',
              borderRadius: '8px',
              textDecoration: 'none',
              fontWeight: 600,
              fontSize: '0.875rem',
              marginLeft: '0.5rem'
            }}
          >
            Sign In / Register
          </Link>
        )}
      </div>
    </nav>
  );
}

export default NavBar;
