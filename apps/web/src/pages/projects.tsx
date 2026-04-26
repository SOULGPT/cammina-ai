import { Link } from 'react-router-dom';
import { useStore } from '../stores';
import { formatDistanceToNow } from 'date-fns';
import { Command, Folder, Settings, Plus, Search, ChevronRight } from 'lucide-react';
import { motion } from 'framer-motion';

export default function Projects() {
  const projects = useStore(state => state.projects);

  return (
    <div className="flex h-screen bg-[#0f0f0f]">
      {/* Sidebar - Compact version */}
      <div className="w-[250px] shrink-0 border-r border-[#2d2d2d] flex flex-col bg-[#121212]">
        <div className="p-4 border-b border-[#2d2d2d] flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg bg-gradient-to-tr from-purple-600 to-blue-500 flex items-center justify-center">
            <Command className="text-white w-4 h-4" />
          </div>
          <span className="font-semibold text-gray-100">Cammina AI</span>
        </div>
        <div className="p-4 flex-1">
          <Link to="/chat" className="flex items-center gap-3 px-2 py-2 rounded-lg text-sm text-gray-400 hover:bg-[#2d2d2d] hover:text-white transition-colors">
            Back to Chat
          </Link>
        </div>
        <div className="p-4 border-t border-[#2d2d2d]">
          <Link to="/settings" className="flex items-center gap-3 px-2 py-2 rounded-lg text-sm text-gray-400 hover:bg-[#2d2d2d] hover:text-white transition-colors">
            <Settings className="w-4 h-4" />
            Settings
          </Link>
        </div>
      </div>

      {/* Main Content */}
      <div className="flex-1 flex flex-col p-8 overflow-y-auto">
        <div className="max-w-6xl mx-auto w-full">
          <div className="flex justify-between items-center mb-8">
            <h1 className="text-3xl font-semibold tracking-tight">Projects</h1>
            <button className="bg-purple-600 hover:bg-purple-700 text-white flex items-center gap-2 rounded-lg px-4 py-2 font-medium transition-colors">
              <Plus className="w-4 h-4" />
              New Project
            </button>
          </div>

          <div className="relative mb-8">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-500" />
            <input 
              type="text" 
              placeholder="Search projects..." 
              className="w-full bg-[#1a1a1a] border border-[#2d2d2d] rounded-xl py-3 pl-11 pr-4 text-gray-200 focus:outline-none focus:border-purple-500 focus:ring-1 focus:ring-purple-500/50 transition-all shadow-lg"
            />
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {projects.map((project, i) => (
              <motion.div 
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: i * 0.1 }}
                key={project.id}
                className="bg-[#1a1a1a] border border-[#2d2d2d] rounded-2xl p-6 hover:border-purple-500/50 hover:shadow-[0_0_30px_rgba(124,58,237,0.1)] transition-all group"
              >
                <div className="flex justify-between items-start mb-4">
                  <div className="p-3 bg-[#2d2d2d] rounded-xl text-purple-400 group-hover:bg-purple-600 group-hover:text-white transition-colors">
                    <Folder className="w-6 h-6" />
                  </div>
                  <span className={`px-2.5 py-1 text-xs font-medium rounded-full ${
                    project.status === 'active' ? 'bg-green-500/10 text-green-400 border border-green-500/20' : 'bg-gray-500/10 text-gray-400 border border-gray-500/20'
                  }`}>
                    {project.status.toUpperCase()}
                  </span>
                </div>
                
                <h3 className="text-lg font-semibold text-gray-200 mb-1">{project.name}</h3>
                <p className="text-sm text-gray-500 mb-6">
                  Updated {formatDistanceToNow(new Date(project.updatedAt))} ago
                </p>

                <Link 
                  to={`/project/${project.id}`}
                  className="flex items-center justify-between w-full text-sm font-medium text-gray-400 hover:text-purple-400 transition-colors"
                >
                  View Details
                  <ChevronRight className="w-4 h-4" />
                </Link>
              </motion.div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
