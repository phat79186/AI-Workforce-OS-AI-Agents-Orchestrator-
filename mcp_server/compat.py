"""Compatibility layer for Model Context Protocol SDK v2, standalone FastMCP, and MCP v1.

Provides a unified interface across:
1. Official MCP Python SDK v2.x (``from mcp.server.mcpserver import MCPServer, Context``)
2. Standalone FastMCP package (``from fastmcp import FastMCP, Context, Client``)
3. Legacy MCP Python SDK v1.x (``from mcp.server.fastmcp import FastMCP, Context``)

Also installs an in-memory compatibility shim for ``mcp.server.fastmcp`` in ``sys.modules``
to prevent ``ModuleNotFoundError`` when older code or third-party fixtures import the legacy path.
"""

from __future__ import annotations

import inspect
import logging
import sys
import types
from typing import Any, Dict, Optional

logger = logging.getLogger("mcp_server.compat")

# ---------------------------------------------------------------------------
# Core Class Detection
# ---------------------------------------------------------------------------

_RawMCPServer: Optional[type] = None
_RawContext: Optional[type] = None
_RawToolError: Optional[type] = None
_RawClient: Optional[type] = None
is_mcp_v2: bool = False

# 1. Try official MCP SDK v2 (mcp.server.mcpserver)
try:
    from mcp.server.mcpserver import Context as _V2Context
    from mcp.server.mcpserver import MCPServer as _V2MCPServer

    _RawMCPServer = _V2MCPServer
    _RawContext = _V2Context
    is_mcp_v2 = True
    logger.debug("Loaded official MCP SDK v2 (mcp.server.mcpserver)")
except (ImportError, ModuleNotFoundError):
    pass

# 2. Try standalone fastmcp package (or fallback)
if _RawMCPServer is None:
    try:
        from fastmcp import Context as _FMCPContext
        from fastmcp import FastMCP as _FMCPFastMCP

        _RawMCPServer = _FMCPFastMCP
        _RawContext = _FMCPContext
        logger.debug("Loaded standalone FastMCP package")
    except (ImportError, ModuleNotFoundError):
        pass

# 3. Try legacy MCP SDK v1 (mcp.server.fastmcp)
if _RawMCPServer is None:
    try:
        # Note: in mcp 2.x this module raises ModuleNotFoundError explicitly
        from mcp.server.fastmcp import Context as _V1Context
        from mcp.server.fastmcp import FastMCP as _V1FastMCP

        _RawMCPServer = _V1FastMCP
        _RawContext = _V1Context
        logger.debug("Loaded legacy MCP SDK v1 (mcp.server.fastmcp)")
    except (ImportError, ModuleNotFoundError):
        pass

# 4. Fallback Context definition if no MCP library is installed
if _RawContext is None:

    class _FallbackContext:
        """Lightweight Context stub for typing and runtime fallback."""

        session: Any = None
        request_id: Optional[str] = None

        async def report_progress(self, progress: float, total: Optional[float] = None) -> None:
            pass

        def info(self, message: str) -> None:
            logger.info("%s", message)

        def error(self, message: str) -> None:
            logger.error("%s", message)

    Context = _FallbackContext
else:
    Context = _RawContext

# 5. Resolve ToolError
try:
    from fastmcp.exceptions import ToolError as _FastMCPToolError

    _RawToolError = _FastMCPToolError
except (ImportError, ModuleNotFoundError):
    try:
        from mcp.shared.exceptions import McpError as _McpError

        class _McpToolError(_McpError):
            pass

        _RawToolError = _McpToolError
    except (ImportError, ModuleNotFoundError):

        class _BaseToolError(Exception):
            pass

        _RawToolError = _BaseToolError

ToolError = _RawToolError

# 6. Resolve Client
try:
    from fastmcp import Client as _FastMCPClient

    _RawClient = _FastMCPClient
except (ImportError, ModuleNotFoundError):
    try:
        from mcp.client.session import ClientSession as _ClientSession

        _RawClient = _ClientSession
    except (ImportError, ModuleNotFoundError):
        _RawClient = None

Client = _RawClient


# ---------------------------------------------------------------------------
# Smart Server Wrapper Factory
# ---------------------------------------------------------------------------


def create_mcp_server(
    name: str = "AI Coding Tools",
    instructions: Optional[str] = None,
    version: str = "2.0.0",
    lifespan: Any = None,
    **kwargs: Any,
) -> Any:
    """Create an MCP server instance compatible with whichever SDK is installed.

    Adapts keyword arguments (e.g. ``on_duplicate``, ``lifespan``, ``instructions``)
    based on the underlying server class signature.
    """
    target_cls = _RawMCPServer
    if target_cls is None:
        raise RuntimeError(
            "Neither 'mcp.server.mcpserver', 'fastmcp', nor 'mcp.server.fastmcp' is available."
        )

    # Introspect constructor parameters
    try:
        sig = inspect.signature(target_cls.__init__)
        params = sig.parameters
        has_var_kwargs = any(p.kind == inspect.Parameter.VAR_KEYWORD for p in params.values())
    except Exception:
        params = {}
        has_var_kwargs = True

    call_kwargs: Dict[str, Any] = {}
    candidate_kwargs = {
        "name": name,
        "instructions": instructions,
        "version": version,
        "lifespan": lifespan,
        **kwargs,
    }

    if has_var_kwargs:
        call_kwargs = candidate_kwargs
    else:
        for k, v in candidate_kwargs.items():
            if k in params:
                call_kwargs[k] = v

    return target_cls(**call_kwargs)


class _ServerMeta(type):
    """Metaclass allowing FastMCP(...) and MCPServer(...) to act as class constructors."""

    def __call__(cls, *args: Any, **kwargs: Any) -> Any:
        if args and "name" not in kwargs:
            kwargs["name"] = args[0]
            args = args[1:]
        return create_mcp_server(*args, **kwargs)


class MCPServer(metaclass=_ServerMeta):
    """Modern MCP v2 server interface."""

    pass


class FastMCP(metaclass=_ServerMeta):
    """Backward-compatible FastMCP server interface alias."""

    pass


# ---------------------------------------------------------------------------
# Virtual Module Shim for legacy mcp.server.fastmcp
# ---------------------------------------------------------------------------


def install_legacy_fastmcp_shim() -> None:
    """Install an in-memory compatibility module for ``mcp.server.fastmcp``.

    In MCP Python SDK v2, importing ``mcp.server.fastmcp`` raises ``ModuleNotFoundError``
    by design. Installing this shim prevents breaks across legacy test fixtures,
    third-party tools, or unmigrated call sites.
    """
    shim_key = "mcp.server.fastmcp"
    needs_shim = False

    if shim_key not in sys.modules:
        needs_shim = True
    else:
        # Check if the existing module has FastMCP or is the breaking v2 stub
        mod = sys.modules[shim_key]
        if not hasattr(mod, "FastMCP") or not hasattr(mod, "Context"):
            needs_shim = True

    if needs_shim:
        shim = types.ModuleType(shim_key)
        shim.FastMCP = FastMCP  # type: ignore[attr-defined]
        shim.MCPServer = MCPServer  # type: ignore[attr-defined]
        shim.Context = Context  # type: ignore[attr-defined]
        shim.ToolError = ToolError  # type: ignore[attr-defined]
        if Client is not None:
            shim.Client = Client  # type: ignore[attr-defined]

        sys.modules[shim_key] = shim

        # Also attach to parent package mcp.server if already imported
        if "mcp.server" in sys.modules:
            try:
                sys.modules["mcp.server"].fastmcp = shim
            except Exception:
                pass


# Install shim on compat import
install_legacy_fastmcp_shim()

__all__ = [
    "MCPServer",
    "FastMCP",
    "Context",
    "ToolError",
    "Client",
    "create_mcp_server",
    "install_legacy_fastmcp_shim",
    "is_mcp_v2",
]
