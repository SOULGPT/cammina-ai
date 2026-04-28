-- ============================================
-- CAMMINA AI - Safe Migration Script
-- Run this in Supabase SQL Editor
-- Works on existing tables — no data loss
-- ============================================
-- This migration DOES NOT drop or recreate tables.
-- It only adds missing columns, new tables,
-- indexes, triggers, RLS policies and realtime.
-- Safe to run on a live project.
-- ============================================


-- ============================================
-- STEP 1: Helper trigger function
-- ============================================
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;


-- ============================================
-- STEP 2: Add missing columns to existing tables
-- Uses ADD COLUMN IF NOT EXISTS — safe on any table
-- ============================================

-- projects: add user_id and updated_at
ALTER TABLE projects
  ADD COLUMN IF NOT EXISTS user_id    UUID REFERENCES auth.users(id) ON DELETE CASCADE,
  ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ DEFAULT NOW();

-- tasks: add user_id, paused_at, updated_at, fix column types
ALTER TABLE tasks
  ADD COLUMN IF NOT EXISTS user_id    UUID REFERENCES auth.users(id) ON DELETE CASCADE,
  ADD COLUMN IF NOT EXISTS paused_at  TIMESTAMPTZ,
  ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ DEFAULT NOW();

-- Change TEXT → JSONB where needed (safe cast, only runs if column is text type)
DO $$
BEGIN
  IF EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_name='tasks' AND column_name='checkpoint_data' AND data_type='text'
  ) THEN
    ALTER TABLE tasks ALTER COLUMN checkpoint_data TYPE JSONB USING checkpoint_data::JSONB;
  END IF;

  IF EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_name='tasks' AND column_name='messages_history' AND data_type='text'
  ) THEN
    ALTER TABLE tasks ALTER COLUMN messages_history TYPE JSONB USING messages_history::JSONB;
  END IF;

  IF EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_name='errors' AND column_name='context' AND data_type='text'
  ) THEN
    ALTER TABLE errors ALTER COLUMN context TYPE JSONB USING context::JSONB;
  END IF;

  IF EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_name='agent_actions' AND column_name='action_details' AND data_type='text'
  ) THEN
    ALTER TABLE agent_actions ALTER COLUMN action_details TYPE JSONB USING action_details::JSONB;
  END IF;

  IF EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_name='memory_snapshots' AND column_name='content' AND data_type='text'
  ) THEN
    ALTER TABLE memory_snapshots ALTER COLUMN content TYPE JSONB USING content::JSONB;
  END IF;
END $$;

-- skills: add user_id, solution column
ALTER TABLE skills
  ADD COLUMN IF NOT EXISTS user_id  UUID REFERENCES auth.users(id) ON DELETE CASCADE,
  ADD COLUMN IF NOT EXISTS solution TEXT;

-- provider_status: add user_id and reset_at if missing
ALTER TABLE provider_status
  ADD COLUMN IF NOT EXISTS user_id  UUID REFERENCES auth.users(id) ON DELETE CASCADE,
  ADD COLUMN IF NOT EXISTS reset_at TIMESTAMPTZ;

-- env_variables: add unique constraint safely
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint
    WHERE conname = 'env_variables_project_id_key_name_key'
  ) THEN
    ALTER TABLE env_variables ADD CONSTRAINT env_variables_project_id_key_name_key
      UNIQUE (project_id, key_name);
  END IF;
END $$;


-- ============================================
-- STEP 3: Add updated_at triggers
-- ============================================
DROP TRIGGER IF EXISTS trg_projects_updated_at ON projects;
CREATE TRIGGER trg_projects_updated_at
  BEFORE UPDATE ON projects
  FOR EACH ROW EXECUTE FUNCTION update_updated_at();

DROP TRIGGER IF EXISTS trg_tasks_updated_at ON tasks;
CREATE TRIGGER trg_tasks_updated_at
  BEFORE UPDATE ON tasks
  FOR EACH ROW EXECUTE FUNCTION update_updated_at();

DROP TRIGGER IF EXISTS trg_skills_updated_at ON skills;
CREATE TRIGGER trg_skills_updated_at
  BEFORE UPDATE ON skills
  FOR EACH ROW EXECUTE FUNCTION update_updated_at();


-- ============================================
-- STEP 4: Create new tables (safe — IF NOT EXISTS)
-- ============================================

-- task_events: drives WebSocket /task/stream/{id}
CREATE TABLE IF NOT EXISTS task_events (
  id          TEXT PRIMARY KEY,
  task_id     TEXT REFERENCES tasks(id) ON DELETE CASCADE,
  project_id  TEXT REFERENCES projects(id) ON DELETE CASCADE,
  event_type  TEXT NOT NULL,
  step_number INTEGER,
  action      TEXT,
  result      TEXT,
  error       TEXT,
  provider    TEXT,
  metadata    JSONB,
  created_at  TIMESTAMPTZ DEFAULT NOW()
);

-- project_files: drives Files tab in ProjectDetails.tsx
CREATE TABLE IF NOT EXISTS project_files (
  id           TEXT PRIMARY KEY,
  project_id   TEXT REFERENCES projects(id) ON DELETE CASCADE,
  task_id      TEXT REFERENCES tasks(id) ON DELETE SET NULL,
  file_path    TEXT NOT NULL,
  action       TEXT NOT NULL,
  content_hash TEXT,
  size_bytes   INTEGER,
  created_at   TIMESTAMPTZ DEFAULT NOW()
);


-- ============================================
-- STEP 5: Indexes
-- ============================================
CREATE INDEX IF NOT EXISTS idx_projects_user        ON projects(user_id);
CREATE INDEX IF NOT EXISTS idx_tasks_user           ON tasks(user_id);
CREATE INDEX IF NOT EXISTS idx_tasks_status         ON tasks(status);
CREATE INDEX IF NOT EXISTS idx_task_events_task     ON task_events(task_id);
CREATE INDEX IF NOT EXISTS idx_task_events_created  ON task_events(created_at);
CREATE INDEX IF NOT EXISTS idx_skills_user          ON skills(user_id);
CREATE INDEX IF NOT EXISTS idx_skills_category      ON skills(category);
CREATE INDEX IF NOT EXISTS idx_project_files_prj    ON project_files(project_id);
CREATE INDEX IF NOT EXISTS idx_project_files_task   ON project_files(task_id);


-- ============================================
-- STEP 6: Row Level Security
-- Drop policies first so re-running is safe
-- ============================================

-- projects
ALTER TABLE projects ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "projects: owner access" ON projects;
CREATE POLICY "projects: owner access" ON projects
  FOR ALL USING (auth.uid() = user_id);

-- tasks
ALTER TABLE tasks ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "tasks: owner access" ON tasks;
CREATE POLICY "tasks: owner access" ON tasks
  FOR ALL USING (auth.uid() = user_id);

-- task_events
ALTER TABLE task_events ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "task_events: owner access" ON task_events;
CREATE POLICY "task_events: owner access" ON task_events
  FOR ALL USING (
    task_id IN (SELECT id FROM tasks WHERE user_id = auth.uid())
  );

-- task_steps
ALTER TABLE task_steps ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "task_steps: owner access" ON task_steps;
CREATE POLICY "task_steps: owner access" ON task_steps
  FOR ALL USING (
    task_id IN (SELECT id FROM tasks WHERE user_id = auth.uid())
  );

-- errors
ALTER TABLE errors ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "errors: owner access" ON errors;
CREATE POLICY "errors: owner access" ON errors
  FOR ALL USING (
    project_id IN (SELECT id FROM projects WHERE user_id = auth.uid())
  );

-- skills
ALTER TABLE skills ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "skills: owner access" ON skills;
CREATE POLICY "skills: owner access" ON skills
  FOR ALL USING (auth.uid() = user_id);

-- provider_status
ALTER TABLE provider_status ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "provider_status: owner access" ON provider_status;
CREATE POLICY "provider_status: owner access" ON provider_status
  FOR ALL USING (auth.uid() = user_id);

-- env_variables
ALTER TABLE env_variables ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "env_variables: owner access" ON env_variables;
CREATE POLICY "env_variables: owner access" ON env_variables
  FOR ALL USING (
    project_id IN (SELECT id FROM projects WHERE user_id = auth.uid())
  );

-- memory_snapshots
ALTER TABLE memory_snapshots ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "memory_snapshots: owner access" ON memory_snapshots;
CREATE POLICY "memory_snapshots: owner access" ON memory_snapshots
  FOR ALL USING (
    project_id IN (SELECT id FROM projects WHERE user_id = auth.uid())
  );

-- agent_actions
ALTER TABLE agent_actions ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "agent_actions: owner access" ON agent_actions;
CREATE POLICY "agent_actions: owner access" ON agent_actions
  FOR ALL USING (
    project_id IN (SELECT id FROM projects WHERE user_id = auth.uid())
  );

-- project_files
ALTER TABLE project_files ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "project_files: owner access" ON project_files;
CREATE POLICY "project_files: owner access" ON project_files
  FOR ALL USING (
    project_id IN (SELECT id FROM projects WHERE user_id = auth.uid())
  );


-- ============================================
-- STEP 7: Supabase Realtime
-- ============================================
ALTER PUBLICATION supabase_realtime ADD TABLE task_events;
ALTER PUBLICATION supabase_realtime ADD TABLE tasks;


-- ============================================
-- STEP 8: Seed default providers for existing users
-- Run this once — inserts providers for any user
-- who already has a project in the system.
-- New users should get these rows on signup via
-- your app's onboarding flow.
-- ============================================
INSERT INTO provider_status (id, user_id, provider_name, status, requests_today)
SELECT
  gen_random_uuid()::text,
  u.user_id,
  p.provider_name,
  'active',
  0
FROM
  (SELECT DISTINCT user_id FROM projects WHERE user_id IS NOT NULL) u
  CROSS JOIN (
    VALUES
      ('openrouter'),
      ('nvidia'),
      ('groq'),
      ('together_ai'),
      ('ollama')
  ) AS p(provider_name)
ON CONFLICT DO NOTHING;
