import React, { useState, useEffect } from 'react';
import Sidebar from './components/Sidebar';
import UploadTab from './components/UploadTab';
import RAGChatTab from './components/RAGChatTab';
import SmartProjectApp from './components/SmartProjectManagement';
import TodoTab from './components/TodoTab';
import LoginPage from './components/login';
import { ChatProvider } from './contexts/chatcontext';
import './App.css';

function App() {
  const [activeTab, setActiveTab] = useState('upload');
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [loading, setLoading] = useState(true);

  const handleLogout = async () => {
    try {
      await fetch('http://localhost:8001/auth/logout', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        }
      });
      setIsAuthenticated(false);
    } catch (error) {
      console.error('Logout error:', error);
      // Force logout even if API call fails
      setIsAuthenticated(false);
    }
  };

  useEffect(() => {
    const checkAuth = async () => {
      try {
        // Check both project and todo status
        const [projectRes, todoRes] = await Promise.all([
          fetch('http://localhost:8001/project/status'),
          fetch('http://localhost:8001/todo/login-status')
        ]);
        
        const projectData = await projectRes.json();
        const todoData = await todoRes.json();
        
        // User authenticated if either service is authenticated
        setIsAuthenticated(projectData.authenticated || todoData.status === 'Authenticated');
      } catch (error) {
        setIsAuthenticated(false);
      } finally {
        setLoading(false);
      }
    };
    
    checkAuth();
    
    // Check auth status periodically to catch login completion
    const interval = setInterval(checkAuth, 2000);
    
    return () => clearInterval(interval);
  }, []);

  if (loading) {
    return <div className="flex items-center justify-center h-screen">Loading...</div>;
  }

  if (!isAuthenticated) {
    return <LoginPage />;
  }

  return (
    <div className="flex h-screen bg-gray-50">
      <Sidebar active={activeTab} onChange={setActiveTab} />
      <main className="flex-1 flex flex-col overflow-hidden">
        <header className="border-b bg-white px-6 py-4 flex items-center justify-between shadow-sm">
          <div className="flex items-center gap-3">
            <img src="/softwareone.png" alt="SoftwareOne" className="h-8" />
            <div className="h-8 w-px bg-gray-300"></div>
            <h1 className="text-xl font-semibold text-gray-900 mt-7">
              AI Document Workflow
            </h1>
          </div>
          <button
            onClick={handleLogout}
            className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500"
          >
            Logout
          </button>
        </header>

        <div className="flex-1 overflow-auto">
          {activeTab === 'upload' && <UploadTab />}

          {activeTab === 'rag' && (
            <ChatProvider type="rag">
              <RAGChatTab />
            </ChatProvider>
          )}

          {activeTab === 'todo' && (
            <ChatProvider type="todo">
              <TodoTab />
            </ChatProvider>
          )}

          {activeTab === 'project' && (
            <ChatProvider type="project">
              <SmartProjectApp />
            </ChatProvider>
          )}
        </div>
      </main>
    </div>
  );
}

export default App;
