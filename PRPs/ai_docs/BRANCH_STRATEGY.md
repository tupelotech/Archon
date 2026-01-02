# Branch Strategy

## Overview

This is a fork of [coleam00/Archon](https://github.com/coleam00/Archon). The branching strategy maintains a clean separation between upstream code and local customizations.

## Branch Diagram

```
upstream/main ─────────────────────────────────────────────► (original Archon)
                 │
                 ▼ fetch/merge
origin/main ─────●─────────────────────────────────────────► (synced with upstream)
                 │
                 ▼ merge
origin/tupelotech ───●───●───●─────────────────────────────► (customizations)
                     │   │   │
                   local preferences
                   features  enhancements
```

## Branch Purposes

| Branch | Purpose |
|--------|---------|
| `main` | Synced with upstream - DO NOT customize |
| `tupelotech` | All custom features and changes |

## Updating from Upstream

```bash
# 1. Fetch latest from upstream
git fetch upstream

# 2. Update main branch
git checkout main
git merge upstream/main
git push origin main

# 3. Merge upstream changes into customization branch
git checkout tupelotech
git merge main
# Resolve any conflicts
git push origin tupelotech
```

## Adding Custom Features

```bash
# Always work on tupelotech branch
git checkout tupelotech

# Make changes, commit
git add -A && git commit -m "feat: description"
git push origin tupelotech
```

## Conflict Resolution

If upstream changes conflict with customizations:
1. Conflicts will appear during `git merge main`
2. Edit conflicting files to keep both upstream and custom changes where possible
3. Test thoroughly before pushing
4. Log significant merge decisions using the Archon changelog system

## Local Files (Not Tracked)

These files contain local configuration and won't be affected by upstream merges:
- `.env` - Environment variables and secrets
- `docker-compose.override.yml` - Local Docker overrides
- `volumes/db-data/` - PostgreSQL data directory

## Service Ports

| Service | Port |
|---------|------|
| Archon UI | 3737 |
| Archon API | 8181 |
| Archon MCP | 8051 |
| Supabase Kong | 8000 |
| Supabase Studio | 3001 |
| PostgreSQL | 5433 |

## Quick Start

```bash
# Start Supabase stack
docker compose -f docker-compose.supabase.yml up -d

# Wait for healthy, then start Archon
docker compose up -d

# Or for hybrid mode (backend Docker, frontend local)
docker compose --profile backend up -d
cd archon-ui-main && npm run dev
```

## Docker Namespace

All containers use `archon-` prefix to avoid collisions:
- Supabase containers: `archon-supabase-db`, `archon-supabase-rest`, `archon-supabase-auth`, `archon-supabase-kong`, `archon-supabase-studio`, `archon-supabase-meta`
- Archon containers: `archon-server`, `archon-mcp`, `archon-ui`
- Networks: `archon-network`, `archon-supabase-network`
- Volumes: `archon-supabase-db-data`

## Known Issues

### MCP Session ID Error After Server Restart

**Symptom**: After restarting `archon-mcp`, MCP tool calls fail with "No valid session ID provided"

**Cause**: FastMCP's streamable HTTP transport stores sessions in memory. When the server restarts, sessions are invalidated but clients (Claude Code, Cursor) cache stale session IDs and don't auto-reconnect.

**Workaround**: Restart Claude Code or disconnect/reconnect the MCP server in settings.

**References**:
- [Cursor Issue #3640](https://github.com/cursor/cursor/issues/3640)
- [Python SDK Issue #880](https://github.com/modelcontextprotocol/python-sdk/issues/880)

**Future Fix**: Implement Redis-backed session persistence or switch to SSE transport.
