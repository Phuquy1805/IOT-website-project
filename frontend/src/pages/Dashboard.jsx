import React, { useState, useCallback } from 'react';
import LatestCaptureCard from '../components/LatestCaptureCard';
import BigToggle from '../components/BigToggle';
import { openDoor, closeDoor, registerFingerprint } from '../services/api';
import ChatWidget from '../components/ChatWidget'; // <- nhận props như ChatBox
import DisplayControl from '../components/DisplayControl';

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

export default function Dashboard() {
  const [doorOpen, setDoorOpen] = useState(false);
  const [cooldown, setCooldown] = useState(false);
  const [error, setError] = useState('');

  // === Chat state ===
  const [messages, setMessages] = useState([
    { sender: 'bot', text: 'Xin chào! Mình có thể giúp gì cho bạn?' },
  ]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);

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
    await sleep(3000); // 3s cooldown
    setCooldown(false);
  };

  // Gửi tin nhắn tới backend /api/chat
  const sendToBot = useCallback(async () => {
    const text = input.trim();
    if (!text || loading) return;

    // push tin nhắn user
    setMessages((prev) => [...prev, { sender: 'user', text }]);
    setInput('');
    setLoading(true);

    try {
      const res = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include', // cần nếu JWT ở cookie
        body: JSON.stringify({ message: text }),
      });

      const data = await res.json();

      if (!res.ok) {
        setMessages((prev) => [
          ...prev,
          { sender: 'bot', text: data?.error || 'Có lỗi xảy ra khi gọi chat.' },
        ]);
      } else {
        // Backend trả 'reply' và (nếu có) 'image_url'
        setMessages((prev) => [
          ...prev,
          {
            sender: 'bot',
            text: data?.reply || '',
            imageUrl: data?.image_url || null, // <-- ChatWidget/ChatBox render ảnh nếu có
          },
        ]);
      }
    } catch (err) {
      setMessages((prev) => [
        ...prev,
        { sender: 'bot', text: err.message || 'Lỗi mạng.' },
      ]);
    } finally {
      setLoading(false);
    }
  }, [input, loading]);

  const onInputChange = (e) => setInput(e.target.value);

  const onKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendToBot();
    }
  };

  return (
    <>
      <div className="container mt-4">
        <h2 className="mb-4">Dashboard</h2>

        <div className="row g-4">
          <div className="col-12 col-lg-8">
            <LatestCaptureCard />
          </div>

          <div className="col-12 col-lg-4">
            <div className="card shadow-sm p-4 mb-4">
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

            {/* DisplayControl dưới Door Control */}
            <DisplayControl />
          </div>
        </div>
      </div>

      {/* Bubble chat ngoài layout chính */}
      <ChatWidget
        messages={messages}
        input={input}
        loading={loading}
        onInputChange={onInputChange}
        onSend={sendToBot}
        onKeyDown={onKeyDown}
      />
      {/*
        Nếu ChatWidget KHÔNG nhận props, thay bằng:
        <ChatBox
          messages={messages}
          input={input}
          loading={loading}
          onInputChange={onInputChange}
          onSend={sendToBot}
          onKeyDown={onKeyDown}
        />
      */}
    </>
  );
}
