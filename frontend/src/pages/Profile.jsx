// src/pages/Profile.jsx
import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { getProfile } from '../services/api';

export default function Profile() {
  const [user, setUser] = useState(null);
  const navigate = useNavigate()

  useEffect(() => {
    getProfile().then(res => setUser(res.data));
  }, []);

  if (!user) {  
    return <div className="container mt-4">Loading profile…</div>;
  }

  const handleChangePassword = async () => {
      navigate('/change-password');
    };
  

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

          <button
            className="btn btn-warning w-100"
            onClick={() => handleChangePassword()}
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