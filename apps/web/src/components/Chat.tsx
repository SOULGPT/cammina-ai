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

  const handleSend = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || activeTask.status === 'running') return;

    const userInput = input.trim();
    setInput('');

    addMessage({
      id: Date.now().toString(),
      role: 'user',
      content: userInput,
      timestamp: new Date().toISOString()
    });

    const handleQuickAction = async (message: string): Promise<boolean> => {
      const taskLower = message.toLowerCase();
      
      // 0. Help Command
      if (taskLower === "help") {
        addMessage({
          id: Date.now().toString(),
          role: 'system',
          content: `Available Quick Commands:
• help - Show this message
• create a file at {path} with content: {content}
• read file at {path}
• run command: {command}
• delete file at {path}
• list files in {path}
• create folder at {path}
• run python {path}
• copy file from {src} to {dst}
• show desktop - List files on your desktop
• open cursor - Opens the Cursor application
• screenshot - Takes a full-screen screenshot
• type in cursor: {text} - Types text into Cursor chat
• type in antigravity: {text} - Types text into Antigravity chat
• focus {app} - Brings an application to the foreground
• cursor do: {instruction} - Starts an autonomous multi-round task with Cursor`,
          timestamp: new Date().toISOString()
        });
        return true;
      }

      // Helper to execute quick task
      const executeQuick = async (payload: any, successMsg?: string) => {
        setActiveTask({ status: 'running' });
        try {
          let url = '/api/task/quick';
          if (payload.action === 'cursor_do') {
            url = '/api/cursor/autonomous';
            payload = { instruction: payload.instruction, project_path: '/Users/miruzaankhan/Desktop' };
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
          } else if (payload.action === 'cursor_type' || payload.action === 'cursor_type_antigravity') {
            content = result.success ? `Typed text into focused window.` : `Error: ${result.error}`;
          } else if (payload.action === 'cursor_focus') {
            content = result.success ? `Focused application: ${payload.app}` : `Error: ${result.error}`;
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
            id: Date.now().toString(),
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

      // 3. Run Command
      if (taskLower.startsWith("run command:")) {
        const cmd = message.split(/run command:/i)[1].trim();
        await executeQuick({ action: 'terminal', command: cmd });
        return true;
      }

      // 4. Delete File
      const deleteMatch = message.match(/delete file at\s+(\S+)/i);
      if (deleteMatch) {
        await executeQuick({ action: 'terminal', command: `rm ${deleteMatch[1]}` }, `File deleted: ${deleteMatch[1]}`);
        return true;
      }

      // 5. List Files
      const listMatch = message.match(/list files in\s+(\S+)/i);
      if (listMatch) {
        await executeQuick({ action: 'terminal', command: `ls -la ${listMatch[1]}` });
        return true;
      }

      // 6. Create Folder
      const folderMatch = message.match(/create folder at\s+(\S+)/i);
      if (folderMatch) {
        await executeQuick({ action: 'terminal', command: `mkdir -p ${folderMatch[1]}` }, `Folder created: ${folderMatch[1]}`);
        return true;
      }

      // 7. Run Python
      const pythonMatch = message.match(/run python\s+(\S+)/i);
      if (pythonMatch) {
        await executeQuick({ action: 'terminal', command: `python3 ${pythonMatch[1]}` });
        return true;
      }

      // 8. Copy File
      const copyMatch = message.match(/copy file from\s+(\S+)\s+to\s+(\S+)/i);
      if (copyMatch) {
        await executeQuick({ action: 'terminal', command: `cp ${copyMatch[1]} ${copyMatch[2]}` }, `Copied ${copyMatch[1]} to ${copyMatch[2]}`);
        return true;
      }

      // 9. Show Desktop
      if (taskLower === "show desktop") {
        await executeQuick({ action: 'terminal', command: `ls -la /Users/miruzaankhan/Desktop` });
        return true;
      }

      // 10. Open Cursor
      if (taskLower === "open cursor") {
        await executeQuick({ action: 'app_open', app: 'Cursor' });
        return true;
      }

      // 11. Screenshot
      if (taskLower === "screenshot") {
        await executeQuick({ action: 'screenshot' });
        return true;
      }

      // 12. Type in Cursor
      if (taskLower.startsWith("type in cursor:")) {
        const text = message.split(/type in cursor:/i)[1].trim();
        await executeQuick({ action: 'cursor_type', text: text });
        return true;
      }

      // 13. Type in Antigravity
      if (taskLower.startsWith("type in antigravity:")) {
        const text = message.split(/type in antigravity:/i)[1].trim();
        await executeQuick({ action: 'cursor_type_antigravity', text: text });
        return true;
      }

      // 14. Focus App
      const focusMatch = message.match(/focus\s+(.+)/i);
      if (focusMatch && !taskLower.includes("cursor") && !taskLower.includes("antigravity")) {
        await executeQuick({ action: 'cursor_focus', app: focusMatch[1] });
        return true;
      }

      // 15. Cursor Do (Autonomous)
      if (taskLower.startsWith("cursor do:")) {
        const instruction = message.split(/cursor do:/i)[1].trim();
        await executeQuick({ action: 'cursor_do', instruction });
        return true;
      }

      return false;
    };

    if (taskMode === 'idle') {
      if (await handleQuickAction(userInput)) return;

      setActiveTask({ status: 'running' });
      setOriginalTask(userInput);
      
      try {
        const res = await fetch('/api/task/start', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            task: userInput,
            project_id: "default",
            project_name: "Default"
          })
        });

        if (!res.ok) throw new Error('Failed to start task');
        const data = await res.json();
        
        setActiveTask({ id: data.task_id, status: 'idle' });
        
        if (data.questions && data.questions.length > 0) {
          setQuestions(data.questions);
          setAnswers([]);
          setTaskMode('answering');
          
          addMessage({
            id: (Date.now() + 1).toString(),
            role: 'system',
            content: `I have a few clarifying questions:\n\n${data.questions.map((q: string, i: number) => `${i + 1}. ${q}`).join('\n')}\n\n(Answer them sequentially, or type 'skip' to proceed immediately)`,
            timestamp: new Date().toISOString()
          });
        } else {
          await fetch('/api/task/execute', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ task_id: data.task_id })
          });
        }
      } catch (err) {
        console.error(err);
        setActiveTask({ status: 'error' });
      }
    } else if (taskMode === 'answering') {
      const newAnswers = [...answers, userInput];
      setAnswers(newAnswers);
      
      if (newAnswers.length >= questions.length || userInput.toLowerCase() === 'skip') {
        setTaskMode('idle');
        setActiveTask({ status: 'running' });
        
        try {
          // Format answers as a dict for the orchestrator
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
        // Prompt for the next question
        addMessage({
          id: (Date.now() + 1).toString(),
          role: 'system',
          content: `Got it. Next: ${questions[newAnswers.length]}`,
          timestamp: new Date().toISOString()
        });
      }
    }
  };

  return (
    <div className="flex flex-col h-full bg-[#0f0f0f] border-r border-[#2d2d2d]">
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
                <pre className="font-sans whitespace-pre-wrap leading-relaxed">
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
