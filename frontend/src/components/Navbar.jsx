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

            {/* Activity dropdown */}
            <li className={`nav-item dropdown ${activityActive ? 'active' : ''}`}>
              <a
                href="#"
                className={`nav-link dropdown-toggle ${activityActive ? 'active' : ''}`}
                id="activityDropdown"
                role="button"
                data-bs-toggle="dropdown"
                data-bs-auto-close="outside"
                aria-expanded="false"
              >
                Activity
              </a>
              <ul className="dropdown-menu dropdown-menu-dark shadow" aria-labelledby="activityDropdown">
                <li>
                  <NavLink className="dropdown-item d-flex align-items-start gap-2" to="/activity/statistics">
                    <i className="bi bi-graph-up" aria-hidden="true"></i>
                    <div>
                      <div>Statistics</div>
                      <small className="text-secondary">Charts & trends</small>
                    </div>
                  </NavLink>
                </li>

                <li>
                  <NavLink className="dropdown-item d-flex align-items-start gap-2" to="/activity/captures">
                    <i className="bi bi-camera" aria-hidden="true"></i>
                    <div>
                      <div>Captures</div>
                      <small className="text-secondary">Photo timeline</small>
                    </div>
                  </NavLink>
                </li>

                <li>
                  <NavLink className="dropdown-item d-flex align-items-start gap-2" to="/activity/fingerprints">
                    <i className="bi bi-fingerprint" aria-hidden="true"></i>
                    <div>
                      <div>Fingerprints</div>
                      <small className="text-secondary">Access records</small>
                    </div>
                  </NavLink>
                </li>

              </ul>
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
