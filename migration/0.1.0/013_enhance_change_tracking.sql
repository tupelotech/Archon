-- =====================================================
-- Enhanced Change Tracking Schema
-- =====================================================
-- This migration enhances the change tracking system with:
-- - Additional change types (style, perf, deps, ci)
-- - Sub-category support for granular classification
-- - Auto-detection metadata in the details JSONB field
--
-- SAFE & IDEMPOTENT: Can be run multiple times without issues
-- =====================================================

-- Add new enum values to change_type (idempotent)
-- PostgreSQL doesn't have IF NOT EXISTS for enum values,
-- so we check pg_enum before adding
DO $$
BEGIN
    -- Add 'style' if not exists
    IF NOT EXISTS (SELECT 1 FROM pg_enum WHERE enumlabel = 'style'
                   AND enumtypid = 'change_type'::regtype) THEN
        ALTER TYPE change_type ADD VALUE 'style';
    END IF;
EXCEPTION
    WHEN duplicate_object THEN NULL;
END $$;

DO $$
BEGIN
    -- Add 'perf' if not exists
    IF NOT EXISTS (SELECT 1 FROM pg_enum WHERE enumlabel = 'perf'
                   AND enumtypid = 'change_type'::regtype) THEN
        ALTER TYPE change_type ADD VALUE 'perf';
    END IF;
EXCEPTION
    WHEN duplicate_object THEN NULL;
END $$;

DO $$
BEGIN
    -- Add 'deps' if not exists
    IF NOT EXISTS (SELECT 1 FROM pg_enum WHERE enumlabel = 'deps'
                   AND enumtypid = 'change_type'::regtype) THEN
        ALTER TYPE change_type ADD VALUE 'deps';
    END IF;
EXCEPTION
    WHEN duplicate_object THEN NULL;
END $$;

DO $$
BEGIN
    -- Add 'ci' if not exists
    IF NOT EXISTS (SELECT 1 FROM pg_enum WHERE enumlabel = 'ci'
                   AND enumtypid = 'change_type'::regtype) THEN
        ALTER TYPE change_type ADD VALUE 'ci';
    END IF;
EXCEPTION
    WHEN duplicate_object THEN NULL;
END $$;

-- Add sub_category column for granular classification (idempotent)
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'archon_changes'
        AND column_name = 'sub_category'
    ) THEN
        ALTER TABLE archon_changes ADD COLUMN sub_category TEXT;
    END IF;
END $$;

-- Add comment for sub_category column
COMMENT ON COLUMN archon_changes.sub_category IS 'Optional sub-category for granular classification (e.g., "ui", "api", "database")';

-- Update comment on details column to document new fields
COMMENT ON COLUMN archon_changes.details IS 'JSONB field for additional metadata. Reserved fields: auto_detected_type (string), confidence_score (0.0-1.0), override_reason (string), detection_signals (array)';

-- Create index on sub_category for filtering (idempotent)
CREATE INDEX IF NOT EXISTS idx_archon_changes_sub_category ON archon_changes(sub_category) WHERE sub_category IS NOT NULL;

-- Note: The following fields are stored in the JSONB 'details' column:
-- - auto_detected_type: The category suggested by the detection service
-- - confidence_score: 0.0 to 1.0 score for the auto-detection
-- - override_reason: Explanation if user changed the auto-detected type
-- - detection_signals: Array of signals used for detection
--
-- Example details structure:
-- {
--   "auto_detected_type": "test",
--   "confidence_score": 0.85,
--   "override_reason": "Actually a bug fix, not just a test update",
--   "detection_signals": ["file_pattern:test_*.py", "content:assert"]
-- }

-- Update change_type comment to include new types
COMMENT ON COLUMN archon_changes.change_type IS 'Category of change: feature, bugfix, refactor, docs, config, test, style, perf, deps, or ci';
