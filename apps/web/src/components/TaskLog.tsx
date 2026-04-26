import { motion } from 'framer-motion';
import { useStore } from '../stores';
import { Play, Pause, Square, Cpu, Server, CheckCircle2, AlertCircle } from 'lucide-react';

export default function TaskLog() {
  const { activeTask, activeProvider, wsConnected } = useStore();

  const progress = activeTask.totalSteps > 0 
    ? Math.min(100, Math.round((activeTask.currentStep / activeTask.totalSteps) * 100))
    : 0;

  return (
    <div className="flex flex-col h-full bg-[#121212] p-6 gap-6 overflow-y-auto">
      <div>
        <h2 className="text-lg font-semibold text-gray-100 flex items-center gap-2 mb-4">
          <Server className="w-5 h-5 text-purple-500" />
          Task Execution
        </h2>
        
        {/* Status Card */}
        <div className="bg-[#1a1a1a] border border-[#2d2d2d] rounded-xl p-4 shadow-lg mb-6">
          <div className="flex justify-between items-center mb-3">
            <span className="text-sm font-medium text-gray-400">Status</span>
            <span className="flex items-center gap-2 text-xs font-medium px-2.5 py-1 rounded-full bg-[#2d2d2d]">
              <span className={`w-2 h-2 rounded-full ${wsConnected ? 'bg-green-500' : 'bg-red-500'}`} />
              {wsConnected ? 'Connected' : 'Offline'}
            </span>
          </div>
          <div className="flex items-center gap-3">
            <div className={`p-2 rounded-lg ${
              activeTask.status === 'running' ? 'bg-purple-500/20 text-purple-400 animate-pulse' :
              activeTask.status === 'completed' ? 'bg-green-500/20 text-green-400' :
              activeTask.status === 'paused_error' ? 'bg-red-500/20 text-red-400' :
              'bg-gray-500/20 text-gray-400'
            }`}>
              {activeTask.status === 'running' ? <Cpu className="w-5 h-5" /> :
               activeTask.status === 'completed' ? <CheckCircle2 className="w-5 h-5" /> :
               activeTask.status === 'paused_error' ? <AlertCircle className="w-5 h-5" /> :
               <Pause className="w-5 h-5" />}
            </div>
            <span className="font-semibold text-gray-200 capitalize">
              {activeTask.status === 'idle' ? 'Ready' : activeTask.status.replace('_', ' ')}
            </span>
          </div>
        </div>

        {/* Progress Tracker */}
        <div className="bg-[#1a1a1a] border border-[#2d2d2d] rounded-xl p-4 shadow-lg mb-6">
          <div className="flex justify-between text-sm mb-2">
            <span className="font-medium text-gray-300">Progress</span>
            <span className="text-purple-400 font-bold">{progress}%</span>
          </div>
          <div className="w-full bg-[#2d2d2d] rounded-full h-2 mb-3 overflow-hidden">
            <motion.div 
              className="bg-gradient-to-r from-purple-600 to-blue-500 h-2 rounded-full"
              initial={{ width: 0 }}
              animate={{ width: `${progress}%` }}
              transition={{ duration: 0.5 }}
            />
          </div>
          <p className="text-xs text-gray-500 text-center">
            Step {activeTask.currentStep} of {activeTask.totalSteps || '?'}
          </p>
        </div>

        {/* Controls */}
        <div className="grid grid-cols-3 gap-3 mb-6">
          <button className="flex flex-col items-center justify-center gap-2 p-3 bg-[#1a1a1a] border border-[#2d2d2d] hover:bg-[#252525] hover:border-purple-500/50 rounded-xl transition-all text-gray-300">
            <Play className="w-4 h-4" />
            <span className="text-xs font-medium">Resume</span>
          </button>
          <button className="flex flex-col items-center justify-center gap-2 p-3 bg-[#1a1a1a] border border-[#2d2d2d] hover:bg-[#252525] rounded-xl transition-all text-gray-300">
            <Pause className="w-4 h-4" />
            <span className="text-xs font-medium">Pause</span>
          </button>
          <button className="flex flex-col items-center justify-center gap-2 p-3 bg-[#1a1a1a] border border-red-900/30 hover:bg-red-900/20 text-red-400 rounded-xl transition-all">
            <Square className="w-4 h-4" />
            <span className="text-xs font-medium">Stop</span>
          </button>
        </div>

        {/* Provider */}
        <div className="bg-[#1a1a1a] border border-[#2d2d2d] rounded-xl p-4 shadow-lg">
          <span className="text-sm font-medium text-gray-400 block mb-2">Active LLM Provider</span>
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded bg-gradient-to-br from-gray-800 to-gray-900 border border-gray-700 flex items-center justify-center">
              <Cpu className="w-4 h-4 text-purple-400" />
            </div>
            <span className="font-semibold text-gray-200 capitalize">{activeProvider}</span>
          </div>
        </div>
      </div>
    </div>
  );
}
