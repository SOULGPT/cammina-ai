import { create } from 'zustand';

export type TaskStatus = 'pending' | 'running' | 'paused' | 'paused_error' | 'completed' | 'error' | 'idle';

export interface TaskState {
  id: string | null;
  status: TaskStatus;
  currentStep: number;
  totalSteps: number;
}

export interface Message {
  id: string;
  role: 'user' | 'agent' | 'system';
  content: string;
  timestamp: string;
}

export interface Project {
  id: string;
  name: string;
  status: 'active' | 'completed';
  updatedAt: string;
}

interface AppState {
  // Global App State
  user: { id: string; email: string } | null | undefined;
  projects: Project[];
  activeProvider: string;
  wsConnected: boolean;

  // Active Task State
  activeTask: TaskState;
  messages: Message[];
  selectedProject: string;

  // Actions
  setUser: (user: { id: string; email: string } | null) => void;
  setProjects: (projects: Project[]) => void;
  setActiveProvider: (provider: string) => void;
  setWsConnected: (connected: boolean) => void;
  
  setActiveTask: (task: Partial<TaskState>) => void;
  addMessage: (message: Message) => void;
  setMessages: (messages: Message[]) => void;
  clearMessages: () => void;
  setSelectedProject: (project: string) => void;
  resetTaskState: () => void;
}

export const useStore = create<AppState>((set) => ({
  user: undefined, // undefined means auth state is still loading
  projects: [
    { id: '1', name: 'Build React App', status: 'active', updatedAt: new Date().toISOString() },
    { id: '2', name: 'Data Pipeline', status: 'completed', updatedAt: new Date(Date.now() - 86400000).toISOString() }
  ],
  activeProvider: 'openrouter',
  wsConnected: false,

  activeTask: {
    id: null,
    status: 'idle',
    currentStep: 0,
    totalSteps: 0,
  },
  messages: [],
  selectedProject: 'general',

  setUser: (user) => set({ user }),
  setProjects: (projects) => set({ projects }),
  setActiveProvider: (activeProvider) => set({ activeProvider }),
  setWsConnected: (wsConnected) => set({ wsConnected }),

  setActiveTask: (task) => set((state) => ({ 
    activeTask: { ...state.activeTask, ...task } 
  })),
  addMessage: (message) => set((state) => ({ 
    messages: [...state.messages, message] 
  })),
  setMessages: (messages) => set({ messages }),
  clearMessages: () => set({ messages: [] }),
  setSelectedProject: (selectedProject) => set({ selectedProject }),
  
  resetTaskState: () => set({
    activeTask: { id: null, status: 'idle', currentStep: 0, totalSteps: 0 },
    messages: [],
    selectedProject: 'general'
  })
}));
