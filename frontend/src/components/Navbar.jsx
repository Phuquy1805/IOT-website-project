// src/components/Navbar.jsx
import React from 'react';
import { NavLink, useNavigate, useLocation } from 'react-router-dom';
import { logout } from '../services/api';
import '../styles/navbar.css';

export default function Navbar() {
  const navigate = useNavigate();
  const { pathname } = useLocation();
  const activityActive = pathname.startsWith('/activity');

  const handleLogout = async () => {
    await logout();
    navigate('/login');
  };

  return (
    <nav className="navbar navbar-expand-lg navbar-dark bg-primary bg-gradient shadow-sm sticky-top">
      <div className="container">
        <NavLink className="navbar-brand d-flex align-items-center" to="/">
          <span className="brand-dot me-2">I</span>
          <span>IoT Dashboard</span>
        </NavLink>

        <button
          className="navbar-toggler"
          type="button"
          data-bs-toggle="collapse"
          data-bs-target="#navMenu"
          aria-controls="navMenu"
          aria-expanded="false"
          aria-label="Toggle navigation"
        >
          <span className="navbar-toggler-icon" />
        </button>

        <div className="collapse navbar-collapse" id="navMenu">
          <ul className="navbar-nav me-auto">
            <li className="nav-item">
              <NavLink end className="nav-link" to="/">
                Dashboard
              </NavLink>
            </li>

            <li className="nav-item">
              <NavLink className="nav-link" to="/profile">
                Profile
              </NavLink>
            </li>

            <li className="nav-item">
              <NavLink className="nav-link" to="/fingerprint-manager">
                Fingerprint Manager
              </NavLink>
            </li>
            
            <li className="nav-item">
              <NavLink className="nav-link" to="/captures">
                Captures
              </NavLink>
            </li>

          </ul>

          <button className="btn btn-outline-light btn-sm" onClick={handleLogout}>
            Logout
          </button>
        </div>
      </div>
    </nav>
  );
}
