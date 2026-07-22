"""
Context Export/Import — Backup and migration for Agentic Team Context.

Independent implementation — does NOT import from orchestrator/context.
Supports JSON export/import for backup, migration, and analysis.
"""

from __future__ import annotations

import json
import logging
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from agentic_team.context.models.schemas import Edge, Node
from agentic_team.context.store.graph_store import GraphStore


class ContextExporter:
    """Export and import agentic team context graph data."""

    EXPORT_VERSION = "1.0"

    def __init__(self, graph_store: GraphStore):
        """Initialize exporter.

        Args:
            graph_store: Graph store instance.
        """
        self.logger = logging.getLogger("agentic_team.context.export")
        self.graph_store = graph_store

    # ------------------------------------------------------------------
    # Export
    # ------------------------------------------------------------------

    def export_json(
        self,
        output_path: str,
        node_types: list[str] | None = None,
    ) -> dict[str, Any]:
        """Export nodes and edges to a JSON file.

        Args:
            output_path: Destination file path.
            node_types: Optional filter — export only these node types.

        Returns:
            Statistics dict.
        """
        nodes_data: list[dict[str, Any]] = []
        edges_data: list[dict[str, Any]] = []

        with self.graph_store._transaction() as cursor:
            if node_types:
                placeholders = ",".join("?" * len(node_types))
                cursor.execute(
                    f"SELECT * FROM nodes WHERE node_type IN ({placeholders})",  # noqa: S608
                    node_types,
                )
            else:
                cursor.execute("SELECT * FROM nodes")

            for row in cursor.fetchall():
                node = self.graph_store._row_to_node(row)
                nodes_data.append(node.to_dict())

            exported_ids = {n["id"] for n in nodes_data}

            cursor.execute("SELECT * FROM edges")
            for row in cursor.fetchall():
                edge = self.graph_store._row_to_edge(row)
                if edge.source_id in exported_ids and edge.target_id in exported_ids:
                    edges_data.append(edge.to_dict())

        payload = {
            "version": self.EXPORT_VERSION,
            "system": "agentic_team",
            "exported_at": datetime.now(timezone.utc).isoformat(),
            "stats": {"nodes": len(nodes_data), "edges": len(edges_data)},
            "nodes": nodes_data,
            "edges": edges_data,
        }

        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, indent=2, default=str)

        self.logger.info(
            "Exported %d nodes and %d edges to %s",
            len(nodes_data),
            len(edges_data),
            output_path,
        )

        return {
            "output_path": output_path,
            "nodes_exported": len(nodes_data),
            "edges_exported": len(edges_data),
            "node_types_filter": node_types,
        }

    # ------------------------------------------------------------------
    # Import
    # ------------------------------------------------------------------

    def import_json(
        self,
        input_path: str,
        merge: bool = True,
    ) -> dict[str, Any]:
        """Import nodes and edges from a JSON file.

        Args:
            input_path: Source file path.
            merge: If True, skip existing node IDs; if False, overwrite.

        Returns:
            Statistics dict.
        """
        with open(input_path, encoding="utf-8") as fh:
            data = json.load(fh)

        nodes_imported = 0
        nodes_skipped = 0
        edges_imported = 0
        edges_skipped = 0

        for node_data in data.get("nodes", []):
            node = Node.from_dict(node_data)
            if merge and self.graph_store.get_node(node.id):
                nodes_skipped += 1
                continue
            self.graph_store.add_node(node)
            nodes_imported += 1

        for edge_data in data.get("edges", []):
            edge = Edge.from_dict(edge_data)
            if merge and self.graph_store.get_edge(edge.id):
                edges_skipped += 1
                continue
            try:
                self.graph_store.add_edge(edge)
                edges_imported += 1
            except Exception as exc:
                self.logger.warning("Failed to import edge %s: %s", edge.id, exc)
                edges_skipped += 1

        self.logger.info(
            "Imported %d nodes and %d edges from %s",
            nodes_imported,
            edges_imported,
            input_path,
        )

        return {
            "input_path": input_path,
            "merge_mode": merge,
            "nodes_imported": nodes_imported,
            "nodes_skipped": nodes_skipped,
            "edges_imported": edges_imported,
            "edges_skipped": edges_skipped,
        }

    # ------------------------------------------------------------------
    # Obsidian Vault
    # ------------------------------------------------------------------

    def export_obsidian(
        self,
        output_path: str,
        node_types: list[str] | None = None,
    ) -> dict[str, Any]:
        """Export context graph as an Obsidian vault with wikilinks.

        Each context node becomes a markdown note with YAML frontmatter
        and ``[[wikilinks]]`` to related nodes.  Open the directory in
        Obsidian and use the graph view (Ctrl/Cmd-G) to explore
        conversations, tasks, decisions, patterns, and mistakes visually.

        Args:
            output_path: Root directory for the Obsidian vault.
            node_types: Optional filter — export only these node types.

        Returns:
            Stats dict: output_path, notes_written, edges_linked, folders.
        """
        type_folders: dict[str, str] = {
            "conversation": "Conversations",
            "task": "Tasks",
            "mistake": "Mistakes",
            "pattern": "Patterns",
            "decision": "Decisions",
            "code_snippet": "Code Snippets",
            "preference": "Preferences",
            "file": "Files",
            "concept": "Concepts",
            "agent_output": "Agent Outputs",
            "project": "Projects",
        }

        type_emoji: dict[str, str] = {
            "conversation": "💬",
            "task": "✅",
            "mistake": "❌",
            "pattern": "🔁",
            "decision": "⚖️",
            "code_snippet": "💻",
            "preference": "⚙️",
            "file": "📄",
            "concept": "💡",
            "agent_output": "🤖",
            "project": "🏗️",
        }

        type_colors: dict[str, str] = {
            "conversation": "#4FC3F7",
            "task": "#4CAF50",
            "mistake": "#F44336",
            "pattern": "#FF9800",
            "decision": "#9C27B0",
            "code_snippet": "#607D8B",
            "preference": "#009688",
            "file": "#2196F3",
            "concept": "#CDDC39",
            "agent_output": "#FF5722",
            "project": "#FFC107",
        }

        # --- load data -----------------------------------------------------

        nodes_data: list[Node] = []
        edges_data: list[Edge] = []

        with self.graph_store._transaction() as cursor:
            if node_types:
                placeholders = ",".join("?" * len(node_types))
                cursor.execute(
                    f"SELECT * FROM nodes WHERE node_type IN ({placeholders})",  # noqa: S608
                    node_types,
                )
            else:
                cursor.execute("SELECT * FROM nodes")

            for row in cursor.fetchall():
                nodes_data.append(self.graph_store._row_to_node(row))

            node_ids = {n.id for n in nodes_data}

            cursor.execute("SELECT * FROM edges")
            for row in cursor.fetchall():
                edge = self.graph_store._row_to_edge(row)
                if edge.source_id in node_ids and edge.target_id in node_ids:
                    edges_data.append(edge)

        node_map: dict[str, Node] = {n.id: n for n in nodes_data}

        # --- adjacency -----------------------------------------------------

        outgoing: dict[str, list[tuple[str, str]]] = {}
        incoming: dict[str, list[tuple[str, str]]] = {}
        for edge in edges_data:
            outgoing.setdefault(edge.source_id, []).append(
                (edge.edge_type.value, edge.target_id),
            )
            incoming.setdefault(edge.target_id, []).append(
                (edge.edge_type.value, edge.source_id),
            )

        # --- create vault --------------------------------------------------

        vault = Path(output_path)
        vault.mkdir(parents=True, exist_ok=True)

        folders_used: set[str] = set()
        for folder_name in type_folders.values():
            (vault / folder_name).mkdir(parents=True, exist_ok=True)
            folders_used.add(folder_name)

        # --- assign unique filenames ---------------------------------------

        created: dict[str, str] = self._assign_obsidian_filenames(
            nodes_data,
            type_folders,
            vault,
            folders_used,
        )

        # --- write notes ---------------------------------------------------

        notes_written = 0
        for node in nodes_data:
            lines = self._build_context_obsidian_note(
                node,
                created,
                node_map,
                outgoing,
                incoming,
                type_emoji,
            )
            fpath = vault / f"{created[node.id]}.md"
            fpath.write_text("\n".join(lines), encoding="utf-8")
            notes_written += 1

        # --- index ---------------------------------------------------------

        self._write_obsidian_index(
            vault,
            nodes_data,
            edges_data,
            created,
            "Agentic Team",
            type_folders,
            type_emoji,
        )

        # --- .obsidian config ----------------------------------------------

        self._write_obsidian_vault_config(vault, type_colors)

        self.logger.info(
            "Exported Obsidian vault: %d notes → %s",
            notes_written,
            output_path,
        )
        return {
            "output_path": output_path,
            "notes_written": notes_written,
            "edges_linked": sum(len(v) for v in outgoing.values()),
            "folders": sorted(folders_used),
        }

    def _assign_obsidian_filenames(
        self,
        nodes: list[Node],
        type_folders: dict[str, str],
        vault: Path,
        folders_used: set[str],
    ) -> dict[str, str]:
        """Assign deduplicated vault-relative paths to each node."""
        created: dict[str, str] = {}
        seen: dict[str, int] = {}
        for node in nodes:
            ntype = node.node_type.value
            folder = type_folders.get(ntype, "Other")
            if folder == "Other":
                (vault / "Other").mkdir(parents=True, exist_ok=True)
                folders_used.add("Other")
            display = node.title or node.content[:80] or node.id[:16]
            base = self._obsidian_sanitize(display)
            key = f"{folder}/{base}"
            if key in seen:
                seen[key] += 1
                base = f"{base} {seen[key]}"
            else:
                seen[key] = 0
            created[node.id] = f"{folder}/{base}"
        return created

    def _build_context_obsidian_note(
        self,
        node: Node,
        created: dict[str, str],
        node_map: dict[str, Node],
        outgoing: dict[str, list[tuple[str, str]]],
        incoming: dict[str, list[tuple[str, str]]],
        type_emoji: dict[str, str],
    ) -> list[str]:
        """Build markdown lines for a single context node note."""
        ntype = node.node_type.value
        emoji = type_emoji.get(ntype, "📎")
        display = node.title or node.content[:80] or node.id[:16]

        fm: dict[str, Any] = {"type": ntype}
        tags = [ntype]
        if node.tags:
            tags.extend(t for t in node.tags if t not in tags)
        fm["tags"] = tags
        fm["importance"] = node.importance_score
        if hasattr(node.created_at, "strftime"):
            fm["created"] = node.created_at.strftime("%Y-%m-%dT%H:%M:%SZ")
        if hasattr(node.updated_at, "strftime"):
            fm["updated"] = node.updated_at.strftime("%Y-%m-%dT%H:%M:%SZ")
        if node.project_id:
            fm["project_id"] = node.project_id
        if node.title and node.title != display:
            fm["aliases"] = [node.title]
        if node.metadata:
            for mk, mv in node.metadata.items():
                if isinstance(mv, (str, int, float, bool)):
                    fm[mk] = mv

        lines: list[str] = ["---"]
        for fk, fv in fm.items():
            lines.append(f"{fk}: {self._obsidian_yaml_val(fv)}")
        lines.append("---")
        lines.append("")
        lines.append(f"# {emoji} {display}")
        lines.append("")

        if node.content:
            lines.append(node.content[:5000])
            lines.append("")

        self._render_obsidian_relationships(
            lines,
            node.id,
            created,
            node_map,
            outgoing,
            incoming,
            display_fn=lambda n: n.title or n.content[:60] or n.id[:12],
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
            esc = ContextExporter._obsidian_yaml_esc
            items = ", ".join(f'"{esc(str(i))}"' if isinstance(i, str) else str(i) for i in v)
            return f"[{items}]"
        return f'"{ContextExporter._obsidian_yaml_esc(str(v))}"'

    def _write_obsidian_index(
        self,
        vault: Path,
        nodes: list[Node],
        edges: list[Edge],
        created: dict[str, str],
        system_name: str,
        type_folders: dict[str, str],
        type_emoji: dict[str, str],
    ) -> None:
        """Write ``_Index.md`` — the Map-of-Content root note."""
        lines = [
            "---",
            'type: "index"',
            "tags: [index, moc, auto-generated]",
            "---",
            "",
            f"# 🗺️ {system_name} — Context Graph",
            "",
            "> Auto-generated Obsidian vault from **Agentic Team** context memory.  ",
            "> Open the graph view (**Ctrl/Cmd + G**) to explore visually.",
            "",
        ]

        # stats
        nodes_by_type: dict[str, list[Node]] = {}
        for n in nodes:
            nodes_by_type.setdefault(n.node_type.value, []).append(n)

        lines.append("## 📊 Overview")
        lines.append("")
        lines.append("| Metric | Count |")
        lines.append("|--------|------:|")
        lines.append(f"| Nodes | {len(nodes)} |")
        lines.append(f"| Edges | {len(edges)} |")
        for ntype, nlist in sorted(nodes_by_type.items()):
            emoji = type_emoji.get(ntype, "📎")
            lines.append(f"| {emoji} {ntype} | {len(nlist)} |")
        lines.append("")

        # categories
        lines.append("## 📑 Categories")
        lines.append("")
        for ntype_val, folder in sorted(type_folders.items()):
            type_nodes = nodes_by_type.get(ntype_val, [])
            if not type_nodes:
                continue
            emoji = type_emoji.get(ntype_val, "📎")
            lines.append(f"### {emoji} {folder} ({len(type_nodes)})")
            lines.append("")
            for n in sorted(type_nodes, key=lambda x: x.title or x.content[:40])[:100]:
                if n.id in created:
                    display = n.title or n.content[:60] or n.id[:12]
                    lines.append(f"- [[{created[n.id]}|{display}]]")
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
                    "query": f"tag:#{ntype_val}",
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
    # Summary
    # ------------------------------------------------------------------

    def get_export_summary(self) -> dict[str, Any]:
        """Preview what would be exported without writing files.

        Returns:
            Summary dict with counts by type.
        """
        with self.graph_store._transaction() as cursor:
            cursor.execute("SELECT node_type, COUNT(*) FROM nodes GROUP BY node_type")
            node_counts = {row[0]: row[1] for row in cursor.fetchall()}

            cursor.execute("SELECT edge_type, COUNT(*) FROM edges GROUP BY edge_type")
            edge_counts = {row[0]: row[1] for row in cursor.fetchall()}

            cursor.execute("SELECT COUNT(*) FROM nodes")
            total_nodes = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM edges")
            total_edges = cursor.fetchone()[0]

        return {
            "total_nodes": total_nodes,
            "total_edges": total_edges,
            "nodes_by_type": node_counts,
            "edges_by_type": edge_counts,
        }
