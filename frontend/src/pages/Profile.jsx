// src/pages/Profile.jsx
import React, { useEffect, useState } from 'react';
import { getProfile } from '../services/api';

export default function Profile() {
  const [user, setUser] = useState(null);

  useEffect(() => {
    getProfile().then(res => setUser(res.data));
  }, []);

  if (!user) {
    return <div className="container mt-4">Loading profile…</div>;
  }

  return (
    <div className="container mt-4">
      <h2>Your Profile</h2>
      <ul className="list-group mt-3">
        <li className="list-group-item"><strong>ID:</strong> {user.id}</li>
        <li className="list-group-item"><strong>Username:</strong> {user.username}</li>
        <li className="list-group-item"><strong>Email:</strong> {user.email}</li>
      </ul>
    </div>
  );
}