-- Realtime publication setup
-- Required by Supabase stack for change data capture

-- Create realtime schema if needed
CREATE SCHEMA IF NOT EXISTS realtime;

-- Create publication for realtime (Archon doesn't use realtime, but stack requires it)
DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_publication WHERE pubname = 'supabase_realtime') THEN
    CREATE PUBLICATION supabase_realtime;
  END IF;
END
$$;
