import { useState, useEffect } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { ChevronLeft, Folder, History, Files, Settings, Plus, Search, ExternalLink, Trash2, Zap } from 'lucide-react';
import { useStore } from '../stores';

type Tab = 'memory' | 'files' | 'tasks' | 'settings';

export default function ProjectDetails() {
  const { projectName } = useParams<{ projectName: string }>();
  const navigate = useNavigate();
  const [activeTab, setActiveTab] = useState<Tab>('memory');
  const [project, setProject] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [showAddNote, setShowAddNote] = useState(false);
  const [newNote, setNewNote] = useState('');

  const setSelectedProject = useStore((state) => state.setSelectedProject);

  const fetchDetails = async () => {
    try {
      const res = await fetch(`/api/projects/${projectName}`);
      const data = await res.json();
      setProject(data);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDetails();
  }, [projectName]);

  const handleAddNote = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newNote.trim()) return;
    try {
      const res = await fetch(`/api/projects/${projectName}/memories`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ content: newNote, memory_type: 'user_note' })
      });
      if (res.ok) {
        setNewNote('');
        setShowAddNote(false);
        fetchDetails();
      }
    } catch (err) { console.error(err); }
  };

  const handleDeleteMemory = async (originalIndex: number) => {
    if (!confirm('Delete this memory?')) return;
    try {
      // The backend needs the index in the ORIGINAL list.
      // Our state 'memories' is REVERSED.
      // originalIndex = (len - 1) - currentIndex
      const res = await fetch(`/api/projects/${projectName}/memories/${originalIndex}`, {
        method: 'DELETE'
      });
      if (res.ok) fetchDetails();
    } catch (err) { console.error(err); }
  };

  const handleDeleteProject = async () => {
    if (!confirm(`Are you sure you want to delete project "${projectName}"? This will delete all logs and memories.`)) return;
    try {
      const res = await fetch(`/api/projects/${projectName}`, { method: 'DELETE' });
      if (res.ok) navigate('/chat');
    } catch (err) { console.error(err); }
  };

  const openInCursor = (path: string) => {
    fetch('/api/task/quick', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ action: 'terminal', command: `open -a Cursor "${path}"` })
    });
  };

  if (loading) return (
    <div className="flex-1 bg-[#0f0f0f] flex items-center justify-center">
      <div className="w-8 h-8 border-4 border-purple-600 border-t-transparent rounded-full animate-spin"></div>
    </div>
  );

  if (!project || project.error) return (
    <div className="flex-1 bg-[#0f0f0f] flex flex-col items-center justify-center text-gray-400">
      <Folder className="w-16 h-16 mb-4 opacity-20" />
      <p>Project not found</p>
      <Link to="/chat" className="mt-4 text-purple-400 hover:underline">Back to Chat</Link>
    </div>
  );

  const filteredMemories = project.memories?.filter((m: any) => 
    m.content.toLowerCase().includes(searchQuery.toLowerCase())
  );

  return (
    <div className="flex-1 bg-[#0f0f0f] flex flex-col overflow-hidden">
      {/* Header */}
      <div className="p-8 border-b border-[#2d2d2d] bg-[#121212]">
        <div className="max-w-6xl mx-auto flex items-start justify-between">
          <div className="flex gap-6 items-center">
            <button 
              onClick={() => navigate('/chat')}
              className="p-2 rounded-xl bg-[#1a1a1a] border border-[#2d2d2d] text-gray-400 hover:text-white transition-all"
            >
              <ChevronLeft className="w-5 h-5" />
            </button>
            <div>
              <div className="flex items-center gap-3 mb-1">
                <h1 className="text-3xl font-black text-white tracking-tight">{project.name}</h1>
                <span className="bg-purple-600/20 text-purple-400 text-xs px-2 py-0.5 rounded-full border border-purple-500/30 font-bold uppercase">
                  {project.memory_count} Memories
                </span>
              </div>
              <p className="text-xs text-gray-500 font-mono">Created: {project.created_at}</p>
            </div>
          </div>
          <div className="flex gap-3">
            <button 
              onClick={() => { setSelectedProject(project.name); navigate('/chat'); }}
              className="px-4 py-2 bg-purple-600 hover:bg-purple-700 text-white rounded-xl text-sm font-bold shadow-lg shadow-purple-500/20 transition-all flex items-center gap-2"
            >
              <Zap className="w-4 h-4" /> Switch to Chat
            </button>
            <button 
              onClick={() => openInCursor(`/Users/miruzaankhan/Desktop/${project.name}`)}
              className="px-4 py-2 bg-[#1a1a1a] border border-[#2d2d2d] text-gray-200 rounded-xl text-sm font-bold hover:bg-[#252525] transition-all flex items-center gap-2"
            >
              <ExternalLink className="w-4 h-4" /> Open in Cursor
            </button>
          </div>
        </div>

        {/* Tabs */}
        <div className="max-w-6xl mx-auto mt-8 flex gap-8">
          {(['memory', 'files', 'tasks', 'settings'] as Tab[]).map((t) => (
            <button
              key={t}
              onClick={() => setActiveTab(t)}
              className={`pb-4 text-sm font-bold uppercase tracking-widest transition-all relative ${
                activeTab === t ? 'text-purple-400' : 'text-gray-500 hover:text-gray-300'
              }`}
            >
              <div className="flex items-center gap-2">
                {t === 'memory' && <History className="w-4 h-4" />}
                {t === 'files' && <Files className="w-4 h-4" />}
                {t === 'tasks' && <Zap className="w-4 h-4" />}
                {t === 'settings' && <Settings className="w-4 h-4" />}
                {t}
              </div>
              {activeTab === t && (
                <motion.div 
                  layoutId="activeTab"
                  className="absolute bottom-0 left-0 right-0 h-0.5 bg-purple-500 shadow-[0_0_10px_#7c3aed]"
                />
              )}
            </button>
          ))}
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-8 scrollbar-thin scrollbar-thumb-[#2d2d2d]">
        <div className="max-w-6xl mx-auto">
          
          {activeTab === 'memory' && (
            <div className="space-y-6">
              <div className="flex items-center justify-between gap-4">
                <div className="flex-1 relative">
                  <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-500" />
                  <input 
                    type="text" 
                    placeholder="Search memories..." 
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    className="w-full bg-[#121212] border border-[#2d2d2d] rounded-xl py-2.5 pl-11 pr-4 text-sm text-white focus:outline-none focus:border-purple-500 transition-all"
                  />
                </div>
                <button 
                  onClick={() => setShowAddNote(true)}
                  className="px-4 py-2.5 bg-purple-600/10 text-purple-400 border border-purple-500/20 rounded-xl text-sm font-bold hover:bg-purple-600/20 transition-all flex items-center gap-2"
                >
                  <Plus className="w-4 h-4" /> Add Note
                </button>
              </div>

              <AnimatePresence>
                {showAddNote && (
                  <motion.div 
                    initial={{ opacity: 0, y: -10 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0, y: -10 }}
                    className="p-6 bg-[#121212] border border-purple-500/30 rounded-2xl"
                  >
                    <form onSubmit={handleAddNote}>
                      <textarea 
                        autoFocus
                        value={newNote}
                        onChange={(e) => setNewNote(e.target.value)}
                        placeholder="What should Cammina remember for this project?"
                        className="w-full bg-[#0f0f0f] border border-[#2d2d2d] rounded-xl p-4 text-sm text-white focus:outline-none focus:border-purple-500 min-h-[100px] mb-4"
                      />
                      <div className="flex justify-end gap-3">
                        <button type="button" onClick={() => setShowAddNote(false)} className="px-4 py-2 text-sm text-gray-500 hover:text-white">Cancel</button>
                        <button type="submit" className="px-6 py-2 bg-purple-600 text-white rounded-lg text-sm font-bold">Save Note</button>
                      </div>
                    </form>
                  </motion.div>
                )}
              </AnimatePresence>

              <div className="grid gap-4">
                {filteredMemories?.map((m: any, i: number) => {
                  const originalIndex = project.memories.length - 1 - i;
                  return (
                    <motion.div 
                      key={m.id || i}
                      initial={{ opacity: 0 }}
                      animate={{ opacity: 1 }}
                      className="p-5 bg-[#121212] border border-[#2d2d2d] rounded-2xl hover:border-[#3d3d3d] transition-all group"
                    >
                      <div className="flex justify-between items-start mb-3">
                        <div className="flex items-center gap-2">
                          <span className={`text-[10px] font-black uppercase px-2 py-0.5 rounded-md border ${
                            m.memory_type === 'user_note' ? 'bg-blue-600/10 text-blue-400 border-blue-500/20' :
                            m.memory_type === 'action' ? 'bg-green-600/10 text-green-400 border-green-500/20' :
                            m.memory_type === 'task_summary' ? 'bg-purple-600/10 text-purple-400 border-purple-500/20' :
                            'bg-gray-600/10 text-gray-400 border-gray-500/20'
                          }`}>
                            {m.memory_type || 'memory'}
                          </span>
                          <span className="text-[10px] text-gray-600 font-mono">{new Date(m.timestamp).toLocaleString()}</span>
                        </div>
                        <button 
                          onClick={() => handleDeleteMemory(originalIndex)}
                          className="opacity-0 group-hover:opacity-100 p-1 text-gray-600 hover:text-red-400 transition-all"
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                      </div>
                      <pre className="font-sans text-sm text-gray-300 whitespace-pre-wrap leading-relaxed">{m.content}</pre>
                    </motion.div>
                  );
                })}
              </div>
            </div>
          )}

          {activeTab === 'files' && (
            <div className="grid gap-4">
              {project.files?.length === 0 ? (
                <div className="text-center py-20 bg-[#121212] rounded-2xl border border-dashed border-[#2d2d2d]">
                  <Files className="w-12 h-12 text-gray-700 mx-auto mb-4" />
                  <p className="text-gray-500">No project files detected in standard locations</p>
                </div>
              ) : (
                project.files?.map((f: any, i: number) => (
                  <div key={i} className="flex items-center justify-between p-4 bg-[#121212] border border-[#2d2d2d] rounded-xl hover:bg-[#161616] transition-all">
                    <div className="flex items-center gap-4">
                      <div className="p-2 bg-[#1a1a1a] rounded-lg">
                        <Folder className="w-4 h-4 text-purple-400" />
                      </div>
                      <div>
                        <div className="text-sm font-bold text-gray-200">{f.name}</div>
                        <div className="text-[10px] text-gray-500 font-mono truncate max-w-md">{f.path}</div>
                      </div>
                    </div>
                    <div className="flex items-center gap-8">
                      <div className="text-right">
                        <div className="text-[10px] text-gray-400 uppercase font-bold tracking-tighter">Modified</div>
                        <div className="text-[10px] text-gray-500 font-mono">{f.modified}</div>
                      </div>
                      <button 
                        onClick={() => openInCursor(f.path)}
                        className="p-2 bg-[#1a1a1a] border border-[#2d2d2d] rounded-lg text-gray-400 hover:text-purple-400 transition-all"
                      >
                        <ExternalLink className="w-4 h-4" />
                      </button>
                    </div>
                  </div>
                ))
              )}
            </div>
          )}

          {activeTab === 'tasks' && (
            <div className="space-y-4">
              {project.tasks?.length === 0 ? (
                <div className="text-center py-20 bg-[#121212] rounded-2xl border border-dashed border-[#2d2d2d]">
                  <Zap className="w-12 h-12 text-gray-700 mx-auto mb-4" />
                  <p className="text-gray-500">No autonomous tasks found in memory</p>
                </div>
              ) : (
                project.tasks?.map((t: any, i: number) => (
                  <div key={i} className="p-6 bg-[#121212] border border-[#2d2d2d] rounded-2xl">
                    <div className="flex justify-between items-start mb-4">
                      <div className="text-sm font-bold text-white">{t.content.split('\n')[0]}</div>
                      <span className="text-[10px] text-gray-600 font-mono">{new Date(t.timestamp).toLocaleString()}</span>
                    </div>
                    <pre className="text-xs text-gray-400 font-sans whitespace-pre-wrap mb-6">{t.content.split('\n').slice(1).join('\n')}</pre>
                    <button 
                      onClick={() => { setSelectedProject(project.name); navigate('/chat'); }}
                      className="px-4 py-2 bg-[#1a1a1a] border border-[#2d2d2d] rounded-xl text-[10px] font-bold uppercase tracking-widest text-purple-400 hover:bg-[#252525]"
                    >
                      Replay in Chat
                    </button>
                  </div>
                ))
              )}
            </div>
          )}

          {activeTab === 'settings' && (
            <div className="max-w-2xl bg-[#121212] border border-[#2d2d2d] rounded-2xl p-8">
              <h2 className="text-xl font-bold text-white mb-8">Project Settings</h2>
              
              <div className="space-y-6">
                <div>
                  <label className="block text-[10px] font-bold text-gray-500 uppercase tracking-widest mb-2">Project Name</label>
                  <input type="text" readOnly value={project.name} className="w-full bg-[#0f0f0f] border border-[#2d2d2d] rounded-xl px-4 py-3 text-white opacity-50 cursor-not-allowed" />
                </div>
                
                <div>
                  <label className="block text-[10px] font-bold text-gray-500 uppercase tracking-widest mb-2">Logs Path</label>
                  <input type="text" readOnly value={`logs/projects/${project.name}`} className="w-full bg-[#0f0f0f] border border-[#2d2d2d] rounded-xl px-4 py-3 text-white opacity-50 font-mono text-xs" />
                </div>

                <div className="pt-8 border-t border-[#2d2d2d]">
                  <h3 className="text-red-400 text-sm font-bold mb-2 uppercase tracking-widest">Danger Zone</h3>
                  <p className="text-xs text-gray-500 mb-6">Once you delete a project, there is no going back. All memories and task logs for this specific project name will be permanently erased.</p>
                  <button 
                    onClick={handleDeleteProject}
                    className="flex items-center gap-2 px-6 py-3 bg-red-950/20 text-red-500 border border-red-900/30 rounded-xl text-sm font-bold hover:bg-red-950/40 transition-all"
                  >
                    <Trash2 className="w-4 h-4" /> Delete Project Data
                  </button>
                </div>
              </div>
            </div>
          )}

        </div>
      </div>
    </div>
  );
}
