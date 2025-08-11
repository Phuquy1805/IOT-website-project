import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { getProfile, updateWebhook } from '../services/api';

export default function Profile() {
  const [user, setUser] = useState(null);
  const [webhook, setWebhook] = useState('');
  const navigate = useNavigate();

  useEffect(() => {
    getProfile().then(res => {
      setUser(res.data);
      setWebhook(res.data.discord_webhook || '');
    });
  }, []);

  const handleChangePassword = () => {
    navigate('/change-password');
  };

  const handleSaveWebhook = async () => {
    try {
      await updateWebhook({ url: webhook });
      alert('Webhook saved!');
    } catch (err) {
      console.error('Error saving webhook:', err.response || err.message || err);
      alert(`Error saving webhook: ${err.response?.data?.error || err.message || 'Unknown error'}`);
    }
  };

  if (!user) {
    return <div className="container mt-4">Loading profile…</div>;
  }

  return (
    <div className="container my-5">
      <div className="row justify-content-center">
        <div className="col-md-6 col-lg-5">
          <div className="card shadow-sm border-0">
            <div className="card-body">
              <h3 className="card-title text-center mb-4">Your Profile</h3>

              <ul className="list-group list-group-flush mb-4">
                <li className="list-group-item d-flex justify-content-between">
                  <span className="fw-semibold">ID</span>
                  <span>{user.id}</span>
                </li>
                <li className="list-group-item d-flex justify-content-between">
                  <span className="fw-semibold">Username</span>
                  <span>{user.username}</span>
                </li>
                <li className="list-group-item d-flex justify-content-between">
                  <span className="fw-semibold">Email</span>
                  <span>{user.email}</span>
                </li>
              </ul>

              {/* Notification Setup */}
              <div className="mb-3">
                <label className="form-label fw-semibold">Notification Setup</label>
                <input
                  type="text"
                  className="form-control"
                  placeholder="Enter Discord Webhook URL"
                  value={webhook}
                  onChange={e => setWebhook(e.target.value)}
                />
              </div>
              <button
                className="btn btn-primary w-100 mb-3"
                onClick={handleSaveWebhook}
              >
                Save Webhook
              </button>

              <button
                className="btn btn-warning w-100"
                onClick={handleChangePassword}
              >
                Change Password
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}