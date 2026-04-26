import { useEffect, useRef } from 'react';
import { useStore } from '../stores';

const ORCHESTRATOR_WS_URL = 'ws://localhost:8000';

export function useTaskWebSocket(taskId: string | null) {
  const ws = useRef<WebSocket | null>(null);
  const { setWsConnected, addMessage, setActiveTask } = useStore();

  useEffect(() => {
    if (!taskId) return;

    const connect = () => {
      ws.current = new WebSocket(`${ORCHESTRATOR_WS_URL}/task/stream/${taskId}`);

      ws.current.onopen = () => {
        setWsConnected(true);
        console.log(`Connected to task stream: ${taskId}`);
      };

      ws.current.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          handleWebSocketMessage(data);
        } catch (err) {
          console.error("Failed to parse WS message", err);
        }
      };

      ws.current.onclose = () => {
        setWsConnected(false);
        console.log(`Disconnected from task stream: ${taskId}`);
        // Optional: Implement reconnect logic here
      };

      ws.current.onerror = (err) => {
        console.error('WebSocket Error:', err);
      };
    };

    connect();

    return () => {
      if (ws.current) {
        ws.current.close();
      }
    };
  }, [taskId, setWsConnected, addMessage, setActiveTask]);

  const handleWebSocketMessage = (data: any) => {
    // Dispatch to Zustand based on event type
    switch (data.type) {
      case 'step_start':
        setActiveTask({ currentStep: data.step.step });
        addMessage({
          id: String(Date.now()),
          role: 'system',
          content: `Starting step ${data.step.step}: ${data.step.description || data.step.action || 'Analyzing...'}`,
          timestamp: data.timestamp
        });
        break;
      
      case 'action':
        addMessage({
          id: String(Date.now()),
          role: 'agent',
          content: `Executing: \n\`\`\`json\n${JSON.stringify(data.action, null, 2)}\n\`\`\``,
          timestamp: data.timestamp
        });
        break;
        
      case 'step_result':
        let resultMsg = '';
        const { action_type, action, result } = data;
        
        if (result.error) {
          resultMsg = `❌ Step failed: ${result.error}`;
        } else if (action_type === 'terminal' || action_type === 'file_list') {
          resultMsg = `Output:\n${result.stdout || result.stderr || '(No output)'}`;
        } else if (action_type === 'file_read') {
          resultMsg = `File Content:\n\n${result.content || '(Empty file)'}`;
        } else if (action_type === 'file_write') {
          resultMsg = `✅ File created successfully at ${action.file_path}`;
        } else {
          resultMsg = `Step completed: ${JSON.stringify(result)}`;
        }

        addMessage({
          id: String(Date.now()),
          role: 'agent',
          content: resultMsg,
          timestamp: data.timestamp
        });
        break;

      case 'result':
        // Optional: show result in terminal log rather than main chat
        break;

      case 'error_limit_reached':
        setActiveTask({ status: 'paused_error' });
        addMessage({
          id: String(Date.now()),
          role: 'system',
          content: `⚠️ Error Limit Reached: ${data.message}`,
          timestamp: data.timestamp
        });
        break;

      case 'completed':
        setActiveTask({ status: 'completed' });
        addMessage({
          id: String(Date.now()),
          role: 'system',
          content: `✅ Task Completed Successfully`,
          timestamp: data.timestamp
        });
        break;
        
      case 'fatal_error':
        setActiveTask({ status: 'error' });
        addMessage({
          id: String(Date.now()),
          role: 'system',
          content: `❌ Fatal Error: ${data.error}`,
          timestamp: data.timestamp
        });
        break;
    }
  };

  return ws.current;
}
