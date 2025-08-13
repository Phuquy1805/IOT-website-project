// src/components/ChatWidget.jsx
import React, { useState } from 'react';
import ChatBox from './ChatBox';
import { chatWithGemini } from '../services/api';

const extractFirstUrl = (s = '') => {
  const m = s.match(/https?:\/\/\S+/i);
  return m ? m[0] : null;
};

export default function ChatWidget() {
  const [open, setOpen] = useState(false);
  const [messages, setMessages] = useState([
    { sender: 'bot', text: 'Chat với em đi 😘' }
  ]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);

  const toggleChat = () => setOpen(!open);
  const handleInputChange = (e) => setInput(e.target.value);

  const handleSend = async () => {
    const text = input.trim();
    if (!text || loading) return;

    // Đẩy tin nhắn user
    setMessages(prev => [...prev, { sender: 'user', text }]);
    setInput('');
    setLoading(true);

    try {
      const response = await chatWithGemini(text); // POST /api/chat
      const data = response?.data ?? {};

      // Backend có thể trả về: { reply, image_url }
      const replyTextRaw = data.reply || 'Em chưa hiểu ý anh 🥺';
      const apiImageUrl = data.image_url || data.imageUrl || null;

      // Trường hợp backend cũ: reply chứa luôn URL -> rút URL ra
      const inferredUrl = !apiImageUrl ? extractFirstUrl(replyTextRaw) : null;

      // Nếu có URL trong reply, có thể xóa URL khỏi text để UI gọn hơn
      const replyText = inferredUrl
        ? replyTextRaw.replace(inferredUrl, '').trim()
        : replyTextRaw;

      setMessages(prev => [
        ...prev,
        {
          sender: 'bot',
          text: replyText,
          imageUrl: apiImageUrl || inferredUrl || null, // <-- ChatBox sẽ hiển thị ảnh
        }
      ]);
    } catch (err) {
      console.error('Lỗi gọi API:', err);
      setMessages(prev => [
        ...prev,
        { sender: 'bot', text: '⚠️ Không thể kết nối với AI' }
      ]);
    } finally {
      setLoading(false);
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter') {
      e.preventDefault(); // tránh submit/nẩy UI
      handleSend();
    }
  };

  return (
    <>
      {/* Nút mở chat */}
      <div
        onClick={toggleChat}
        style={{
          position: 'fixed',
          bottom: '20px',
          left: '20px',
          width: '60px',
          height: '60px',
          borderRadius: '50%',
          backgroundColor: '#3b7ea1',
          color: '#fff',
          display: 'flex',
          justifyContent: 'center',
          alignItems: 'center',
          fontSize: '1.8rem',
          cursor: 'pointer',
          zIndex: 1000,
          boxShadow: '0 0 10px rgba(0,0,0,0.2)'
        }}
      >
        💬
      </div>

      {/* Hộp chat */}
      {open && (
        <div
          style={{
            position: 'fixed',
            bottom: '90px',
            left: '20px',
            width: 'clamp(360px, 40vw, 560px)',
            height: 'min(70vh, 640px)',
            backgroundColor: '#fff',
            borderRadius: '12px',
            boxShadow: '0 8px 24px rgba(0,0,0,0.2)',
            overflow: 'hidden',
            zIndex: 1000,
            display: 'flex',
            flexDirection: 'column'
          }}
        >
          <ChatBox
            messages={messages}
            input={input}
            onInputChange={handleInputChange}
            onSend={handleSend}
            onKeyDown={handleKeyDown}
            loading={loading}
          />
        </div>
      )}

    </>
  );
}
