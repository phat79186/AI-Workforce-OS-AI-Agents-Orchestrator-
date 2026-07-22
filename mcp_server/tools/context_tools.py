"""Context memory MCP tools for storing and retrieving context."""

from __future__ import annotations

from typing import Any

from mcp.server.fastmcp import Context

# Lazy import to avoid import errors if context module not available
_memory_manager = None


def _get_memory_manager() -> Any:
    """Get or create memory manager instance."""
    global _memory_manager  # noqa: PLW0603
    if _memory_manager is None:
        try:
            from orchestrator.context.memory_manager import MemoryManager

            _memory_manager = MemoryManager()
        except ImportError:
            return None
    return _memory_manager


async def store_conversation(
    ctx: Context,
    content: str,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Store a conversation in context memory.

    Args:
        ctx: MCP context
        content: Conversation content to store
        metadata: Optional metadata (tags, source, etc.)

    Returns:
        Storage confirmation with node ID.
    """
    manager = _get_memory_manager()
    if manager is None:
        return {"error": "Context system not available"}

    try:
        node_id = manager.store_conversation(
            messages=[{"role": "user", "content": content}],
            metadata=metadata,
        )
        return {
            "success": True,
            "node_id": node_id,
            "message": "Conversation stored successfully",
        }
    except Exception as e:
        return {"error": str(e)}


async def store_task(
    ctx: Context,
    description: str,
    result: str,
    success: bool = True,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Store a task execution in context memory.

    Args:
        ctx: MCP context
        description: Task description
        result: Task result/output
        success: Whether task succeeded
        metadata: Optional metadata

    Returns:
        Storage confirmation with node ID.
    """
    manager = _get_memory_manager()
    if manager is None:
        return {"error": "Context system not available"}

    try:
        node_id = manager.store_task(
            task_description=description,
            outcome=result,
            success=success,
            metadata=metadata,
        )
        return {
            "success": True,
            "node_id": node_id,
            "message": "Task stored successfully",
        }
    except Exception as e:
        return {"error": str(e)}


async def log_mistake(
    ctx: Context,
    description: str,
    correction: str,
    context: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Log a mistake for learning.

    Args:
        ctx: MCP context
        description: Description of the mistake
        correction: How it was corrected
        context: Additional context
        metadata: Optional metadata

    Returns:
        Storage confirmation with node ID.
    """
    manager = _get_memory_manager()
    if manager is None:
        return {"error": "Context system not available"}

    try:
        node_id = manager.log_mistake(
            error_type="general",
            error_message=description,
            context_description=context or "",
            correction=correction,
        )
        return {
            "success": True,
            "node_id": node_id,
            "message": "Mistake logged for future learning",
        }
    except Exception as e:
        return {"error": str(e)}


async def search_context(
    ctx: Context,
    query: str,
    limit: int = 10,
    node_types: list[str] | None = None,
) -> dict[str, Any]:
    """Search context memory using hybrid search.

    Args:
        ctx: MCP context
        query: Search query
        limit: Maximum results to return
        node_types: Filter by node types

    Returns:
        Search results with relevance scores.
    """
    manager = _get_memory_manager()
    if manager is None:
        return {"error": "Context system not available"}

    try:
        results = manager.search(query, limit=limit, node_types=node_types)
        return {
            "query": query,
            "results": [
                {
                    "node_id": r.node.id,
                    "content": r.node.content[:500],
                    "node_type": r.node.node_type.value,
                    "score": r.score,
                    "metadata": r.node.metadata,
                }
                for r in results
            ],
            "count": len(results),
        }
    except Exception as e:
        return {"error": str(e)}


async def get_relevant_context(
    ctx: Context,
    task_description: str,
    limit: int = 5,
) -> dict[str, Any]:
    """Get relevant context for a task.

    Args:
        ctx: MCP context
        task_description: Description of current task
        limit: Maximum context items to return

    Returns:
        Relevant context including past tasks, mistakes, and patterns.
    """
    manager = _get_memory_manager()
    if manager is None:
        return {"error": "Context system not available"}

    try:
        raw = manager.get_relevant_context(task_description, limit=limit)

        result: dict[str, Any] = {
            "task": task_description,
            "related_tasks": [
                {"content": t["node"]["content"][:300], "score": t["score"]}
                for t in raw.get("tasks", [])
            ],
            "relevant_mistakes": [
                {"content": m["node"]["content"][:300], "score": m["score"]}
                for m in raw.get("mistakes", [])
            ],
            "patterns": [
                {"content": p["node"]["content"][:300], "score": p["score"]}
                for p in raw.get("patterns", [])
            ],
        }

        return result
    except Exception as e:
        return {"error": str(e)}


async def store_pattern(
    ctx: Context,
    name: str,
    description: str,
    example: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Store a learned pattern.

    Args:
        ctx: MCP context
        name: Pattern name
        description: Pattern description
        example: Optional example code/usage
        metadata: Optional metadata

    Returns:
        Storage confirmation.
    """
    manager = _get_memory_manager()
    if manager is None:
        return {"error": "Context system not available"}

    try:
        node_id = manager.store_pattern(
            pattern_name=name,
            pattern_type="general",
            description=description,
            examples=[example] if example else [],
        )
        return {
            "success": True,
            "node_id": node_id,
            "message": "Pattern stored successfully",
        }
    except Exception as e:
        return {"error": str(e)}


async def get_context_stats(ctx: Context) -> dict[str, Any]:
    """Get statistics about the context memory.

    Args:
        ctx: MCP context

    Returns:
        Context memory statistics.
    """
    manager = _get_memory_manager()
    if manager is None:
        return {"error": "Context system not available"}

    try:
        stats = manager.graph_store.get_stats()
        return {
            "total_nodes": stats.get("total_nodes", 0),
            "total_edges": stats.get("total_edges", 0),
            "nodes_by_type": stats.get("nodes_by_type", {}),
            "edges_by_type": stats.get("edges_by_type", {}),
        }
    except Exception as e:
        return {"error": str(e)}


def register_context_tools(mcp: Any) -> None:
    """Register context tools with MCP server."""
    mcp.tool()(store_conversation)
    mcp.tool()(store_task)
    mcp.tool()(log_mistake)
    mcp.tool()(search_context)
    mcp.tool()(get_relevant_context)
    mcp.tool()(store_pattern)
    mcp.tool()(get_context_stats)


# Alias for backward compatibility
store_task_result = store_task
