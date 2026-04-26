import { useParams, Link } from 'react-router-dom';
import { useStore } from '../../stores';
import { Folder, ArrowLeft, BrainCircuit, TerminalSquare, AlertCircle } from 'lucide-react';

export default function ProjectDetails() {
  const { id } = useParams();
  const project = useStore(state => state.projects.find(p => p.id === id));

  if (!project) {
    return <div className="p-8 text-center text-gray-400">Project not found</div>;
  }

  return (
    <div className="flex h-screen bg-[#0f0f0f] text-gray-200">
      <div className="flex-1 flex flex-col p-8 overflow-y-auto">
        <div className="max-w-6xl mx-auto w-full">
          <Link to="/projects" className="flex items-center gap-2 text-sm text-gray-500 hover:text-white transition-colors mb-6">
            <ArrowLeft className="w-4 h-4" />
            Back to Projects
          </Link>

          <div className="flex justify-between items-start mb-8">
            <div className="flex items-center gap-4">
              <div className="w-12 h-12 rounded-xl bg-[#2d2d2d] flex items-center justify-center shadow-lg">
                <Folder className="w-6 h-6 text-purple-400" />
              </div>
              <div>
                <h1 className="text-3xl font-semibold tracking-tight">{project.name}</h1>
                <p className="text-sm text-gray-500 mt-1">Project ID: {project.id}</p>
              </div>
            </div>
            
            <span className={`px-3 py-1 text-xs font-semibold uppercase tracking-wide rounded-full ${
              project.status === 'active' ? 'bg-green-500/10 text-green-400 border border-green-500/20' : 'bg-gray-500/10 text-gray-400 border border-gray-500/20'
            }`}>
              {project.status}
            </span>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            <div className="lg:col-span-2 space-y-6">
              {/* Task History */}
              <div className="bg-[#1a1a1a] border border-[#2d2d2d] rounded-2xl p-6 shadow-lg">
                <h2 className="text-lg font-semibold flex items-center gap-2 mb-4">
                  <TerminalSquare className="w-5 h-5 text-blue-400" />
                  Task History
                </h2>
                <div className="space-y-3 text-sm">
                  <div className="p-3 bg-[#0f0f0f] border border-[#2d2d2d] rounded-lg">
                    <span className="text-gray-400 font-mono text-xs block mb-1">Yesterday</span>
                    Scaffolded React application with Vite and Tailwind
                  </div>
                  <div className="p-3 bg-[#0f0f0f] border border-[#2d2d2d] rounded-lg">
                    <span className="text-gray-400 font-mono text-xs block mb-1">2 days ago</span>
                    Initialized git repository and structure
                  </div>
                </div>
              </div>

              {/* Error Log */}
              <div className="bg-[#1a1a1a] border border-[#2d2d2d] rounded-2xl p-6 shadow-lg">
                <h2 className="text-lg font-semibold flex items-center gap-2 mb-4">
                  <AlertCircle className="w-5 h-5 text-red-400" />
                  Resolved Errors
                </h2>
                <div className="space-y-3 text-sm">
                  <div className="p-3 bg-red-950/20 border border-red-900/30 rounded-lg text-gray-300">
                    <span className="text-red-400 font-mono text-xs block mb-1">npm ERR! code ERESOLVE</span>
                    Fixed dependency conflict with eslint peer dependencies
                  </div>
                </div>
              </div>
            </div>

            <div className="space-y-6">
              {/* Memory Insights */}
              <div className="bg-[#1a1a1a] border border-[#2d2d2d] rounded-2xl p-6 shadow-lg">
                <h2 className="text-lg font-semibold flex items-center gap-2 mb-4">
                  <BrainCircuit className="w-5 h-5 text-purple-400" />
                  Memory Vectors
                </h2>
                <div className="text-center p-6 border border-dashed border-[#2d2d2d] rounded-xl">
                  <p className="text-3xl font-bold text-gray-200 mb-1">128</p>
                  <p className="text-xs text-gray-500 uppercase tracking-wide">Embeddings Stored</p>
                </div>
              </div>
            </div>
          </div>

        </div>
      </div>
    </div>
  );
}
