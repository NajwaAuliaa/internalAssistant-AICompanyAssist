import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { useChat } from '../contexts/chatcontext';
import MarkdownRenderer from './MarkdownRenderer';
import { Button } from './ui/button';
import { Card, CardContent, CardHeader, CardTitle } from './ui/card';
import { Textarea } from './ui/textarea';

const API_BASE = 'http://localhost:8001';

function TodoTab() {
  const { messages, setMessages } = useChat('todo');
  const [inputMessage, setInputMessage] = useState('');
  const [loading, setLoading] = useState(false);
  const [examples, setExamples] = useState([]);
  const [suggestions, setSuggestions] = useState('');

  useEffect(() => {
    loadExamples();
    loadSuggestions();
  }, []);

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
    <div className="p-6 space-y-6">
      <Card>
        <CardHeader>
          <CardTitle>Smart Microsoft To-Do Assistant</CardTitle>
          <p className="text-muted-foreground"><strong>Powered by Azure OpenAI</strong> - Chat dengan AI untuk mengelola To-Do Anda menggunakan bahasa natural!</p>
        </CardHeader>
        <CardContent>
          <p className="text-muted-foreground">Anda sudah login dan dapat menggunakan semua fitur Todo management.</p>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>AI-Enhanced Features</CardTitle>
        </CardHeader>
        <CardContent>
          <ul className="space-y-2 text-sm">
            <li><strong>Natural Language Understanding</strong> - Gunakan bahasa sehari-hari</li>
            <li><strong>Smart Task Matching</strong> - AI akan mencari task yang Anda maksud</li>
            <li><strong>Intelligent Insights</strong> - Analisis produktivitas dan suggestions</li>
            <li><strong>Context-Aware Responses</strong> - Memahami konteks dan intent Anda</li>
          </ul>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Chat dengan Smart To-Do Assistant</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            <div className="h-96 overflow-y-auto space-y-4 p-4 border rounded-md">
              {messages.map((message, index) => (
                <div key={index} className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                  <div className={`max-w-xs lg:max-w-md px-4 py-2 rounded-lg ${
                    message.role === 'user' 
                      ? 'bg-primary text-primary-foreground' 
                      : 'bg-muted text-muted-foreground'
                  }`}>
                    {message.role === 'assistant' ? (
                      <MarkdownRenderer content={message.content} />
                    ) : (
                      <div className="whitespace-pre-wrap">{message.content}</div>
                    )}
                  </div>
                </div>
              ))}
              {loading && (
                <div className="flex justify-start">
                  <div className="bg-muted px-4 py-2 rounded-lg">
                    <em>Processing...</em>
                  </div>
                </div>
              )}
            </div>

            <div className="flex space-x-2">
              <Textarea
                value={inputMessage}
                onChange={(e) => setInputMessage(e.target.value)}
                onKeyPress={handleKeyPress}
                placeholder="Contoh: 'Analisis produktivitas saya' atau 'Buatkan task review laporan deadline besok'"
                rows={3}
                className="flex-1"
              />
              <Button 
                onClick={sendMessage}
                disabled={loading || !inputMessage.trim()}
              >
                Send
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Quick Actions (AI-Enhanced)</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 gap-2">
            {quickActions.map((action, index) => (
              <Button
                key={index}
                onClick={() => handleQuickAction(action)}
                variant="outline"
                className="text-left justify-start h-auto p-3"
              >
                {action.substring(0, 30)}...
              </Button>
            ))}
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Contoh & Quick Actions</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div>
              <h4 className="font-semibold mb-3">Contoh Natural Language:</h4>
              <div className="space-y-2">
                {examples.map((example, index) => (
                  <div key={index} className="text-sm text-muted-foreground">
                    • {example}
                  </div>
                ))}
              </div>
            </div>
            
            <div>
              <h4 className="font-semibold mb-3">Smart Suggestions:</h4>
              <div className="text-sm text-muted-foreground whitespace-pre-wrap">
                {suggestions}
              </div>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

export default TodoTab;