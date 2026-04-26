import { Link } from 'react-router-dom';
import { useStore } from '../stores';
import { useTaskWebSocket } from '../hooks/useTaskWebSocket';
import ChatComponent from '../components/Chat';
import TaskLog from '../components/TaskLog';
import ErrorLog from '../components/ErrorLog';
import { Command, Folder, Settings, Plus } from 'lucide-react';

export default function ChatPage() {
  const activeTask = useStore((state) => state.activeTask);
  
  // Initialize WebSocket connection for the active task
  useTaskWebSocket(activeTask.id);

  return (
    <div className="flex h-screen overflow-hidden bg-[#0f0f0f]">
      {/* Left Sidebar */}
      <div className="w-[250px] shrink-0 border-r border-[#2d2d2d] flex flex-col bg-[#121212]">
        <div className="p-4 border-b border-[#2d2d2d] flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg bg-gradient-to-tr from-purple-600 to-blue-500 flex items-center justify-center shadow-lg">
            <Command className="text-white w-4 h-4" />
          </div>
          <span className="font-semibold text-gray-100 tracking-wide">Cammina AI</span>
        </div>
        
        <div className="p-4">
          <button className="w-full bg-purple-600 hover:bg-purple-700 text-white flex items-center justify-center gap-2 rounded-lg py-2.5 text-sm font-medium transition-colors shadow-lg shadow-purple-500/20">
            <Plus className="w-4 h-4" />
            New Task
          </button>
        </div>

        <div className="flex-1 overflow-y-auto px-2">
          <div className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2 px-2 mt-4">Recent Projects</div>
          <div className="space-y-1">
            <Link to="/projects" className="flex items-center gap-3 px-2 py-2 rounded-lg text-sm text-gray-300 hover:bg-[#2d2d2d] hover:text-white transition-colors">
              <Folder className="w-4 h-4 text-purple-400" />
              Web UI Setup
            </Link>
            <Link to="/projects" className="flex items-center gap-3 px-2 py-2 rounded-lg text-sm text-gray-300 hover:bg-[#2d2d2d] hover:text-white transition-colors">
              <Folder className="w-4 h-4 text-blue-400" />
              API Integration
            </Link>
          </div>
        </div>

        <div className="p-4 border-t border-[#2d2d2d]">
          <Link to="/settings" className="flex items-center gap-3 px-2 py-2 rounded-lg text-sm text-gray-400 hover:bg-[#2d2d2d] hover:text-white transition-colors">
            <Settings className="w-4 h-4" />
            Settings
          </Link>
        </div>
      </div>

      {/* Main Chat Area */}
      <div className="flex-1 flex flex-col min-w-0">
        <div className="flex-1 overflow-hidden relative">
          <ChatComponent />
        </div>
        
        {/* Bottom Error Panel - visible only if errors exist or optionally collapsable */}
        <div className="shrink-0 max-h-48">
          <ErrorLog />
        </div>
      </div>

      {/* Right Panel */}
      <div className="w-[300px] shrink-0 border-l border-[#2d2d2d]">
        <TaskLog />
      </div>
    </div>
  );
}
