"""
Interactive HTML graph visualization using vis.js Network.

Generates a self-contained HTML file with:
  - Interactive force-directed graph layout
  - Node coloring by type
  - Click-to-expand neighbor detail
  - Search/filter controls
  - Legend and statistics panel
"""

from __future__ import annotations

import html as html_lib
import json
import logging
import os
from typing import Any

from graphify.core.graph import GraphStore

logger = logging.getLogger(__name__)

# Node type → color mapping
_NODE_COLORS: dict[str, str] = {
    "PROJECT": "#2ecc71",
    "DIRECTORY": "#f39c12",
    "FILE": "#3498db",
    "CLASS": "#9b59b6",
    "FUNCTION": "#e74c3c",
    "TEST": "#1abc9c",
    "IMPORT": "#7f8c8d",
    "DEPENDENCY": "#e91e63",
    "CONFIG": "#795548",
    "DOCUMENTATION": "#8bc34a",
    "RATIONALE": "#ff9800",
    "PATTERN": "#00bcd4",
    "VARIABLE": "#607d8b",
    "COMMUNITY": "#673ab7",
    "MODULE": "#009688",
}

_NODE_SHAPES: dict[str, str] = {
    "PROJECT": "diamond",
    "DIRECTORY": "triangle",
    "FILE": "dot",
    "CLASS": "box",
    "FUNCTION": "ellipse",
    "TEST": "star",
    "RATIONALE": "hexagon",
}


class HTMLRenderer:
    """Generates interactive vis.js HTML from the graph store."""

    def __init__(self, store: GraphStore) -> None:
        self._store = store

    def render(
        self,
        project_id: str,
        output_dir: str = "",
        max_nodes: int = 500,
        filename: str = "graph.html",
    ) -> str:
        """Build HTML and optionally write to file. Returns the HTML string."""
        nodes = self._store.get_nodes(project_id=project_id, limit=max_nodes)
        edges = self._store.get_edges(project_id=project_id)

        node_ids = {n.id for n in nodes}

        # Build vis.js data
        vis_nodes = self._build_vis_nodes(nodes)
        vis_edges = self._build_vis_edges(edges, node_ids)
        stats = self._store.stats(project_id)
        meta = self._store.get_project_meta(project_id)

        project_name = meta.name if meta else project_id
        html_content = self._build_html(
            project_name,
            vis_nodes,
            vis_edges,
            stats,
        )

        if output_dir:
            path = os.path.join(output_dir, filename)
            with open(path, "w", encoding="utf-8") as fh:
                fh.write(html_content)
            logger.info("HTML visualization written to %s", path)

        return html_content

    # ------------------------------------------------------------------
    # Data builders
    # ------------------------------------------------------------------

    @staticmethod
    def _build_vis_nodes(nodes: list) -> list[dict[str, Any]]:
        vis = []
        for n in nodes:
            ntype = n.node_type.value
            color = _NODE_COLORS.get(ntype, "#9e9e9e")
            shape = _NODE_SHAPES.get(ntype, "dot")
            label = n.name[:40] if n.name else n.id[:8]

            vis.append(
                {
                    "id": n.id,
                    "label": label,
                    "title": (
                        f"<b>{html_lib.escape(n.name)}</b><br>"
                        f"Type: {ntype}<br>"
                        f"File: {html_lib.escape(n.file_path)}<br>"
                        f"Line: {n.line_start}"
                    ),
                    "color": {"background": color, "border": color},
                    "shape": shape,
                    "group": ntype,
                    "font": {"color": "#ffffff", "size": 11},
                }
            )
        return vis

    @staticmethod
    def _build_vis_edges(edges: list, node_ids: set) -> list[dict[str, Any]]:
        vis = []
        for e in edges:
            if e.source_id not in node_ids or e.target_id not in node_ids:
                continue
            vis.append(
                {
                    "from": e.source_id,
                    "to": e.target_id,
                    "label": e.edge_type.value,
                    "arrows": "to",
                    "font": {"size": 8, "color": "#666"},
                    "color": {"opacity": 0.5 + (e.confidence * 0.5)},
                    "title": f"{e.edge_type.value} (conf: {e.confidence:.1f})",
                }
            )
        return vis

    # ------------------------------------------------------------------
    # HTML template
    # ------------------------------------------------------------------

    @staticmethod
    def _build_html(
        project_name: str,
        vis_nodes: list,
        vis_edges: list,
        stats: dict,
    ) -> str:
        nodes_json = json.dumps(vis_nodes).replace("</", "<\\/")
        edges_json = json.dumps(vis_edges).replace("</", "<\\/")
        escaped_name = html_lib.escape(project_name)

        return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Graphify — {escaped_name}</title>
<script src="https://unpkg.com/vis-network@9.1.6/standalone/umd/vis-network.min.js"></script>
<style>
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
         background: #1a1a2e; color: #e0e0e0; }}
  #header {{ background: #16213e; padding: 12px 24px; display: flex;
             justify-content: space-between; align-items: center; }}
  #header h1 {{ font-size: 18px; color: #00d4ff; }}
  #search {{ padding: 6px 12px; border-radius: 4px; border: 1px solid #333;
             background: #0f3460; color: #fff; width: 300px; }}
  #graph {{ width: 100%; height: calc(100vh - 120px); }}
  #stats {{ background: #16213e; padding: 8px 24px; display: flex; gap: 24px;
            font-size: 13px; }}
  .stat {{ color: #aaa; }}
  .stat b {{ color: #00d4ff; }}
  #legend {{ position: absolute; bottom: 60px; right: 16px; background: #16213ecc;
             padding: 12px; border-radius: 8px; font-size: 12px; }}
  .leg-item {{ display: flex; align-items: center; gap: 6px; margin: 3px 0; }}
  .leg-dot {{ width: 12px; height: 12px; border-radius: 50%; display: inline-block; }}
  #detail {{ position: absolute; top: 60px; right: 16px; background: #16213eee;
             padding: 16px; border-radius: 8px; max-width: 350px; display: none;
             font-size: 13px; max-height: 60vh; overflow-y: auto; }}
  #detail h3 {{ color: #00d4ff; margin-bottom: 8px; }}
  #detail .close {{ cursor: pointer; float: right; color: #ff6b6b; }}
</style>
</head>
<body>
<div id="header">
  <h1>📊 Graphify — {escaped_name}</h1>
  <input id="search" type="text" placeholder="Search nodes..." oninput="filterNodes(this.value)">
</div>
<div id="graph"></div>
<div id="stats">
  <span class="stat">Nodes: <b>{stats.get('nodes', 0)}</b></span>
  <span class="stat">Edges: <b>{stats.get('edges', 0)}</b></span>
  <span class="stat">Showing: <b id="shown">{len(vis_nodes)}</b> nodes</span>
</div>
<div id="legend">
  {"".join(f'<div class="leg-item"><span class="leg-dot" style="background:{c}"></span>{t}</div>' for t, c in _NODE_COLORS.items() if t in {n.get("group") for n in vis_nodes})}
</div>
<div id="detail">
  <span class="close" onclick="document.getElementById('detail').style.display='none'">✕</span>
  <h3 id="det-name"></h3>
  <div id="det-body"></div>
</div>
<script>
function esc(s) {{ var d = document.createElement('div'); d.textContent = s; return d.innerHTML; }}
var allNodes = {nodes_json};
var allEdges = {edges_json};
var nodesDS = new vis.DataSet(allNodes);
var edgesDS = new vis.DataSet(allEdges);
var container = document.getElementById('graph');
var data = {{ nodes: nodesDS, edges: edgesDS }};
var options = {{
  physics: {{ solver: 'forceAtlas2Based', forceAtlas2Based: {{ gravitationalConstant: -30, springLength: 80 }},
              stabilization: {{ iterations: 150 }} }},
  interaction: {{ hover: true, tooltipDelay: 200, navigationButtons: true }},
  edges: {{ smooth: {{ type: 'continuous' }} }},
}};
var network = new vis.Network(container, data, options);

network.on('click', function(params) {{
  if (params.nodes.length > 0) {{
    var nid = params.nodes[0];
    var node = nodesDS.get(nid);
    document.getElementById('det-name').textContent = node.label;
    var neighbors = network.getConnectedNodes(nid);
    var html = '<p>Type: ' + esc(node.group) + '</p>';
    html += '<p>Connections: ' + neighbors.length + '</p><hr>';
    neighbors.forEach(function(nb) {{
      var n = nodesDS.get(nb);
      if (n) html += '<div style="margin:2px 0">' + esc(n.group) + ': <b>' + esc(n.label) + '</b></div>';
    }});
    document.getElementById('det-body').innerHTML = html;
    document.getElementById('detail').style.display = 'block';
  }}
}});

function filterNodes(query) {{
  if (!query) {{ nodesDS.update(allNodes.map(function(n){{ return {{id:n.id, hidden:false}}; }})); return; }}
  var q = query.toLowerCase();
  allNodes.forEach(function(n) {{
    nodesDS.update({{ id: n.id, hidden: !n.label.toLowerCase().includes(q) }});
  }});
  document.getElementById('shown').textContent =
    allNodes.filter(function(n){{ return n.label.toLowerCase().includes(q); }}).length;
}}
</script>
</body>
</html>"""
