"""
Export formatters — serialize the project graph to JSON, DOT (Graphviz),

GraphML, and Markdown for documentation or visualization.
"""

from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from typing import Any

from graphify.core.graph import GraphStore
from graphify.core.schema import NodeType

logger = logging.getLogger(__name__)


class GraphExporter:
    """Export a project graph to various formats."""

    def __init__(self, store: GraphStore) -> None:
        self._store = store

    # ------------------------------------------------------------------
    # JSON
    # ------------------------------------------------------------------

    def to_json(self, project_id: str = "", indent: int = 2) -> str:
        """Export full graph as JSON."""
        data = self._collect(project_id)
        return json.dumps(data, indent=indent, default=str)

    # ------------------------------------------------------------------
    # DOT (Graphviz)
    # ------------------------------------------------------------------

    def to_dot(self, project_id: str = "", max_nodes: int = 500) -> str:
        """Export graph as Graphviz DOT format."""
        nodes = self._store.get_nodes(project_id=project_id, limit=max_nodes)
        edges = self._store.get_edges(project_id=project_id)

        node_ids = {n.id for n in nodes}
        lines = ["digraph project {", "  rankdir=LR;", "  node [shape=box, fontsize=10];", ""]

        # Color map by type
        colors = {
            NodeType.PROJECT: "#4CAF50",
            NodeType.DIRECTORY: "#FFC107",
            NodeType.FILE: "#2196F3",
            NodeType.CLASS: "#9C27B0",
            NodeType.FUNCTION: "#FF5722",
            NodeType.TEST: "#00BCD4",
            NodeType.IMPORT: "#607D8B",
            NodeType.DEPENDENCY: "#E91E63",
            NodeType.CONFIG: "#795548",
            NodeType.DOCUMENTATION: "#8BC34A",
        }

        for node in nodes:
            color = colors.get(node.node_type, "#9E9E9E")
            label = node.name.replace('"', '\\"')[:40]
            ntype = node.node_type.value
            lines.append(
                f'  "{node.id}" [label="{label}\\n({ntype})" '
                f'style=filled fillcolor="{color}" fontcolor=white];'
            )

        lines.append("")
        for edge in edges:
            if edge.source_id in node_ids and edge.target_id in node_ids:
                label = edge.edge_type.value
                lines.append(
                    f'  "{edge.source_id}" -> "{edge.target_id}" [label="{label}" fontsize=8];'
                )

        lines.append("}")
        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Markdown
    # ------------------------------------------------------------------

    def to_markdown(self, project_id: str = "") -> str:
        """Export project summary as Markdown."""
        meta = self._store.get_project_meta(project_id)
        stats = self._store.stats(project_id)

        lines = []
        name = meta.name if meta else project_id
        lines.append(f"# Project Graph: {name}")
        lines.append("")

        if meta:
            lines.append(f"**Path:** `{meta.root_path}`  ")
            lines.append(f"**Files:** {meta.total_files}  ")
            lines.append(f"**Lines:** {meta.total_lines:,}  ")
            lines.append(f"**Classes:** {meta.total_classes}  ")
            lines.append(f"**Functions:** {meta.total_functions}  ")
            lines.append(f"**Tests:** {meta.total_tests}  ")
            lines.append("")

        # Node type breakdown
        lines.append("## Graph Statistics")
        lines.append("")
        lines.append("| Metric | Count |")
        lines.append("|--------|-------|")
        lines.append(f"| Total Nodes | {stats['nodes']} |")
        lines.append(f"| Total Edges | {stats['edges']} |")
        for ntype, count in sorted(stats.get("node_types", {}).items()):
            lines.append(f"| {ntype} nodes | {count} |")
        lines.append("")

        # Languages
        if meta and meta.languages:
            lines.append("## Languages")
            lines.append("")
            for lang, count in sorted(meta.languages.items(), key=lambda x: x[1], reverse=True):
                lines.append(f"- **{lang}**: {count} files")
            lines.append("")

        # Dependencies
        if meta and meta.dependencies:
            lines.append("## Dependencies")
            lines.append("")
            for dep in sorted(meta.dependencies):
                lines.append(f"- {dep}")
            lines.append("")

        # Frameworks
        if meta and meta.frameworks:
            lines.append("## Detected Frameworks")
            lines.append("")
            for fw in sorted(meta.frameworks):
                lines.append(f"- {fw}")
            lines.append("")

        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Obsidian Vault
    # ------------------------------------------------------------------

    def to_obsidian(
        self,
        project_id: str = "",
        output_dir: str = "obsidian-vault",
        max_nodes: int = 5000,
    ) -> dict[str, Any]:
        """Export project graph as an Obsidian vault with wikilinks.

        Each graph node becomes a markdown note with YAML frontmatter and
        ``[[wikilinks]]`` to connected nodes.  Open the generated directory
        as an Obsidian vault and use the graph view (Ctrl/Cmd-G) to explore
        every relationship interactively.

        Args:
            project_id: Project to export (empty string exports all).
            output_dir: Root directory for the vault.
            max_nodes: Cap on exported nodes to avoid huge vaults.

        Returns:
            Stats dict: ``output_dir``, ``notes_written``, ``edges_linked``,
            ``folders``.
        """
        type_folders: dict[str, str] = {
            "PROJECT": "Projects",
            "DIRECTORY": "Directories",
            "FILE": "Files",
            "MODULE": "Modules",
            "CLASS": "Classes",
            "FUNCTION": "Functions",
            "IMPORT": "Imports",
            "DEPENDENCY": "Dependencies",
            "CONFIG": "Config",
            "DOCUMENTATION": "Docs",
            "TEST": "Tests",
            "PATTERN": "Patterns",
            "VARIABLE": "Variables",
            "RATIONALE": "Rationale",
            "COMMUNITY": "Communities",
        }

        type_emoji: dict[str, str] = {
            "PROJECT": "🏗️",
            "DIRECTORY": "📁",
            "FILE": "📄",
            "MODULE": "📦",
            "CLASS": "🔷",
            "FUNCTION": "⚡",
            "IMPORT": "📥",
            "DEPENDENCY": "📦",
            "CONFIG": "⚙️",
            "DOCUMENTATION": "📝",
            "TEST": "🧪",
            "PATTERN": "🔁",
            "VARIABLE": "📌",
            "RATIONALE": "💡",
            "COMMUNITY": "🏘️",
        }

        type_colors: dict[str, str] = {
            "PROJECT": "#4CAF50",
            "DIRECTORY": "#FFC107",
            "FILE": "#2196F3",
            "MODULE": "#3F51B5",
            "CLASS": "#9C27B0",
            "FUNCTION": "#FF5722",
            "IMPORT": "#607D8B",
            "DEPENDENCY": "#E91E63",
            "CONFIG": "#795548",
            "DOCUMENTATION": "#8BC34A",
            "TEST": "#00BCD4",
            "PATTERN": "#FF9800",
            "VARIABLE": "#009688",
            "RATIONALE": "#CDDC39",
            "COMMUNITY": "#673AB7",
        }

        # --- load data -----------------------------------------------------

        nodes = self._store.get_nodes(project_id=project_id, limit=max_nodes)
        edges = self._store.get_edges(project_id=project_id)
        meta = self._store.get_project_meta(project_id)

        if not nodes:
            logger.warning("No nodes for project_id=%s — vault will be empty.", project_id)

        node_map: dict[str, Any] = {n.id: n for n in nodes}
        node_ids = set(node_map.keys())

        # --- adjacency -----------------------------------------------------

        outgoing: dict[str, list[tuple[str, str]]] = {}
        incoming: dict[str, list[tuple[str, str]]] = {}
        for edge in edges:
            if edge.source_id in node_ids and edge.target_id in node_ids:
                outgoing.setdefault(edge.source_id, []).append(
                    (edge.edge_type.value, edge.target_id),
                )
                incoming.setdefault(edge.target_id, []).append(
                    (edge.edge_type.value, edge.source_id),
                )

        # --- create vault --------------------------------------------------

        vault = Path(output_dir)
        vault.mkdir(parents=True, exist_ok=True)

        folders_used: set[str] = set()
        for folder_name in type_folders.values():
            (vault / folder_name).mkdir(parents=True, exist_ok=True)
            folders_used.add(folder_name)

        # --- assign unique filenames ---------------------------------------

        created: dict[str, str] = {}
        seen: dict[str, int] = {}
        for node in nodes:
            ntype = node.node_type.value
            folder = type_folders.get(ntype, "Other")
            if folder == "Other":
                (vault / "Other").mkdir(parents=True, exist_ok=True)
                folders_used.add("Other")
            base = self._obsidian_sanitize(node.name or node.id[:16])
            key = f"{folder}/{base}"
            if key in seen:
                seen[key] += 1
                base = f"{base} {seen[key]}"
            else:
                seen[key] = 0
            created[node.id] = f"{folder}/{base}"

        # --- write notes ---------------------------------------------------

        notes_written = 0
        for node in nodes:
            lines = self._build_graphify_obsidian_note(
                node,
                created,
                node_map,
                outgoing,
                incoming,
                type_emoji,
            )
            note_path = vault / f"{created[node.id]}.md"
            note_path.write_text("\n".join(lines), encoding="utf-8")
            notes_written += 1

        # --- index (MOC) ---------------------------------------------------

        self._write_obsidian_index(
            vault,
            nodes,
            created,
            meta,
            project_id,
            type_folders,
            type_emoji,
        )

        # --- .obsidian config ----------------------------------------------

        self._write_obsidian_vault_config(vault, type_colors)

        logger.info("Exported Obsidian vault: %d notes → %s", notes_written, output_dir)
        return {
            "output_dir": str(vault),
            "notes_written": notes_written,
            "edges_linked": sum(len(v) for v in outgoing.values()),
            "folders": sorted(folders_used),
        }

    def _build_graphify_obsidian_note(
        self,
        node: Any,
        created: dict[str, str],
        node_map: dict[str, Any],
        outgoing: dict[str, list[tuple[str, str]]],
        incoming: dict[str, list[tuple[str, str]]],
        type_emoji: dict[str, str],
    ) -> list[str]:
        """Build markdown lines for a single Graphify node note."""
        from datetime import datetime, timezone  # noqa: F811 — lazy import

        ntype = node.node_type.value
        emoji = type_emoji.get(ntype, "📎")

        fm: dict[str, Any] = {"type": ntype.lower()}
        tags = [ntype.lower()]
        if node.language:
            fm["language"] = node.language
            tags.append(node.language)
        if node.file_path:
            fm["file"] = node.file_path
        if node.line_start:
            fm["line_start"] = node.line_start
        if node.line_end:
            fm["line_end"] = node.line_end
        if node.qualified_name and node.qualified_name != node.name:
            fm["qualified_name"] = node.qualified_name
            fm["aliases"] = [node.qualified_name]
        if node.created_at:
            try:
                dt = datetime.fromtimestamp(node.created_at, tz=timezone.utc)
                fm["created"] = dt.strftime("%Y-%m-%dT%H:%M:%SZ")
            except (OSError, ValueError, OverflowError):
                pass
        if node.metadata:
            for mk, mv in node.metadata.items():
                if isinstance(mv, (str, int, float, bool)):
                    fm[mk] = mv
        fm["tags"] = tags

        lines: list[str] = ["---"]
        for fk, fv in fm.items():
            lines.append(f"{fk}: {self._obsidian_yaml_val(fv)}")
        lines.append("---")
        lines.append("")
        lines.append(f"# {emoji} {node.name}")
        lines.append("")

        if node.content:
            lines.append(node.content[:3000])
            lines.append("")
        if node.file_path:
            loc = f"> 📄 `{node.file_path}`"
            if node.line_start:
                loc += f" · lines {node.line_start}–{node.line_end}"
            lines.append(loc)
            lines.append("")

        self._render_obsidian_relationships(
            lines,
            node.id,
            created,
            node_map,
            outgoing,
            incoming,
            display_fn=lambda n: n.name or n.id[:12],
        )
        return lines

    @staticmethod
    def _render_obsidian_relationships(
        lines: list[str],
        node_id: str,
        created: dict[str, str],
        node_map: dict[str, Any],
        outgoing: dict[str, list[tuple[str, str]]],
        incoming: dict[str, list[tuple[str, str]]],
        display_fn: Any = None,
    ) -> None:
        """Append relationship wikilinks to note lines."""
        out_edges = outgoing.get(node_id, [])
        in_edges = incoming.get(node_id, [])

        if not out_edges and not in_edges:
            return

        lines.append("## Relationships")
        lines.append("")

        for direction, edge_list in [("→", out_edges), ("←", in_edges)]:
            if not edge_list:
                continue
            grouped: dict[str, list[str]] = {}
            for etype, other_id in edge_list:
                grouped.setdefault(etype, []).append(other_id)
            for etype, other_ids in sorted(grouped.items()):
                label = etype.replace("_", " ").title()
                lines.append(f"### {direction} {label}")
                lines.append("")
                for oid in other_ids:
                    if oid in created:
                        other = node_map[oid]
                        dname = display_fn(other) if display_fn else oid[:12]
                        lines.append(f"- [[{created[oid]}|{dname}]]")
                lines.append("")

    @staticmethod
    def _obsidian_sanitize(name: str) -> str:
        """Sanitize a string for use as an Obsidian filename."""
        s = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "-", name)
        s = s.strip(". ")
        return s[:200] if s else "_unnamed"

    @staticmethod
    def _obsidian_yaml_esc(t: str) -> str:
        """Escape a string for YAML double-quoted values."""
        return t.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n").replace("\r", "")

    @staticmethod
    def _obsidian_yaml_val(v: Any) -> str:
        """Format a value for YAML frontmatter."""
        if isinstance(v, bool):
            return "true" if v else "false"
        if isinstance(v, (int, float)):
            return str(v)
        if isinstance(v, list):
            if not v:
                return "[]"
            items = ", ".join(
                f'"{GraphExporter._obsidian_yaml_esc(str(i))}"' if isinstance(i, str) else str(i)
                for i in v
            )
            return f"[{items}]"
        return f'"{GraphExporter._obsidian_yaml_esc(str(v))}"'

    def _write_obsidian_index(
        self,
        vault: Path,
        nodes: list,
        created: dict[str, str],
        meta: Any,
        project_id: str,
        type_folders: dict[str, str],
        type_emoji: dict[str, str],
    ) -> None:
        """Write ``_Index.md`` — the Map-of-Content root note."""
        project_name = meta.name if meta else (project_id or "Project")
        stats = self._store.stats(project_id)

        lines = [
            "---",
            'type: "index"',
            "tags: [index, moc, auto-generated]",
            "---",
            "",
            f"# 🗺️ {project_name}",
            "",
            "> Auto-generated Obsidian vault from **Graphify** code analysis.  ",
            "> Open the graph view (**Ctrl/Cmd + G**) to explore visually.",
            "",
        ]

        # stats table
        lines.append("## 📊 Overview")
        lines.append("")
        lines.append("| Metric | Count |")
        lines.append("|--------|------:|")
        lines.append(f"| Nodes | {stats.get('nodes', 0)} |")
        lines.append(f"| Edges | {stats.get('edges', 0)} |")
        for ntype, count in sorted(stats.get("node_types", {}).items()):
            emoji = type_emoji.get(ntype, "📎")
            lines.append(f"| {emoji} {ntype} | {count} |")
        lines.append("")

        if meta:
            if meta.languages:
                lines.append("## 🌐 Languages")
                lines.append("")
                for lang, count in sorted(
                    meta.languages.items(),
                    key=lambda x: x[1],
                    reverse=True,
                ):
                    lines.append(f"- **{lang}** — {count} files")
                lines.append("")
            if meta.frameworks:
                lines.append("## 🔧 Frameworks")
                lines.append("")
                for fw in sorted(meta.frameworks):
                    lines.append(f"- {fw}")
                lines.append("")

        # categories
        nodes_by_type: dict[str, list] = {}
        for n in nodes:
            nodes_by_type.setdefault(n.node_type.value, []).append(n)

        lines.append("## 📑 Categories")
        lines.append("")
        for ntype_val, folder in sorted(type_folders.items()):
            type_nodes = nodes_by_type.get(ntype_val, [])
            if not type_nodes:
                continue
            emoji = type_emoji.get(ntype_val, "📎")
            lines.append(f"### {emoji} {folder} ({len(type_nodes)})")
            lines.append("")
            for n in sorted(type_nodes, key=lambda x: x.name)[:100]:
                if n.id in created:
                    lines.append(f"- [[{created[n.id]}|{n.name}]]")
            if len(type_nodes) > 100:
                lines.append(f"- *… and {len(type_nodes) - 100} more*")
            lines.append("")

        (vault / "_Index.md").write_text("\n".join(lines), encoding="utf-8")

    @staticmethod
    def _write_obsidian_vault_config(
        vault: Path,
        type_colors: dict[str, str],
    ) -> None:
        """Write ``.obsidian/`` configuration for graph-view colours."""
        obs = vault / ".obsidian"
        obs.mkdir(parents=True, exist_ok=True)

        color_groups = []
        for ntype_val, hex_color in type_colors.items():
            rgb_int = int(hex_color.lstrip("#"), 16)
            color_groups.append(
                {
                    "query": f"tag:#{ntype_val.lower()}",
                    "color": {"a": 1, "rgb": rgb_int},
                }
            )

        graph_cfg = {
            "collapse-filter": False,
            "search": "",
            "showTags": True,
            "showAttachments": False,
            "hideUnresolved": False,
            "showOrphans": True,
            "collapse-color-groups": False,
            "colorGroups": color_groups,
            "collapse-display": False,
            "lineSizeMultiplier": 1,
            "nodeSizeMultiplier": 1.1,
            "collapse-forces": False,
            "centerStrength": 0.5,
            "repelStrength": 10,
            "linkStrength": 1,
            "linkDistance": 250,
            "scale": 1,
            "close": False,
        }
        (obs / "graph.json").write_text(
            json.dumps(graph_cfg, indent=2),
            encoding="utf-8",
        )

        appearance = {
            "baseFontSize": 16,
            "theme": "obsidian",
            "cssTheme": "",
            "interfaceFontFamily": "",
            "textFontFamily": "",
            "monospaceFontFamily": "",
        }
        (obs / "appearance.json").write_text(
            json.dumps(appearance, indent=2),
            encoding="utf-8",
        )

        core_plugins = [
            "file-explorer",
            "global-search",
            "switcher",
            "graph",
            "backlink",
            "outgoing-link",
            "tag-pane",
            "page-preview",
            "command-palette",
            "editor-status",
            "starred",
        ]
        (obs / "core-plugins.json").write_text(
            json.dumps(core_plugins, indent=2),
            encoding="utf-8",
        )

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _collect(self, project_id: str) -> dict[str, Any]:
        """Collect full graph data for serialization."""
        nodes = self._store.get_nodes(project_id=project_id, limit=10_000)
        edges = self._store.get_edges(project_id=project_id)
        meta = self._store.get_project_meta(project_id)

        return {
            "project": {
                "id": project_id,
                "name": meta.name if meta else "",
                "root_path": meta.root_path if meta else "",
            },
            "nodes": [
                {
                    "id": n.id,
                    "type": n.node_type.value,
                    "name": n.name,
                    "qualified_name": n.qualified_name,
                    "file_path": n.file_path,
                    "language": n.language,
                    "line_start": n.line_start,
                    "line_end": n.line_end,
                    "metadata": n.metadata,
                }
                for n in nodes
            ],
            "edges": [
                {
                    "source": e.source_id,
                    "target": e.target_id,
                    "type": e.edge_type.value,
                    "weight": e.weight,
                    "confidence": e.confidence,
                    "provenance": e.provenance,
                }
                for e in edges
            ],
            "stats": self._store.stats(project_id),
        }

    # ------------------------------------------------------------------
    # GraphML (Gephi / yEd compatible)
    # ------------------------------------------------------------------

    def to_graphml(self, project_id: str = "", max_nodes: int = 2000) -> str:
        """Export graph as GraphML XML for Gephi and yEd."""
        import xml.etree.ElementTree as ET  # pylint: disable=C0415

        nodes = self._store.get_nodes(project_id=project_id, limit=max_nodes)
        edges = self._store.get_edges(project_id=project_id)
        node_ids = {n.id for n in nodes}

        ns = "http://graphml.graphstruct.org/graphml"
        root = ET.Element("graphml", xmlns=ns)

        for attr, atype, afor in [
            ("node_type", "string", "node"),
            ("name", "string", "node"),
            ("file_path", "string", "node"),
            ("language", "string", "node"),
            ("edge_type", "string", "edge"),
            ("confidence", "double", "edge"),
            ("provenance", "string", "edge"),
        ]:
            key = ET.SubElement(root, "key")
            key.set("id", attr)
            key.set("for", afor)
            key.set("attr.name", attr)
            key.set("attr.type", atype)

        graph = ET.SubElement(root, "graph", id="G", edgedefault="directed")

        for node in nodes:
            n_el = ET.SubElement(graph, "node", id=node.id)
            for key_id, value in [
                ("node_type", node.node_type.value),
                ("name", node.name),
                ("file_path", node.file_path),
                ("language", node.language),
            ]:
                d = ET.SubElement(n_el, "data", key=key_id)
                d.text = value

        for i, edge in enumerate(edges):
            if edge.source_id in node_ids and edge.target_id in node_ids:
                e_el = ET.SubElement(
                    graph,
                    "edge",
                    id=f"e{i}",
                    source=edge.source_id,
                    target=edge.target_id,
                )
                for key_id, value in [
                    ("edge_type", edge.edge_type.value),
                    ("confidence", str(edge.confidence)),
                    ("provenance", edge.provenance),
                ]:
                    d = ET.SubElement(e_el, "data", key=key_id)
                    d.text = value

        return ET.tostring(root, encoding="unicode", xml_declaration=True)
