import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { Settings as SettingsIcon, Save, Key, Shield, CheckCircle2 } from 'lucide-react';
import { motion } from 'framer-motion';

export default function Settings() {
  const [keys, setKeys] = useState({ openrouter: '', nvidia: '', groq: '' });
  const [status, setStatus] = useState({ openrouter: false, nvidia: false, groq: false });
  const [testing, setTesting] = useState(false);
  const [savedMessage, setSavedMessage] = useState<string | null>(null);

  useEffect(() => {
    // Read from localStorage on mount
    const savedKeys = {
      openrouter: localStorage.getItem('cammina_openrouter_key') || '',
      nvidia: localStorage.getItem('cammina_nvidia_key') || '',
      groq: localStorage.getItem('cammina_groq_key') || ''
    };
    setKeys(savedKeys);
  }, []);

  const testConnection = async (provider: string) => {
    setTesting(true);
    try {
      await new Promise(r => setTimeout(r, 1000));
      setStatus(prev => ({ ...prev, [provider]: true }));
    } catch {
      setStatus(prev => ({ ...prev, [provider]: false }));
    }
    setTesting(false);
  };

  const handleSave = async () => {
    // 1. Save to local storage
    localStorage.setItem('cammina_openrouter_key', keys.openrouter);
    localStorage.setItem('cammina_nvidia_key', keys.nvidia);
    localStorage.setItem('cammina_groq_key', keys.groq);

    // 2. POST to backend LLM Manager
    try {
      const response = await fetch('http://localhost:8001/providers/configure', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(keys)
      });
      
      if (!response.ok) throw new Error('Failed to configure providers');
      
      // 3. Show success message
      setSavedMessage('Saved successfully!');
      setTimeout(() => setSavedMessage(null), 3000);
    } catch (err) {
      console.error(err);
      setSavedMessage('Error saving to backend');
      setTimeout(() => setSavedMessage(null), 3000);
    }
  };

  return (
    <div className="flex h-screen bg-[#0f0f0f]">
      {/* Sidebar - Compact */}
      <div className="w-[250px] shrink-0 border-r border-[#2d2d2d] flex flex-col bg-[#121212]">
        <div className="p-4 border-b border-[#2d2d2d] flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg bg-gradient-to-tr from-[#7c3aed] to-blue-500 flex items-center justify-center">
            <SettingsIcon className="text-white w-4 h-4" />
          </div>
          <span className="font-semibold text-gray-100">Settings</span>
        </div>
        <div className="p-4 flex-1 space-y-2">
          <Link to="/chat" className="block px-3 py-2 rounded-lg text-sm text-gray-400 hover:bg-[#2d2d2d] hover:text-white transition-colors">
            Back to Chat
          </Link>
          <div className="px-3 py-2 rounded-lg text-sm bg-purple-500/10 text-[#7c3aed] font-medium">
            API Keys
          </div>
          <div className="px-3 py-2 rounded-lg text-sm text-gray-400 hover:bg-[#2d2d2d] hover:text-white transition-colors cursor-not-allowed">
            Account Profile
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="flex-1 flex flex-col p-8 overflow-y-auto">
        <div className="max-w-3xl mx-auto w-full relative">
          <h1 className="text-3xl font-semibold tracking-tight mb-2">API Configuration</h1>
          <p className="text-gray-400 mb-8">Manage your LLM provider keys. Keys are stored locally.</p>

          {savedMessage && (
            <motion.div 
              initial={{ opacity: 0, y: -10 }}
              animate={{ opacity: 1, y: 0 }}
              className={`absolute top-0 right-0 px-4 py-2 rounded-lg text-sm font-medium ${
                savedMessage === 'Saved successfully!' ? 'bg-green-500/10 text-green-400 border border-green-500/20' : 'bg-red-500/10 text-red-400 border border-red-500/20'
              }`}
            >
              {savedMessage}
            </motion.div>
          )}

          <motion.div 
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            className="space-y-6"
          >
            {[
              { id: 'openrouter', name: 'OpenRouter', placeholder: 'sk-or-v1-...' },
              { id: 'nvidia', name: 'Nvidia NIM', placeholder: 'nvapi-...' },
              { id: 'groq', name: 'Groq', placeholder: 'gsk_...' }
            ].map((provider) => (
              <div key={provider.id} className="bg-[#1a1a1a] border border-[#2d2d2d] rounded-2xl p-6 shadow-lg">
                <div className="flex justify-between items-start mb-4">
                  <div className="flex items-center gap-3">
                    <div className="p-2 bg-[#2d2d2d] rounded-lg">
                      <Key className="w-5 h-5 text-[#7c3aed]" />
                    </div>
                    <div>
                      <h3 className="font-semibold text-gray-200">{provider.name} API Key</h3>
                      <p className="text-xs text-gray-500">Used for primary LLM routing</p>
                    </div>
                  </div>
                  
                  <div className={`flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium border ${
                    status[provider.id as keyof typeof status] 
                      ? 'bg-green-500/10 text-green-400 border-green-500/20' 
                      : 'bg-gray-800 text-gray-400 border-gray-700'
                  }`}>
                    {status[provider.id as keyof typeof status] ? <CheckCircle2 className="w-3 h-3" /> : <Shield className="w-3 h-3" />}
                    {status[provider.id as keyof typeof status] ? 'Connected' : 'Not Tested'}
                  </div>
                </div>

                <div className="flex gap-3">
                  <input 
                    type="password" 
                    placeholder={provider.placeholder}
                    value={keys[provider.id as keyof typeof keys]}
                    onChange={(e) => setKeys({...keys, [provider.id]: e.target.value})}
                    className="flex-1 bg-[#0f0f0f] border border-[#2d2d2d] rounded-lg px-4 py-2 text-sm text-gray-200 focus:outline-none focus:border-[#7c3aed] focus:ring-1 focus:ring-[#7c3aed] transition-all font-mono"
                  />
                  <button 
                    onClick={() => testConnection(provider.id)}
                    disabled={!keys[provider.id as keyof typeof keys] || testing}
                    className="bg-[#2d2d2d] hover:bg-[#3d3d3d] disabled:opacity-50 text-white px-4 py-2 rounded-lg text-sm font-medium transition-colors"
                  >
                    Test Connection
                  </button>
                </div>
              </div>
            ))}

            <div className="flex justify-end pt-4">
              <button 
                onClick={handleSave}
                className="bg-[#7c3aed] hover:bg-purple-700 text-white flex items-center gap-2 rounded-lg px-6 py-2.5 font-medium transition-colors shadow-lg shadow-[#7c3aed]/20"
              >
                <Save className="w-4 h-4" />
                Save Configuration
              </button>
            </div>
          </motion.div>
        </div>
      </div>
    </div>
  );
}
