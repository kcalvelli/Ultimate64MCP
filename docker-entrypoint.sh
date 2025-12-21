#!/bin/bash
# Commodore 64 Ultimate MCP Server - Docker Entrypoint
# https://github.com/yourusername/c64-ultimate-mcp

set -e

echo "======================================"
echo " Commodore 64 Ultimate MCP Server"
echo " Hosted Version (SSE)"
echo "======================================"

# Check for C64 host environment variable
if [ -n "$C64_HOST" ]; then
    echo "✓ C64_HOST: $C64_HOST"
else
    echo "ℹ No C64 host configured"
    echo "  Use 'ultimate_set_connection' tool to set connection"
    echo "  Or set C64_HOST environment variable"
fi

echo "======================================"
echo "Starting server on port 8000..."
echo ""

# Execute the MCP server
# Pass "$@" to allow overriding arguments or flags
exec python3 /app/mcp_ultimate_server.py "$@"
