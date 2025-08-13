import { useEffect, useRef } from 'react';
import styles from '../styles/ChatBox.module.css';

function ChatBox({ messages, input, onInputChange, onSend, onKeyDown, loading }) {
  const messagesEndRef = useRef(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, loading]);

  return (
    <div className={styles.chatContainer}>
      <div className={styles.header}>ChatBot</div>

      <div className={styles.messages}>
        {messages.map((msg, idx) => (
          <div
            key={idx}
            className={`${styles.message} ${msg.sender === 'user' ? styles.user : styles.bot}`}
          >
            <span className={styles.icon}>
              {msg.sender === 'user' ? '👤' : '🤖'}
            </span>

            <div className={styles.messageBubble}>
              {/* text (nếu có) */}
              {msg.text && <div>{msg.text}</div>}

              {/* image (nếu có) */}
              {msg.imageUrl && (
                <a href={msg.imageUrl} target="_blank" rel="noreferrer">
                  <img
                    src={msg.imageUrl}
                    alt="capture"
                    className={styles.messageImage}
                    loading="lazy"
                  />
                </a>
              )}
            </div>
          </div>
        ))}

        {loading && (
          <div className={`${styles.message} ${styles.bot}`}>
            <span className={styles.icon}>🤖</span>
            <div className={styles.messageBubble}>
              <em>Bot is typing...</em>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      <div className={styles.inputArea}>
        <input
          type="text"
          className={styles.inputField}
          placeholder="Type a message..."
          value={input}
          onChange={onInputChange}
          onKeyDown={onKeyDown}
          disabled={loading}
        />
        <button
          className={styles.sendButton}
          onClick={onSend}
          disabled={loading}
        >
          ✈️
        </button>
      </div>
    </div>
  );
}

export default ChatBox;