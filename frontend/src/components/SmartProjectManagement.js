import React, { useState, useEffect } from 'react';
import { Send, List, BarChart3, AlertTriangle, Target, Calendar, MessageCircle } from 'lucide-react';
import { useChat } from '../contexts/chatcontext';
import MarkdownRenderer from './MarkdownRenderer';

const API_BASE = 'http://localhost:8001';

function SmartProjectApp() {
  const [projects, setProjects] = useState([]);
  const [selectedProject, setSelectedProject] = useState('');
  const [projectDetail, setProjectDetail] = useState(null);

  const { messages: chatMessages, setMessages: setChatMessages } = useChat('project');
  const [currentMessage, setCurrentMessage] = useState('');
  const [chatLoading, setChatLoading] = useState(false);
  
  const [loading, setLoading] = useState({
    projects: false,
    projectDetail: false
  });

  useEffect(() => {
    fetchProjects();
  }, []);

  const fetchProjects = async () => {
    setLoading(prev => ({ ...prev, projects: true }));
    try {
      const response = await fetch(`${API_BASE}/projects`);
      const data = await response.json();
      
      let projectList = [];
      if (data.projects) {
        if (Array.isArray(data.projects)) {
          projectList = data.projects;
        } else if (typeof data.projects === 'string') {
          try {
            const parsed = JSON.parse(data.projects);
            projectList = Array.isArray(parsed) ? parsed : [data.projects];
          } catch {
            projectList = [data.projects];
          }
        } else {
          projectList = Object.values(data.projects);
        }
      }
      
      setProjects(projectList);
      
    } catch (error) {
      console.error('Error fetching projects:', error);
      setProjects([]);
    }
    setLoading(prev => ({ ...prev, projects: false }));
  };

  const fetchProjectDetail = async (projectName) => {
    setLoading(prev => ({ ...prev, projectDetail: true }));
    setSelectedProject(projectName);
    try {
      const response = await fetch(`${API_BASE}/projects/${encodeURIComponent(projectName)}`);
      const data = await response.json();
      setProjectDetail(data.project_detail || data);
    } catch (error) {
      setProjectDetail({ error: 'Failed to fetch project detail' });
    }
    setLoading(prev => ({ ...prev, projectDetail: false }));
  };

  const sendChatMessage = async (message = currentMessage) => {
    if (!message.trim()) return;

    const userMessage = {
      role: 'user',
      content: message,
      timestamp: new Date().toISOString()
    };

    setChatMessages([...chatMessages, userMessage]);
    setCurrentMessage('');
    setChatLoading(true);

    try {
      const response = await fetch(`${API_BASE}/project-chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message })
      });

      const data = await response.json();
      
      const assistantMessage = {
        role: 'assistant',
        content: data.answer || 'No response received',
        timestamp: new Date().toISOString()
      };

      setChatMessages([...chatMessages, userMessage, assistantMessage]);
    } catch (error) {
      console.error('Chat error:', error);
      const errorMessage = {
        role: 'assistant',
        content: 'Error processing your request. Please try again.',
        timestamp: new Date().toISOString(),
        error: true
      };
      setChatMessages([...chatMessages, userMessage, errorMessage]);
    }
    
    setChatLoading(false);
  };

  const handleQuickAction = async (action) => {
    const actionMessages = {
      'list project': 'Tampilkan semua project dengan status dan progress lengkap',
      'portfolio overview': 'Berikan overview progress semua project dengan insight dan recommendations',
      'problem analysis': 'Identifikasi project yang bermasalah atau tertinggal dengan analisis root cause',
      'priority ranking': 'Ranking project berdasarkan prioritas dan urgency dengan actionable recommendations',
      'weekly summary': 'Buatkan weekly summary semua project dengan achievement dan next steps'
    };

    const message = actionMessages[action] || action;
    await sendChatMessage(message);
  };

  const formatTimestamp = (timestamp) => {
    return new Date(timestamp).toLocaleTimeString('id-ID', { 
      hour: '2-digit', 
      minute: '2-digit' 
    });
  };

  const renderProjects = () => {
    if (loading.projects) {
      return <div className="text-center py-4">Loading projects...</div>;
    }

    if (!Array.isArray(projects)) {
      return (
        <div className="text-gray-500 text-center py-4">
          <div>Invalid projects data format</div>
          <button 
            onClick={fetchProjects}
            className="text-blue-600 underline mt-2"
          >
            Retry
          </button>
        </div>
      );
    }

    if (projects.length === 0) {
      return (
        <div className="text-gray-500 text-center py-4">
          <div>No projects found</div>
          <button 
            onClick={fetchProjects}
            className="text-blue-600 underline mt-2"
          >
            Refresh
          </button>
        </div>
      );
    }

    return (
      <div className="space-y-2">
        {projects.map((project, idx) => (
          <button
            key={idx}
            onClick={() => fetchProjectDetail(project)}
            className={`w-full text-left p-3 rounded-lg transition-colors ${
              selectedProject === project 
                ? 'bg-blue-100 border-2 border-blue-500' 
                : 'bg-gray-50 hover:bg-gray-100 border-2 border-transparent'
            }`}
          >
            <span className="font-medium">{project}</span>
          </button>
        ))}
      </div>
    );
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100">
      <div className="container mx-auto px-4 py-6">
        <div className="mb-8 text-center">
          <h1 className="text-4xl font-bold text-gray-800 mb-2">Smart Project Management</h1>
          <p className="text-lg text-gray-600">AI-Powered Project Analysis & Insights</p>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="lg:col-span-1">
            <div className="bg-white rounded-lg shadow-md p-6 mb-6">
              <h3 className="text-xl font-semibold mb-4 flex items-center">
                <List className="mr-2" size={20} />
                Projects ({Array.isArray(projects) ? projects.length : 0})
              </h3>
              
              {renderProjects()}
            </div>

            <div className="bg-white rounded-lg shadow-md p-6">
              <h4 className="text-lg font-semibold mb-4">Quick Actions</h4>
              <div className="space-y-2">
                <button 
                  onClick={() => handleQuickAction('list project')}
                  disabled={chatLoading}
                  className="w-full flex items-center space-x-2 p-2 text-left bg-blue-50 hover:bg-blue-100 rounded-lg disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  <List size={16} />
                  <span>List All Projects</span>
                </button>
                <button 
                  onClick={() => handleQuickAction('portfolio overview')}
                  disabled={chatLoading}
                  className="w-full flex items-center space-x-2 p-2 text-left bg-green-50 hover:bg-green-100 rounded-lg disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  <BarChart3 size={16} />
                  <span>Portfolio Overview</span>
                </button>
                <button 
                  onClick={() => handleQuickAction('problem analysis')}
                  disabled={chatLoading}
                  className="w-full flex items-center space-x-2 p-2 text-left bg-orange-50 hover:bg-orange-100 rounded-lg disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  <AlertTriangle size={16} />
                  <span>Problem Analysis</span>
                </button>
                <button 
                  onClick={() => handleQuickAction('priority ranking')}
                  disabled={chatLoading}
                  className="w-full flex items-center space-x-2 p-2 text-left bg-purple-50 hover:bg-purple-100 rounded-lg disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  <Target size={16} />
                  <span>Priority Ranking</span>
                </button>
                <button 
                  onClick={() => handleQuickAction('weekly summary')}
                  disabled={chatLoading}
                  className="w-full flex items-center space-x-2 p-2 text-left bg-indigo-50 hover:bg-indigo-100 rounded-lg disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  <Calendar size={16} />
                  <span>Weekly Summary</span>
                </button>
              </div>
            </div>
          </div>

          <div className="lg:col-span-2">
            <div className="bg-white rounded-lg shadow-md flex flex-col h-[600px]">
              <div className="flex items-center justify-between p-4 border-b">
                <h3 className="text-xl font-semibold flex items-center">
                  <MessageCircle className="mr-2" size={20} />
                  Smart Project Chat
                </h3>
              </div>

              <div className="flex-1 overflow-y-auto p-4 space-y-4">
                {chatMessages.map((msg, idx) => (
                  <div key={idx} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                    <div className={`max-w-xs lg:max-w-md px-4 py-2 rounded-lg ${
                      msg.role === 'user' 
                        ? 'bg-blue-600 text-white' 
                        : msg.error 
                        ? 'bg-red-50 border border-red-200 text-red-800'
                        : 'bg-gray-100 text-gray-800'
                    }`}>
                      {msg.role === 'assistant' ? (
                        <MarkdownRenderer content={msg.content} />
                      ) : (
                        <div className="whitespace-pre-wrap">{msg.content}</div>
                      )}
                      <div className={`text-xs mt-1 ${
                        msg.role === 'user' ? 'text-blue-100' : 'text-gray-500'
                      }`}>
                        {formatTimestamp(msg.timestamp)}
                        {msg.quickAction && <span className="ml-2 italic">Quick Action</span>}
                      </div>
                    </div>
                  </div>
                ))}
                
                {chatLoading && (
                  <div className="flex justify-start">
                    <div className="bg-gray-100 rounded-lg px-4 py-2">
                      <div className="flex space-x-1">
                        <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce"></div>
                        <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{animationDelay: '0.1s'}}></div>
                        <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{animationDelay: '0.2s'}}></div>
                      </div>
                    </div>
                  </div>
                )}
              </div>

              <div className="p-4 border-t">
                <div className="flex space-x-2">
                  <input
                    type="text"
                    value={currentMessage}
                    onChange={(e) => setCurrentMessage(e.target.value)}
                    onKeyPress={(e) => e.key === 'Enter' && !e.shiftKey && sendChatMessage()}
                    placeholder="Ask about your projects..."
                    disabled={chatLoading}
                    className="flex-1 border border-gray-300 rounded-lg px-4 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:bg-gray-100"
                  />
                  <button
                    onClick={() => sendChatMessage()}
                    disabled={chatLoading || !currentMessage.trim()}
                    className="bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center"
                  >
                    <Send size={16} />
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>

        {projectDetail && (
          <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
            <div className="bg-white rounded-lg max-w-2xl max-h-[80vh] overflow-auto p-6">
              <div className="flex justify-between items-center mb-4">
                <h3 className="text-xl font-semibold">Project Detail: {selectedProject}</h3>
                <button 
                  onClick={() => setProjectDetail(null)}
                  className="text-gray-500 hover:text-gray-700 text-xl font-bold"
                >
                  ×
                </button>
              </div>
              <div className="whitespace-pre-wrap text-sm">
                {loading.projectDetail ? (
                  <div className="text-center py-8">Loading project detail...</div>
                ) : (
                  typeof projectDetail === 'object' ? 
                    JSON.stringify(projectDetail, null, 2) : 
                    projectDetail
                )}
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export default SmartProjectApp;