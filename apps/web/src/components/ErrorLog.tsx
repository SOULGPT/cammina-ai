import { AlertCircle, XCircle } from 'lucide-react';
import { useStore } from '../stores';
import { motion, AnimatePresence } from 'framer-motion';

export default function ErrorLog() {
  const messages = useStore((state) => state.messages);
  const errors = messages.filter(m => m.role === 'system' && m.content.includes('Error'));

  return (
    <div className="bg-[#121212] border-t border-[#2d2d2d] h-48 overflow-y-auto p-4 scrollbar-thin scrollbar-thumb-[#2d2d2d]">
      <h3 className="text-red-400 font-semibold text-sm flex items-center gap-2 mb-3">
        <AlertCircle className="w-4 h-4" />
        Error Log ({errors.length})
      </h3>
      
      <div className="space-y-2">
        <AnimatePresence>
          {errors.length === 0 ? (
            <p className="text-gray-500 text-sm">No errors in current session.</p>
          ) : (
            errors.map((err) => (
              <motion.div 
                key={err.id}
                initial={{ opacity: 0, x: -10 }}
                animate={{ opacity: 1, x: 0 }}
                className="bg-red-950/20 border border-red-900/30 rounded p-3 flex items-start gap-3"
              >
                <XCircle className="w-4 h-4 text-red-500 mt-0.5 shrink-0" />
                <div className="text-sm text-gray-300 font-mono whitespace-pre-wrap">
                  {err.content}
                </div>
              </motion.div>
            ))
          )}
        </AnimatePresence>
      </div>
    </div>
  );
}
