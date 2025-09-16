import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { useChat } from '../contexts/chatcontext';
import MarkdownRenderer from './MarkdownRenderer';

const API_BASE = process.env.REACT_APP_API_URL || 'http://localhost:8001' ;

function TodoTab() {
  const { messages, setMessages } = useChat('todo');
  const [inputMessage, setInputMessage] = useState('');
  const [loading, setLoading] = useState(false);
  const [loginStatus, setLoginStatus] = useState('Checking...');
  const [examples, setExamples] = useState([]);
  const [suggestions, setSuggestions] = useState('');

  useEffect(() => {
    checkLoginStatus();
    loadExamples();
    loadSuggestions();
  }, []);

  const checkLoginStatus = async () => {
    try {
      const response = await axios.get(`${API_BASE}/todo/login-status`);
      setLoginStatus(response.data.status);
    } catch (error) {
      setLoginStatus('Error checking status');
    }
  };

  const handleLogin = async () => {
    try {
      const response = await axios.get(`${API_BASE}/todo/login-url`);
      window.open(response.data.auth_url, '_blank');
      setLoginStatus('Browser will open for Microsoft login. After login, return here and click Refresh Status.');
    } catch (error) {
      setLoginStatus(`Error: ${error.message}`);
    }
  };

  const loadExamples = async () => {
    try {
      const response = await axios.get(`${API_BASE}/todo/examples`);
      setExamples(response.data.examples);
    } catch (error) {
      console.error('Error loading examples:', error);
    }
  };

  const loadSuggestions = async () => {
    try {
      const response = await axios.get(`${API_BASE}/todo/suggestions`);
      setSuggestions(response.data.suggestions);
    } catch (error) {
      console.error('Error loading suggestions:', error);
    }
  };

  const sendMessage = async () => {
    if (!inputMessage.trim()) return;

    const userMessage = { role: 'user', content: inputMessage, timestamp: new Date().toISOString() };
    setMessages([...messages, userMessage]);
    setInputMessage('');
    setLoading(true);

    try {
      const response = await axios.post(`${API_BASE}/todo-chat`, {
        message: inputMessage
      });
      
      const assistantMessage = { 
        role: 'assistant', 
        content: response.data.answer,
        timestamp: new Date().toISOString()
      };
      setMessages([...messages, userMessage, assistantMessage]);
    } catch (error) {
      const errorMessage = {
        role: 'assistant',
        content: `Error: ${error.response?.data?.detail || error.message}`,
        timestamp: new Date().toISOString()
      };
      setMessages([...messages, userMessage, errorMessage]);
    } finally {
      setLoading(false);
    }
  };

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  const quickActions = [
    'Analisis semua task saya dan berikan insight tentang produktivitas',
    'Tampilkan task yang urgent dan deadline hari ini dengan prioritas',
    'Buatkan laporan produktivitas saya berdasarkan task yang sudah selesai',
    'Prioritaskan task saya berdasarkan deadline dan urgency',
    'Tunjukkan semua task yang overdue dan beri saran penanganan',
    'Berikan saran untuk mengoptimalkan manajemen task saya',
    'Buatkan summary task yang diselesaikan minggu ini',
    'Bantu saya planning task baru untuk project yang akan datang'
  ];

  const handleQuickAction = (action) => {
    setInputMessage(action);
  };

  return (
    <div className="todo-tab">
      <h2>Smart Microsoft To-Do Assistant</h2>
      <p><strong>Powered by Azure OpenAI</strong> - Chat dengan AI untuk mengelola To-Do Anda menggunakan bahasa natural!</p>

      {/* Login Status Section */}
      <div className="login-section">
        <div className="login-status">
          <label>Status Login:</label>
          <div className="status-text">{loginStatus}</div>
        </div>
        <div className="login-buttons">
          <button onClick={handleLogin} className="btn-secondary">
            Login ke Microsoft
          </button>
          <button onClick={checkLoginStatus} className="btn-secondary">
            Refresh Status
          </button>
        </div>
      </div>

      {/* AI Info Banner */}
      <div className="ai-info">
        <h3>AI-Enhanced Features:</h3>
        <ul>
          <li><strong>Natural Language Understanding</strong> - Gunakan bahasa sehari-hari</li>
          <li><strong>Smart Task Matching</strong> - AI akan mencari task yang Anda maksud</li>
          <li><strong>Intelligent Insights</strong> - Analisis produktivitas dan suggestions</li>
          <li><strong>Context-Aware Responses</strong> - Memahami konteks dan intent Anda</li>
        </ul>
      </div>

      {/* Main Chat Interface */}
      <div className="chat-container">
        <h3>Chat dengan Smart To-Do Assistant</h3>
        
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
                <em>Processing...</em>
              </div>
            </div>
          )}
        </div>

        <div className="chat-input-container">
          <textarea
            value={inputMessage}
            onChange={(e) => setInputMessage(e.target.value)}
            onKeyPress={handleKeyPress}
            placeholder="Contoh: 'Analisis produktivitas saya' atau 'Buatkan task review laporan deadline besok'"
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

      {/* Quick Actions */}
      <div className="quick-actions">
        <h4>Quick Actions (AI-Enhanced)</h4>
        <div className="quick-buttons">
          {quickActions.map((action, index) => (
            <button
              key={index}
              onClick={() => handleQuickAction(action)}
              className="btn-quick"
            >
              {action.substring(0, 30)}...
            </button>
          ))}
        </div>
      </div>

      {/* Examples and Suggestions */}
      <details className="examples-section">
        <summary>Contoh & Quick Actions</summary>
        
        <div className="examples-grid">
          <div className="examples-column">
            <h4>Contoh Natural Language:</h4>
            <div className="examples-list">
              {examples.map((example, index) => (
                <div key={index} className="example-item">
                  • {example}
                </div>
              ))}
            </div>
          </div>
          
          <div className="suggestions-column">
            <h4>Smart Suggestions:</h4>
            <div className="suggestions-content">
              <pre>{suggestions}</pre>
            </div>
          </div>
        </div>
      </details>
    </div>
  );
}

export default TodoTab;