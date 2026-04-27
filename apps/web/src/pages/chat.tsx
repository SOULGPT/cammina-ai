import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { useStore } from '../stores';
import { useTaskWebSocket } from '../hooks/useTaskWebSocket';
import ChatComponent from '../components/Chat';
import TaskLog from '../components/TaskLog';
import ErrorLog from '../components/ErrorLog';
import { Command, Folder, Settings, Plus, LogOut, RotateCcw, ArrowRight } from 'lucide-react';
import { supabase } from '../lib/supabase';
import { motion, AnimatePresence } from 'framer-motion';

export default function ChatPage() {
  const activeTask = useStore((state) => state.activeTask);
  const selectedProject = useStore((state) => state.selectedProject);
  const setSelectedProject = useStore((state) => state.setSelectedProject);
  
  const [projects, setProjects] = useState<any[]>([]);
  const [showNewProjectModal, setShowNewProjectModal] = useState(false);
  const [newProjectName, setNewProjectName] = useState('');
  const [isRefreshing, setIsRefreshing] = useState(false);

  // Initialize WebSocket connection for the active task
  useTaskWebSocket(activeTask.id);

  const loadProjects = async () => {
    setIsRefreshing(true);
    try {
      const response = await fetch("/api/projects");
      const data = await response.json();
      setProjects(data.projects || []);
    } catch (e) {
      console.error("Failed to load projects:", e);
    } finally {
      setTimeout(() => setIsRefreshing(false), 500);
    }
  };

  useEffect(() => {
    loadProjects();
  }, []);

  const handleCreateProject = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newProjectName.trim()) return;

    try {
      const response = await fetch("/api/projects/create", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name: newProjectName.trim() })
      });
      const result = await response.json();
      if (result.success) {
        setNewProjectName('');
        setShowNewProjectModal(false);
        await loadProjects();
        setSelectedProject(result.name);
      }
    } catch (e) {
      console.error("Failed to create project:", e);
    }
  };

  return (
    <div className="flex h-screen overflow-hidden bg-[#0f0f0f]">
      {/* Left Sidebar */}
      <div className="w-[260px] shrink-0 border-r border-[#2d2d2d] flex flex-col bg-[#121212]">
        <div className="p-4 border-b border-[#2d2d2d] flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg bg-gradient-to-tr from-purple-600 to-blue-500 flex items-center justify-center shadow-lg">
            <Command className="text-white w-4 h-4" />
          </div>
          <span className="font-semibold text-gray-100 tracking-wide">Cammina AI</span>
        </div>
        
        <div className="p-4">
          <button 
            onClick={() => setShowNewProjectModal(true)}
            className="w-full bg-purple-600 hover:bg-purple-700 text-white flex items-center justify-center gap-2 rounded-lg py-2.5 text-sm font-medium transition-colors shadow-lg shadow-purple-500/20"
          >
            <Plus className="w-4 h-4" />
            New Task
          </button>
        </div>

        <div className="flex-1 overflow-y-auto px-2">
          <div className="flex items-center justify-between px-2 mt-4 mb-2">
            <div className="text-[10px] font-bold text-gray-500 uppercase tracking-widest">Recent Projects</div>
            <button 
              onClick={loadProjects}
              className={`text-gray-500 hover:text-white transition-all ${isRefreshing ? 'animate-spin' : ''}`}
            >
              <RotateCcw className="w-3 h-3" />
            </button>
          </div>
          
          <div className="space-y-0.5">
            {projects.length === 0 ? (
              <p className="text-xs text-gray-600 px-3 py-4 italic">No projects found</p>
            ) : (
              projects.map((project) => (
                <div
                  key={project.name}
                  className={`w-full flex items-center gap-1 group rounded-lg transition-all ${
                    selectedProject === project.name 
                      ? 'bg-purple-600/10 text-purple-400 border border-purple-500/20' 
                      : 'text-gray-400 hover:bg-[#1a1a1a] hover:text-gray-200 border border-transparent'
                  }`}
                >
                  <button
                    onClick={() => {
                      setSelectedProject(project.name);
                      window.history.pushState({}, '', `/chat?project=${project.name}`);
                    }}
                    className="flex-1 flex items-center gap-3 px-3 py-2 text-sm text-left truncate"
                  >
                    <Folder className={`w-4 h-4 shrink-0 ${selectedProject === project.name ? 'text-purple-400' : 'text-gray-500 group-hover:text-gray-400'}`} />
                    <span className="truncate">{project.name}</span>
                    {project.memory_count > 0 && (
                      <span className="bg-purple-600/20 text-purple-400 text-[10px] px-1.5 py-0.5 rounded-full border border-purple-500/20 font-bold">
                        {project.memory_count}
                      </span>
                    )}
                  </button>
                  <Link 
                    to={`/project/${project.name}`}
                    className="p-2 opacity-0 group-hover:opacity-100 hover:text-white transition-all"
                  >
                    <ArrowRight className="w-3.5 h-3.5" />
                  </Link>
                </div>
              ))
            )}
          </div>
        </div>

        <div className="p-4 border-t border-[#2d2d2d] space-y-1">
          <Link to="/settings" className="flex items-center gap-3 px-2 py-2 rounded-lg text-sm text-gray-400 hover:bg-[#2d2d2d] hover:text-white transition-colors">
            <Settings className="w-4 h-4" />
            Settings
          </Link>
          <button 
            onClick={() => supabase.auth.signOut()}
            className="w-full flex items-center gap-3 px-2 py-2 rounded-lg text-sm text-red-400 hover:bg-red-950/30 hover:text-red-300 transition-colors"
          >
            <LogOut className="w-4 h-4" />
            Sign Out
          </button>
        </div>
      </div>

      {/* Main Chat Area */}
      <div className="flex-1 flex flex-col min-w-0">
        <div className="flex-1 overflow-hidden relative">
          <ChatComponent />
        </div>
        
        {/* Bottom Error Panel */}
        <div className="shrink-0 max-h-48">
          <ErrorLog />
        </div>
      </div>

      {/* Right Panel */}
      <div className="w-[320px] shrink-0 border-l border-[#2d2d2d] bg-[#0d0d0d]">
        <TaskLog />
      </div>

      {/* New Project Modal */}
      <AnimatePresence>
        {showNewProjectModal && (
          <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm">
            <motion.div 
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.95 }}
              className="w-full max-w-md bg-[#1a1a1a] border border-[#2d2d2d] rounded-2xl p-6 shadow-2xl"
            >
              <h3 className="text-lg font-bold text-white mb-4">Create New Project</h3>
              <form onSubmit={handleCreateProject}>
                <div className="mb-6">
                  <label className="block text-[10px] font-bold text-gray-500 uppercase tracking-widest mb-2">Project Name</label>
                  <input
                    autoFocus
                    type="text"
                    value={newProjectName}
                    onChange={(e) => setNewProjectName(e.target.value)}
                    placeholder="e.g. backend-api, marketing-site"
                    className="w-full bg-[#0f0f0f] border border-[#2d2d2d] rounded-xl px-4 py-3 text-white focus:outline-none focus:border-purple-500 transition-all"
                  />
                </div>
                <div className="flex gap-3">
                  <button
                    type="button"
                    onClick={() => setShowNewProjectModal(false)}
                    className="flex-1 px-4 py-2.5 rounded-xl border border-[#2d2d2d] text-gray-400 hover:text-white hover:bg-[#2d2d2d] transition-all text-sm font-medium"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    className="flex-1 px-4 py-2.5 rounded-xl bg-purple-600 text-white hover:bg-purple-700 transition-all text-sm font-medium shadow-lg shadow-purple-500/20"
                  >
                    Create Project
                  </button>
                </div>
              </form>
            </motion.div>
          </div>
        )}
      </AnimatePresence>
    </div>
  );
}
