// src/components/LatestCaptureCard.jsx
import React, { useEffect, useMemo, useState } from 'react';
import { getLatestCapture } from '../services/api';

export default function LatestCaptureCard({ title = 'Latest Camera Capture', pollMs = 5000 }) {
  const [imgUrl, setImgUrl] = useState(null);
  const [timestamp, setTimestamp] = useState(null);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState(null);
  const [autoRefresh, setAutoRefresh] = useState(true);
  const [intervalMs, setIntervalMs] = useState(pollMs);

  const cacheBustedUrl = useMemo(() => {
    if (!imgUrl) return null;
    return `${imgUrl}${imgUrl.includes('?') ? '&' : '?'}t=${Date.now()}`;
  }, [imgUrl, timestamp]);

  const fetchLatest = async () => {
    try {
      setErr(null);
      const { data } = await getLatestCapture();
      setImgUrl(data.url);
      setTimestamp(data.timestamp);
    } catch (e) {
      setErr(e?.response?.data?.error || e.message || 'Failed to load');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchLatest(); }, []);
  useEffect(() => {
    if (!autoRefresh) return;
    const id = setInterval(fetchLatest, intervalMs);
    return () => clearInterval(id);
  }, [autoRefresh, intervalMs]);

  const lastUpdated = useMemo(() => {
    if (!timestamp) return '-';
    try { return new Date(timestamp * 1000).toLocaleString(); }
    catch { return String(timestamp); }
  }, [timestamp]);

  return (
    <div className="card shadow-sm">
      <div className="card-header d-flex align-items-center justify-content-between">
        <span className="fw-semibold">{title}</span>
        <div className="d-flex align-items-center gap-2">
          <div className="form-check form-switch m-0">
            <input
              id="autoRefreshSwitch"
              className="form-check-input"
              type="checkbox"
              checked={autoRefresh}
              onChange={(e) => setAutoRefresh(e.target.checked)}
            />
            <label className="form-check-label ms-2" htmlFor="autoRefreshSwitch">
              Auto-refresh
            </label>
          </div>

          <select
            className="form-select form-select-sm"
            style={{ width: 110 }}
            value={intervalMs}
            onChange={(e) => setIntervalMs(Number(e.target.value))}
          >
            <option value={3000}>3s</option>
            <option value={5000}>5s</option>
            <option value={10000}>10s</option>
            <option value={30000}>30s</option>
          </select>

          <button
            className="btn btn-sm btn-outline-primary"
            onClick={fetchLatest}
            disabled={loading}
            title="Refresh now"
          >
            Refresh
          </button>
        </div>
      </div>

      <div className="card-body">
        {loading ? (
          <div className="d-flex align-items-center justify-content-center" style={{ height: 320 }}>
            <div className="spinner-border" role="status" aria-label="Loading" />
          </div>
        ) : err ? (
          <div className="alert alert-warning mb-0">
            <strong>Unable to load:</strong> {String(err)}
          </div>
        ) : imgUrl ? (
          <div className="border rounded-3 p-2" style={{ background: '#f8f9fa' }}>
            <div className="d-flex align-items-center justify-content-center" style={{ width: '100%', height: 360, overflow: 'hidden' }}>
              <img
                src={cacheBustedUrl}
                alt="Latest capture"
                className="img-fluid"
                style={{ maxHeight: '100%', objectFit: 'contain' }}
                onError={() => setErr('Image failed to load')}
              />
            </div>
          </div>
        ) : (
          <div className="text-muted">No capture available yet.</div>
        )}
      </div>

      <div className="card-footer d-flex justify-content-between small text-muted">
        <span>Last updated: {lastUpdated}</span>
        {imgUrl && (
          <a href={imgUrl} target="_blank" rel="noreferrer" className="text-decoration-none">
            Open original
          </a>
        )}
      </div>
    </div>
  );
}
