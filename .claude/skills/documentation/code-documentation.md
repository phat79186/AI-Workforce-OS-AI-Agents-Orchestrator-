# Skill: Code Documentation

Write clear, comprehensive code documentation with docstrings and comments.

## Capabilities
- Google-style docstrings
- Type hints documentation
- Module and package docs
- Inline comments (when needed)
- README files
- Changelog maintenance

## Patterns

### Module Docstring
```python
"""Graph-based context storage for AI agent memory.

This module provides persistent storage for conversations, tasks, mistakes,
and patterns using a SQLite-backed graph database with full-text search.

Example:
    >>> from orchestrator.context import GraphStore
    >>> store = GraphStore("context.db")
    >>> node = ConversationNode(
    ...     title="Code review session",
    ...     messages=[{"role": "user", "content": "Review my code"}]
    ... )
    >>> store.add_node(node)

Note:
    The database file is created automatically if it doesn't exist.
    Thread safety is ensured through thread-local connections.

See Also:
    - :class:`MemoryManager`: High-level API for context operations
    - :mod:`orchestrator.context.schemas`: Node and edge type definitions
"""
```

### Class Docstring
```python
class GraphStore:
    """SQLite-backed graph database with full-text search.

    Provides storage for nodes and edges with support for full-text search
    via FTS5, JSON metadata columns, and embedding vectors.

    Attributes:
        db_path: Path to the SQLite database file.

    Example:
        >>> store = GraphStore("/path/to/context.db")
        >>> node = TaskNode(title="Fix bug", content="...")
        >>> node_id = store.add_node(node)
        >>> retrieved = store.get_node(node_id)

    Note:
        Uses thread-local connections for thread safety. Each thread
        gets its own database connection.
    """

    def __init__(self, db_path: str) -> None:
        """Initialize the graph store.

        Args:
            db_path: Path to SQLite database file. Created if not exists.

        Raises:
            PermissionError: If the path is not writable.
        """
```

### Function Docstring (Google Style)
```python
def add_node(self, node: BaseNode) -> str:
    """Add a node to the graph.

    Inserts a new node with automatic ID generation if not provided.
    The node is indexed for full-text search and optionally embedded.

    Args:
        node: The node to add. Must be a subclass of BaseNode with
            at minimum a title and content.

    Returns:
        The ID of the created node. If the node had an ID, returns
        the same ID. Otherwise, returns a newly generated UUID.

    Raises:
        ValueError: If node validation fails (empty title or content).
        sqlite3.IntegrityError: If a node with the same ID exists.

    Example:
        >>> node = TaskNode(
        ...     title="Implement feature",
        ...     content="Add user authentication",
        ...     status="completed"
        ... )
        >>> node_id = store.add_node(node)
        >>> print(f"Created node: {node_id}")

    Note:
        The node is automatically indexed for full-text search.
        To also generate embeddings, call `embed_node()` after.
    """
```

### Type Hints with Documentation
```python
from typing import List, Optional, TypeVar, Generic

T = TypeVar('T', bound='BaseNode')

class SearchResult(Generic[T]):
    """Result from a search operation.

    Attributes:
        node: The matched node.
        score: Relevance score (0.0 to 1.0).
        highlights: Matching text snippets with highlighting.
    """

    node: T
    score: float
    highlights: List[str]

    def __init__(
        self,
        node: T,
        score: float,
        highlights: Optional[List[str]] = None
    ) -> None:
        """Initialize search result.

        Args:
            node: The matched node.
            score: Relevance score between 0.0 and 1.0.
            highlights: Optional list of highlighted matching snippets.
        """
```

### README Structure
```markdown
# Project Name

Brief description of what the project does.

## Features

- Feature 1
- Feature 2

## Installation

```bash
pip install project-name
```

## Quick Start

```python
from project import Client

client = Client()
result = client.do_something()
```

## Configuration

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| timeout | int | 30 | Request timeout in seconds |

## API Reference

See [API Documentation](docs/api.md).

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md).

## License

MIT License - see [LICENSE](LICENSE).
```

### Changelog Entry
```markdown
## [1.2.0] - 2024-01-15

### Added
- Graph-based context storage system (#123)
- Hybrid search combining BM25 and semantic search (#124)

### Changed
- Improved task routing algorithm for better agent selection
- Updated Flask to 3.0.0

### Fixed
- Memory leak in embedding service (#125)
- Race condition in concurrent task execution (#126)

### Deprecated
- `execute_sync()` method - use `execute()` with `await` instead

### Security
- Fixed SQL injection vulnerability in search (CVE-2024-XXXXX)
```

## Checklist
- [ ] All public APIs have docstrings
- [ ] Args, Returns, Raises documented
- [ ] Examples included for complex functions
- [ ] Type hints on all signatures
- [ ] Module has overview docstring
- [ ] README explains quick start
- [ ] CHANGELOG follows Keep a Changelog
- [ ] Comments explain "why", not "what"
