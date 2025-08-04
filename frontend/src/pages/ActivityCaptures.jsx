// src/pages/ActivityCaptures.jsx
import React, { useEffect, useMemo, useRef, useState } from 'react';
import { getCaptures } from '../services/api';
import '../styles/activityCaptures.css';

const PAGE_SIZE = 30;

// ---------- date helpers (robust for <input type="date">) ----------
const ymd = (d) => {
  if (!(d instanceof Date) || isNaN(d.getTime())) return '';
  // format YYYY-MM-DD in local time
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, '0');
  const day = String(d.getDate()).padStart(2, '0');
  return `${y}-${m}-${day}`;
};

const ymdToStartEpoch = (s) => {
  // returns epoch seconds for 00:00:00 local of given YYYY-MM-DD; null if invalid/empty
  if (!s || !/^\d{4}-\d{2}-\d{2}$/.test(s)) return null;
  const d = new Date(`${s}T00:00:00`);
  return isNaN(d.getTime()) ? null : Math.floor(d.getTime() / 1000);
};

const ymdToEndEpoch = (s) => {
  if (!s || !/^\d{4}-\d{2}-\d{2}$/.test(s)) return null;
  const d = new Date(`${s}T23:59:59`);
  return isNaN(d.getTime()) ? null : Math.floor(d.getTime() / 1000);
};

export default function ActivityCaptures() {
  // default range: last 24h
  const nowSec = Math.floor(Date.now() / 1000);
  const defaultStart = new Date((nowSec - 24 * 3600) * 1000);
  const defaultEnd = new Date(nowSec * 1000);

  // keep inputs as strings (prevents invalid Date exceptions)
  const [startStr, setStartStr] = useState(ymd(defaultStart));
  const [endStr, setEndStr] = useState(ymd(defaultEnd));

  // image loading 
  const [imgLoading, setImgLoading] = useState(false);

  // derived epochs
  const startEpoch = useMemo(() => ymdToStartEpoch(startStr), [startStr]);
  const endEpoch = useMemo(() => ymdToEndEpoch(endStr), [endStr]);

  const [items, setItems] = useState([]);
  const [total, setTotal] = useState(0);
  const [offset, setOffset] = useState(0);
  const [loading, setLoading] = useState(false);
  const [initialized, setInitialized] = useState(false);
  const [error, setError] = useState(null);

  // modal state
  const [active, setActive] = useState(null);
  const modalRef = useRef(null);

  const validRange = startEpoch !== null && endEpoch !== null && endEpoch >= startEpoch;

  const formatLocal = (ts) => new Date(ts * 1000).toLocaleString();
  const fileNameFromUrl = (u) => {
    try { return new URL(u).pathname.split('/').pop(); }
    catch { return u; }
  };

  const openModal = () => {
    if (!modalRef.current) return;
    const modal = window.bootstrap?.Modal.getOrCreateInstance(modalRef.current);
    modal?.show();
  };

  // Load a page (tries order=desc first; falls back if backend lacks it)
  const loadPage = async ({ reset = false, customOffset = null } = {}) => {
    if (!validRange) return;
    setLoading(true); setError(null);
    try {
      const res = await getCaptures({
        start: startEpoch, end: endEpoch,
        limit: PAGE_SIZE,
        offset: customOffset ?? (reset ? 0 : offset),
        order: 'desc',
      });
      const data = res.data;
      setTotal(data.total ?? 0);
      if (reset) {
        setItems(data.items || []);
        setOffset((data.items || []).length);
      } else {
        setItems((prev) => [...prev, ...(data.items || [])]);
        setOffset((prev) => prev + (data.items?.length || 0));
      }
      setInitialized(true);
    } catch (e) {
      // Fallback: compute newest page manually using asc + offset from end
      try {
        const probe = await getCaptures({
          start: startEpoch, end: endEpoch, limit: 1, offset: 0, order: 'asc'
        });
        const t = probe.data.total ?? 0;
        setTotal(t);
        const off = Math.max(t - PAGE_SIZE, 0);
        const page = await getCaptures({
          start: startEpoch, end: endEpoch, limit: PAGE_SIZE, offset: off, order: 'asc'
        });
        const list = page.data.items || [];
        list.reverse(); // newest first in UI
        setItems(list);
        setOffset(t);
        setInitialized(true);
        setError(null);
      } catch (e2) {
        setError(e2?.response?.data?.error || e2.message || 'Load failed');
      }
    } finally {
      setLoading(false);
    }
  };

  // Initial load
  useEffect(() => {
    loadPage({ reset: true });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const applyDateRange = () => {
    if (!validRange) return;
    setItems([]); setOffset(0);
    loadPage({ reset: true });
  };

  const loadMore = () => {
    if (!validRange) return;
    loadPage({ reset: false });
  };

  const fullImageUrl = useMemo(() => {
    if (!active?.url) return null;
    const sep = active.url.includes('?') ? '&' : '?';
    return `${active.url}${sep}t=${Date.now()}`;
  }, [active]);

  return (
    <div className="container py-4">
      <h3 className="mb-3">Activity &rsaquo; Captures</h3>

      {/* Filters */}
      <div className="card mb-3">
        <div className="card-body">
          <div className="row g-3 align-items-end">
            <div className="col-12 col-md-4">
              <label className="form-label">Start date</label>
              <input
                type="date"
                className={`form-control ${startEpoch === null ? 'is-invalid' : ''}`}
                value={startStr}
                onChange={(e) => setStartStr(e.target.value)}
              />
              {startEpoch === null && (
                <div className="invalid-feedback">Please enter a valid date.</div>
              )}
            </div>
            <div className="col-12 col-md-4">
              <label className="form-label">End date</label>
              <input
                type="date"
                className={`form-control ${endEpoch === null ? 'is-invalid' : ''}`}
                value={endStr}
                onChange={(e) => setEndStr(e.target.value)}
              />
              {endEpoch === null && (
                <div className="invalid-feedback">Please enter a valid date.</div>
              )}
            </div>
            <div className="col-12 col-md-4 d-flex gap-2">
              <button
                className="btn btn-primary flex-grow-1"
                onClick={applyDateRange}
                disabled={loading || !validRange}
              >
                Apply
              </button>
              <button
                className="btn btn-outline-secondary"
                onClick={() => {
                  const ns = Math.floor(Date.now() / 1000);
                  setStartStr(ymd(new Date((ns - 24 * 3600) * 1000)));
                  setEndStr(ymd(new Date(ns * 1000)));
                }}
                disabled={loading}
                title="Last 24h"
              >
                24h
              </button>
            </div>
          </div>
          {!validRange && (
            <div className="mt-2 small text-danger">
              Invalid range: end must be on/after start.
            </div>
          )}
        </div>
      </div>

      {/* List */}
      <div className="card">
        <div className="card-header d-flex justify-content-between align-items-center">
          <span className="fw-semibold">Latest Captures</span>
          <small className="text-muted">
            {initialized ? `${items.length}/${total}` : ''}
          </small>
        </div>

        <div className="list-group list-group-flush">
          {!initialized && (
            <div className="list-group-item py-5 text-center text-muted">
              <div className="spinner-border" role="status" aria-label="Loading" />
            </div>
          )}

          {initialized && items.length === 0 && !loading && !error && (
            <div className="list-group-item py-5 text-center text-muted">
              No captures found for the selected range.
            </div>
          )}

          {error && (
            <div className="list-group-item py-3">
              <div className="alert alert-warning mb-0">{String(error)}</div>
            </div>
          )}

          {items.map((it) => (
            <button
              key={it.id}
              className="list-group-item list-group-item-action capture-row d-flex align-items-center gap-3 text-start py-2"
              onClick={() => { setActive(it); setImgLoading(true); openModal(); }}
            >
              {/* representative icon (or swap to a tiny <img> later) */}
              <div className="d-inline-flex align-items-center justify-content-center rounded capture-thumb">
                <i className="bi bi-image" />
              </div>

              {/* main text block */}
              <div className="flex-grow-1">
                <div className="fw-semibold text-truncate">{fileNameFromUrl(it.url)}</div>
                <div className="small text-muted">
                  ID #{it.id}
                </div>
                <div className="small text-truncate" style={{ maxWidth: 560 }}>
                  {it.description ? it.description : '—'}
                </div>
              </div>

              {/* RIGHT-SIDE TIMESTAMP */}
              <div className="ms-auto small text-muted text-nowrap">
                {formatLocal(it.timestamp)}
              </div>

              <i className="bi bi-chevron-right text-muted ms-2" />
            </button>
          ))}

          {/* Load more */}
          {initialized && items.length < total && (
            <div className="list-group-item text-center">
              <button className="btn btn-outline-primary" onClick={loadMore} disabled={loading || !validRange}>
                {loading ? 'Loading…' : 'Load more'}
              </button>
            </div>
          )}
        </div>
      </div>

      {/* Full image modal */}
      <div className="modal fade" tabIndex="-1" ref={modalRef} aria-hidden="true">
        <div className="modal-dialog modal-dialog-centered modal-lg">
          <div className="modal-content">
            <div className="modal-header">
              <h6 className="modal-title">
                {active ? fileNameFromUrl(active.url) : 'Preview'}
              </h6>
              <button type="button" className="btn-close" data-bs-dismiss="modal" aria-label="Close" />
            </div>
            <div className="modal-body">
              {active ? (
                <div className="position-relative text-center" style={{ minHeight: '50vh' }}>
                  {/* Spinner while image loads */}
                  {imgLoading && (
                    <div className="d-flex align-items-center justify-content-center w-100 h-100 position-absolute top-0 start-0">
                      <div className="spinner-border" role="status" aria-label="Loading image..." />
                    </div>
                  )}

                  <img
                    src={fullImageUrl}
                    alt={active.description || 'capture'}
                    className="img-fluid rounded"
                    style={{ maxHeight: '70vh', objectFit: 'contain', opacity: imgLoading ? 0 : 1, transition: 'opacity .2s ease' }}
                    onLoad={() => setImgLoading(false)}
                    onError={(e) => { e.currentTarget.alt = 'Failed to load image'; setImgLoading(false); }}
                  />

                  <div className="small text-muted mt-2">
                    ID #{active.id} &middot; {formatLocal(active.timestamp)}
                  </div>
                  {active.description && (
                    <div className="small mt-1">{active.description}</div>
                  )}
                </div>
              ) : (
                <div className="text-muted">No image selected.</div>
              )}
            </div>

            <div className="modal-footer">
              {active && (
                <a className="btn btn-outline-secondary" href={active.url} target="_blank" rel="noreferrer">
                  Open original
                </a>
              )}
              <button type="button" className="btn btn-primary" data-bs-dismiss="modal">Close</button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
