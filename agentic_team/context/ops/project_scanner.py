"""
Project Scanner - Analyzes a project directory to build context graph nodes.

Independent implementation — does NOT import from orchestrator/context.
Scans file structure, detects languages/frameworks, reads configs, and
creates graph nodes representing the project's architecture and conventions.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from agentic_team.context.models.schemas import (
    DecisionNode,
    Edge,
    EdgeType,
    Node,
    NodeType,
    PatternNode,
    ProjectNode,
)

logger = logging.getLogger("agentic_team.context.project_scanner")

# File extensions → language mapping
LANGUAGE_MAP: dict[str, str] = {
    ".py": "python",
    ".js": "javascript",
    ".ts": "typescript",
    ".tsx": "tsx",
    ".jsx": "jsx",
    ".java": "java",
    ".kt": "kotlin",
    ".go": "go",
    ".rs": "rust",
    ".rb": "ruby",
    ".php": "php",
    ".cs": "csharp",
    ".cpp": "cpp",
    ".c": "c",
    ".h": "c",
    ".hpp": "cpp",
    ".swift": "swift",
    ".scala": "scala",
    ".r": "r",
    ".R": "r",
    ".sql": "sql",
    ".sh": "shell",
    ".bash": "shell",
    ".zsh": "shell",
    ".yml": "yaml",
    ".yaml": "yaml",
    ".json": "json",
    ".toml": "toml",
    ".xml": "xml",
    ".html": "html",
    ".css": "css",
    ".scss": "scss",
    ".less": "less",
    ".md": "markdown",
    ".rst": "restructuredtext",
    ".dockerfile": "docker",
    ".tf": "terraform",
    ".proto": "protobuf",
    ".graphql": "graphql",
    ".gql": "graphql",
}

# Framework detection patterns: (file_pattern, framework_name)
FRAMEWORK_INDICATORS: list[tuple[str, str]] = [
    ("requirements.txt", "python"),
    ("pyproject.toml", "python"),
    ("setup.py", "python"),
    ("Pipfile", "python"),
    ("package.json", "node"),
    ("tsconfig.json", "typescript"),
    ("Cargo.toml", "rust"),
    ("go.mod", "go"),
    ("Gemfile", "ruby"),
    ("pom.xml", "java-maven"),
    ("build.gradle", "java-gradle"),
    ("composer.json", "php"),
    ("mix.exs", "elixir"),
    ("next.config.js", "nextjs"),
    ("next.config.mjs", "nextjs"),
    ("next.config.ts", "nextjs"),
    ("nuxt.config.ts", "nuxtjs"),
    ("angular.json", "angular"),
    ("vue.config.js", "vuejs"),
    ("vite.config.ts", "vite"),
    ("vite.config.js", "vite"),
    ("webpack.config.js", "webpack"),
    ("tailwind.config.js", "tailwindcss"),
    ("tailwind.config.ts", "tailwindcss"),
    ("docker-compose.yml", "docker-compose"),
    ("docker-compose.yaml", "docker-compose"),
    ("Dockerfile", "docker"),
    (".dockerignore", "docker"),
    ("Makefile", "make"),
    ("Jenkinsfile", "jenkins"),
    (".github/workflows", "github-actions"),
    (".gitlab-ci.yml", "gitlab-ci"),
    (".circleci/config.yml", "circleci"),
    ("pytest.ini", "pytest"),
    ("pyproject.toml", "pytest"),
    ("jest.config.js", "jest"),
    ("jest.config.ts", "jest"),
    (".eslintrc.json", "eslint"),
    (".eslintrc.js", "eslint"),
    ("eslint.config.js", "eslint"),
    (".prettierrc", "prettier"),
    ("alembic.ini", "alembic"),
    ("manage.py", "django"),
    ("app.py", "flask-or-fastapi"),
    ("main.py", "fastapi-or-app"),
    ("serverless.yml", "serverless"),
    ("terraform.tf", "terraform"),
    ("k8s/", "kubernetes"),
    ("helm/", "helm"),
    ("prisma/schema.prisma", "prisma"),
    ("drizzle.config.ts", "drizzle"),
]

# Directories to skip during scanning
SKIP_DIRS: set[str] = {
    ".git",
    ".svn",
    ".hg",
    "__pycache__",
    "node_modules",
    ".venv",
    "venv",
    "env",
    ".env",
    ".tox",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    "dist",
    "build",
    ".next",
    ".nuxt",
    "target",
    "out",
    "coverage",
    "htmlcov",
    ".idea",
    ".vscode",
    ".DS_Store",
    "vendor",
    "bower_components",
    ".eggs",
    "*.egg-info",
}

MAX_FILE_SIZE_BYTES = 256 * 1024  # 256 KB — skip very large files
MAX_FILES_TO_SCAN = 5000  # Safety limit for very large repos


def generate_project_id(project_path: str) -> str:
    """Generate a deterministic project_id from the absolute path.

    Uses a SHA-256 prefix so that the same directory always yields the
    same project_id, enabling idempotent rescans.
    """
    normalized = os.path.normpath(os.path.abspath(project_path))
    return hashlib.sha256(normalized.encode()).hexdigest()[:16]


class ProjectScanner:
    """Scans a project directory and produces context graph nodes."""

    def __init__(self, project_path: str):
        self.project_path = Path(project_path).resolve()
        if not self.project_path.is_dir():
            raise ValueError(f"Project path is not a directory: {self.project_path}")
        self.project_id = generate_project_id(str(self.project_path))
        self.project_name = self.project_path.name

    def scan(self) -> dict[str, Any]:
        """Perform a full project scan.

        Returns:
            Dictionary with:
                - project_node: ProjectNode
                - file_nodes: list of Node (FILE type)
                - pattern_nodes: list of PatternNode
                - decision_nodes: list of DecisionNode
                - edges: list of Edge
                - summary: dict with language/framework stats
        """
        logger.info("Scanning project: %s (id=%s)", self.project_path, self.project_id)

        files_info = self._scan_files()
        languages = self._detect_languages(files_info)
        frameworks = self._detect_frameworks()
        structure = self._analyze_structure(files_info)
        config_insights = self._read_config_files()

        project_node = ProjectNode(
            title=f"Project: {self.project_name}",
            content=self._build_project_summary(languages, frameworks, structure),
            project_path=str(self.project_path),
            project_name=self.project_name,
            languages=sorted(languages.keys(), key=lambda k: languages[k], reverse=True),
            frameworks=sorted(set(frameworks)),
            description=f"Project at {self.project_path} with {len(files_info)} files",
            file_count=len(files_info),
            last_scanned=datetime.now(timezone.utc).isoformat(),
            project_id=self.project_id,
            importance_score=3.0,
            tags=["project", "root"] + sorted(set(frameworks))[:10],
        )

        file_nodes = self._build_file_nodes(files_info)
        pattern_nodes = self._build_pattern_nodes(languages, frameworks, structure)
        decision_nodes = self._build_decision_nodes(config_insights, frameworks)
        edges = self._build_edges(project_node, file_nodes, pattern_nodes, decision_nodes)

        summary = {
            "project_name": self.project_name,
            "project_id": self.project_id,
            "path": str(self.project_path),
            "total_files": len(files_info),
            "languages": languages,
            "frameworks": frameworks,
            "file_nodes_created": len(file_nodes),
            "pattern_nodes_created": len(pattern_nodes),
            "decision_nodes_created": len(decision_nodes),
            "edges_created": len(edges),
        }

        logger.info(
            "Scan complete: %d files, %d languages, %d frameworks",
            len(files_info),
            len(languages),
            len(frameworks),
        )

        return {
            "project_node": project_node,
            "file_nodes": file_nodes,
            "pattern_nodes": pattern_nodes,
            "decision_nodes": decision_nodes,
            "edges": edges,
            "summary": summary,
        }

    def _scan_files(self) -> list[dict[str, Any]]:
        """Walk the directory tree collecting file metadata."""
        files: list[dict[str, Any]] = []
        count = 0

        for root, dirs, filenames in os.walk(self.project_path):
            # Filter out skipped directories in-place
            dirs[:] = [d for d in dirs if d not in SKIP_DIRS and not d.startswith(".")]

            rel_root = Path(root).relative_to(self.project_path)

            for fname in filenames:
                if count >= MAX_FILES_TO_SCAN:
                    break
                if fname.startswith(".") and fname not in {
                    ".env.example",
                    ".gitignore",
                    ".dockerignore",
                    ".editorconfig",
                    ".eslintrc.json",
                    ".prettierrc",
                }:
                    continue

                fpath = Path(root) / fname
                try:
                    stat = fpath.stat()
                except OSError:
                    continue

                if stat.st_size > MAX_FILE_SIZE_BYTES:
                    continue

                ext = fpath.suffix.lower()
                language = LANGUAGE_MAP.get(ext, "")

                files.append(
                    {
                        "path": str(rel_root / fname),
                        "abs_path": str(fpath),
                        "extension": ext,
                        "language": language,
                        "size_bytes": stat.st_size,
                        "directory": str(rel_root),
                    }
                )
                count += 1

            if count >= MAX_FILES_TO_SCAN:
                break

        return files

    def _detect_languages(self, files_info: list[dict[str, Any]]) -> dict[str, int]:
        """Count files per detected language."""
        lang_counts: dict[str, int] = {}
        for f in files_info:
            lang = f.get("language")
            if lang:
                lang_counts[lang] = lang_counts.get(lang, 0) + 1
        return lang_counts

    def _detect_frameworks(self) -> list[str]:
        """Detect frameworks/tools based on indicator files."""
        detected: list[str] = []
        for indicator, framework in FRAMEWORK_INDICATORS:
            target = self.project_path / indicator
            if target.exists():
                if framework not in detected:
                    detected.append(framework)

        # Read package.json for JS/TS frameworks
        pkg_json = self.project_path / "package.json"
        if pkg_json.is_file():
            try:
                data = json.loads(pkg_json.read_text(encoding="utf-8", errors="replace"))
                all_deps = {
                    **data.get("dependencies", {}),
                    **data.get("devDependencies", {}),
                }
                dep_framework_map = {
                    "react": "react",
                    "react-dom": "react",
                    "vue": "vuejs",
                    "@angular/core": "angular",
                    "svelte": "svelte",
                    "express": "express",
                    "fastify": "fastify",
                    "nestjs": "nestjs",
                    "@nestjs/core": "nestjs",
                    "prisma": "prisma",
                    "drizzle-orm": "drizzle",
                    "sequelize": "sequelize",
                    "typeorm": "typeorm",
                    "mongoose": "mongoose",
                    "jest": "jest",
                    "vitest": "vitest",
                    "mocha": "mocha",
                    "cypress": "cypress",
                    "playwright": "playwright",
                    "tailwindcss": "tailwindcss",
                    "styled-components": "styled-components",
                    "redux": "redux",
                    "zustand": "zustand",
                    "mobx": "mobx",
                }
                for dep, fw in dep_framework_map.items():
                    if dep in all_deps and fw not in detected:
                        detected.append(fw)
            except (json.JSONDecodeError, OSError):
                pass

        # Read pyproject.toml / requirements.txt for Python
        pyproject = self.project_path / "pyproject.toml"
        if pyproject.is_file():
            try:
                content = pyproject.read_text(encoding="utf-8", errors="replace").lower()
                py_framework_map = {
                    "django": "django",
                    "flask": "flask",
                    "fastapi": "fastapi",
                    "sqlalchemy": "sqlalchemy",
                    "pydantic": "pydantic",
                    "celery": "celery",
                    "pytest": "pytest",
                    "alembic": "alembic",
                }
                for pkg, fw in py_framework_map.items():
                    if pkg in content and fw not in detected:
                        detected.append(fw)
            except OSError:
                pass

        return detected

    def _analyze_structure(self, files_info: list[dict[str, Any]]) -> dict[str, Any]:
        """Analyze project directory structure for architecture patterns."""
        top_dirs: set[str] = set()
        all_dirs: set[str] = set()
        for f in files_info:
            parts = Path(f["directory"]).parts
            if parts and parts[0] != ".":
                top_dirs.add(parts[0])
            for i in range(len(parts)):
                all_dirs.add(str(Path(*parts[: i + 1])))

        return {
            "top_level_dirs": sorted(top_dirs),
            "all_dirs": sorted(all_dirs)[:100],
            "total_dirs": len(all_dirs),
            "total_files": len(files_info),
        }

    def _read_config_files(self) -> list[dict[str, str]]:
        """Read key configuration files for insight extraction."""
        config_files = [
            "README.md",
            "pyproject.toml",
            "package.json",
            "tsconfig.json",
            "Makefile",
            ".editorconfig",
        ]
        insights: list[dict[str, str]] = []

        for cfg in config_files:
            cfg_path = self.project_path / cfg
            if cfg_path.is_file():
                try:
                    content = cfg_path.read_text(encoding="utf-8", errors="replace")
                    # Truncate for storage
                    insights.append(
                        {
                            "file": cfg,
                            "content": content[:4000],
                        }
                    )
                except OSError:
                    pass

        return insights

    def _build_project_summary(
        self,
        languages: dict[str, int],
        frameworks: list[str],
        structure: dict[str, Any],
    ) -> str:
        """Build a human-readable project summary."""
        lines = [
            f"# Project: {self.project_name}",
            f"Path: {self.project_path}",
            f"Total files: {structure['total_files']}",
            f"Total directories: {structure['total_dirs']}",
            "",
            "## Languages",
        ]
        for lang, count in sorted(languages.items(), key=lambda x: x[1], reverse=True)[:15]:
            lines.append(f"  - {lang}: {count} files")

        if frameworks:
            lines.append("")
            lines.append("## Frameworks & Tools")
            for fw in frameworks:
                lines.append(f"  - {fw}")

        if structure["top_level_dirs"]:
            lines.append("")
            lines.append("## Top-Level Structure")
            for d in structure["top_level_dirs"][:20]:
                lines.append(f"  - {d}/")

        return "\n".join(lines)

    def _build_file_nodes(self, files_info: list[dict[str, Any]]) -> list[Node]:
        """Create FILE-type nodes for significant directories (not individual files)."""
        dir_files: dict[str, list[dict[str, Any]]] = {}
        for f in files_info:
            d = f["directory"] or "."
            dir_files.setdefault(d, []).append(f)

        nodes: list[Node] = []
        for directory, dir_file_list in sorted(dir_files.items()):
            langs = set()
            for f in dir_file_list:
                if f["language"]:
                    langs.add(f["language"])

            file_names = [Path(f["path"]).name for f in dir_file_list[:30]]
            content = (
                f"Directory: {directory}\n"
                f"Files ({len(dir_file_list)}): {', '.join(file_names)}\n"
                f"Languages: {', '.join(sorted(langs)) if langs else 'n/a'}"
            )

            node = Node(
                node_type=NodeType.FILE,
                title=f"Dir: {directory}",
                content=content,
                tags=["file", "directory"] + sorted(langs),
                metadata={"directory": directory, "file_count": len(dir_file_list)},
                project_id=self.project_id,
                importance_score=min(2.0, 0.5 + len(dir_file_list) * 0.05),
            )
            nodes.append(node)

        return nodes

    def _build_pattern_nodes(
        self,
        languages: dict[str, int],
        frameworks: list[str],
        structure: dict[str, Any],
    ) -> list[PatternNode]:
        """Create pattern nodes for detected architecture and conventions."""
        patterns: list[PatternNode] = []

        # Detect project structure pattern
        top_dirs = set(structure.get("top_level_dirs", []))
        known_patterns = {
            frozenset({"src", "tests"}): ("src-tests layout", "Standard source/test separation"),
            frozenset({"app", "tests"}): ("app-tests layout", "Application with test directory"),
            frozenset({"lib", "test"}): ("lib-test layout", "Library with test directory"),
            frozenset({"frontend", "backend"}): (
                "monorepo-fullstack",
                "Fullstack monorepo with frontend/backend separation",
            ),
            frozenset({"packages"}): ("monorepo-packages", "Monorepo with packages workspace"),
            frozenset({"services"}): (
                "microservices",
                "Microservices architecture with services directory",
            ),
        }

        for indicator_dirs, (pattern_name, desc) in known_patterns.items():
            if indicator_dirs.issubset(top_dirs):
                patterns.append(
                    PatternNode(
                        title=f"Structure: {pattern_name}",
                        content=desc,
                        pattern_name=pattern_name,
                        pattern_type="project_structure",
                        description=desc,
                        project_id=self.project_id,
                        tags=["pattern", "structure", "project-scanned"],
                        importance_score=1.5,
                    )
                )

        # Language-based conventions
        primary_langs = sorted(languages.items(), key=lambda x: x[1], reverse=True)[:3]
        if primary_langs:
            lang_list = [lang for lang, _ in primary_langs]
            patterns.append(
                PatternNode(
                    title=f"Primary languages: {', '.join(lang_list)}",
                    content=(
                        f"This project primarily uses {', '.join(lang_list)}. "
                        f"Agents should generate code in these languages and follow "
                        f"their respective conventions."
                    ),
                    pattern_name="primary_languages",
                    pattern_type="convention",
                    description=f"Primary languages: {', '.join(lang_list)}",
                    languages=lang_list,
                    frameworks=frameworks[:10],
                    project_id=self.project_id,
                    tags=["pattern", "language", "convention", "project-scanned"],
                    importance_score=2.0,
                )
            )

        # Framework conventions
        for fw in frameworks[:10]:
            patterns.append(
                PatternNode(
                    title=f"Framework: {fw}",
                    content=f"This project uses {fw}. Follow {fw} best practices and conventions.",
                    pattern_name=f"uses_{fw}",
                    pattern_type="framework",
                    description=f"Project uses {fw}",
                    frameworks=[fw],
                    project_id=self.project_id,
                    tags=["pattern", "framework", fw, "project-scanned"],
                    importance_score=1.5,
                )
            )

        return patterns

    def _build_decision_nodes(
        self,
        config_insights: list[dict[str, str]],
        frameworks: list[str],
    ) -> list[DecisionNode]:
        """Create decision nodes from detected configuration choices."""
        decisions: list[DecisionNode] = []

        # Detect testing framework decisions
        test_fws = [
            fw
            for fw in frameworks
            if fw in {"pytest", "jest", "vitest", "mocha", "cypress", "playwright"}
        ]
        if test_fws:
            decisions.append(
                DecisionNode(
                    title=f"Testing: {', '.join(test_fws)}",
                    content=f"Project uses {', '.join(test_fws)} for testing.",
                    decision_title=f"Testing: {', '.join(test_fws)}",
                    decision_description=f"Testing framework(s) detected: {', '.join(test_fws)}",
                    rationale="Detected from project configuration files",
                    project_id=self.project_id,
                    tags=["decision", "testing", "project-scanned"],
                    importance_score=1.5,
                )
            )

        # Detect CI/CD decisions
        ci_fws = [
            fw for fw in frameworks if fw in {"github-actions", "gitlab-ci", "circleci", "jenkins"}
        ]
        if ci_fws:
            decisions.append(
                DecisionNode(
                    title=f"CI/CD: {', '.join(ci_fws)}",
                    content=f"Project uses {', '.join(ci_fws)} for CI/CD.",
                    decision_title=f"CI/CD: {', '.join(ci_fws)}",
                    decision_description=f"CI/CD system(s) detected: {', '.join(ci_fws)}",
                    rationale="Detected from project configuration files",
                    project_id=self.project_id,
                    tags=["decision", "ci-cd", "project-scanned"],
                    importance_score=1.5,
                )
            )

        # Detect containerization
        if "docker" in frameworks or "docker-compose" in frameworks:
            decisions.append(
                DecisionNode(
                    title="Containerization: Docker",
                    content="Project uses Docker for containerization.",
                    decision_title="Containerization: Docker",
                    decision_description="Docker containerization detected",
                    rationale="Detected from Dockerfile / docker-compose",
                    project_id=self.project_id,
                    tags=["decision", "docker", "infrastructure", "project-scanned"],
                    importance_score=1.5,
                )
            )

        return decisions

    def _build_edges(
        self,
        project_node: ProjectNode,
        file_nodes: list[Node],
        pattern_nodes: list[PatternNode],
        decision_nodes: list[DecisionNode],
    ) -> list[Edge]:
        """Create edges linking project → files, patterns, decisions."""
        edges: list[Edge] = []

        for node in file_nodes:
            edges.append(
                Edge(
                    source_id=project_node.id,
                    target_id=node.id,
                    edge_type=EdgeType.CONTAINS,
                    metadata={"relationship": "project_contains_directory"},
                )
            )

        for node in pattern_nodes:
            edges.append(
                Edge(
                    source_id=project_node.id,
                    target_id=node.id,
                    edge_type=EdgeType.RELATED_TO,
                    metadata={"relationship": "project_pattern"},
                )
            )

        for node in decision_nodes:
            edges.append(
                Edge(
                    source_id=project_node.id,
                    target_id=node.id,
                    edge_type=EdgeType.RELATED_TO,
                    metadata={"relationship": "project_decision"},
                )
            )

        return edges
