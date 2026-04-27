import { useEffect } from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import { useStore } from './stores';
import { supabase } from './lib/supabase';
import Login from './pages/login';
import Signup from './pages/signup';
import Chat from './pages/chat';
import Projects from './pages/projects';
import Settings from './pages/settings';
import ProjectDetails from './pages/ProjectDetails';

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const user = useStore((state) => state.user);
  
  if (user === undefined) {
    return <div className="min-h-screen flex items-center justify-center bg-[#0f0f0f] text-purple-500">Loading...</div>;
  }
  
  if (user === null) {
    return <Navigate to="/login" replace />;
  }
  
  return <>{children}</>;
}

export default function App() {
  const setUser = useStore((state) => state.setUser);

  useEffect(() => {
    // Check active session on load
    supabase.auth.getSession().then(({ data: { session } }) => {
      setUser(session?.user ? { id: session.user.id, email: session.user.email || '' } : null);
    });

    // Listen for auth changes
    const { data: { subscription } } = supabase.auth.onAuthStateChange((_event, session) => {
      setUser(session?.user ? { id: session.user.id, email: session.user.email || '' } : null);
    });

    return () => subscription.unsubscribe();
  }, [setUser]);

  return (
    <div className="dark bg-[#0f0f0f] text-gray-100 min-h-screen font-sans antialiased selection:bg-purple-500/30">
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route path="/signup" element={<Signup />} />
        <Route path="/" element={<Navigate to="/chat" replace />} />
        
        {/* Protected Routes */}
        <Route path="/chat" element={
          <ProtectedRoute><Chat /></ProtectedRoute>
        } />
        <Route path="/projects" element={
          <ProtectedRoute><Projects /></ProtectedRoute>
        } />
        <Route path="/project/:projectName" element={
          <ProtectedRoute><ProjectDetails /></ProtectedRoute>
        } />
        <Route path="/settings" element={
          <ProtectedRoute><Settings /></ProtectedRoute>
        } />
      </Routes>
    </div>
  );
}
