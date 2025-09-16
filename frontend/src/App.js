import React, { useState } from 'react';
import Sidebar from './components/Sidebar';
import UploadTab from './components/UploadTab';
import RAGChatTab from './components/RAGChatTab';
import SmartProjectApp from './components/SmartProjectManagement';
import TodoTab from './components/TodoTab';
import { ChatProvider } from './contexts/chatcontext';
import './App.css';

function App() {
  const [activeTab, setActiveTab] = useState('upload');

  return (
    <div className="flex h-screen bg-gray-100">
      {/* Sidebar */}
      <Sidebar active={activeTab} onChange={setActiveTab} />

      {/* Main Content */}
      <div className="flex-1 p-8 overflow-auto">
        <header className="flex justify-between items-center mb-8">
          <h1 className="text-2xl font-bold">AI Internal Assistant</h1>
        </header>

        <div className="space-y-6">
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
      </div>
    </div>
  );
}

export default App;
