#!/bin/bash
# Restart Archon backend services
# Usage: ./scripts/restart-backend.sh [--rebuild]

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_ROOT"

echo "🔄 Restarting Archon backend services..."

if [[ "$1" == "--rebuild" ]]; then
    echo "📦 Rebuilding containers (includes new code changes)..."
    docker compose build archon-server archon-mcp 2>&1 | grep -E "^(#|archon-|time=)" || true
    docker compose up -d archon-server archon-mcp 2>&1 | grep -v "^INFO:" || true
    echo "🔄 Recreating frontend to refresh network..."
    docker compose up -d archon-frontend 2>&1 | grep -v "^INFO:" || true
else
    echo "🔁 Restarting existing containers..."
    docker restart archon-server archon-mcp archon-ui
fi

echo "⏳ Containers started, waiting for health checks..."
sleep 3

echo "⏳ Waiting for services to become healthy..."

# Wait for backend health (max 60 seconds)
for i in {1..60}; do
    if curl -s --max-time 2 http://localhost:8181/health | grep -q '"ready":\s*true'; then
        echo "✅ Backend is healthy"
        break
    fi
    if [[ $i -eq 60 ]]; then
        echo "❌ Backend failed to become healthy"
        echo "📋 Logs:"
        docker logs archon-server --tail 30
        exit 1
    fi
    sleep 1
done

# Wait for MCP health (max 30 seconds)
for i in {1..30}; do
    if docker ps --filter "name=archon-mcp" --format "{{.Status}}" | grep -q "healthy"; then
        echo "✅ MCP server is healthy"
        break
    fi
    if [[ $i -eq 30 ]]; then
        echo "⚠️  MCP server not healthy yet (may still be starting)"
    fi
    sleep 1
done

echo ""
echo "🎉 Restart complete!"
echo ""
echo "Service Status:"
docker ps --filter "name=archon-server" --filter "name=archon-mcp" --format "  {{.Names}}: {{.Status}}"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "⚠️  IMPORTANT: MCP Session Reminder"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "If you're using Claude Code, Cursor, or another MCP client:"
echo "  → Restart your IDE or reconnect the MCP server"
echo ""
echo "FastMCP sessions are stored in memory and invalidated on restart."
echo "See: PRPs/ai_docs/BRANCH_STRATEGY.md#known-issues"
echo ""
