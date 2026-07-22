"""
Config file analyzer — extracts structure from YAML, JSON, TOML,

Dockerfiles, and .env files.
"""

from __future__ import annotations

import hashlib
import json
import logging
import re
from typing import Any

from graphify.analyzers.base import AnalysisResult, BaseAnalyzer
from graphify.core.schema import Edge, EdgeType, Node, NodeType

logger = logging.getLogger(__name__)

_DOCKERFILE_CMD_RE = re.compile(
    r"^(FROM|RUN|COPY|ADD|CMD|ENTRYPOINT|EXPOSE|ENV|WORKDIR|ARG)\s+(.+)", re.MULTILINE
)
_ENV_VAR_RE = re.compile(r"^([A-Z_][A-Z0-9_]+)\s*=\s*(.*)$", re.MULTILINE)


class ConfigAnalyzer(BaseAnalyzer):
    """Analyzer for configuration files."""

    def analyze(
        self,
        source: str,
        file_path: str,
        file_node_id: str,
        project_id: str,
    ) -> AnalysisResult:
        """Analyze a config file and extract structure."""
        basename = file_path.rsplit("/", maxsplit=1)[-1] if "/" in file_path else file_path
        lower = basename.lower()

        if lower.endswith((".yaml", ".yml")):
            return self._analyze_yaml(source, file_path, file_node_id, project_id)
        if lower.endswith(".json"):
            return self._analyze_json(source, file_path, file_node_id, project_id, basename)
        if lower.endswith(".toml"):
            return self._analyze_toml(source, file_path, file_node_id, project_id)
        if lower.startswith("dockerfile") or lower == "containerfile":
            return self._analyze_dockerfile(source, file_path, file_node_id, project_id)
        if lower.startswith(".env"):
            return self._analyze_env(source, file_path, file_node_id, project_id)

        return AnalysisResult()

    # ------------------------------------------------------------------
    # YAML
    # ------------------------------------------------------------------

    def _analyze_yaml(
        self,
        source: str,
        file_path: str,
        file_node_id: str,
        project_id: str,
    ) -> AnalysisResult:
        nodes: list[Node] = []
        edges: list[Edge] = []

        try:
            import yaml  # pylint: disable=C0415

            data = yaml.safe_load(source)
        except (ImportError, yaml.YAMLError, ValueError):
            return AnalysisResult()

        if isinstance(data, dict):
            self._walk_dict(data, file_path, file_node_id, project_id, nodes, edges, depth=0)

        return AnalysisResult(nodes=nodes, edges=edges)

    # ------------------------------------------------------------------
    # JSON
    # ------------------------------------------------------------------

    def _analyze_json(
        self,
        source: str,
        file_path: str,
        file_node_id: str,
        project_id: str,
        basename: str,
    ) -> AnalysisResult:
        nodes: list[Node] = []
        edges: list[Edge] = []

        try:
            data = json.loads(source)
        except json.JSONDecodeError:
            return AnalysisResult()

        # Special handling for package.json
        if basename == "package.json" and isinstance(data, dict):
            return self._analyze_package_json(data, file_path, file_node_id, project_id)

        if isinstance(data, dict):
            self._walk_dict(data, file_path, file_node_id, project_id, nodes, edges, depth=0)

        return AnalysisResult(nodes=nodes, edges=edges)

    def _analyze_package_json(
        self,
        data: dict,
        file_path: str,
        file_node_id: str,
        project_id: str,
    ) -> AnalysisResult:
        nodes: list[Node] = []
        edges: list[Edge] = []

        for section in ("dependencies", "devDependencies", "peerDependencies"):
            deps = data.get(section, {})
            if not isinstance(deps, dict):
                continue
            for dep_name, version in deps.items():
                dep_id = _make_id(project_id, "dep", dep_name)
                nodes.append(
                    Node(
                        id=dep_id,
                        node_type=NodeType.DEPENDENCY,
                        name=dep_name,
                        qualified_name=dep_name,
                        file_path=file_path,
                        language="json",
                        content=f"{dep_name}@{version}",
                        metadata={"version": str(version), "section": section},
                        project_id=project_id,
                    )
                )
                edges.append(
                    Edge(
                        source_id=file_node_id,
                        target_id=dep_id,
                        edge_type=EdgeType.DEPENDS_ON,
                        project_id=project_id,
                    )
                )

        # Scripts
        scripts = data.get("scripts", {})
        if isinstance(scripts, dict):
            for script_name, command in scripts.items():
                cfg_id = _make_id(project_id, "cfg", f"script:{script_name}")
                nodes.append(
                    Node(
                        id=cfg_id,
                        node_type=NodeType.CONFIG,
                        name=f"script:{script_name}",
                        file_path=file_path,
                        language="json",
                        content=str(command)[:500],
                        project_id=project_id,
                    )
                )
                edges.append(
                    Edge(
                        source_id=file_node_id,
                        target_id=cfg_id,
                        edge_type=EdgeType.CONFIGURED_BY,
                        project_id=project_id,
                    )
                )

        return AnalysisResult(nodes=nodes, edges=edges)

    # ------------------------------------------------------------------
    # TOML
    # ------------------------------------------------------------------

    def _analyze_toml(
        self,
        source: str,
        file_path: str,
        file_node_id: str,
        project_id: str,
    ) -> AnalysisResult:
        nodes: list[Node] = []
        edges: list[Edge] = []

        try:
            import tomllib  # pylint: disable=C0415

            data = tomllib.loads(source)
        except ImportError:
            try:
                import tomli as tomllib  # pylint: disable=C0415

                data = tomllib.loads(source)
            except ImportError:
                return AnalysisResult()
        except (ValueError, KeyError):
            return AnalysisResult()

        # Extract dependencies from pyproject.toml
        if isinstance(data, dict):
            deps = data.get("project", {}).get("dependencies", [])
            if isinstance(deps, list):
                for dep in deps:
                    dep_name = re.split(r"[>=<!\[;]", str(dep), maxsplit=1)[0].strip()
                    if dep_name:
                        dep_id = _make_id(project_id, "dep", dep_name)
                        nodes.append(
                            Node(
                                id=dep_id,
                                node_type=NodeType.DEPENDENCY,
                                name=dep_name,
                                qualified_name=dep_name,
                                file_path=file_path,
                                language="toml",
                                content=str(dep),
                                project_id=project_id,
                            )
                        )
                        edges.append(
                            Edge(
                                source_id=file_node_id,
                                target_id=dep_id,
                                edge_type=EdgeType.DEPENDS_ON,
                                project_id=project_id,
                            )
                        )
            self._walk_dict(data, file_path, file_node_id, project_id, nodes, edges, depth=0)

        return AnalysisResult(nodes=nodes, edges=edges)

    # ------------------------------------------------------------------
    # Dockerfile
    # ------------------------------------------------------------------

    def _analyze_dockerfile(
        self,
        source: str,
        file_path: str,
        file_node_id: str,
        project_id: str,
    ) -> AnalysisResult:
        nodes: list[Node] = []
        edges: list[Edge] = []

        for match in _DOCKERFILE_CMD_RE.finditer(source):
            cmd = match.group(1)
            args = match.group(2).strip()
            line = source[: match.start()].count("\n") + 1
            cfg_id = _make_id(project_id, "docker", f"{file_path}:{line}:{cmd}")
            nodes.append(
                Node(
                    id=cfg_id,
                    node_type=NodeType.CONFIG,
                    name=f"{cmd} {args[:60]}",
                    file_path=file_path,
                    language="dockerfile",
                    line_start=line,
                    content=f"{cmd} {args}"[:500],
                    metadata={"instruction": cmd},
                    project_id=project_id,
                )
            )
            edges.append(
                Edge(
                    source_id=file_node_id,
                    target_id=cfg_id,
                    edge_type=EdgeType.CONFIGURED_BY,
                    project_id=project_id,
                )
            )

        return AnalysisResult(nodes=nodes, edges=edges)

    # ------------------------------------------------------------------
    # .env files
    # ------------------------------------------------------------------

    def _analyze_env(
        self,
        source: str,
        file_path: str,
        file_node_id: str,
        project_id: str,
    ) -> AnalysisResult:
        nodes: list[Node] = []
        edges: list[Edge] = []

        for match in _ENV_VAR_RE.finditer(source):
            var_name = match.group(1)
            cfg_id = _make_id(project_id, "env", f"{file_path}:{var_name}")
            nodes.append(
                Node(
                    id=cfg_id,
                    node_type=NodeType.VARIABLE,
                    name=var_name,
                    file_path=file_path,
                    language="shell",
                    content=f"{var_name}=***",  # redact values
                    project_id=project_id,
                )
            )
            edges.append(
                Edge(
                    source_id=file_node_id,
                    target_id=cfg_id,
                    edge_type=EdgeType.CONFIGURED_BY,
                    project_id=project_id,
                )
            )

        return AnalysisResult(nodes=nodes, edges=edges)

    # ------------------------------------------------------------------
    # Shared dict walker
    # ------------------------------------------------------------------

    def _walk_dict(
        self,
        data: dict[str, Any],
        file_path: str,
        parent_id: str,
        project_id: str,
        nodes: list[Node],
        edges: list[Edge],
        depth: int,
        prefix: str = "",
    ) -> None:
        """Walk a nested dict creating CONFIG nodes for top-level keys."""
        if depth > 2:
            return
        for key, value in data.items():
            qualified = f"{prefix}.{key}" if prefix else key
            cfg_id = _make_id(project_id, "cfg", f"{file_path}:{qualified}")
            content = str(value)[:500] if not isinstance(value, dict) else f"({len(value)} keys)"

            nodes.append(
                Node(
                    id=cfg_id,
                    node_type=NodeType.CONFIG,
                    name=key,
                    qualified_name=qualified,
                    file_path=file_path,
                    content=content,
                    project_id=project_id,
                )
            )
            edges.append(
                Edge(
                    source_id=parent_id,
                    target_id=cfg_id,
                    edge_type=EdgeType.CONFIGURED_BY,
                    project_id=project_id,
                )
            )

            if isinstance(value, dict):
                self._walk_dict(
                    value, file_path, cfg_id, project_id, nodes, edges, depth + 1, qualified
                )


def _make_id(project_id: str, prefix: str, name: str) -> str:
    raw = f"{project_id}:{prefix}:{name}"
    return hashlib.sha256(raw.encode()).hexdigest()[:16]
