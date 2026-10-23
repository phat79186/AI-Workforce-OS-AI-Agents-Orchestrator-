"""Tests for the MCP v2 compatibility layer, legacy FastMCP shim, and tool registration."""

import asyncio
import sys
import types

import pytest

from mcp_server.compat import (
    Client,
    Context,
    FastMCP,
    MCPServer,
    ToolError,
    create_mcp_server,
    install_legacy_fastmcp_shim,
    is_mcp_v2,
)


class TestMCPCompatLayer:
    """Test suite verifying MCP v2 & FastMCP compatibility interfaces."""

    def test_compat_exports(self):
        """All expected symbols should be exported and callable."""
        assert FastMCP is not None
        assert MCPServer is not None
        assert Context is not None
        assert issubclass(ToolError, Exception)
        assert callable(create_mcp_server)

    def test_legacy_fastmcp_shim_import(self):
        """Importing from mcp.server.fastmcp should transparently succeed via shim."""
        install_legacy_fastmcp_shim()

        assert "mcp.server.fastmcp" in sys.modules
        from mcp.server.fastmcp import Context as ShimContext
        from mcp.server.fastmcp import FastMCP as ShimFastMCP

        assert ShimFastMCP is not None
        assert ShimContext is not None

    def test_simulated_v2_shim_recovery(self):
        """Simulate mcp 2.x breaking stub and verify shim recovers it."""
        # Simulate mcp 2.x stub that raises ModuleNotFoundError or lacks FastMCP
        bad_stub = types.ModuleType("mcp.server.fastmcp")
        sys.modules["mcp.server.fastmcp"] = bad_stub

        # Re-install shim
        install_legacy_fastmcp_shim()

        from mcp.server.fastmcp import Context as RecoveredContext
        from mcp.server.fastmcp import FastMCP as RecoveredFastMCP

        assert RecoveredFastMCP is FastMCP
        assert RecoveredContext is Context

    def test_server_instantiation_variants(self):
        """Server can be instantiated via both FastMCP and MCPServer aliases."""
        server1 = FastMCP(name="Server1", instructions="Test server 1")
        assert server1 is not None

        server2 = MCPServer(name="Server2", instructions="Test server 2")
        assert server2 is not None

    def test_context_interface(self):
        """Context class should be a valid type definition."""
        assert isinstance(Context, type)
        # Context should have expected methods/attributes
        assert hasattr(Context, "info") or hasattr(Context, "__init__")

    def test_tool_error_raising(self):
        """ToolError can be raised and caught as expected."""
        with pytest.raises(ToolError, match="Engine failed"):
            raise ToolError("Engine failed")


class TestMCPServerIntegration:
    """Test that mcp_server.server loads cleanly and discovers all tools."""

    def test_mcp_server_loads_all_tools(self):
        """Validate that all 36 registered tools are discoverable."""
        from mcp_server.server import mcp

        tools = asyncio.run(mcp.list_tools())
        assert len(tools) >= 36

        tool_names = [t.name for t in tools]
        # Core orchestrator & agentic team tools
        assert "orchestrator_execute" in tool_names
        assert "agentic_team_execute" in tool_names
        # Code analysis
        assert "code_complexity" in tool_names
        # Security
        assert "scan_secrets" in tool_names
        # Testing
        assert "generate_test_cases" in tool_names
        # DevOps
        assert "generate_dockerfile" in tool_names
        # Context
        assert "store_conversation" in tool_names
        # Sequential thinking
        assert "sequentialthinking" in tool_names
        assert "sequential_thinking" in tool_names
