import React, { useState } from 'react';
import { sendLCDMessage } from '../services/api';

export default function DisplayControl() {
  const [text, setText] = useState('');
  const [displaying, setDisplaying] = useState('');

  const handleSend = async () => {
    if (!text.trim()) return;
    try {
      await sendLCDMessage(text.trim());
      setDisplaying(text.trim());
      setText('');
    } catch (err) {
      console.error('Failed to send LCD message:', err);
    }
  };

  return (
    <div className="card" style={{ borderTop: '4px solid #1E90FF', padding: '10px' }}>
      <h4 style={{ marginBottom: '8px' }}>Display</h4>
      <div style={{ fontSize: '14px', marginBottom: '5px' }}>
        Displaying:
      </div>
      <div style={{ fontWeight: 'bold', color: '#1E90FF', marginBottom: '10px' }}>
        {displaying || '---'}
      </div>
      <div style={{ display: 'flex', gap: '5px' }}>
        <input
          type="text"
          value={text}
          placeholder="Enter message..."
          onChange={(e) => setText(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter') {
              handleSend();
            }
          }}
          style={{ flex: 1 }}
        />
        <button
          onClick={handleSend}
          style={{
            backgroundColor: '#1E90FF',
            color: 'white',
            border: 'none',
            padding: '0 12px'
          }}
        >
          Send
        </button>
      </div>
    </div>
  );
}