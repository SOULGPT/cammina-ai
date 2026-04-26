import { Routes, Route, Navigate } from 'react-router-dom';
import { useStore } from './stores';
import Login from './pages/login';
import Chat from './pages/chat';
import Projects from './pages/projects';
import Settings from './pages/settings';
import ProjectDetails from './pages/project/[id]';

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const user = useStore((state) => state.user);
  if (!user) {
    return <Navigate to="/login" replace />;
  }
  return <>{children}</>;
}

export default function App() {
  return (
    <div className="dark bg-[#0f0f0f] text-gray-100 min-h-screen font-sans antialiased selection:bg-purple-500/30">
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route path="/" element={<Navigate to="/chat" replace />} />
        
        {/* Protected Routes */}
        <Route path="/chat" element={
          <ProtectedRoute><Chat /></ProtectedRoute>
        } />
        <Route path="/projects" element={
          <ProtectedRoute><Projects /></ProtectedRoute>
        } />
        <Route path="/project/:id" element={
          <ProtectedRoute><ProjectDetails /></ProtectedRoute>
        } />
        <Route path="/settings" element={
          <ProtectedRoute><Settings /></ProtectedRoute>
        } />
      </Routes>
    </div>
  );
}
