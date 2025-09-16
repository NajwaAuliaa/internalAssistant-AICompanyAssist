import React from 'react';
import { Package, FileText, Upload, MessageSquare, ListChecks, ClipboardList } from 'lucide-react';

function Sidebar({ active, onChange }) {
  return (
    <div className="w-64 h-screen bg-gray-900 text-white flex flex-col p-4">
      <h2 className="text-xl font-semibold mb-6">Menu</h2>

      <div className="mb-4">
        <p className="text-gray-400 text-sm mb-2">Internal Assistant</p>

        <button
          className={`flex items-center gap-2 px-4 py-2 rounded-lg mb-1 ${
            active === 'upload' ? 'bg-gray-700' : 'hover:bg-gray-800'
          }`}
          onClick={() => onChange('upload')}
        >
          <Upload size={18} /> Upload & Index
        </button>

        <button
          className={`flex items-center gap-2 px-4 py-2 rounded-lg mb-1 ${
            active === 'rag' ? 'bg-gray-700' : 'hover:bg-gray-800'
          }`}
          onClick={() => onChange('rag')}
        >
          <MessageSquare size={18} /> RAG Chat
        </button>

        <button
          className={`flex items-center gap-2 px-4 py-2 rounded-lg mb-1 ${
            active === 'project' ? 'bg-gray-700' : 'hover:bg-gray-800'
          }`}
          onClick={() => onChange('project')}
        >
          <ClipboardList size={18} /> Project Management
        </button>

        <button
          className={`flex items-center gap-2 px-4 py-2 rounded-lg ${
            active === 'todo' ? 'bg-gray-700' : 'hover:bg-gray-800'
          }`}
          onClick={() => onChange('todo')}
        >
          <ListChecks size={18} /> Smart To-Do
        </button>
      </div>

      <hr className="border-gray-700 my-4" />

      <button 
        className="flex items-center gap-2 px-4 py-2 rounded-lg mb-2 opacity-50 cursor-not-allowed"
        disabled
      >
        <Package size={18} /> Product Recommendation
      </button>

      <button 
        className="flex items-center gap-2 px-4 py-2 rounded-lg opacity-50 cursor-not-allowed"
        disabled
      >
        <FileText size={18} /> Contract Risk Detector
      </button>
    </div>
  );
}

export default Sidebar;
