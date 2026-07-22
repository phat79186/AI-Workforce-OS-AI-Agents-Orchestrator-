# Graphify — Architecture Reference

> Internal architecture documentation for the Graphify knowledge-graph engine.

---

## System Overview

Graphify is a self-contained subsystem (zero imports from `orchestrator/` or `agentic_team/`)
that transforms any project directory into a queryable SQLite-backed knowledge graph.

```mermaid
graph TB
    INPUT["Project Directory<br/>(source code, docs, configs)"]
    SCANNER["Scanner<br/>walks file tree"]
    CACHE["ContentCache<br/>SHA-256 dedup"]
    ANALYZERS["Analyzers<br/>Python/JS/Doc/Config/Generic"]
    GRAPH["GraphStore<br/>SQLite + FTS5 + WAL"]
    MIGRATIONS["Migrations<br/>v1 → v2 → v3"]
    SEARCH["Search Layer<br/>FTS + Query Engine"]
    OUTPUT["Output<br/>CLI / API / Export / HTML"]

    INPUT --> SCANNER
    SCANNER --> CACHE
    SCANNER --> ANALYZERS
    ANALYZERS --> GRAPH
    GRAPH --> MIGRATIONS
    GRAPH --> SEARCH
    SEARCH --> OUTPUT
```

---

## Core Components

### 1. Scanner (`core/scanner.py`)

The Scanner orchestrates the scan process:

```mermaid
flowchart TD
    START[scan(path)] --> WALK[os.walk directory tree]
    WALK --> FILTER{.graphifyignore?}
    FILTER -->|excluded| SKIP[Skip file]
    FILTER -->|included| SIZE{> max_file_size?}
    SIZE -->|too large| SKIP
    SIZE -->|ok| HASH[SHA-256 hash]
    HASH --> CACHED{In cache?}
    CACHED -->|yes| COUNT[Increment cache hits]
    CACHED -->|no| LANG[Classify language]
    LANG --> ANALYZE[Run analyzer]
    ANALYZE --> STORE[Store nodes + edges]
    STORE --> UPDATECACHE[Update cache]
    COUNT --> NEXT[Next file]
    UPDATECACHE --> NEXT
    SKIP --> NEXT
    NEXT --> DONE{More files?}
    DONE -->|yes| FILTER
    DONE -->|no| INDEX[Rebuild FTS index]
    INDEX --> SUMMARY[Return ScanSummary]
```

**Key design decisions:**
- Project ID is a SHA-256 prefix of the canonical directory path (deterministic, portable)
- Files are classified by extension into language categories
- Each analyzer returns an `AnalysisResult` with nodes and edges
- Incremental mode: only re-analyzes files whose content hash changed

### 2. GraphStore (`core/graph.py`)

The persistence layer uses SQLite with several hardening features:

```mermaid
erDiagram
    nodes {
        text id PK
        text node_type
        text name
        text file_path
        integer line_number
        text language
        text docstring
        text source_snippet
        text metadata_json
        text project_id
        text created_at
        text updated_at
    }

    edges {
        text source_id FK
        text target_id FK
        text edge_type
        text label
        real confidence
        text provenance
        text project_id
    }

    nodes_fts {
        text name
        text node_type
        text file_path
        text docstring
    }

    scan_metrics {
        integer id PK
        text project_id
        real started_at
        real duration_s
        integer files_total
        integer files_cached
        real cache_hit_rate
        text analyzer_ms_json
        integer nodes_added
        integer edges_added
    }

    graph_snapshots {
        integer id PK
        text project_id
        text label
        real created_at
        text nodes_json
        text edges_json
    }

    schema_meta {
        integer version PK
        text applied_at
    }

    nodes ||--o{ edges : "source/target"
    nodes ||--o{ nodes_fts : "indexed"
```

**Design patterns:**
- **Thread-local connections** via `threading.local()` — safe for multi-threaded API servers
- **WAL mode** for concurrent reads during writes
- **FTS5 virtual table** for efficient full-text search
- **Context manager** (`with GraphStore() as store:`) for automatic cleanup

### 3. Schema (`core/schema.py`)

Type-safe node and edge definitions:

```mermaid
classDiagram
    class NodeType {
        <<enumeration>>
        FILE
        CLASS
        FUNCTION
        METHOD
        IMPORT
        VARIABLE
        MODULE
        PACKAGE
        TEST
        DECORATOR
        INTERFACE
        CONFIG_KEY
        DOCUMENT
        SECTION
        RATIONALE
        PROJECT
    }

    class EdgeType {
        <<enumeration>>
        CONTAINS
        IMPORTS
        CALLS
        INHERITS
        IMPLEMENTS
        DEPENDS_ON
        TESTS
        DECORATES
        REFERENCES
        DOCUMENTS
        HAS_CONFIG
        SEMANTICALLY_SIMILAR
        HAS_RATIONALE
        BELONGS_TO_PROJECT
    }

    class EdgeProvenance {
        <<enumeration>>
        EXTRACTED
        INFERRED
        AMBIGUOUS
    }

    class Node {
        +id: str
        +node_type: NodeType
        +name: str
        +file_path: str
        +line_number: int
        +language: str
        +project_id: str
        +metadata: dict
    }

    class Edge {
        +source_id: str
        +target_id: str
        +edge_type: EdgeType
        +confidence: float
        +provenance: EdgeProvenance
        +project_id: str
    }
```

### 4. Migrations (`core/migrations.py`)

Schema evolution with version tracking:

```mermaid
graph LR
    V1["v1: Base schema<br/>nodes + edges + FTS"] --> V2["v2: Confidence<br/>+ confidence column<br/>+ provenance column"]
    V2 --> V3["v3: Operations<br/>+ scan_metrics table<br/>+ graph_snapshots table"]
```

- Decorator-based migration registry (`@_register(version)`)
- Idempotent: skips already-applied migrations
- `schema_meta` table tracks applied versions with timestamps

### 5. Cache (`core/cache.py`)

Content-addressable cache using SHA-256:

```mermaid
graph LR
    FILE[File content] --> SHA[SHA-256 hash]
    SHA --> LOOKUP{Hash in cache?}
    LOOKUP -->|hit| SKIP[Skip analysis]
    LOOKUP -->|miss| ANALYZE[Run analyzer]
    ANALYZE --> UPDATE[Store hash in cache]
```

- Per-project cache tables (`cache_{project_id}`)
- Survives process restarts (SQLite-backed)
- Enables incremental scans with O(1) change detection

---

## Analyzer Pipeline

```mermaid
graph TB
    FILE[Source File] --> CLASSIFY[classify_language]
    CLASSIFY --> |python| PY[PythonAnalyzer]
    CLASSIFY --> |javascript/typescript| JS[JavaScriptAnalyzer]
    CLASSIFY --> |markdown/rst| DOC[DocAnalyzer]
    CLASSIFY --> |yaml/json/toml| CFG[ConfigAnalyzer]
    CLASSIFY --> |go/rust/java/c++/other| GEN[GenericAnalyzer]

    PY --> |ast.parse| AST[AST Walk]
    AST --> CLASSES[ClassDef nodes]
    AST --> FUNCTIONS[FunctionDef nodes]
    AST --> IMPORTS[Import nodes]
    AST --> CALLS[Call graph edges]
    AST --> DECORATORS[Decorator nodes]
    AST --> RATIONALE[Comment rationale]

    JS --> REGEX[Regex patterns]
    REGEX --> JSCLASS[class/function nodes]
    REGEX --> JSIMPORT[import/export edges]

    subgraph Result
        CLASSES --> AR[AnalysisResult]
        FUNCTIONS --> AR
        IMPORTS --> AR
        CALLS --> AR
        DECORATORS --> AR
        RATIONALE --> AR
        JSCLASS --> AR
        JSIMPORT --> AR
    end
```

### Python Analyzer (Deep AST)

The Python analyzer is the most sophisticated, using `ast.parse` for:

1. **Classes** — Name, bases, methods, decorators, docstrings
2. **Functions** — Name, args, return type, decorators, docstrings
3. **Imports** — `import x` and `from x import y`
4. **Call graph** — Function/method calls with resolved targets
5. **Rationale comments** — `# NOTE:`, `# HACK:`, `# WHY:`, `# IMPORTANT:`
6. **Type annotations** — Parameter types, return types

---

## Search & Query Architecture

```mermaid
graph TB
    subgraph "Search Layer"
        FTS[FTSEngine<br/>Full-text search via FTS5]
        QE[QueryEngine<br/>Graph traversal + analytics]
    end

    subgraph "FTS Capabilities"
        FS[search(query)]
        FN[search_by_name(name)]
    end

    subgraph "Query Capabilities"
        EX[explain_node(name)]
        FP[find_path(start, end)]
        CD[detect_communities()]
        GN[god_nodes()]
        CH[complexity_hotspots()]
        SG[get_subgraph(node, depth)]
        LB[language_breakdown()]
    end

    FTS --> FS
    FTS --> FN
    QE --> EX
    QE --> FP
    QE --> CD
    QE --> GN
    QE --> CH
    QE --> SG
    QE --> LB
```

---

## Operations Layer

### Metrics Collection

```mermaid
graph LR
    SCAN[Scanner] -->|start/stop timer| SM[ScanMetrics]
    SM -->|record| MS[MetricsStore]
    MS -->|SQLite| DB[(scan_metrics table)]
    API[REST API] -->|history/averages| MS
```

### Diffing & Snapshots

```mermaid
graph LR
    USER[User/API] -->|take_snapshot| GD[GraphDiffer]
    GD -->|serialize| DB[(graph_snapshots)]
    USER -->|diff_snapshots| GD
    GD -->|compare| DIFF[GraphDiff]
    DIFF -->|nodes_added<br/>nodes_removed<br/>edges_added<br/>edges_removed| RESULT[Diff Result]
```

### File Watching

```mermaid
graph TD
    FS[File System Events] --> WD{watchdog<br/>installed?}
    WD -->|yes| OBS[Observer<br/>OS-level notifications]
    WD -->|no| POLL[Polling loop<br/>100ms interval]
    OBS --> FW[FileWatcher]
    POLL --> FW
    FW --> FILTER{Is relevant?<br/>Not .git, node_modules, etc.}
    FILTER -->|yes| QUEUE[Pending queue]
    FILTER -->|no| DROP[Discard]
    QUEUE --> DEBOUNCE{2s elapsed?}
    DEBOUNCE -->|yes| FLUSH[Flush → callback]
    DEBOUNCE -->|no| WAIT[Wait]
```

---

## Error Handling

```mermaid
classDiagram
    class GraphifyError {
        <<base>>
        +code: str
        +message: str
    }
    class ScanError {
        +path: str
    }
    class AnalysisError {
        +file_path: str
        +analyzer: str
    }
    class GraphError
    class SchemaVersionError {
        +expected: int
        +actual: int
    }
    class NodeNotFoundError {
        +node_id: str
    }
    class ConfigError
    class ExportError {
        +format: str
    }
    class RenderError
    class ValidationError {
        +field: str
    }
    class PathTraversalError {
        +path: str
        +root: str
    }
    class WatchError

    GraphifyError <|-- ScanError
    GraphifyError <|-- AnalysisError
    GraphifyError <|-- GraphError
    GraphifyError <|-- ConfigError
    GraphifyError <|-- ExportError
    GraphifyError <|-- RenderError
    GraphifyError <|-- WatchError
    GraphError <|-- SchemaVersionError
    GraphError <|-- NodeNotFoundError
    ValidationError --|> GraphifyError
    PathTraversalError --|> ValidationError
```

---

## REST API Architecture

```mermaid
graph TB
    CLIENT[HTTP Client] --> CORS[CORS Middleware]
    CORS --> ROUTER[Flask Router]

    ROUTER --> HEALTH[/api/health]
    ROUTER --> PROJ[/api/projects/*]
    ROUTER --> SRCH[/api/search*]
    ROUTER --> GRAPH[/api/classes, dependencies, ...]
    ROUTER --> INTEL[/api/god-nodes, explain, ...]
    ROUTER --> METRICS[/api/metrics/*]
    ROUTER --> SNAP[/api/snapshots/*]
    ROUTER --> EXPORT[/api/export/*]

    subgraph "Error Handling"
        VE[ValidationError → 400]
        GE[GraphifyError → 500]
        NF[404 → Not Found]
        GEN[Exception → 500]
    end

    ROUTER --> VE
    ROUTER --> GE
    ROUTER --> NF
    ROUTER --> GEN
```

---

## Extension Points

### Adding a New Analyzer

1. Create `graphify/analyzers/my_analyzer.py`
2. Subclass `BaseAnalyzer`
3. Implement `analyze(file_path, content, project_id) → AnalysisResult`
4. Register the language mapping in `Scanner._get_analyzer()`

### Adding a New Export Format

1. Add a method to `GraphExporter` in `export/formatters.py`
2. Wire it into `cli.py` export command and `api/server.py`

### Adding a New Migration

1. Add a function in `core/migrations.py` with the `@_register(version)` decorator
2. Bump `SCHEMA_VERSION` in `core/graph.py`

---

## Performance Characteristics

| Operation | Complexity | Notes |
|-----------|-----------|-------|
| Full scan (cold) | O(n × f) | n = files, f = avg file size |
| Incremental scan | O(Δ) | Only changed files |
| FTS search | O(log n) | SQLite FTS5 inverted index |
| BFS path finding | O(V + E) | Bounded by graph size |
| God node analysis | O(n log n) | Sort by degree |
| Community detection | O(V + E) | Connected components |
| Cache lookup | O(1) | SHA-256 hash comparison |

---

## Thread Safety

- **GraphStore**: Thread-local `sqlite3.Connection` objects (each thread gets its own)
- **WAL mode**: Multiple readers, single writer — no reader blocking
- **FileWatcher**: Thread-safe pending queue with `threading.Lock`
- **MetricsStore / GraphDiffer**: Use GraphStore's thread-local connection getter

---

## File Layout

```
graphify/                    # 34 Python files, ~6400 LOC
├── core/                    # Data layer (12 files)
│   ├── graph.py             # SQLite store (700 LOC)
│   ├── scanner.py           # File tree walker
│   ├── schema.py            # Type definitions
│   ├── cache.py             # SHA-256 cache
│   ├── config.py            # Configuration
│   ├── migrations.py        # Schema evolution
│   ├── metrics.py           # Scan performance
│   ├── differ.py            # Snapshots & diffs
│   ├── watcher.py           # File system watch
│   ├── validation.py        # Input safety
│   ├── exceptions.py        # Error hierarchy
│   └── ignore.py            # .graphifyignore
├── analyzers/               # Language parsers (6 files)
├── search/                  # Query engines (2 files)
├── api/                     # REST API (1 file)
├── export/                  # Formatters (1 file)
├── report/                  # Markdown generator (1 file)
└── visualization/           # HTML renderer (1 file)
```
