import React, { useState } from 'react';
import { Package, FileText, Upload, MessageSquare, ListChecks, ClipboardList, Menu, X, ChevronDown, ChevronRight, Bot } from 'lucide-react';
import { Button } from './ui/button';
import { Card } from './ui/card';

function Sidebar({ active, onChange }) {
  const [isOpen, setIsOpen] = useState(true);
  const [isInternalAssistantOpen, setIsInternalAssistantOpen] = useState(true);

  return (
    <div 
      className={`${isOpen ? 'w-64' : 'w-16'} h-screen flex flex-col transition-all duration-300 rounded-none border-r bg-sidebar text-sidebar-foreground border-sidebar-border shadow-sm`}
    >
      {/* Header */}
      <div className="p-4 border-b border-sidebar-border">
        <div className="flex items-center justify-between">
          {isOpen && <h2 className="text-sm font-semibold text-sidebar-foreground flex-1 mr-2">AI Document Workflow</h2>}
          <Button
            variant="sidebar-ghost"
            className="flex-shrink-0 w-12 h-12 p-1 hover:bg-sidebar-accent"
            onClick={() => setIsOpen(!isOpen)}
          >
            {isOpen ? <X size={24} /> : <Menu size={24} />}
          </Button>
        </div>
      </div>

      {/* Menu Items */}
      <div className="flex-1 p-2 space-y-1">
        {/* Internal Assistant Section */}
        <Button
          variant="sidebar-ghost"
          className={`w-full ${isOpen ? 'justify-start' : 'justify-center'} h-12`}
          onClick={() => setIsInternalAssistantOpen(!isInternalAssistantOpen)}
        >
          {isOpen ? (
            <div className="flex items-center w-full">
              <div className="w-5 flex justify-center">
                {isInternalAssistantOpen ? <ChevronDown size={16} /> : <ChevronRight size={16} />}
              </div>
              <div className="w-5 flex justify-center ml-2">
                <Bot size={20} />
              </div>
              <span className="ml-3">Internal Assistant</span>
            </div>
          ) : (
            <Bot size={20} />
          )}
        </Button>

        {/* Sub-menu items */}
        {isInternalAssistantOpen && isOpen && (
          <div className="space-y-1">
            <Button
              variant={active === 'upload' ? 'sidebar-default' : 'sidebar-ghost'}
              className="w-full justify-start h-10 text-sm"
              onClick={() => onChange('upload')}
            >
              <div className="flex items-center w-full">
                <div className="w-5"></div>
                <div className="w-5 flex justify-center ml-2">
                  <Upload size={16} />
                </div>
                <span className="ml-3">Upload & Index</span>
              </div>
            </Button>

            <Button
              variant={active === 'rag' ? 'sidebar-default' : 'sidebar-ghost'}
              className="w-full justify-start h-10 text-sm"
              onClick={() => onChange('rag')}
            >
              <div className="flex items-center w-full">
                <div className="w-5"></div>
                <div className="w-5 flex justify-center ml-2">
                  <MessageSquare size={16} />
                </div>
                <span className="ml-3">RAG Chat</span>
              </div>
            </Button>

            <Button
              variant={active === 'project' ? 'sidebar-default' : 'sidebar-ghost'}
              className="w-full justify-start h-10 text-sm"
              onClick={() => onChange('project')}
            >
              <div className="flex items-center w-full">
                <div className="w-5"></div>
                <div className="w-5 flex justify-center ml-2">
                  <ClipboardList size={16} />
                </div>
                <span className="ml-3">Project Management</span>
              </div>
            </Button>

            <Button
              variant={active === 'todo' ? 'sidebar-default' : 'sidebar-ghost'}
              className="w-full justify-start h-10 text-sm"
              onClick={() => onChange('todo')}
            >
              <div className="flex items-center w-full">
                <div className="w-5"></div>
                <div className="w-5 flex justify-center ml-2">
                  <ListChecks size={16} />
                </div>
                <span className="ml-3">Smart To-Do</span>
              </div>
            </Button>
          </div>
        )}

        {/* Other main menu items */}
        <Button 
          variant="sidebar-ghost"
          className={`w-full ${isOpen ? 'justify-start' : 'justify-center'} h-12 opacity-50 cursor-not-allowed`}
          disabled
        >
          {isOpen ? (
            <div className="flex items-center w-full">
              <div className="w-5"></div>
              <div className="w-5 flex justify-center ml-2">
                <Package size={20} />
              </div>
              <span className="ml-3">Product Recommendation</span>
            </div>
          ) : (
            <Package size={20} />
          )}
        </Button>

        <Button 
          variant="sidebar-ghost"
          className={`w-full ${isOpen ? 'justify-start' : 'justify-center'} h-12 opacity-50 cursor-not-allowed`}
          disabled
        >
          {isOpen ? (
            <div className="flex items-center w-full">
              <div className="w-5"></div>
              <div className="w-5 flex justify-center ml-2">
                <FileText size={20} />
              </div>
              <span className="ml-3">Contract Risk Detector</span>
            </div>
          ) : (
            <FileText size={20} />
          )}
        </Button>
      </div>
    </div>
  );
}

export default Sidebar;