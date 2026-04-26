import { useState, useRef, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useStore } from '../stores';
import { Send, Bot, User, Command } from 'lucide-react';

export default function ChatComponent() {
  const [input, setInput] = useState('');
  const messages = useStore((state) => state.messages);
  const activeTask = useStore((state) => state.activeTask);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleSend = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim()) return;

    // TODO: implement API call to start/answer task
    useStore.getState().addMessage({
      id: Date.now().toString(),
      role: 'user',
      content: input,
      timestamp: new Date().toISOString()
    });
    
    setInput('');
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
