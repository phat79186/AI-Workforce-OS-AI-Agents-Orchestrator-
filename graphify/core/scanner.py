"""
Directory scanner — walks a project tree, classifies files, dispatches

to language-specific analyzers, and assembles the complete graph.

Supports incremental updates via SHA-256 content caching: re-scans only
process files whose content has changed since the last run.
"""

from __future__ import annotations

import logging
import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

from graphify.core.cache import ContentCache
from graphify.core.config import GraphifyConfig
from graphify.core.graph import GraphStore
from graphify.core.ignore import IgnoreFilter
from graphify.core.schema import (
    Edge,
    EdgeType,
    Node,
    NodeType,
    ProjectSummary,
    classify_language,
    generate_project_id,
)

logger = logging.getLogger(__name__)


class Scanner:
    """Walks a directory tree, analyzes source files, and builds a graph."""

    def __init__(
        self,
        root_path: str,
        store: GraphStore,
        config: GraphifyConfig | None = None,
    ) -> None:
        self._root = os.path.normpath(os.path.abspath(root_path))
        if not os.path.isdir(self._root):
            raise FileNotFoundError(f"Not a directory: {self._root}")

        self._store = store
        self._config = config or GraphifyConfig()
        self._project_id = generate_project_id(self._root)
        self._project_name = os.path.basename(self._root)

        # Ignore filter (.graphifyignore support)
        self._ignore = IgnoreFilter(self._root)

        # Content cache for incremental updates
        self._cache: ContentCache | None = None
        if self._config.use_cache:
            self._cache = ContentCache(store._get_conn)  # noqa: SLF001

        # Accumulators (populated during scan)
        self._nodes: list[Node] = []
        self._edges: list[Edge] = []
        self._language_counts: dict[str, int] = {}
        self._total_lines = 0
        self._total_classes = 0
        self._total_functions = 0
        self._total_tests = 0
        self._dependencies: list[str] = []
        self._frameworks: list[str] = []
        self._file_count = 0
        self._cached_count = 0
        self._failed_files: list[str] = []

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def scan(self, incremental: bool = False) -> ProjectSummary:
        """Execute full or incremental scan and return project summary.

        Args:
            incremental: If True, skip files whose SHA-256 hash hasn't changed.
        """
        start = time.time()
        logger.info("Scanning project: %s (incremental=%s)", self._root, incremental)

        # Phase 1: collect eligible file paths
        file_paths = self._collect_files()
        logger.info("Found %d eligible files", len(file_paths))

        # Phase 2: filter for changed files (incremental mode)
        pending_hashes: dict[str, str] = {}
        if incremental and self._cache:
            file_paths, removed, pending_hashes = self._filter_changed(file_paths)
            self._handle_removals(removed)
            logger.info(
                "%d files changed, %d cached, %d removed",
                len(file_paths),
                self._cached_count,
                len(removed),
            )

        # Phase 3: create project root node
        self._create_project_node()

        # Phase 4: create directory structure nodes
        self._create_directory_nodes(file_paths)

        # Phase 5: analyze files (parallelised)
        self._analyze_files(file_paths)

        # Phase 6: detect frameworks from accumulated data
        self._detect_frameworks()

        # Phase 7: flush to store
        self._store.add_nodes_bulk(self._nodes)
        self._store.add_edges_bulk(self._edges)

        # Phase 8: build and save summary
        summary = ProjectSummary(
            project_id=self._project_id,
            root_path=self._root,
            name=self._project_name,
            languages=dict(self._language_counts),
            total_files=self._file_count + self._cached_count,
            total_lines=self._total_lines,
            total_classes=self._total_classes,
            total_functions=self._total_functions,
            total_tests=self._total_tests,
            dependencies=self._dependencies,
            frameworks=self._frameworks,
            scanned_at=time.time(),
        )
        self._store.save_project_meta(summary)

        elapsed = time.time() - start
        logger.info(
            "Scan complete: %d files (%d cached, %d failed), %d nodes, %d edges in %.2fs",
            self._file_count,
            self._cached_count,
            len(self._failed_files),
            len(self._nodes),
            len(self._edges),
            elapsed,
        )
        if self._failed_files:
            logger.warning("Failed files: %s", ", ".join(self._failed_files))
        return summary

    @property
    def project_id(self) -> str:
        """Return the deterministic project ID."""
        return self._project_id

    # ------------------------------------------------------------------
    # Phase 1: file collection
    # ------------------------------------------------------------------

    def _collect_files(self) -> list[str]:
        """Walk directory tree respecting config limits, skip rules, and .graphifyignore."""
        result: list[str] = []
        skip_dirs = self._config.skip_dirs
        skip_files = self._config.skip_files
        binary_ext = self._config.binary_extensions

        for dirpath, dirnames, filenames in os.walk(self._root):
            # Compute depth
            rel = os.path.relpath(dirpath, self._root)
            depth = 0 if rel == "." else rel.count(os.sep) + 1
            if depth > self._config.max_depth:
                dirnames.clear()
                continue

            # Prune skip directories (in-place to prevent os.walk descent)
            dirnames[:] = sorted(
                d for d in dirnames if d not in skip_dirs and not d.startswith(".")
            )

            # Also prune directories matching .graphifyignore
            if self._ignore.has_rules:
                dirnames[:] = [
                    d
                    for d in dirnames
                    if not self._ignore.is_ignored(
                        os.path.relpath(os.path.join(dirpath, d), self._root)
                    )
                ]

            for fname in sorted(filenames):
                if fname in skip_files or fname.startswith("."):
                    continue
                _, ext = os.path.splitext(fname)
                if ext.lower() in binary_ext:
                    continue

                fpath = os.path.join(dirpath, fname)

                # Check .graphifyignore
                if self._ignore.has_rules:
                    rel_path = os.path.relpath(fpath, self._root)
                    if self._ignore.is_ignored(rel_path):
                        continue

                try:
                    size = os.path.getsize(fpath)
                except OSError:
                    continue
                if size > self._config.max_file_size_bytes:
                    continue

                result.append(fpath)
                if len(result) >= self._config.max_files:
                    logger.warning("Reached max_files limit (%d)", self._config.max_files)
                    return result
        return result

    # ------------------------------------------------------------------
    # Phase 2: incremental change detection
    # ------------------------------------------------------------------

    def _filter_changed(self, file_paths: list[str]) -> tuple[list[str], set[str], dict[str, str]]:
        """Compare current files against cache; return (changed, removed, pending_hashes)."""
        if not self._cache:
            return file_paths, set(), {}

        cached_hashes = self._cache.get_all_hashes(self._project_id)
        current_rel_paths = set()
        changed: list[str] = []
        new_hashes: dict[str, str] = {}

        for fpath in file_paths:
            rel = os.path.relpath(fpath, self._root)
            current_rel_paths.add(rel)

            try:
                current_hash = ContentCache.hash_file(fpath)
            except OSError:
                continue

            cached_hash = cached_hashes.get(rel)
            if cached_hash == current_hash:
                self._cached_count += 1
                continue

            changed.append(fpath)
            new_hashes[rel] = current_hash

        # Detect removed files
        removed = set(cached_hashes.keys()) - current_rel_paths

        # NOTE: Do NOT write new_hashes to cache here — that happens
        # in _analyze_files after each file is successfully analyzed.
        # Writing early would mark failed files as "cached" permanently.

        # Clean cache for removed files
        if removed:
            self._cache.remove_paths(removed, self._project_id)

        return changed, removed, new_hashes

    def _handle_removals(self, removed: set[str]) -> None:
        """Delete graph nodes for files that no longer exist."""
        for rel_path in removed:
            self._store.delete_file_nodes(rel_path, self._project_id)

    # ------------------------------------------------------------------
    # Phase 2: project root
    # ------------------------------------------------------------------

    def _create_project_node(self) -> None:
        """Create the root PROJECT node."""
        node = Node(
            id=self._project_id,
            node_type=NodeType.PROJECT,
            name=self._project_name,
            qualified_name=self._root,
            file_path=self._root,
            project_id=self._project_id,
            content=f"Project root: {self._root}",
        )
        self._nodes.append(node)

    # ------------------------------------------------------------------
    # Phase 3: directory structure
    # ------------------------------------------------------------------

    def _create_directory_nodes(self, file_paths: list[str]) -> None:
        """Create DIRECTORY nodes for each unique directory containing files."""
        seen_dirs: dict[str, str] = {}  # abs_path → node_id

        for fpath in file_paths:
            dirpath = os.path.dirname(fpath)
            while dirpath and dirpath >= self._root:
                if dirpath in seen_dirs:
                    break
                rel = os.path.relpath(dirpath, self._root)
                node_id = f"dir-{generate_project_id(dirpath)[:12]}"
                seen_dirs[dirpath] = node_id

                self._nodes.append(
                    Node(
                        id=node_id,
                        node_type=NodeType.DIRECTORY,
                        name=os.path.basename(dirpath) or self._project_name,
                        qualified_name=rel if rel != "." else self._project_name,
                        file_path=dirpath,
                        project_id=self._project_id,
                    )
                )

                # Edge: parent dir or project CONTAINS this dir
                parent = os.path.dirname(dirpath)
                if parent in seen_dirs:
                    parent_id = seen_dirs[parent]
                elif dirpath == self._root:
                    parent_id = ""
                else:
                    parent_id = self._project_id

                if parent_id:
                    self._edges.append(
                        Edge(
                            source_id=parent_id,
                            target_id=node_id,
                            edge_type=EdgeType.CONTAINS,
                            project_id=self._project_id,
                        )
                    )
                dirpath = os.path.dirname(dirpath)

    # ------------------------------------------------------------------
    # Phase 4: file analysis (parallelised)
    # ------------------------------------------------------------------

    def _analyze_files(self, file_paths: list[str]) -> None:
        """Dispatch files to analyzers using a thread pool."""
        from graphify.analyzers import get_analyzer  # pylint: disable=C0415

        workers = min(self._config.worker_threads, len(file_paths) or 1)
        new_hashes: dict[str, str] = {}

        with ThreadPoolExecutor(max_workers=workers) as pool:
            futures = {
                pool.submit(self._analyze_one_file, fpath, get_analyzer): fpath
                for fpath in file_paths
            }
            for future in as_completed(futures):
                fpath = futures[future]
                try:
                    nodes, edges, meta = future.result()
                    self._nodes.extend(nodes)
                    self._edges.extend(edges)
                    self._merge_meta(meta)
                    self._file_count += 1

                    # Record hash for cache
                    if self._cache:
                        rel = os.path.relpath(fpath, self._root)
                        content_hash = meta.get("content_hash", "")
                        if content_hash:
                            new_hashes[rel] = content_hash
                except Exception:
                    self._failed_files.append(fpath)
                    logger.error("Failed to analyze %s", fpath, exc_info=True)

        # Bulk update cache
        if self._cache and new_hashes:
            self._cache.set_hashes_bulk(new_hashes, self._project_id)

    def _analyze_one_file(self, fpath: str, get_analyzer_fn) -> tuple[list[Node], list[Edge], dict]:
        """Analyze a single file: create FILE node, run analyzer, collect results."""
        rel_path = os.path.relpath(fpath, self._root)
        lang = classify_language(fpath)
        file_node_id = f"file-{generate_project_id(fpath)[:12]}"

        # Read file content
        try:
            with open(fpath, encoding="utf-8", errors="replace") as fh:
                source = fh.read()
        except OSError:
            return [], [], {}

        line_count = source.count("\n") + 1
        content_hash = ContentCache.hash_content(source)

        # Create FILE node
        file_node = Node(
            id=file_node_id,
            node_type=NodeType.FILE,
            name=os.path.basename(fpath),
            qualified_name=rel_path,
            file_path=rel_path,
            language=lang.value,
            line_start=1,
            line_end=line_count,
            content=source[:2000],  # truncate for indexing
            metadata={"size_bytes": len(source), "line_count": line_count},
            project_id=self._project_id,
        )

        nodes = [file_node]
        edges = []

        # Edge: directory CONTAINS file
        dir_id = f"dir-{generate_project_id(os.path.dirname(fpath))[:12]}"
        edges.append(
            Edge(
                source_id=dir_id,
                target_id=file_node_id,
                edge_type=EdgeType.CONTAINS,
                project_id=self._project_id,
            )
        )

        # Run language-specific analyzer
        analyzer = get_analyzer_fn(lang)
        if analyzer is not None:
            result = analyzer.analyze(
                source=source,
                file_path=rel_path,
                file_node_id=file_node_id,
                project_id=self._project_id,
            )
            nodes.extend(result.nodes)
            edges.extend(result.edges)

        meta = {
            "language": lang.value,
            "line_count": line_count,
            "classes": sum(1 for n in nodes if n.node_type == NodeType.CLASS),
            "functions": sum(1 for n in nodes if n.node_type == NodeType.FUNCTION),
            "tests": sum(1 for n in nodes if n.node_type == NodeType.TEST),
            "content_hash": content_hash,
        }
        return nodes, edges, meta

    # ------------------------------------------------------------------
    # Metadata merging
    # ------------------------------------------------------------------

    def _merge_meta(self, meta: dict) -> None:
        """Merge per-file metadata into project accumulators."""
        lang = meta.get("language", "unknown")
        self._language_counts[lang] = self._language_counts.get(lang, 0) + 1
        self._total_lines += meta.get("line_count", 0)
        self._total_classes += meta.get("classes", 0)
        self._total_functions += meta.get("functions", 0)
        self._total_tests += meta.get("tests", 0)

    def _detect_frameworks(self) -> None:
        """Detect frameworks from dependency and file patterns."""
        indicators: dict[str, list[str]] = {
            "Flask": ["flask"],
            "Django": ["django"],
            "FastAPI": ["fastapi"],
            "React": ["react", "react-dom"],
            "Vue": ["vue"],
            "Angular": ["@angular/core"],
            "Next.js": ["next"],
            "Express": ["express"],
            "pytest": ["pytest"],
            "Jest": ["jest"],
            "Spring": ["spring-boot"],
            "Rails": ["rails"],
            "Tailwind CSS": ["tailwindcss"],
        }
        dep_set = {d.lower() for d in self._dependencies}
        for framework, markers in indicators.items():
            if any(m.lower() in dep_set for m in markers):
                self._frameworks.append(framework)
