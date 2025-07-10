// src/pages/ChangePassword.jsx
import React, { useState } from 'react';
import { changePassword } from '../services/api';

export default function ChangePassword() {
  const [oldPwd, setOld]      = useState('');
  const [newPwd, setNew]      = useState('');
  const [message, setMessage] = useState(null);

  const handleSubmit = async e => {
    e.preventDefault();
    try {
      await changePassword(oldPwd, newPwd);
      setMessage({ type: 'success', text: 'Password updated.' });
    } catch (err) {
      setMessage({ type: 'danger', text: err.response?.data?.error || 'Error' });
    }
  };

  return (
    <div className="container mt-4" style={{ maxWidth: '500px' }}>
      <h2>Change Password</h2>
      {message && (
        <div className={`alert alert-${message.type}`}>{message.text}</div>
      )}
      <form onSubmit={handleSubmit}>
        <div className="mb-3">
          <label className="form-label">Old Password</label>
          <input type="password" className="form-control"
                 value={oldPwd} required
                 onChange={e => setOld(e.target.value)} />
        </div>
        <div className="mb-4">
          <label className="form-label">New Password</label>
          <input type="password" className="form-control"
                 value={newPwd} required
                 onChange={e => setNew(e.target.value)} />
        </div>
        <button type="submit" className="btn btn-warning w-100">
          Update Password
        </button>
      </form>
    </div>
  );
}
