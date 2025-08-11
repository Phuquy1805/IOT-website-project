import React, { useState } from 'react';
import LatestCaptureCard from '../components/LatestCaptureCard';
import BigToggle from '../components/BigToggle';
import { openDoor, closeDoor, registerFingerprint } from '../services/api'; 


const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

export default function Dashboard() {
  const [doorOpen, setDoorOpen]   = useState(false);
  const [cooldown, setCooldown]   = useState(false);
  const [error, setError]         = useState('');

  const flipDoor = async () => {
    if (cooldown) return;
    setCooldown(true);
    setError('');
    try {
      doorOpen ? await closeDoor() : await openDoor();
      setDoorOpen(!doorOpen);
    } catch (e) {
      setError(e.response?.data?.error || e.message);
    }
    await sleep(3000);  // 3s cooldown
    setCooldown(false);
  };

  return (
    <div className="container mt-4">
      <h2 className="mb-4">Dashboard</h2>

      <div className="row g-4">
        <div className="col-12 col-lg-8">
          <LatestCaptureCard />
        </div>

        <div className="col-12 col-lg-4">
          <div className="card shadow-sm p-4">
            <h5 className="mb-3">Door Control</h5>

            <BigToggle
              id="doorToggle"
              checked={doorOpen}
              disabled={cooldown}
              onChange={flipDoor}
              label={doorOpen ? 'OPEN' : 'CLOSED'}
            />

            {error && (
              <div className="alert alert-danger py-1 mt-2" style={{ fontSize: '0.8rem' }}>
                {error}
              </div>
            )}
            {cooldown && (
              <small className="text-muted d-block mt-2">wait&nbsp;3&nbsp;s…</small>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}