// src/pages/VerifyOTP.jsx
import React, { useState, useEffect } from 'react';
import { useNavigate, useLocation, Link } from 'react-router-dom';
import { registerVerify, registerSendOTP }   from '../services/api';

export default function VerifyOTP() {
  const navigate = useNavigate();
  const { state } = useLocation();
  const { username, email, password } = state || {};

  // redirect back to /register if required data is missing
  useEffect(() => {
    if (!username || !email || !password) {
      navigate('/register', { replace: true });
    }
  }, [username, email, password, navigate]);

  const [otp, setOtp]           = useState('');
  const [error, setError]       = useState('');
  const [loading, setLoading]   = useState(false);
  const [resending, setResending] = useState(false);

  const handleChange = e => {
    setOtp(e.target.value.replace(/\D/g, '')); // digits only
  };

  const handleSubmit = async e => {
    e.preventDefault();
    setError('');

    if (otp.length !== 6) {
      setError('Please enter the full 6-digit code');
      return;
    }

    setLoading(true);
    try {
      await registerVerify(username, email, password, otp);
      navigate('/login');
    } catch (err) {
      setError(err.response?.data?.error || 'OTP verification failed');
    } finally {
      setLoading(false);
    }
  };

  const handleResend = async e => {
    e.preventDefault();
    setError('');

    setResending(true);
    try {
      await registerSendOTP(username, email, password);
    } catch (err) {
      setError(err.response?.data?.error || 'Could not resend code');
    } finally {
      setResending(false);
    }
  };

  // if we’re redirecting, don’t render anything
  if (!username || !email || !password) return null;

  return (
    <div className="container vh-100 d-flex align-items-center">
      <div className="mx-auto" style={{ maxWidth: '420px' }}>
        <h3 className="mb-4 text-center">Verify Your Email</h3>
        <p className="text-center">
          We sent a 6-digit code to <strong>{email}</strong>. Enter it below.
        </p>

        {error && <div className="alert alert-danger">{error}</div>}

        <form onSubmit={handleSubmit}>
          <div className="mb-3">
            <label className="form-label">OTP Code</label>
            <input
              type="text"
              inputMode="numeric"
              autoComplete="one-time-code"
              className="form-control text-center fw-bold fs-3"
              style={{ letterSpacing: '0.4rem', height: '4rem', borderWidth: '2px' }}
              maxLength={6}
              value={otp}
              onChange={handleChange}
              disabled={loading}
              required
            />
          </div>

          <button type="submit" className="btn btn-primary w-100" disabled={loading}>
            {loading ? (
              <>
                <span className="spinner-border spinner-border-sm me-2" role="status" aria-hidden="true"></span>
                Verifying…
              </>
            ) : (
              'Verify & Complete Registration'
            )}
          </button>
        </form>

        <p className="mt-3 text-center">
          Didn’t receive it?{' '}
          <button
            onClick={handleResend}
            className="btn btn-link p-0 align-baseline"
            disabled={resending}
          >
            {resending ? 'Sending…' : 'Resend code'}
          </button>
        </p>

        <p className="mt-2 text-center">
          Wrong email? <Link to="/register">Start over</Link>
        </p>
      </div>
    </div>
  );
}
