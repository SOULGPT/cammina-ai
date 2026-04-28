import { useState, useRef, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useStore } from '../stores';
import { Send, Bot, User, Command, Zap, Layout, Folder, Github, Terminal, History, Info } from 'lucide-react';

export default function ChatComponent() {
  const [input, setInput] = useState('');
  const [taskMode, setTaskMode] = useState<'idle' | 'answering'>('idle');
  const [originalTask, setOriginalTask] = useState('');
  const [questions, setQuestions] = useState<string[]>([]);
  const [answers, setAnswers] = useState<string[]>([]);
  const [showSuggestions, setShowSuggestions] = useState(false);
  
  const [projects, setProjects] = useState<any[]>([]);
  const [userPaths, setUserPaths] = useState({ home: '', desktop: '' });

  const messages = useStore((state) => state.messages);
  const activeTask = useStore((state) => state.activeTask);
  const selectedProject = useStore((state) => state.selectedProject);
  const { addMessage, setActiveTask, clearMessages, setSelectedProject } = useStore();
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const loadProjects = () => {
    fetch('/api/projects')
      .then(res => res.json())
      .then(data => {
        setProjects(data.projects || []);
      })
      .catch(err => console.error('Failed to load projects:', err));
  };

  useEffect(() => {
    loadProjects();
    fetch('/api/user/home')
      .then(res => res.json())
      .then(data => setUserPaths({ home: data.home, desktop: data.desktop }))
      .catch(err => console.error('Failed to load user paths:', err));
  }, []);

  const suggestions = [
    { text: "help", icon: <Info className="w-3 h-3" /> },
    { text: "git status", icon: <Github className="w-3 h-3" /> },
    { text: "install dependencies", icon: <Terminal className="w-3 h-3" /> },
    { text: "run app", icon: <Zap className="w-3 h-3" /> },
    { text: "show memory", icon: <History className="w-3 h-3" /> },
    { text: "clean memory", icon: <History className="w-3 h-3" /> },
    { text: "cursor do: ", icon: <Bot className="w-3 h-3" /> },
    { text: "new project: ", icon: <Folder className="w-3 h-3" /> },
    { text: "services status", icon: <Layout className="w-3 h-3" /> },
  ];

  const handleQuickAction = async (message: string): Promise<boolean> => {
    const msg = message.toLowerCase().trim();
    
    const projectPath = selectedProject && selectedProject !== 'general' 
      ? `${userPaths.desktop}/${selectedProject}` 
      : `${userPaths.desktop}/cammina`;

    // 1. MEMORY CLEANUP - URGENT PRIORITY
    if (msg === "clean memory" || msg === "clear memory" || msg === "clean all memory") {
      setActiveTask({ status: 'running' });
      try {
        const response = await fetch('/api/memory/cleanup-all', { method: 'POST' });
        const result = await response.json();
        addMessage({
          id: `agent-${Date.now()}`,
          role: 'agent',
          content: `Cleaned up memory. Removed ${result.deleted || 0} bad entries. Type "show memory" to verify.`,
          timestamp: new Date().toISOString()
        });
      } catch (err) { 
        addMessage({ 
          id: `err-${Date.now()}`,
          role: 'agent', 
          content: "Error cleaning memory.", 
          timestamp: new Date().toISOString() 
        });
      } finally { 
        setActiveTask({ status: 'idle' }); 
      }
      return true;
    }

    if (msg.startsWith("clear memory for ")) {
      const projectName = message.slice(17).trim();
      if (projectName) {
        setActiveTask({ status: 'running' });
        try {
          const res = await fetch('/api/memory/cleanup', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ project_name: projectName })
          });
          const result = await res.json();
          addMessage({
            id: `agent-${Date.now()}`,
            role: 'agent',
            content: `Cleaned ${result.deleted || 0} entries from ${projectName} memory.`,
            timestamp: new Date().toISOString()
          });
        } catch (err) { 
          addMessage({ 
            id: `err-${Date.now()}`,
            role: 'agent', 
            content: "Error cleaning project memory.", 
            timestamp: new Date().toISOString() 
          });
        } finally { 
          setActiveTask({ status: 'idle' }); 
        }
        return true;
      }
    }

    // Helper for terminal tasks
    const executeQuickTerminal = async (command: string, cwd?: string) => {
      setActiveTask({ status: 'running' });
      try {
        const res = await fetch('/api/task/quick', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ action: 'terminal', command, project_name: selectedProject, cwd: cwd || projectPath })
        });
        const result = await res.json();
        addMessage({
          id: `agent-${Date.now()}`,
          role: 'agent',
          content: result.error ? `Error: ${result.error}` : `Output:\n${result.stdout || result.stderr || 'Success'}`,
          timestamp: new Date().toISOString()
        });
      } catch (err) { console.error(err); }
      finally { setActiveTask({ status: 'idle' }); }
    };

    const executeGenericQuick = async (payload: any) => {
      setActiveTask({ status: 'running' });
      try {
        let url = '/api/task/quick';
        if (payload.action === 'cursor_do') {
          url = '/api/cursor/autonomous';
          payload = { instruction: payload.instruction, project_path: projectPath, project_name: selectedProject };
        } else {
          payload = { ...payload, project_name: selectedProject, cwd: projectPath };
        }
        const res = await fetch(url, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) });
        const result = await res.json();
        addMessage({ id: `agent-${Date.now()}`, role: 'agent', content: result.error ? `Error: ${result.error}` : "Action completed.", timestamp: new Date().toISOString() });
      } catch (err) { console.error(err); }
      finally { setActiveTask({ status: 'idle' }); }
    };

    if (msg === "services status") { await executeQuickTerminal('./cammina status', '/Users/miruzaankhan/Desktop/cammina'); return true; }
    if (msg === "check ports") { await executeQuickTerminal('lsof -i :3000,8000,8001,8002,8765'); return true; }
    if (msg === "git status") { await executeQuickTerminal('git status'); return true; }
    if (msg === "git push") { await executeQuickTerminal('git add . && git commit -m "update" && git push origin main'); return true; }
    if (msg === "git pull") { await executeQuickTerminal('git pull'); return true; }
    if (msg === "install dependencies") { await executeQuickTerminal('if [ -f package.json ]; then npm install; elif [ -f requirements.txt ]; then pip3 install -r requirements.txt; else echo "No file found"; fi'); return true; }
    if (msg === "run app") { await executeQuickTerminal('if grep -q "\\"start\\":" package.json 2>/dev/null; then npm start; elif [ -f app.py ]; then python3 app.py; else echo "No start file"; fi'); return true; }
    if (msg === "open project in cursor") { await executeQuickTerminal(`open -a Cursor "${projectPath}"`); return true; }
    if (msg === "what files changed") { await executeQuickTerminal('git diff --name-only'); return true; }
    if (msg === "show errors") { await executeQuickTerminal('cat logs/errors/*.json 2>/dev/null'); return true; }

    if (msg === "services status") { await executeQuickTerminal('./cammina status', `${userPaths.desktop}/cammina`); return true; }

    if (msg === "open desktop") { await executeQuickTerminal(`open ${userPaths.desktop}`); return true; }

    if (msg === "restart services") { await executeQuickTerminal('./cammina restart', `${userPaths.desktop}/cammina`); return true; }
    if (msg === "stop services") { await executeQuickTerminal('./cammina stop', `${userPaths.desktop}/cammina`); return true; }

    if (msg === "show memory") {
      setActiveTask({ status: 'running' });
      try {
        const res = await fetch('/api/memory/search', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ query: selectedProject, project_name: selectedProject, limit: 10 }) });
        const data = await res.json();
        addMessage({ id: `agent-${Date.now()}`, role: 'agent', content: `Memory for ${selectedProject}:\n${data.results?.map((r: any) => `• ${r.content}`).join('\n') || "Empty."}`, timestamp: new Date().toISOString() });
      } catch (err) { console.error(err); }
      finally { setActiveTask({ status: 'idle' }); }
      return true;
    }

    if (msg === 'help') {
      addMessage({ id: `agent-${Date.now()}`, role: 'agent', content: "Quick actions: git status, services status, clean memory, show memory, help, etc.", timestamp: new Date().toISOString() });
      return true;
    }
    if (msg === 'clear chat') { clearMessages(); return true; }

    if (msg.startsWith("remember this:")) {
      const note = message.slice(14).trim();
      try {
        await fetch("/api/memory/save", { method: "POST", headers: {"Content-Type": "application/json"}, body: JSON.stringify({ content: note, project_name: selectedProject, memory_type: "user_note", is_explicit: true }) });
        addMessage({ id: `agent-${Date.now()}`, role: 'agent', content: `Saved to ${selectedProject}: "${note}"`, timestamp: new Date().toISOString() });
      } catch (err) { console.error(err); }
      return true;
    }

    if (msg.startsWith("cursor do:")) { await executeGenericQuick({ action: 'cursor_do', instruction: message.slice(10).trim() }); return true; }

    return false;
  };

  const handleSend = async (e?: React.FormEvent, overrideInput?: string) => {
    if (e) e.preventDefault();
    const finalInput = overrideInput || input;
    if (!finalInput.trim() || activeTask.status === 'running') return;

    const userInput = finalInput.trim();
    if (!overrideInput) setInput('');
    setShowSuggestions(false);

    const msgId = `${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
    addMessage({
      id: msgId,
      role: 'user',
      content: userInput,
      timestamp: new Date().toISOString()
    });

    // Check quick actions FIRST before anything else
    const handled = await handleQuickAction(userInput);
    if (handled) return; // STOP HERE if handled

    if (taskMode === 'idle') {
      try {
        const response = await fetch('/api/task/start', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ task: userInput, project_id: selectedProject, project_name: selectedProject })
        });
        const data = await response.json();
        
        if (data.questions && data.questions.length > 0) {
          setTaskMode('answering');
          setOriginalTask(userInput);
          setQuestions(data.questions);
          setAnswers([]);
          setActiveTask({ id: data.task_id, status: 'idle' });
          addMessage({ id: `sys-${Date.now()}`, role: 'system', content: `I have clarifying questions:\n\n1. ${data.questions[0]}`, timestamp: new Date().toISOString() });
        } else {
          const ansRes = await fetch('/api/task/answer', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ task_id: data.task_id, task: userInput, answers: {} })
          });
          if (!ansRes.ok) throw new Error('Failed to initialize plan');
          const exeRes = await fetch('/api/task/execute', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ task_id: data.task_id })
          });
          if (!exeRes.ok) throw new Error('Failed to start execution');
          setActiveTask({ id: data.task_id, status: 'running' });
        }
      } catch (err: any) {
        console.error(err);
        setActiveTask({ status: 'error' });
        addMessage({ id: `err-${Date.now()}`, role: 'system', content: `Error: ${err.message}`, timestamp: new Date().toISOString() });
      }
    } else if (taskMode === 'answering') {
      const newAnswers = [...answers, userInput];
      setAnswers(newAnswers);
      if (newAnswers.length >= questions.length || userInput.toLowerCase() === 'skip') {
        setTaskMode('idle');
        setActiveTask({ status: 'running' });
        try {
          const answersDict = questions.reduce((acc, q, i) => {
            if (newAnswers[i]) acc[q] = newAnswers[i];
            return acc;
          }, {} as Record<string, string>);
          await fetch('/api/task/answer', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ task_id: activeTask.id, task: originalTask, answers: answersDict })
          });
          await fetch('/api/task/execute', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ task_id: activeTask.id })
          });
        } catch (err) { console.error(err); setActiveTask({ status: 'error' }); }
      } else {
        addMessage({ id: `sys-${Date.now()}`, role: 'system', content: `Next: ${questions[newAnswers.length]}`, timestamp: new Date().toISOString() });
      }
    }
  };

  return (
    <div className="flex flex-col h-full bg-[#0f0f0f] text-gray-200">
      <div className="p-4 border-b border-[#2d2d2d] bg-[#121212] flex items-center justify-between shadow-lg z-10">
        <div className="flex items-center gap-3">
          <div className="p-2 bg-purple-600/10 rounded-lg text-purple-400">
            <Command className="w-5 h-5" />
          </div>
          <div>
            <h2 className="text-sm font-bold text-gray-100 uppercase tracking-widest">Cammina AI</h2>
            <div className="flex items-center gap-2 mt-1">
              <span className="text-[10px] text-gray-500 uppercase font-bold">Project:</span>
              <select 
                value={selectedProject} 
                onChange={(e) => setSelectedProject(e.target.value)}
                className="bg-[#2d2d2d] text-white border border-purple-500/50 rounded-md px-2 py-1 text-[10px] focus:outline-none focus:ring-1 focus:ring-purple-500 transition-all cursor-pointer"
              >
                <option value="">Select Project...</option>
                {projects.map(p => (
                  <option key={p.name} value={p.name}>{p.name}</option>
                ))}
              </select>
            </div>
          </div>
        </div>
        <div className="flex items-center gap-2">
          {activeTask.status === 'running' && (
            <div className="flex items-center gap-2 px-3 py-1 bg-purple-600/20 rounded-full border border-purple-500/30">
              <div className="w-1.5 h-1.5 bg-purple-400 rounded-full animate-pulse"></div>
              <span className="text-[10px] font-bold text-purple-400 uppercase tracking-tighter">Processing</span>
            </div>
          )}
        </div>
      </div>

      <div className="flex-1 overflow-y-auto p-6 space-y-6 scrollbar-thin scrollbar-thumb-[#2d2d2d]">
        <AnimatePresence initial={false}>
          {messages.map((msg) => (
            <motion.div
              key={msg.id}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              className={`flex gap-4 ${msg.role === 'user' ? 'flex-row-reverse' : 'flex-row'}`}
            >
              <div className={`w-8 h-8 rounded-full flex items-center justify-center shrink-0 shadow-lg ${
                msg.role === 'user' ? 'bg-purple-600' : msg.role === 'system' ? 'bg-blue-600' : 'bg-[#1a1a1a] border border-[#2d2d2d]'
              }`}>
                {msg.role === 'user' ? <User className="w-4 h-4 text-white" /> : 
                 msg.role === 'system' ? <Command className="w-4 h-4 text-white" /> : 
                 <Bot className="w-4 h-4 text-purple-400" />}
              </div>
              <div className={`max-w-[80%] rounded-2xl px-5 py-3 ${
                msg.role === 'user' ? 'bg-purple-600 text-white' : msg.role === 'system' ? 'bg-blue-900/20 text-blue-300 border border-blue-800/50 text-sm' : 'bg-[#1a1a1a] border border-[#2d2d2d] text-gray-200'
              }`}>
                <pre className="font-sans whitespace-pre-wrap leading-relaxed text-sm">{msg.content}</pre>
              </div>
            </motion.div>
          ))}
        </AnimatePresence>
        <div ref={messagesEndRef} />
      </div>

      <div className="p-4 bg-[#0f0f0f] relative">
        <AnimatePresence>
          {showSuggestions && (
            <motion.div 
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: 10 }}
              className="absolute bottom-full left-4 right-4 mb-2 p-2 bg-[#121212] border border-[#2d2d2d] rounded-xl flex gap-2 overflow-x-auto shadow-2xl z-20 no-scrollbar"
            >
              {suggestions.map((s, i) => (
                <button
                  key={i}
                  onClick={() => { setInput(s.text); handleSend(undefined, s.text); }}
                  className="whitespace-nowrap flex items-center gap-1.5 px-3 py-1.5 bg-[#1a1a1a] border border-[#2d2d2d] hover:border-purple-500 rounded-lg text-xs text-gray-400 hover:text-white transition-all group"
                >
                  <span className="text-purple-400 group-hover:scale-110 transition-transform">{s.icon}</span>
                  {s.text}
                </button>
              ))}
            </motion.div>
          )}
        </AnimatePresence>

        <form onSubmit={handleSend} className="relative max-w-4xl mx-auto">
          <input
            type="text"
            value={input}
            onFocus={() => setShowSuggestions(true)}
            onBlur={() => setTimeout(() => setShowSuggestions(false), 200)}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Describe your task to orchestrate..."
            className="w-full bg-[#1a1a1a] border border-[#2d2d2d] rounded-2xl py-4 pl-6 pr-14 text-gray-200 focus:outline-none focus:border-purple-500 focus:ring-1 focus:ring-purple-500/50 transition-all shadow-xl"
            disabled={activeTask.status === 'running'}
          />
          <button
            type="submit"
            disabled={!input.trim() || activeTask.status === 'running'}
            className="absolute right-2 top-2 p-2 rounded-xl bg-purple-600 text-white hover:bg-purple-700 disabled:opacity-50 disabled:hover:bg-purple-600 transition-colors"
          >
            <Send className="w-5 h-5" />
          </button>
        </form>
      </div>
    </div>
  );
}
