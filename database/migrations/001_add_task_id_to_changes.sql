-- Migration: Add task_id to archon_changes
-- Description: Link changes to tasks for changelog consolidation
-- Date: 2026-01-02

-- Add task_id column with foreign key to archon_tasks
ALTER TABLE archon_changes
ADD COLUMN IF NOT EXISTS task_id UUID REFERENCES archon_tasks(id) ON DELETE SET NULL;

-- Create index for efficient task-based queries
CREATE INDEX IF NOT EXISTS idx_changes_task_id ON archon_changes(task_id);

-- Add comment explaining the column
COMMENT ON COLUMN archon_changes.task_id IS 'Optional link to the task this change is associated with. Used for grouping changes in changelog view.';
