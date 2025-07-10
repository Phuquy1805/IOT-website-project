// src/pages/Register.jsx
import React, { useState } from 'react';
import { register } from '../services/api';
import { validateUsername, validatePassword } from '../utils/validation';
import { useNavigate, Link } from 'react-router-dom';

export default function Register() {
  const [username, setUsername] = useState('');
  const [email, setEmail]       = useState('');
  const [password, setPassword] = useState('');
  const [usernameErr,  setUsernameErr]  = useState('');
  const [passwordErr,  setPasswordErr]  = useState('');
  const [submitErr,    setSubmitErr]    = useState('');
  const navigate = useNavigate();


  const handleUsernameChange = e => {
    const v = e.target.value;
    setUsername(v);
    setUsernameErr(
      validateUsername(v)
        ? ''
        : 'Username must consists of letters, numbers or underscore only'
    );
  };

  const handlePasswordChange = e => {
    const v = e.target.value;
    setPassword(v);
    setPasswordErr(
      validatePassword(v)
        ? ''
        : 'Password must be longer than 8 characters, msut includes letters, numbers & special character'
    );
  };

  const handleSubmit = async e => {
    e.preventDefault();
    // block submission if invalid
    if (!validateUsername(username)) {
      setUsernameErr('Please fix your username');
      return;
    }
    if (!validatePassword(password)) {
      setPasswordErr('Please fix your password');
      return;
    }

    try {
      await register(username, email, password);
      navigate('/login');
    } catch (err) {
      setSubmitErr(err.response?.data?.error || 'Registration failed');
    }
  };

    return (
    <div className="container mt-5" style={{ maxWidth: '450px' }}>
      <h3 className="mb-4 text-center">Register</h3>

      {submitErr && <div className="alert alert-danger">{submitErr}</div>}

      <form onSubmit={handleSubmit}>
        <div className="mb-3">
          <label className="form-label">Username</label>
          <input
            type="text"
            className={`form-control ${usernameErr ? 'is-invalid' : ''}`}
            value={username}
            onChange={handleUsernameChange}
            required
          />
          {usernameErr && <div className="invalid-feedback">{usernameErr}</div>}
        </div>

        <div className="mb-3">
          <label className="form-label">Email</label>
          <input
            type="email"
            className="form-control"
            value={email}
            onChange={e => setEmail(e.target.value)}
            required
          />
        </div>

        <div className="mb-4">
          <label className="form-label">Password</label>
          <input
            type="password"
            className={`form-control ${passwordErr ? 'is-invalid' : ''}`}
            value={password}
            onChange={handlePasswordChange}
            required
          />
          {passwordErr && <div className="invalid-feedback">{passwordErr}</div>}
        </div>

        <button type="submit" className="btn btn-success w-100">
          Register
        </button>
      </form>

      <p className="mt-3 text-center">
        Already have an account? <Link to="/login">Login</Link>
      </p>
    </div>
  );
}