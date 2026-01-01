-- Placeholder for webhooks functionality
-- Required by Supabase stack but not used by Archon

CREATE SCHEMA IF NOT EXISTS supabase_functions;
GRANT USAGE ON SCHEMA supabase_functions TO postgres, anon, authenticated, service_role;
