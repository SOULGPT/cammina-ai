CREATE TABLE IF NOT EXISTS projects (
  id TEXT PRIMARY KEY,
  name TEXT NOT NULL UNIQUE,
  description TEXT,
  folder_path TEXT,
  status TEXT DEFAULT 'active',
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  completed_at DATETIME,
  completed INTEGER DEFAULT 0
);
CREATE TABLE IF NOT EXISTS tasks (
  id TEXT PRIMARY KEY,
  project_id TEXT REFERENCES projects(id),
  title TEXT NOT NULL,
  description TEXT,
  status TEXT DEFAULT 'pending',
  started_at DATETIME,
  completed_at DATETIME,
  checkpoint_data TEXT,
  current_step INTEGER DEFAULT 0,
  total_steps INTEGER,
  provider_used TEXT,
  error_count INTEGER DEFAULT 0,
  messages_history TEXT,
  timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS task_steps (
  id TEXT PRIMARY KEY,
  task_id TEXT REFERENCES tasks(id),
  step_number INTEGER,
  action TEXT,
  action_type TEXT,
  result TEXT,
  status TEXT,
  timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS errors (
  id TEXT PRIMARY KEY,
  task_id TEXT REFERENCES tasks(id),
  project_id TEXT REFERENCES projects(id),
  source TEXT,
  error_type TEXT,
  error_message TEXT,
  context TEXT,
  fix_attempted TEXT,
  fix_result TEXT,
  provider_used TEXT,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS skills (
  id TEXT PRIMARY KEY,
  name TEXT NOT NULL UNIQUE,
  category TEXT,
  description TEXT,
  learned_from_project TEXT,
  success_rate REAL DEFAULT 0.0,
  usage_count INTEGER DEFAULT 0,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS provider_status (
  id TEXT PRIMARY KEY,
  provider_name TEXT NOT NULL UNIQUE,
  status TEXT DEFAULT 'active',
  last_used DATETIME,
  rate_limit_reset DATETIME,
  requests_today INTEGER DEFAULT 0,
  last_error TEXT,
  reset_at DATETIME
);
CREATE TABLE IF NOT EXISTS env_variables (
  id TEXT PRIMARY KEY,
  project_id TEXT REFERENCES projects(id),
  key_name TEXT NOT NULL,
  encrypted_value TEXT NOT NULL,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS memory_snapshots (
  id TEXT PRIMARY KEY,
  project_id TEXT REFERENCES projects(id),
  task_id TEXT REFERENCES tasks(id),
  snapshot_type TEXT,
  content TEXT,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS agent_actions (
  id TEXT PRIMARY KEY,
  task_id TEXT REFERENCES tasks(id),
  project_id TEXT REFERENCES projects(id),
  action_type TEXT,
  action_details TEXT,
  result TEXT,
  duration_ms INTEGER,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_tasks_project ON tasks(project_id);
CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status);
CREATE INDEX IF NOT EXISTS idx_task_steps_task ON task_steps(task_id);
CREATE INDEX IF NOT EXISTS idx_errors_task ON errors(task_id);
CREATE INDEX IF NOT EXISTS idx_errors_project ON errors(project_id);
CREATE INDEX IF NOT EXISTS idx_provider_status_name ON provider_status(provider_name);
CREATE INDEX IF NOT EXISTS idx_agent_actions_task ON agent_actions(task_id);
CREATE INDEX IF NOT EXISTS idx_memory_snapshots_project ON memory_snapshots(project_id);
INSERT OR IGNORE INTO provider_status (id, provider_name, status, requests_today)
VALUES
  ('prov-001', 'openrouter', 'active', 0),
  ('prov-002', 'nvidia', 'active', 0),
  ('prov-003', 'groq', 'active', 0),
  ('prov-004', 'ollama', 'active', 0);
