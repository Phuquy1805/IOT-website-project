// src/pages/Dashboard.jsx
import React from 'react';
import LatestCaptureCard from '../components/LatestCaptureCard';

export default function Dashboard() {
  return (
    <div className="container mt-4">
      <h2 className="mb-4">Dashboard</h2>

      <div className="row g-4">
        <div className="col-12 col-lg-8">
          <LatestCaptureCard />
        </div>

        <div className="col-12 col-lg-4">
          <div className="card h-100">
            <div className="card-header">Stats</div>
            <div className="card-body">
              <p className="text-muted mb-0">Add more widgets here…</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
