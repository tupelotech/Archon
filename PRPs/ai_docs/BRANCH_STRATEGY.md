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
| Archon Redis | 6380 |
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
- Archon containers: `archon-server`, `archon-mcp`, `archon-ui`, `archon-redis`
- Networks: `archon-network`, `archon-supabase-network`
- Volumes: `archon-supabase-db-data`, `archon-redis-data`

## Known Issues

### MCP Session ID Error After Server Restart

**Symptom**: After restarting `archon-mcp`, MCP tool calls fail with "No valid session ID provided"

**Root Cause**: FastMCP's streamable HTTP transport maintains session state in two layers:
1. **Transport layer** (`_request_streams` dict) - Stores request/response state internally
2. **Session manager** - Tracks session IDs and expiration

While Archon's session manager now uses Redis for persistence, the transport layer's internal state cannot be externally persisted. This is a fundamental limitation of the MCP Python SDK.

**Technical Details**:
- The `StreamableHTTPSessionManager` stores sessions in memory
- Even with Redis-backed event stores, the `_request_streams` dictionary breaks session resumption
- The error occurs when a client sends a stale session ID after server restart

**Current Workaround**: Restart Claude Code or disconnect/reconnect the MCP server in settings.

**What We've Implemented**:
- Added `archon-redis` container on port 6380 for session persistence
- Updated `SessionManager` to use Redis backend when available
- This prepares for future MCP SDK improvements and enables UI settings persistence

**References**:
- [Python SDK Issue #880](https://github.com/modelcontextprotocol/python-sdk/issues/880) - Horizontal scaling session persistence
- [Python SDK Issue #1180](https://github.com/modelcontextprotocol/python-sdk/issues/1180) - Session management in Kubernetes
- [Cursor Issue #3640](https://github.com/cursor/cursor/issues/3640) - Client reconnection issues

**Future Improvements**: Monitor MCP SDK for session persistence fixes, consider SSE transport as alternative.
