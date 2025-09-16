import React, { useState } from "react";
import axios from "axios";
import { useChat } from "../contexts/chatcontext";
import MarkdownRenderer from './MarkdownRenderer';

const API_BASE = process.env.REACT_APP_API_URL || "http://localhost:8001";

function RAGChatTab() {
  const { messages, setMessages } = useChat('rag');
  const [inputMessage, setInputMessage] = useState("");
  const [loading, setLoading] = useState(false);

  const sendMessage = async () => {
    if (!inputMessage.trim()) return;

    const userMessage = { role: "user", content: inputMessage, timestamp: new Date().toISOString() };
    setMessages([...messages, userMessage]);
    setInputMessage("");
    setLoading(true);

    try {
      const response = await axios.post(`${API_BASE}/rag-chat`, {
        message: inputMessage,
      });

      const assistantMessage = {
        role: "assistant",
        content: response.data.answer,
        timestamp: new Date().toISOString()
      };
      setMessages([...messages, userMessage, assistantMessage]);
    } catch (error) {
      const errorMessage = {
        role: "assistant",
        content: `Error: ${error.response?.data?.detail || error.message}`,
        timestamp: new Date().toISOString()
      };
      setMessages([...messages, userMessage, errorMessage]);
    } finally {
      setLoading(false);
    }
  };

  const handleKeyPress = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  return (
    <div className="rag-chat-tab">
      <p>Tanya dokumen yang sudah di-index.</p>

      <div className="chat-container">
        <div className="chat-messages">
          {messages.map((message, index) => (
            <div key={index} className={`message ${message.role}`}>
              <div className="message-content">
                {message.role === 'assistant' ? (
                  <MarkdownRenderer content={message.content} />
                ) : (
                  <pre>{message.content}</pre>
                )}
              </div>
            </div>
          ))}
          {loading && (
            <div className="message assistant">
              <div className="message-content">
                <em>Thinking...</em>
              </div>
            </div>
          )}
        </div>

        <div className="chat-input-container">
          <textarea
            value={inputMessage}
            onChange={(e) => setInputMessage(e.target.value)}
            onKeyPress={handleKeyPress}
            placeholder="Tanyakan SOP/kebijakan…"
            rows={3}
          />
          <button
            onClick={sendMessage}
            disabled={loading || !inputMessage.trim()}
            className="btn-primary"
          >
            Send
          </button>
        </div>
      </div>
    </div>
  );
}

export default RAGChatTab;