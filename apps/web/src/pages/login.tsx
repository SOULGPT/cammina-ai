import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import { useStore } from '../stores';
import { Command, Github } from 'lucide-react';

export default function Login() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const navigate = useNavigate();
  const setUser = useStore((state) => state.setUser);

  const handleLogin = (e: React.FormEvent) => {
    e.preventDefault();
    // Fake login
    setUser({ name: 'User', email });
    navigate('/chat');
  };

  return (
    <div className="min-h-screen flex items-center justify-center p-4">
      <motion.div 
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5, ease: "easeOut" }}
        className="w-full max-w-md"
      >
        <div className="flex justify-center mb-8">
          <div className="w-12 h-12 rounded-xl bg-gradient-to-tr from-purple-600 to-blue-500 flex items-center justify-center shadow-lg shadow-purple-500/20">
            <Command className="text-white w-6 h-6" />
          </div>
        </div>
        
        <div className="bg-[#1a1a1a] border border-[#2d2d2d] rounded-2xl p-8 shadow-2xl backdrop-blur-xl">
          <h1 className="text-2xl font-semibold text-center mb-2">Welcome to Cammina AI</h1>
          <p className="text-gray-400 text-center text-sm mb-8">Sign in to orchestrate your agents</p>
          
          <form onSubmit={handleLogin} className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-400 mb-1">Email</label>
              <input 
                type="email" 
                required
                className="w-full bg-[#0f0f0f] border border-[#2d2d2d] rounded-lg px-4 py-2 text-sm focus:outline-none focus:border-purple-500 focus:ring-1 focus:ring-purple-500 transition-colors"
                placeholder="you@example.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-400 mb-1">Password</label>
              <input 
                type="password" 
                required
                className="w-full bg-[#0f0f0f] border border-[#2d2d2d] rounded-lg px-4 py-2 text-sm focus:outline-none focus:border-purple-500 focus:ring-1 focus:ring-purple-500 transition-colors"
                placeholder="••••••••"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
              />
            </div>
            
            <button 
              type="submit"
              className="w-full bg-purple-600 hover:bg-purple-700 text-white font-medium rounded-lg px-4 py-2.5 transition-colors mt-2"
            >
              Sign In
            </button>
          </form>

          <div className="mt-6 flex items-center justify-between">
            <hr className="w-full border-[#2d2d2d]" />
            <span className="p-2 text-xs text-gray-500 font-medium">OR</span>
            <hr className="w-full border-[#2d2d2d]" />
          </div>

          <div className="mt-6 space-y-3">
            <button className="w-full flex items-center justify-center gap-2 bg-[#2d2d2d] hover:bg-[#3d3d3d] text-white font-medium rounded-lg px-4 py-2.5 transition-colors">
              <Github className="w-4 h-4" />
              Continue with GitHub
            </button>
            <button className="w-full flex items-center justify-center gap-2 bg-[#2d2d2d] hover:bg-[#3d3d3d] text-white font-medium rounded-lg px-4 py-2.5 transition-colors">
              <svg className="w-4 h-4" viewBox="0 0 24 24"><path fill="currentColor" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" /><path fill="currentColor" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" /><path fill="currentColor" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" /><path fill="currentColor" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" /></svg>
              Continue with Google
            </button>
          </div>
          
          <p className="mt-8 text-center text-xs text-gray-500">
            Don't have an account? <a href="#" className="text-purple-400 hover:text-purple-300">Sign up</a>
          </p>
        </div>
      </motion.div>
    </div>
  );
}
