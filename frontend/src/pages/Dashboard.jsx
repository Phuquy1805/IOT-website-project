import React, { useState } from 'react';
import LatestCaptureCard from '../components/LatestCaptureCard';
import BigToggle from '../components/BigToggle';
import { openDoor, closeDoor, registerFingerprint } from '../services/api'; 


const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

export default function Dashboard() {
  const [doorOpen, setDoorOpen]   = useState(false);
  const [cooldown, setCooldown]   = useState(false);
  const [error, setError]         = useState('');
    
  // State mới cho việc đăng ký vân tay
  const [isRegistering, setIsRegistering] = useState(false);
  const [fingerprintStatus, setFingerprintStatus] = useState('');
  const [fingerprintError, setFingerprintError] = useState('');

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

  // Hàm xử lý khi nhấn nút đăng ký vân tay
  const handleRegisterFingerprint = async () => {
    if (isRegistering) return;

    setIsRegistering(true);
    setFingerprintStatus('Đang gửi yêu cầu đến thiết bị...');
    setFingerprintError('');
    try {
      const response = await registerFingerprint();
      setFingerprintStatus('Yêu cầu thành công! Vui lòng làm theo hướng dẫn trên thiết bị.');
      setTimeout(() => {
        setIsRegistering(false);
        setFingerprintStatus('');
      }, 30000); // Reset sau 30 giây
    } catch (e) {
      setFingerprintError(e.response?.data?.error || e.message);
      setFingerprintStatus('');
      setIsRegistering(false);
    }
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

          {/* Phần thêm cho đăng ký vân tay */}
          <div className="card shadow-sm p-4">
            <h5 className="mb-3">Fingerprint Management</h5>
            <button
              className="btn btn-primary"
              onClick={handleRegisterFingerprint}
              disabled={isRegistering}
            >
              {isRegistering ? 'Đang xử lý...' : 'Đăng kí vân tay mới'}
            </button>
            {fingerprintStatus && (
              <div className="alert alert-info py-1 mt-2" style={{ fontSize: '0.8rem' }}>
                {fingerprintStatus}
              </div>
            )}
            {fingerprintError && (
              <div className="alert alert-danger py-1 mt-2" style={{ fontSize: '0.8rem' }}>
                {fingerprintError}
              </div>
            )}
          </div>

        </div>
      </div>
    </div>
  );
}