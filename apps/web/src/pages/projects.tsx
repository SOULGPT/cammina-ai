import { useState, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { formatDistanceToNow } from 'date-fns';
import { Command, Folder, Settings, Plus, Search, Activity, Brain } from 'lucide-react';
import { motion } from 'framer-motion';

export default function Projects() {
  const [projects, setProjects] = useState<any[]>([]);
  const [searchTerm, setSearchTerm] = useState('');
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();

  useEffect(() => {
    fetchProjects();
  }, []);

  const fetchProjects = async () => {
    try {
      const res = await fetch('/api/projects');
      const data = await res.json();
      setProjects(data.projects || []);
    } catch (err) {
      console.error('Failed to fetch projects:', err);
    } finally {
      setLoading(false);
    }
  };

  const filteredProjects = projects.filter(p => 
    p.name.toLowerCase().includes(searchTerm.toLowerCase())
  );

  const openProject = (projectName: string) => {
    // Navigate to chat and could potentially set a store value for active project
    navigate(`/chat?project=${projectName}`);
  };

  return (
    <div className="flex h-screen bg-[#0f0f0f] text-gray-100 font-sans">
      {/* Sidebar - Compact version */}
      <div className="w-[250px] shrink-0 border-r border-[#2d2d2d] flex flex-col bg-[#121212]">
        <div className="p-4 border-b border-[#2d2d2d] flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg bg-gradient-to-tr from-purple-600 to-blue-500 flex items-center justify-center">
            <Command className="text-white w-4 h-4" />
          </div>
          <span className="font-semibold text-gray-100">Cammina AI</span>
        </div>
        <div className="p-4 flex-1">
          <Link to="/chat" className="flex items-center gap-3 px-3 py-2 rounded-lg text-sm text-gray-400 hover:bg-[#2d2d2d] hover:text-white transition-all">
            <Activity className="w-4 h-4" />
            Back to Chat
          </Link>
        </div>
        <div className="p-4 border-t border-[#2d2d2d]">
          <Link to="/settings" className="flex items-center gap-3 px-3 py-2 rounded-lg text-sm text-gray-400 hover:bg-[#2d2d2d] hover:text-white transition-all">
            <Settings className="w-4 h-4" />
            Settings
          </Link>
        </div>
      </div>

      {/* Main Content */}
      <div className="flex-1 flex flex-col p-8 overflow-y-auto">
        <div className="max-w-6xl mx-auto w-full">
          <div className="flex justify-between items-center mb-8">
            <div>
              <h1 className="text-4xl font-bold tracking-tight mb-2 bg-clip-text text-transparent bg-gradient-to-r from-white to-gray-500">
                Projects
              </h1>
              <p className="text-gray-500">Manage and explore your AI-driven development projects</p>
            </div>
            <button className="bg-purple-600 hover:bg-purple-700 text-white flex items-center gap-2 rounded-xl px-5 py-2.5 font-medium transition-all shadow-lg shadow-purple-900/20 active:scale-95">
              <Plus className="w-4 h-4" />
              New Project
            </button>
          </div>

          <div className="relative mb-10">
            <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-500" />
            <input 
              type="text" 
              placeholder="Search by project name..." 
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-full bg-[#161616] border border-[#2d2d2d] rounded-2xl py-4 pl-12 pr-4 text-gray-200 focus:outline-none focus:border-purple-500 focus:ring-2 focus:ring-purple-500/20 transition-all shadow-xl"
            />
          </div>

          {loading ? (
            <div className="flex items-center justify-center py-20">
              <div className="animate-spin rounded-full h-8 w-8 border-t-2 border-purple-500"></div>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              {filteredProjects.map((project, i) => (
                <motion.div 
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: i * 0.05 }}
                  key={project.name}
                  className="bg-[#161616] border border-[#2d2d2d] rounded-2xl p-6 hover:border-purple-500/50 hover:bg-[#1c1c1c] transition-all group relative overflow-hidden"
                >
                  <div className="absolute top-0 right-0 w-32 h-32 bg-purple-600/5 blur-3xl rounded-full -mr-10 -mt-10"></div>
                  
                  <div className="flex justify-between items-start mb-6">
                    <div className="p-3 bg-[#262626] rounded-xl text-purple-400 group-hover:scale-110 transition-transform">
                      <Folder className="w-6 h-6" />
                    </div>
                    <div className="flex flex-col items-end gap-2">
                      <span className="px-3 py-1 text-xs font-bold bg-purple-500/10 text-purple-400 border border-purple-500/20 rounded-full">
                        {project.task_count} TASKS
                      </span>
                    </div>
                  </div>
                  
                  <h3 className="text-xl font-bold text-gray-100 mb-2 group-hover:text-purple-400 transition-colors">
                    {project.name}
                  </h3>
                  
                  <div className="flex items-center gap-2 text-xs text-gray-500 mb-8">
                    <Activity className="w-3 h-3" />
                    {project.last_active ? (
                      <span>Active {formatDistanceToNow(new Date(project.last_active))} ago</span>
                    ) : (
                      <span>No activity yet</span>
                    )}
                  </div>

                  <div className="flex gap-3">
                    <button 
                      onClick={() => openProject(project.name)}
                      className="flex-1 bg-white/5 hover:bg-white/10 text-gray-200 text-sm font-semibold py-2.5 rounded-xl transition-all border border-white/5 flex items-center justify-center gap-2"
                    >
                      Open Chat
                    </button>
                    <button className="p-2.5 bg-purple-600/10 hover:bg-purple-600/20 text-purple-400 rounded-xl transition-all border border-purple-500/10" title="View Memory">
                      <Brain className="w-5 h-5" />
                    </button>
                  </div>
                </motion.div>
              ))}
              
              {filteredProjects.length === 0 && (
                <div className="col-span-full py-20 text-center border-2 border-dashed border-[#2d2d2d] rounded-3xl">
                  <p className="text-gray-500">No projects found matching your search.</p>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
