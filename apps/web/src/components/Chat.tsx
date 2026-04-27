import { useState, useRef, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useStore } from '../stores';
import { Send, Bot, User, Command } from 'lucide-react';

export default function ChatComponent() {
  const [input, setInput] = useState('');
  const [taskMode, setTaskMode] = useState<'idle' | 'answering'>('idle');
  const [originalTask, setOriginalTask] = useState('');
  const [questions, setQuestions] = useState<string[]>([]);
  const [answers, setAnswers] = useState<string[]>([]);
  
  const [projects, setProjects] = useState<any[]>([]);
  const [selectedProject, setSelectedProject] = useState<string>('general');

  const messages = useStore((state) => state.messages);
  const activeTask = useStore((state) => state.activeTask);
  const { addMessage, setActiveTask } = useStore();
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  useEffect(() => {
    fetch('/api/projects')
      .then(res => res.json())
      .then(data => {
        setProjects(data.projects || []);
      })
      .catch(err => console.error('Failed to load projects:', err));
  }, []);

  const handleSend = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || activeTask.status === 'running') return;

    const userInput = input.trim();
    setInput('');

    const msgId = `${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
    addMessage({
      id: msgId,
      role: 'user',
      content: userInput,
      timestamp: new Date().toISOString()
    });

    const handleQuickAction = async (message: string): Promise<boolean> => {
      const taskLower = message.toLowerCase();
      
      // Memory Commands
      if (taskLower.startsWith("remember this:")) {
        if (!selectedProject || selectedProject === 'general') {
          addMessage({
            id: `sys-${Date.now()}`,
            role: 'agent',
            content: "Please select a project from the dropdown at the top first.",
            timestamp: new Date().toISOString()
          });
          return true;
        }
        
        const note = message.slice(14).trim();
        try {
          const response = await fetch("/api/memory/save", {
            method: "POST",
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify({
              content: note,
              project_name: selectedProject,
              memory_type: "user_note"
            })
          });
          const result = await response.json();
          if (result.success) {
            addMessage({
              id: `agent-${Date.now()}`,
              role: 'agent', 
              content: `Remembered: "${note}" saved to project "${selectedProject}"`,
              timestamp: new Date().toISOString()
            });
          }
        } catch (err) {
          console.error("Memory save failed:", err);
        }
        return true;
      }
      
      if (taskLower.startsWith("what did i do on")) {
        const projName = message.split("on ")[1]?.trim();
        if (projName) {
          setActiveTask({ status: 'running' });
          try {
            const res = await fetch('/api/memory/search', {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({ 
                query: projName, 
                project_name: projName, 
                limit: 10 
              })
            });
            const data = await res.json();
            const results = data.results?.map((r: any) => `• ${r.content}`).join('\n') || "No matching memory found.";
            
            addMessage({
              id: `agent-${Date.now()}`,
              role: 'agent',
              content: `Recent Memory for ${projName}:\n${results}`,
              timestamp: new Date().toISOString()
            });
          } catch (err) {
            console.error(err);
          } finally {
            setActiveTask({ status: 'idle' });
          }
          return true;
        }
      }

      // Helper to execute quick task
      const executeQuick = async (payload: any, successMsg?: string) => {
        setActiveTask({ status: 'running' });
        try {
          let url = '/api/task/quick';
          if (payload.action === 'cursor_do') {
            url = '/api/cursor/autonomous';
            payload = { 
              instruction: payload.instruction, 
              project_path: '/Users/miruzaankhan/Desktop',
              project_name: selectedProject 
            };
          } else {
            payload = { ...payload, project_name: selectedProject };
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
            content = result.success ? `Opened application: ${payload.app}` : `Error: ${result.error}`;
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
            content: `Quick Action: ${content}`,
            timestamp: new Date().toISOString()
          });
          setActiveTask({ status: 'idle' });
        } catch (err) {
          console.error(err);
          setActiveTask({ status: 'error' });
        }
      };

      // 1. Create File
      const fileWriteMatch = message.match(/create a file at\s+(\S+)\s+with content:\s*(.+)/i);
      if (fileWriteMatch) {
        await executeQuick({ action: 'file_write', path: fileWriteMatch[1], content: fileWriteMatch[2] });
        return true;
      }

      // 2. Read File
      const fileReadMatch = message.match(/read file at\s+(\S+)/i);
      if (fileReadMatch) {
        await executeQuick({ action: 'file_read', path: fileReadMatch[1] });
        return true;
      }

      // 3. Cursor Do
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
          body: JSON.stringify({ 
            task: userInput, 
            project_id: selectedProject,
            project_name: selectedProject 
          })
        });
        const data = await response.json();
        
        if (data.questions && data.questions.length > 0) {
          setTaskMode('answering');
          setOriginalTask(userInput);
          setQuestions(data.questions);
          setAnswers([]);
          setActiveTask({ id: data.task_id, status: 'idle' });
          
          addMessage({
            id: `sys-${Date.now()}`,
            role: 'system',
            content: `I have ${data.questions.length} clarifying questions:\n\n1. ${data.questions[0]}`,
            timestamp: new Date().toISOString()
          });
        } else {
          const ansRes = await fetch('/api/task/answer', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ 
              task_id: data.task_id, 
              task: userInput, 
              answers: {}
            })
          });
          
          if (!ansRes.ok) {
            const err = await ansRes.json();
            throw new Error(err.detail || 'Failed to initialize plan');
          }

          const exeRes = await fetch('/api/task/execute', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ task_id: data.task_id })
          });
          
          if (!exeRes.ok) {
            const err = await exeRes.json();
            throw new Error(err.detail || 'Failed to start execution');
          }
          
          setActiveTask({ id: data.task_id, status: 'running' });
        }
      } catch (err: any) {
        console.error(err);
        setActiveTask({ status: 'error' });
        addMessage({
          id: `err-${Date.now()}`,
          role: 'system',
          content: `Error: ${err.message}`,
          timestamp: new Date().toISOString()
        });
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
            body: JSON.stringify({
              task_id: activeTask.id,
              task: originalTask,
              answers: answersDict
            })
          });
          
          await fetch('/api/task/execute', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ task_id: activeTask.id })
          });
        } catch (err) {
          console.error(err);
          setActiveTask({ status: 'error' });
        }
      } else {
        addMessage({
          id: `sys-${Date.now()}`,
          role: 'system',
          content: `Got it. Next: ${questions[newAnswers.length]}`,
          timestamp: new Date().toISOString()
        });
      }
    }
  };

  return (
    <div className="flex flex-col h-full bg-[#0f0f0f] text-gray-200">
      {/* Header with Project Selector */}
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
                msg.role === 'user' 
                  ? 'bg-purple-600' 
                  : msg.role === 'system' 
                    ? 'bg-blue-600' 
                    : 'bg-[#1a1a1a] border border-[#2d2d2d]'
              }`}>
                {msg.role === 'user' ? <User className="w-4 h-4 text-white" /> : 
                 msg.role === 'system' ? <Command className="w-4 h-4 text-white" /> : 
                 <Bot className="w-4 h-4 text-purple-400" />}
              </div>
              
              <div className={`max-w-[80%] rounded-2xl px-5 py-3 ${
                msg.role === 'user' 
                  ? 'bg-purple-600 text-white' 
                  : msg.role === 'system'
                    ? 'bg-blue-900/20 text-blue-300 border border-blue-800/50 text-sm'
                    : 'bg-[#1a1a1a] border border-[#2d2d2d] text-gray-200'
              }`}>
                <pre className="font-sans whitespace-pre-wrap leading-relaxed text-sm">
                  {msg.content}
                </pre>
              </div>
            </motion.div>
          ))}
        </AnimatePresence>
        
        {activeTask.status === 'running' && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="flex items-center gap-3 text-purple-400 p-2"
          >
            <div className="flex gap-1">
              <span className="w-1.5 h-1.5 bg-purple-500 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
              <span className="w-1.5 h-1.5 bg-purple-500 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
              <span className="w-1.5 h-1.5 bg-purple-500 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
            </div>
            <span className="text-sm font-medium">Cammina AI is thinking...</span>
          </motion.div>
        )}
        <div ref={messagesEndRef} />
      </div>

      <div className="p-4 bg-[#0f0f0f]">
        <form onSubmit={handleSend} className="relative max-w-4xl mx-auto">
          <input
            type="text"
            value={input}
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
