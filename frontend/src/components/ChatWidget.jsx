import React, { useState } from 'react';
import ChatBox from './ChatBox';
import { chatWithGemini } from '../services/api'; 

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
    if (!input.trim()) return;

    const userMessage = { sender: 'user', text: input };
    setMessages((prev) => [...prev, userMessage]);
    setInput('');
    setLoading(true);

    try {
      const response = await chatWithGemini(input); 
      const replyText = response.data.reply || 'Em chưa hiểu ý anh 🥺';
      setMessages((prev) => [...prev, { sender: 'bot', text: replyText }]);
    } catch (error) {
      console.error('Lỗi gọi API:', error);
      setMessages((prev) => [...prev, { sender: 'bot', text: '⚠️ Không thể kết nối với AI' }]);
    } finally {
      setLoading(false);
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter') handleSend();
  };

  return (
    <>
      {}
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

      {}
      {open && (
        <div
          style={{
            position: 'fixed',
            bottom: '90px',
            left: '20px',
            width: '350px',
            height: '500px',
            backgroundColor: '#fff',
            borderRadius: '8px',
            boxShadow: '0 4px 12px rgba(0,0,0,0.2)',
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