# MCP Discovery Protocol Specification

**Version:** 1.0.0
**Status:** Draft
**Author:** TrueFlow Team

## Overview

The MCP Discovery Protocol enables automatic discovery of MCP servers, tools, skills, and datasources across local machines and networks. It provides a unified way for AI agents to find and connect to available services without manual configuration.

## Goals

1. **Zero-config discovery** - Services should be discoverable without manual registration
2. **Multi-transport support** - Work with stdio, HTTP, WebSocket, and other transports
3. **Backward compatible** - Work with existing MCP servers without modification
4. **Extensible** - Support new service types and discovery methods
5. **Lightweight** - Minimal overhead and dependencies

## Service Types

| Type | Description | Example |
|------|-------------|---------|
| `mcp_server` | Full MCP server with tools/resources | TrueFlow, filesystem, GitHub MCP |
| `tool` | Individual tool/function | Code analyzer, file searcher |
| `skill` | Claude Code skill | `/commit`, `/review-pr` |
| `datasource` | Database, API, or file source | PostgreSQL, REST API, S3 bucket |
| `resource` | MCP resource provider | Documentation, config files |
| `gateway` | Aggregator/proxy service | This discovery gateway |

## Transport Types

| Transport | Address Format | Example |
|-----------|---------------|---------|
| `stdio` | `command args...` | `python mcp_server.py` |
| `http` | `http://host:port` | `http://localhost:8080` |
| `sse` | `http://host:port/sse` | `http://localhost:8080/events` |
| `websocket` | `ws://host:port` | `ws://localhost:8080/ws` |
| `unix_socket` | `/path/to/socket` | `/tmp/mcp.sock` |
| `tcp` | `host:port` | `localhost:5678` |

## Discovery Methods

### 1. File-Based Registry

**Location:** `~/.mcp/registry.json`

Services register themselves in a shared JSON file:

```json
{
  "version": "1.0.0",
  "updated_at": "2025-01-21T10:30:00Z",
  "services": {
    "abc123": {
      "id": "abc123",
      "name": "trueflow",
      "type": "mcp_server",
      "endpoint": {
        "transport": "stdio",
        "address": "python trueflow_mcp_server.py"
      },
      "version": "1.0.0",
      "description": "Code visualization and analysis",
      "tools": ["trace_connect", "analyze_performance", "manim_generate_video"],
      "tags": ["python", "visualization", "tracing"],
      "registered_at": "2025-01-21T10:00:00Z",
      "last_seen": "2025-01-21T10:30:00Z",
      "ttl_sec": 300
    }
  }
}
```

### 2. Config File Discovery

Automatically reads MCP configurations from:

| Platform | Path |
|----------|------|
| Windows | `%APPDATA%\Claude\claude_desktop_config.json` |
| macOS | `~/Library/Application Support/Claude/claude_desktop_config.json` |
| Linux | `~/.config/claude/claude_desktop_config.json` |

Also checks:
- `~/.mcp/config.json`
- `~/.config/mcp/config.json`

### 3. Well-Known HTTP Endpoint

MCP servers can expose capabilities at `/.well-known/mcp`:

```http
GET /.well-known/mcp HTTP/1.1
Accept: application/json
```

Response:

```json
{
  "name": "my-mcp-server",
  "version": "1.0.0",
  "description": "My awesome MCP server",
  "tools": [
    {"name": "tool1", "description": "Does something"},
    {"name": "tool2", "description": "Does something else"}
  ],
  "resources": [
    "myserver://data/users",
    "myserver://data/items"
  ],
  "capabilities": [
    {"name": "code_analysis", "description": "Analyzes code"}
  ],
  "tags": ["python", "analysis"]
}
```

### 4. UDP Multicast (mDNS-style)

Services broadcast announcements on multicast group `224.0.0.251:5353`:

```
MCPDISCO{"magic":"MCPDISCO","version":1,"action":"announce","service":{...}}
```

**Announcement packet structure:**
- Magic header: `MCPDISCO` (8 bytes)
- JSON payload with service metadata

**Actions:**
- `announce` - Service availability announcement
- `query` - Request for service announcements
- `goodbye` - Service going offline

### 5. Port Scanning

Probe common ports for MCP-capable services:

```python
COMMON_PORTS = [
    8080, 8081, 8765,  # MCP/API
    3000, 3001,        # Dev servers
    5000, 5001,        # Flask
    8000, 8001,        # FastAPI
]
```

## Service Registration

### Register via CLI

```bash
python mcp_discovery_protocol.py register \
  --name "my-service" \
  --type mcp_server \
  --transport stdio \
  --address "python my_mcp_server.py" \
  --description "My MCP server"
```

### Register via API (Gateway)

```json
{
  "tool": "register_service",
  "arguments": {
    "name": "my-service",
    "service_type": "mcp_server",
    "transport": "stdio",
    "address": "python my_mcp_server.py"
  }
}
```

### Self-Registration (in MCP server code)

```python
from mcp_discovery_protocol import ServiceRegistry, DiscoverableService, ServiceEndpoint

registry = ServiceRegistry()
registry.register(DiscoverableService(
    id="",
    name="my-server",
    type=ServiceType.MCP_SERVER,
    endpoint=ServiceEndpoint(
        transport=TransportType.STDIO,
        address="python my_mcp_server.py"
    ),
    tools=["tool1", "tool2"],
    ttl_sec=300
))
```

## Service Query

### Query by Type

```bash
python mcp_discovery_protocol.py query --type mcp_server
```

### Query by Capability

```bash
python mcp_discovery_protocol.py query --capability "code_analysis"
```

### Query via Gateway Tool

```json
{
  "tool": "discover_services",
  "arguments": {
    "service_type": "mcp_server",
    "capability": "code_analysis",
    "refresh": true
  }
}
```

## MCP Gateway Server

The gateway acts as a meta-MCP server that:

1. **Aggregates** all discovered services
2. **Exposes unified tools**:
   - `discover_services` - Find services
   - `list_all_tools` - List tools from all servers
   - `call_remote_tool` - Invoke tool on remote server
   - `register_service` - Add new service
   - `refresh_discovery` - Re-scan for services

3. **Routes requests** to appropriate backends

### Running the Gateway

```bash
# As MCP server (stdio)
python mcp_discovery_protocol.py serve

# In Claude Desktop config
{
  "mcpServers": {
    "mcp-gateway": {
      "command": "python",
      "args": ["mcp_discovery_protocol.py", "serve"]
    }
  }
}
```

## Heartbeat & TTL

Services must maintain their presence:

- **TTL (Time-to-Live):** Default 300 seconds
- **Heartbeat interval:** Recommended every 60 seconds
- **Stale cleanup:** Registry removes services past TTL

```python
# Heartbeat
registry.heartbeat(service_id)
```

## Security Considerations

1. **Local only by default** - UDP discovery limited to local network
2. **No secrets in registry** - Don't store API keys in registry
3. **Auth metadata only** - Store auth type, not credentials
4. **Process isolation** - Gateway doesn't share credentials between servers

## Future Extensions

1. **Remote registries** - Centralized discovery servers
2. **Service mesh** - Cross-network discovery with auth
3. **Health checks** - Active probing of service health
4. **Load balancing** - Multiple instances of same service
5. **Versioning** - Semantic version matching for compatibility

## Example: Making Your MCP Server Discoverable

### Option 1: Add well-known endpoint

```python
@app.route('/.well-known/mcp')
def mcp_info():
    return {
        "name": "my-server",
        "version": "1.0.0",
        "tools": [{"name": "my_tool", "description": "..."}]
    }
```

### Option 2: Self-register on startup

```python
from mcp_discovery_protocol import ServiceRegistry, DiscoverableService

def register_with_discovery():
    registry = ServiceRegistry()
    registry.register(DiscoverableService(
        name="my-server",
        type=ServiceType.MCP_SERVER,
        endpoint=ServiceEndpoint(
            transport=TransportType.STDIO,
            address=sys.argv[0]
        ),
        tools=["tool1", "tool2"]
    ))

# Call on startup
register_with_discovery()
```

### Option 3: Announce via UDP

```python
from mcp_discovery_protocol import UDPDiscovery, DiscoverableService

discovery = UDPDiscovery()
service = DiscoverableService(...)

# Run in background
asyncio.create_task(discovery.announce(service, interval=30))
```

## Reference Implementation

See `mcp_discovery_protocol.py` for the complete reference implementation including:

- `ServiceRegistry` - File-based registry
- `MCPConfigDiscovery` - Config file discovery
- `UDPDiscovery` - Multicast discovery
- `HTTPProbe` - HTTP endpoint probing
- `MCPGateway` - Aggregating MCP server
