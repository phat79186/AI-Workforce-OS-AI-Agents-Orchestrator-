"""MCP Server for AI Coding Tools — Task Execution & Monitoring.

Exposes both the Orchestrator and Agentic Team engines as MCP tools
so any MCP-compatible client can submit tasks, check status, inspect
agents, and monitor health across both systems.
"""

# Ensure MCP v2 / FastMCP compatibility layer and legacy shim are active
from mcp_server.compat import Context, FastMCP, MCPServer, ToolError, is_mcp_v2

__all__ = [
    "Context",
    "FastMCP",
    "MCPServer",
    "ToolError",
    "is_mcp_v2",
]
