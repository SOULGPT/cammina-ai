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

    if (taskMode === 'idle') {
      // Check for Quick Task patterns
      const taskLower = userInput.toLowerCase();
      
      // 1. Quick File Write: "create a file at {path} with content: {content}"
      if (taskLower.startsWith("create a file at")) {
        const pathMatch = userInput.match(/create a file at\s+(\S+)\s+with content:\s*(.+)/i);
        if (pathMatch) {
          const path = pathMatch[1];
          const content = pathMatch[2];
          
          setActiveTask({ status: 'running' });
          try {
            const res = await fetch('/api/task/quick', {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({ action: "file_write", path: path, content: content })
            });
            const result = await res.json();
            
            if (result.success) {
              addMessage({
                id: Date.now().toString(),
                role: 'bot',
                content: `File created successfully at ${path}`,
                timestamp: new Date().toISOString()
              });
            } else {
              addMessage({
                id: Date.now().toString(),
                role: 'bot',
                content: `Error: ${result.error || 'Failed to create file'}`,
                timestamp: new Date().toISOString()
              });
            }
            setActiveTask({ status: 'idle' });
            return;
          } catch (err) {
            console.error(err);
            setActiveTask({ status: 'error' });
            return;
          }
        }
      }
      
      // 2. Quick Terminal: "run command: {command}"
      if (taskLower.startsWith("run command:")) {
        const cmd = userInput.split(/run command:/i)[1].trim();
        setActiveTask({ status: 'running' });
        try {
          const res = await fetch('/api/task/quick', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ action: "terminal", command: cmd })
          });
          const result = await res.json();
          addMessage({
            id: Date.now().toString(),
            role: 'bot',
            content: `Quick Action: Terminal command executed.\n\nOutput:\n${result.stdout || result.stderr || 'No output'}`,
            timestamp: new Date().toISOString()
          });
          setActiveTask({ status: 'idle' });
          return;
        } catch (err) {
          console.error(err);
          setActiveTask({ status: 'error' });
          return;
        }
      }

      // 3. Quick File Read: "read file at {path}"
      if (taskLower.startsWith("read file at")) {
        const pathPart = userInput.split(/read file at/i)[1].trim();
        setActiveTask({ status: 'running' });
        try {
          const res = await fetch('/api/task/quick', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ action: "file_read", path: pathPart })
          });
          const result = await res.json();
          addMessage({
            id: Date.now().toString(),
            role: 'bot',
            content: `Quick Action: File read completed.\n\nContent:\n${result.content || result.error || 'No content'}`,
            timestamp: new Date().toISOString()
          });
          setActiveTask({ status: 'idle' });
          return;
        } catch (err) {
          console.error(err);
          setActiveTask({ status: 'error' });
          return;
        }
      }

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
