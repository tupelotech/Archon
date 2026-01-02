-- =====================================================
-- Add Change Tracking Table for Archon
-- =====================================================
-- This migration adds a change tracking system to capture
-- development changes made during AI-assisted sessions.
--
-- Features:
-- - Tracks changes by type (feature, bugfix, refactor, etc.)
-- - Links changes to projects
-- - Stores affected files and commit SHAs
-- - Enables changelog generation
--
-- SAFE & IDEMPOTENT: Can be run multiple times without issues
-- Compatible with complete_setup.sql for fresh installations
-- =====================================================

-- Create enum type for change type (safe, idempotent)
DO $$ BEGIN
    CREATE TYPE change_type AS ENUM ('feature', 'bugfix', 'refactor', 'docs', 'config', 'test');
EXCEPTION
    WHEN duplicate_object THEN
        RAISE NOTICE 'change_type enum already exists, skipping creation';
END $$;

-- Create the archon_changes table (safe, idempotent)
CREATE TABLE IF NOT EXISTS archon_changes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID REFERENCES archon_projects(id) ON DELETE SET NULL,
    session_id TEXT,
    change_type change_type NOT NULL,
    summary TEXT NOT NULL,
    details JSONB DEFAULT '{}'::jsonb,
    files_affected TEXT[] DEFAULT ARRAY[]::TEXT[],
    commit_sha TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create indexes for common query patterns (safe, idempotent)
CREATE INDEX IF NOT EXISTS idx_archon_changes_project ON archon_changes(project_id);
CREATE INDEX IF NOT EXISTS idx_archon_changes_created ON archon_changes(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_archon_changes_type ON archon_changes(change_type);
CREATE INDEX IF NOT EXISTS idx_archon_changes_session ON archon_changes(session_id);

-- Add comments to document the table and columns
COMMENT ON TABLE archon_changes IS 'Tracks development changes made during AI-assisted sessions for changelog generation and auditing';
COMMENT ON COLUMN archon_changes.id IS 'Unique identifier for the change entry';
COMMENT ON COLUMN archon_changes.project_id IS 'Optional reference to the associated Archon project';
COMMENT ON COLUMN archon_changes.session_id IS 'Claude Code session identifier for grouping related changes';
COMMENT ON COLUMN archon_changes.change_type IS 'Category of change: feature, bugfix, refactor, docs, config, or test';
COMMENT ON COLUMN archon_changes.summary IS 'Brief description of what changed';
COMMENT ON COLUMN archon_changes.details IS 'JSONB field for additional metadata (impact, related issues, etc.)';
COMMENT ON COLUMN archon_changes.files_affected IS 'Array of file paths that were modified';
COMMENT ON COLUMN archon_changes.commit_sha IS 'Git commit SHA if the change was committed';
COMMENT ON COLUMN archon_changes.created_at IS 'Timestamp when the change was recorded';

-- Enable RLS (Row Level Security) for the table
ALTER TABLE archon_changes ENABLE ROW LEVEL SECURITY;

-- Create RLS policies (safe, idempotent with DROP IF EXISTS pattern)
DO $$ BEGIN
    DROP POLICY IF EXISTS "Allow service role full access to changes" ON archon_changes;
    CREATE POLICY "Allow service role full access to changes" ON archon_changes
        FOR ALL USING (auth.role() = 'service_role');
EXCEPTION
    WHEN undefined_object THEN
        -- Policy doesn't exist, create it
        CREATE POLICY "Allow service role full access to changes" ON archon_changes
            FOR ALL USING (auth.role() = 'service_role');
END $$;

DO $$ BEGIN
    DROP POLICY IF EXISTS "Allow authenticated users to manage changes" ON archon_changes;
    CREATE POLICY "Allow authenticated users to manage changes" ON archon_changes
        FOR ALL TO authenticated
        USING (true);
EXCEPTION
    WHEN undefined_object THEN
        CREATE POLICY "Allow authenticated users to manage changes" ON archon_changes
            FOR ALL TO authenticated
            USING (true);
END $$;

-- Note: This migration creates the foundation for change tracking.
-- Changes can be:
-- - feature: New functionality added
-- - bugfix: Bug fixes and corrections
-- - refactor: Code restructuring without behavior changes
-- - docs: Documentation updates
-- - config: Configuration changes
-- - test: Test additions or modifications
--
-- This migration is safe to run multiple times and will not conflict
-- with complete_setup.sql for fresh installations.
