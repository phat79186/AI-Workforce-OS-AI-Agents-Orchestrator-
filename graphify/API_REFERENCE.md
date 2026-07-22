# Graphify — API Reference

> Complete endpoint reference for the Graphify REST API.

**Base URL:** `http://127.0.0.1:5004`

**Start server:**
```bash
python -m graphify serve --db .graphify.db --port 5004
```

All responses are JSON. All endpoints support CORS.

---

## Common Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `project_id` | string | Filter results to a specific project (SHA-256 prefix) |
| `limit` | int | Max results to return (default varies, max 500) |
| `top` | int | Top-N for ranked results (default 20, max 100) |

---

## Health

### `GET /api/health`

Health check and basic statistics.

**Response:**
```json
{
  "status": "ok",
  "db": ".graphify.db",
  "total_nodes": 1542
}
```

---

## Projects

### `GET /api/projects`

List all scanned projects.

**Response:**
```json
[
  {
    "project_id": "a1b2c3d4e5f6",
    "name": "my-project",
    "root_path": "/home/user/my-project",
    "total_files": 142,
    "total_lines": 28500,
    "languages": ["python", "javascript", "yaml"],
    "scanned_at": "2025-01-15T10:30:00Z"
  }
]
```

### `GET /api/projects/<project_id>`

Project summary with node/edge statistics.

### `GET /api/projects/<project_id>/stats`

Detailed statistics breakdown by type.

---

## Search

### `GET /api/search`

Full-text search across all nodes.

**Parameters:**

| Param | Required | Description |
|-------|----------|-------------|
| `q` | ✅ | Search query |
| `project_id` | | Filter by project |
| `limit` | | Max results (default 50, max 500) |

**Response:**
```json
[
  {
    "name": "UserAuthentication",
    "type": "CLASS",
    "file": "src/auth.py",
    "score": 0.95,
    "snippet": "class UserAuthentication:..."
  }
]
```

### `GET /api/search/name`

Exact name search (prefix match).

**Parameters:**

| Param | Required | Description |
|-------|----------|-------------|
| `name` | ✅ | Node name to search |
| `project_id` | | Filter by project |

**Response:**
```json
[
  {
    "id": "abc123",
    "name": "UserAuthentication",
    "type": "CLASS",
    "file": "src/auth.py"
  }
]
```

---

## Graph Queries

### `GET /api/files/<file_path>`

Get all nodes within a specific file.

### `GET /api/classes`

Get class hierarchy with inheritance relationships.

### `GET /api/dependencies`

Get import/dependency graph.

### `GET /api/tests`

Get test files and their relationships.

### `GET /api/hotspots`

Get complexity hotspots (files with most nodes/connections).

**Parameters:** `top` (default 20), `project_id`

### `GET /api/languages`

Get language breakdown with file counts.

**Response:**
```json
{
  "python": {"files": 85, "nodes": 420},
  "javascript": {"files": 32, "nodes": 180},
  "yaml": {"files": 12, "nodes": 45}
}
```

### `GET /api/subgraph/<node_id>`

Get a node and its neighborhood up to N hops.

**Parameters:** `depth` (default 3, max 5)

---

## Intelligence

### `GET /api/god-nodes`

Find highest-degree nodes — the concepts everything connects through.

**Parameters:** `top` (default 20, max 100), `project_id`

**Response:**
```json
[
  {
    "name": "Database",
    "type": "CLASS",
    "file": "src/db.py",
    "degree": 47
  }
]
```

### `GET /api/explain/<name>`

Explain a node: its neighbors, edge types, rationale, and context.

**Parameters:** `project_id`

**Response:**
```json
{
  "node": {
    "name": "UserService",
    "type": "CLASS",
    "file": "src/services/user.py"
  },
  "neighbors": [
    {"name": "Database", "edge_type": "IMPORTS", "direction": "outgoing"},
    {"name": "UserModel", "edge_type": "DEPENDS_ON", "direction": "outgoing"}
  ],
  "rationale": "# NOTE: Main user service implementing auth and profile ops"
}
```

### `GET /api/path/<start>/<end>`

Find shortest path between two nodes (BFS).

**Parameters:** `project_id`

**Response:**
```json
{
  "path": ["UserService", "Database", "ConnectionPool"],
  "edges": [
    {"from": "UserService", "to": "Database", "type": "IMPORTS"},
    {"from": "Database", "to": "ConnectionPool", "type": "DEPENDS_ON"}
  ],
  "length": 2
}
```

### `GET /api/communities`

Detect communities (connected components) in the graph.

**Parameters:** `project_id`

**Response:**
```json
{
  "count": 5,
  "communities": {
    "community_0": {
      "size": 42,
      "nodes": ["UserService", "Database", "..."]
    }
  }
}
```

---

## Metrics

### `GET /api/metrics/<project_id>`

Get scan metrics history and averages.

**Parameters:** `limit` (default 20, max 100)

**Response:**
```json
{
  "history": [
    {
      "id": 1,
      "started_at": 1705312200.0,
      "duration_s": 3.45,
      "files_total": 142,
      "files_cached": 130,
      "cache_hit_rate": 0.915,
      "nodes_added": 12,
      "edges_added": 8
    }
  ],
  "averages": {
    "total_scans": 15,
    "avg_duration_s": 2.1,
    "avg_files_total": 140,
    "avg_cache_hit_rate": 0.92
  }
}
```

---

## Snapshots & Diffing

### `GET /api/snapshots/<project_id>`

List all graph snapshots for a project (newest first).

**Response:**
```json
[
  {
    "id": 2,
    "project_id": "a1b2c3",
    "label": "v1.1",
    "created_at": 1705312200.0,
    "node_count": 156,
    "edge_count": 203
  }
]
```

### `POST /api/snapshots/<project_id>/take`

Take a snapshot of the current graph state.

**Parameters:** `label` (optional, query param)

**Response:**
```json
{
  "snapshot_id": 3
}
```

### `GET /api/diff/<snap_a>/<snap_b>`

Diff two snapshots by ID.

**Response:**
```json
{
  "project_id": "a1b2c3",
  "before_label": "v1.0",
  "after_label": "v1.1",
  "nodes_added": [{"id": "n1", "name": "NewClass", "type": "CLASS"}],
  "nodes_removed": [],
  "edges_added": [{"source": "NewClass", "target": "Base", "type": "INHERITS"}],
  "edges_removed": [],
  "summary": {
    "nodes_added": 1,
    "nodes_removed": 0,
    "edges_added": 1,
    "edges_removed": 0
  }
}
```

---

## Export

### `GET /api/export/json`

Export the full graph as JSON.

**Parameters:** `project_id`

### `GET /api/export/dot`

Export as DOT format for Graphviz.

### `GET /api/export/markdown`

Export as Markdown summary.

### `GET /api/export/graphml`

Export as GraphML for Gephi/yEd.

---

## Error Responses

All errors return structured JSON:

### 400 — Validation Error
```json
{
  "error": "Invalid project_id format",
  "code": "VALIDATION_ERROR",
  "field": "project_id"
}
```

### 404 — Not Found
```json
{
  "error": "Not found"
}
```

### 500 — Server Error
```json
{
  "error": "Database connection failed",
  "code": "GRAPH_ERROR"
}
```

---

## CORS Headers

All responses include:

```
Access-Control-Allow-Origin: *
Access-Control-Allow-Methods: GET, POST, OPTIONS
Access-Control-Allow-Headers: Content-Type, Authorization
X-Content-Type-Options: nosniff
```
