# Changelog

All notable changes to this fork will be documented in this file.

## [Unreleased]

### Added

#### Self-Hosted Supabase Stack
- `docker-compose.supabase.yml` - Complete self-hosted Supabase configuration
  - PostgreSQL 15.6.1 with pgvector extension
  - PostgREST v12.2.0 for REST API
  - GoTrue v2.164.0 for authentication
  - Kong 2.8.1 API gateway
  - Supabase Studio for database management
  - Postgres Meta for introspection

- `volumes/db/roles.sql` - Database role initialization
  - Creates required Supabase roles (anon, authenticated, service_role, authenticator)
  - Sets up supabase_auth_admin and supabase_admin roles
  - Configures Row Level Security bypass for service_role
  - Creates auth schema and extensions schema

- `volumes/db/webhooks.sql` - Webhook trigger functions for Supabase

- `volumes/db/realtime.sql` - Realtime publication setup

- `volumes/api/kong.yml` - Kong API gateway configuration
  - Routes for PostgREST (/rest/v1/)
  - Routes for GoTrue auth (/auth/v1/)
  - CORS configuration
  - API key authentication

#### Docker Namespace Isolation
- All containers use `archon-` prefix to avoid collisions with other projects
- Supabase containers: `archon-supabase-db`, `archon-supabase-rest`, `archon-supabase-auth`, `archon-supabase-kong`, `archon-supabase-studio`, `archon-supabase-meta`
- Archon containers: `archon-server`, `archon-mcp`, `archon-ui`
- Networks: `archon-network`, `archon-supabase-network`
- Volumes: `archon-supabase-db-data`
- PostgreSQL on port 5433 (avoids conflict with other projects using 5432)

#### Local Configuration Override System
- `docker-compose.override.yml` (gitignored) - Local overrides that won't conflict with upstream
- Enables clean `git merge upstream/main` without configuration conflicts

### Changed

- `.env` - Configured for self-hosted Supabase
  - `SUPABASE_URL=http://host.docker.internal:8000`
  - Uses demo JWT keys matching self-hosted configuration
  - PostgreSQL on port 5433

- `.gitignore` - Added `docker-compose.override.yml` to keep local config separate

### Documentation

- `PRPs/ai_docs/MCP_TOOLS.md` - Extracted MCP tools documentation from CLAUDE.md
- `CLAUDE.md` - Improved with critical patterns, development modes, working directories

## Fork Information

This is a fork of [coleam00/Archon](https://github.com/coleam00/Archon).

### Upstream Tracking
```bash
# Fetch upstream changes
git fetch upstream

# Merge upstream updates
git merge upstream/main

# Push to fork
git push origin stable
```

### Local Files (Not Tracked)
These files contain local configuration and won't be affected by upstream merges:
- `.env` - Environment variables and secrets
- `docker-compose.override.yml` - Local Docker overrides
- `volumes/db-data/` - PostgreSQL data directory

### Service Ports
| Service | Port |
|---------|------|
| Archon UI | 3737 |
| Archon API | 8181 |
| Archon MCP | 8051 |
| Supabase Kong | 8000 |
| Supabase Studio | 3001 |
| PostgreSQL | 5433 |

### Quick Start
```bash
# Start Supabase stack
docker compose -f docker-compose.supabase.yml up -d

# Wait for healthy, then start Archon
docker compose up -d

# Or for hybrid mode (backend Docker, frontend local)
docker compose --profile backend up -d
cd archon-ui-main && npm run dev
```
