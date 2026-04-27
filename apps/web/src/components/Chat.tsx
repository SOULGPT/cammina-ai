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
  const [selectedProject, setSelectedProject] = useState<string>('general');

  const messages = useStore((state) => state.messages);
  const activeTask = useStore((state) => state.activeTask);
  const { addMessage, setActiveTask, clearMessages } = useStore();
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
  }, []);

  const suggestions = [
    { text: "help", icon: <Info className="w-3 h-3" /> },
    { text: "git status", icon: <Github className="w-3 h-3" /> },
    { text: "install dependencies", icon: <Terminal className="w-3 h-3" /> },
    { text: "run app", icon: <Zap className="w-3 h-3" /> },
    { text: "show memory", icon: <History className="w-3 h-3" /> },
    { text: "cursor do: ", icon: <Bot className="w-3 h-3" /> },
    { text: "create a file at path with content: ", icon: <Zap className="w-3 h-3" /> },
    { text: "new project: ", icon: <Folder className="w-3 h-3" /> },
    { text: "services status", icon: <Layout className="w-3 h-3" /> },
  ];

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

    const handleQuickAction = async (message: string): Promise<boolean> => {
      const taskLower = message.toLowerCase();
      
      const projectPath = selectedProject && selectedProject !== 'general' 
        ? `/Users/miruzaankhan/Desktop/${selectedProject}` 
        : `/Users/miruzaankhan/Desktop/cammina`;

      // Helper to execute quick task
      const executeQuick = async (payload: any, successMsg?: string) => {
        setActiveTask({ status: 'running' });
        try {
          let url = '/api/task/quick';
          if (payload.action === 'cursor_do') {
            url = '/api/cursor/autonomous';
            payload = { 
              instruction: payload.instruction, 
              project_path: projectPath,
              project_name: selectedProject 
            };
          } else {
            payload = { 
              ...payload, 
              project_name: selectedProject,
              cwd: payload.cwd || projectPath
            };
          }

          const res = await fetch(url, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
          });
          const result = await res.json();
          
          let content = '';
          if (payload.action === 'file_write') {
            content = result.success ? (successMsg || `File created at ${payload.path}`) : `Error: ${result.error}`;
          } else if (payload.action === 'file_read') {
            content = result.error ? `Error: ${result.error}` : `File Content:\n\n${result.content}`;
          } else if (payload.action === 'terminal') {
            content = result.error ? `Error: ${result.error}` : `Output:\n${result.stdout || result.stderr || 'Success (no output)'}`;
          } else if (payload.action === 'screenshot') {
            content = result.image_base64 ? `Screenshot captured! [Base64 content received]` : `Error: ${result.error}`;
          } else if (payload.action === 'app_open') {
            content = result.success ? `Opened application: ${payload.app_name || payload.app}` : `Error: ${result.error}`;
          } else if (url.includes('autonomous')) {
            if (result.success) {
              const newFiles = Array.isArray(result.new_files) ? result.new_files : [];
              const commandsRun = Array.isArray(result.commands_run) ? result.commands_run.map((c: any) => c.command) : [];
              const summaryResults = Array.isArray(result.results) ? result.results : [];
              
              content = [
                `Autonomous task finished. Rounds: ${result.rounds || 1}`,
                result.project_path ? `New project created at: ${result.project_path}` : '',
                `New files: ${newFiles.length}`,
                `Commands run: ${commandsRun.length > 0 ? commandsRun.join(', ') : 'none'}`,
                `Details: ${summaryResults.join(' | ')}`,
                result.chat_text ? `Cursor said: ${result.chat_text.slice(0, 200)}` : ''
              ].filter(Boolean).join('\n');
            } else {
              content = `Error: ${result.error || 'Unknown error'}`;
            }
          }

          addMessage({
            id: `agent-${Date.now()}`,
            role: 'agent',
            content: content,
            timestamp: new Date().toISOString()
          });
          setActiveTask({ status: 'idle' });
        } catch (err) {
          console.error(err);
          setActiveTask({ status: 'error' });
        }
      };

      // 1. HELP
      if (taskLower === 'help') {
        const helpText = `Available Quick Commands:
• git status | git push | git pull
• install dependencies | run app
• open project in cursor | open desktop
• what files changed | show errors | check ports
• restart services | stop services | services status
• show memory | what did i do on {project}
• remember this: {note}
• new project: {name}
• cursor do: {instruction}
• create a file at {path} with content: {content}
• read file at {path}
• clear chat`;
        addMessage({
          id: `sys-${Date.now()}`,
          role: 'agent',
          content: helpText,
          timestamp: new Date().toISOString()
        });
        return true;
      }

      // 2. CLEAR CHAT
      if (taskLower === 'clear chat') {
        clearMessages();
        return true;
      }

      // 3. GIT COMMANDS
      if (taskLower === 'git status') {
        await executeQuick({ action: 'terminal', command: 'git status' });
        return true;
      }
      if (taskLower === 'git push') {
        await executeQuick({ action: 'terminal', command: 'git add . && git commit -m "update" && git push origin main' });
        return true;
      }
      if (taskLower === 'git pull') {
        await executeQuick({ action: 'terminal', command: 'git pull' });
        return true;
      }

      // 4. INSTALL & RUN
      if (taskLower === 'install dependencies') {
        await executeQuick({ action: 'terminal', command: 'if [ -f package.json ]; then npm install; elif [ -f requirements.txt ]; then pip3 install -r requirements.txt; else echo "No dependency file found"; fi' });
        return true;
      }
      if (taskLower === 'run app') {
        await executeQuick({ action: 'terminal', command: 'if grep -q "\\"start\\":" package.json 2>/dev/null; then npm start; elif [ -f app.py ]; then python3 app.py; elif [ -f index.js ]; then node index.js; else echo "No start file found"; fi' });
        return true;
      }

      // 5. OPEN ACTIONS
      if (taskLower === 'open project in cursor') {
        await executeQuick({ action: 'terminal', command: `open -a Cursor "${projectPath}"` });
        return true;
      }
      if (taskLower === 'open desktop') {
        await executeQuick({ action: 'terminal', command: 'open /Users/miruzaankhan/Desktop' });
        return true;
      }

      // 6. SYSTEM INFO
      if (taskLower === 'what files changed') {
        await executeQuick({ action: 'terminal', command: 'git diff --name-only' });
        return true;
      }
      if (taskLower === 'show errors') {
        await executeQuick({ action: 'terminal', command: 'cat logs/errors/*.json 2>/dev/null || echo "No error logs found"' });
        return true;
      }
      if (taskLower === 'check ports') {
        await executeQuick({ action: 'terminal', command: 'lsof -i :3000,8000,8001,8002,8765' });
        return true;
      }

      // 7. SERVICES
      if (taskLower === 'restart services') {
        await executeQuick({ action: 'terminal', command: './cammina restart', cwd: '/Users/miruzaankhan/Desktop/cammina' });
        return true;
      }
      if (taskLower === 'stop services') {
        await executeQuick({ action: 'terminal', command: './cammina stop', cwd: '/Users/miruzaankhan/Desktop/cammina' });
        return true;
      }
      if (taskLower === 'services status') {
        await executeQuick({ action: 'terminal', command: './cammina status', cwd: '/Users/miruzaankhan/Desktop/cammina' });
        return true;
      }

      // 8. MEMORY & PROJECTS
      if (taskLower === 'show memory' || taskLower === 'what did i do on') {
        const projName = taskLower.includes('on') ? message.split("on ")[1]?.trim() : selectedProject;
        if (projName) {
          setActiveTask({ status: 'running' });
          try {
            const res = await fetch('/api/memory/search', {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({ query: projName, project_name: projName, limit: 10 })
            });
            const data = await res.json();
            const results = data.results?.map((r: any) => `• ${r.content}`).join('\n') || "No memory found.";
            addMessage({
              id: `agent-${Date.now()}`,
              role: 'agent',
              content: `Memory for ${projName}:\n${results}`,
              timestamp: new Date().toISOString()
            });
          } catch (err) { console.error(err); }
          finally { setActiveTask({ status: 'idle' }); }
          return true;
        }
      }

      if (taskLower.startsWith("remember this:")) {
        if (!selectedProject || selectedProject === 'general') {
          addMessage({ id: `sys-${Date.now()}`, role: 'agent', content: "Please select a project first.", timestamp: new Date().toISOString() });
          return true;
        }
        const note = message.slice(14).trim();
        try {
          const res = await fetch("/api/memory/save", {
            method: "POST",
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify({ content: note, project_name: selectedProject, memory_type: "user_note" })
          });
          const result = await res.json();
          if (result.success) {
            addMessage({ id: `agent-${Date.now()}`, role: 'agent', content: `Saved to ${selectedProject}: "${note}"`, timestamp: new Date().toISOString() });
          }
        } catch (err) { console.error(err); }
        return true;
      }

      if (taskLower.startsWith("new project:")) {
        const name = message.slice(12).trim();
        if (name) {
          try {
            await fetch('/api/memory/project/init', {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({ project_id: `${Date.now()}`, project_name: name })
            });
            addMessage({ id: `sys-${Date.now()}`, role: 'agent', content: `Project "${name}" created.`, timestamp: new Date().toISOString() });
            loadProjects();
          } catch (err) { console.error(err); }
          return true;
        }
      }

      // 9. CORE TOOLS
      const fileWriteMatch = message.match(/create a file at\s+(\S+)\s+with content:\s*(.+)/i);
      if (fileWriteMatch) {
        await executeQuick({ action: 'file_write', path: fileWriteMatch[1], content: fileWriteMatch[2] });
        return true;
      }
      const fileReadMatch = message.match(/read file at\s+(\S+)/i);
      if (fileReadMatch) {
        await executeQuick({ action: 'file_read', path: fileReadMatch[1] });
        return true;
      }
      if (taskLower.startsWith("cursor do:")) {
        await executeQuick({ action: 'cursor_do', instruction: message.slice(10).trim() });
        return true;
      }

      return false;
    };

    const isQuick = await handleQuickAction(userInput);
    if (isQuick) return;

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
        {/* Suggestions Bar */}
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
