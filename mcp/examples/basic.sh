# Start MCP server with stdio transport
migrator-gen-mcp

# Start MCP server with HTTP transport
migrator-gen-mcp --transport http --port 8001

# Test health endpoint
curl http://localhost:8001/health

# List available tools
curl http://localhost:8001/tools

# Call a tool
curl -X POST http://localhost:8001/tools/list_libraries/call \
  -H "Content-Type: application/json" \
  -d '{}'
