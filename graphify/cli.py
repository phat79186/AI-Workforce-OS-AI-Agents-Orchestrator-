"""
Graphify CLI — command-line interface for scanning projects,

querying graphs, generating reports, and exporting data.

Usage:
    python -m graphify scan /path/to/project
    python -m graphify scan /path/to/project --update
    python -m graphify search "class User" --project /path/to/project
    python -m graphify stats /path/to/project
    python -m graphify report /path/to/project
    python -m graphify query "what connects X to Y"
    python -m graphify explain NodeName
    python -m graphify path StartNode EndNode
    python -m graphify export json /path/to/project
    python -m graphify serve --db .graphify.db
"""

from __future__ import annotations

import logging
import os
import sys
import time

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.tree import Tree

from graphify.core.config import GraphifyConfig
from graphify.core.graph import GraphStore
from graphify.core.scanner import Scanner
from graphify.core.schema import NodeType, generate_project_id
from graphify.export.formatters import GraphExporter
from graphify.search.fts_engine import FTSEngine
from graphify.search.query_engine import QueryEngine

console = Console()
logger = logging.getLogger("graphify")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _resolve_path(path: str) -> str:
    """Resolve a user-supplied path (absolute or relative)."""
    expanded = os.path.expanduser(path.strip().strip("'\""))
    resolved = os.path.normpath(os.path.abspath(expanded))
    if not os.path.isdir(resolved):
        console.print(f"[red]Error:[/red] Not a directory: {resolved}")
        sys.exit(1)
    return resolved


def _get_store(path: str, db: str | None = None) -> GraphStore:
    """Get or create a GraphStore for a project path."""
    config = GraphifyConfig(db_path=db or "")
    db_path = config.resolve_db_path(path)
    return GraphStore(db_path)


def _get_project_id(path: str) -> str:
    """Generate project ID from path."""
    return generate_project_id(path)


def build_graph(path: str, db: str | None = None, **kwargs) -> GraphStore:
    """Scan a project and return the populated store (used by __init__.py factory)."""
    resolved = _resolve_path(path)
    config = GraphifyConfig(db_path=db or "", **kwargs)
    store = GraphStore(config.resolve_db_path(resolved))
    scanner = Scanner(resolved, store, config)
    scanner.scan()
    return store


# ---------------------------------------------------------------------------
# CLI group
# ---------------------------------------------------------------------------


@click.group()
@click.option("--verbose", "-v", is_flag=True, help="Enable debug logging.")
def main(verbose: bool) -> None:
    """Graphify — turn any project into a queryable context graph."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)-8s %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )


# ---------------------------------------------------------------------------
# scan
# ---------------------------------------------------------------------------


@main.command()
@click.argument("path")
@click.option("--db", default=None, help="Custom database path (default: <project>/.graphify.db).")
@click.option("--max-files", default=10_000, type=int, help="Max files to scan.")
@click.option("--workers", default=4, type=int, help="Parallel worker threads.")
@click.option("--update", is_flag=True, help="Incremental update — only re-scan changed files.")
@click.option("--report/--no-report", default=True, help="Generate GRAPH_REPORT.md.")
@click.option("--html/--no-html", "gen_html", default=True, help="Generate interactive graph.html.")
def scan(
    path: str,
    db: str | None,
    max_files: int,
    workers: int,
    update: bool,
    report: bool,  # pylint: disable=redefined-outer-name
    gen_html: bool,
) -> None:
    """Scan a project directory and build its context graph."""
    resolved = _resolve_path(path)
    config = GraphifyConfig(
        db_path=db or "",
        max_files=max_files,
        worker_threads=workers,
        generate_report=report,
        generate_html=gen_html,
    )

    with GraphStore(config.resolve_db_path(resolved)) as store:
        mode_label = "Updating" if update else "Scanning"
        with console.status(f"[bold green]{mode_label} project..."):
            start = time.time()
            scanner = Scanner(resolved, store, config)
            summary = scanner.scan(incremental=update)
            elapsed = time.time() - start

        # Display results
        table = Table(title=f"✅ Scan Complete — {summary.name}", show_header=True)
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="green", justify="right")

        table.add_row("Project ID", summary.project_id)
        table.add_row("Path", summary.root_path)
        table.add_row("Files scanned", str(summary.total_files))
        table.add_row("Total lines", f"{summary.total_lines:,}")
        table.add_row("Classes", str(summary.total_classes))
        table.add_row("Functions", str(summary.total_functions))
        table.add_row("Tests", str(summary.total_tests))
        table.add_row("Languages", ", ".join(summary.languages.keys()))
        if summary.frameworks:
            table.add_row("Frameworks", ", ".join(summary.frameworks))
        table.add_row("Scan time", f"{elapsed:.2f}s")

        graph_stats = store.stats(summary.project_id)
        table.add_row("Graph nodes", str(graph_stats["nodes"]))
        table.add_row("Graph edges", str(graph_stats["edges"]))
        table.add_row("Database", config.resolve_db_path(resolved))

        console.print(table)

        # Generate output files
        output_dir = os.path.join(resolved, "graphify-out")
        if report or gen_html:
            os.makedirs(output_dir, exist_ok=True)

        if report:
            from graphify.report.generator import ReportGenerator  # pylint: disable=C0415

            gen = ReportGenerator(store)
            gen.generate(summary.project_id, output_dir=output_dir)
            console.print(
                f"[green]📄 Report:[/green] {os.path.join(output_dir, 'GRAPH_REPORT.md')}"
            )

        if gen_html:
            from graphify.visualization.html_renderer import HTMLRenderer  # pylint: disable=C0415

            renderer = HTMLRenderer(store)
            renderer.render(summary.project_id, output_dir=output_dir)
            console.print(f"[green]🌐 HTML:[/green] {os.path.join(output_dir, 'graph.html')}")

        # Also export graph.json
        if report or gen_html:
            exporter = GraphExporter(store)
            json_path = os.path.join(output_dir, "graph.json")
            with open(json_path, "w", encoding="utf-8") as fh:
                fh.write(exporter.to_json(summary.project_id))
            console.print(f"[green]📦 JSON:[/green] {json_path}")


# ---------------------------------------------------------------------------
# search
# ---------------------------------------------------------------------------


@main.command()
@click.argument("query")
@click.option("--path", "-p", default=".", help="Project path.")
@click.option("--db", default=None, help="Database path.")
@click.option(
    "--type", "-t", "node_type", default=None, help="Filter by node type (e.g. CLASS, FUNCTION)."
)
@click.option("--limit", "-n", default=20, type=int, help="Max results.")
def search(query: str, path: str, db: str | None, node_type: str | None, limit: int) -> None:
    """Search the project graph using full-text search."""
    resolved = _resolve_path(path)
    pid = _get_project_id(resolved)

    with _get_store(resolved, db) as store:
        fts = FTSEngine(store)
        ntype = NodeType(node_type) if node_type else None
        results = fts.search(query, project_id=pid, node_type=ntype, limit=limit)

        if not results:
            console.print("[yellow]No results found.[/yellow]")
            return

        table = Table(title=f"Search: '{query}' ({len(results)} results)", show_header=True)
        table.add_column("#", style="dim", width=4)
        table.add_column("Type", style="cyan", width=12)
        table.add_column("Name", style="green")
        table.add_column("File", style="blue")
        table.add_column("Score", justify="right", width=8)

        for i, r in enumerate(results, 1):
            node = r["node"]
            table.add_row(
                str(i),
                node.node_type.value,
                node.name,
                node.file_path[:50],
                f"{r['score']:.2f}",
            )

        console.print(table)


# ---------------------------------------------------------------------------
# stats
# ---------------------------------------------------------------------------


@main.command()
@click.argument("path", default=".")
@click.option("--db", default=None, help="Database path.")
def stats(path: str, db: str | None) -> None:
    """Show graph statistics for a project."""
    resolved = _resolve_path(path)
    pid = _get_project_id(resolved)

    with _get_store(resolved, db) as store:
        query_engine = QueryEngine(store)
        data = query_engine.summary(pid)
        meta = store.get_project_meta(pid)

        if not meta:
            console.print("[yellow]No graph found. Run 'graphify scan' first.[/yellow]")
            return

        table = Table(title=f"📊 {meta.name}", show_header=True)
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="green", justify="right")

        table.add_row("Nodes", str(data.get("nodes", 0)))
        table.add_row("Edges", str(data.get("edges", 0)))
        for ntype, count in sorted(data.get("node_types", {}).items()):
            table.add_row(f"  {ntype}", str(count))
        table.add_row("", "")
        for lang, count in sorted(
            data.get("languages", {}).items(), key=lambda x: x[1], reverse=True
        ):
            table.add_row(f"  {lang}", str(count))

        console.print(table)


# ---------------------------------------------------------------------------
# report
# ---------------------------------------------------------------------------


@main.command()
@click.argument("path", default=".")
@click.option("--db", default=None, help="Database path.")
def report(path: str, db: str | None) -> None:
    """Generate GRAPH_REPORT.md from an existing graph."""
    from graphify.report.generator import ReportGenerator  # pylint: disable=C0415

    resolved = _resolve_path(path)
    pid = _get_project_id(resolved)

    with _get_store(resolved, db) as store:
        meta = store.get_project_meta(pid)
        if not meta:
            console.print("[yellow]No graph found. Run 'graphify scan' first.[/yellow]")
            return

        output_dir = os.path.join(resolved, "graphify-out")
        os.makedirs(output_dir, exist_ok=True)

        gen = ReportGenerator(store)
        gen.generate(pid, output_dir=output_dir)
        console.print(
            f"[green]📄 Report written to {os.path.join(output_dir, 'GRAPH_REPORT.md')}[/green]"
        )


# ---------------------------------------------------------------------------
# explain
# ---------------------------------------------------------------------------


@main.command()
@click.argument("name")
@click.option("--path", "-p", default=".", help="Project path.")
@click.option("--db", default=None, help="Database path.")
def explain(name: str, path: str, db: str | None) -> None:
    """Explain a specific node — what it is and what it connects to."""
    resolved = _resolve_path(path)
    pid = _get_project_id(resolved)

    with _get_store(resolved, db) as store:
        qe = QueryEngine(store)
        result = qe.explain_node(name, project_id=pid)
        if "error" in result:
            console.print(f"[yellow]{result['error']}[/yellow]")
            return

        node = result["node"]
        degree = result["degree"]

        console.print(
            Panel(
                f"[cyan]{node['name']}[/cyan] ({node['type']})\n"
                f"File: {node['file_path']}\n"
                f"Lines: {node['line_start']}-{node['line_end']}\n"
                f"Degree: in={degree['in_degree']} out={degree['out_degree']} total={degree['total']}",
                title="Node Detail",
            )
        )

        if result["outgoing"]:
            table = Table(title="Outgoing Connections", show_header=True)
            table.add_column("Target", style="green")
            table.add_column("Type", style="cyan")
            table.add_column("Edge", style="blue")
            table.add_column("Conf", justify="right", width=6)
            for conn in result["outgoing"][:20]:
                table.add_row(
                    conn["node"]["name"][:40],
                    conn["node"]["type"],
                    conn["edge_type"],
                    f"{conn['confidence']:.1f}",
                )
            console.print(table)

        if result["incoming"]:
            table = Table(title="Incoming Connections", show_header=True)
            table.add_column("Source", style="green")
            table.add_column("Type", style="cyan")
            table.add_column("Edge", style="blue")
            table.add_column("Conf", justify="right", width=6)
            for conn in result["incoming"][:20]:
                table.add_row(
                    conn["node"]["name"][:40],
                    conn["node"]["type"],
                    conn["edge_type"],
                    f"{conn['confidence']:.1f}",
                )
            console.print(table)


# ---------------------------------------------------------------------------
# path (find shortest path between nodes)
# ---------------------------------------------------------------------------


@main.command("path")
@click.argument("start")
@click.argument("end")
@click.option("--path", "-p", "project_path", default=".", help="Project path.")
@click.option("--db", default=None, help="Database path.")
def find_path(start: str, end: str, project_path: str, db: str | None) -> None:
    """Find the shortest path between two named nodes."""
    resolved = _resolve_path(project_path)
    pid = _get_project_id(resolved)

    with _get_store(resolved, db) as store:
        qe = QueryEngine(store)
        path_nodes = qe.find_path(start, end, project_id=pid)
        if not path_nodes:
            console.print(f"[yellow]No path found between '{start}' and '{end}'.[/yellow]")
            return

        tree = Tree(f"[bold]Path: {start} → {end}[/bold] ({len(path_nodes)} hops)")
        for i, node in enumerate(path_nodes):
            prefix = "→ " if i > 0 else "⬤ "
            tree.add(f"{prefix}[cyan]{node['name']}[/cyan] ({node['type']}) — {node['file_path']}")

        console.print(tree)


# ---------------------------------------------------------------------------
# export
# ---------------------------------------------------------------------------


@main.command()
@click.argument("fmt", type=click.Choice(["json", "dot", "markdown", "graphml", "obsidian"]))
@click.argument("path", default=".")
@click.option("--db", default=None, help="Database path.")
@click.option("--output", "-o", default=None, help="Output file (default: stdout).")
def export(fmt: str, path: str, db: str | None, output: str | None) -> None:
    """Export the project graph to JSON, DOT, Markdown, GraphML, or Obsidian vault."""
    resolved = _resolve_path(path)
    pid = _get_project_id(resolved)

    with _get_store(resolved, db) as store:
        exporter = GraphExporter(store)

        # Obsidian produces a directory, not a single file.
        if fmt == "obsidian":
            out_dir = output or os.path.join(resolved, "obsidian-vault")
            result = exporter.to_obsidian(pid, output_dir=out_dir)
            console.print(
                f"[green]🟣 Obsidian vault:[/green] {result['notes_written']} notes → {out_dir}"
            )
            return

        if fmt == "json":
            content = exporter.to_json(pid)
        elif fmt == "dot":
            content = exporter.to_dot(pid)
        elif fmt == "graphml":
            content = exporter.to_graphml(pid)
        else:
            content = exporter.to_markdown(pid)

        if output:
            with open(output, "w", encoding="utf-8") as fh:
                fh.write(content)
            console.print(f"[green]Exported to {output}[/green]")
        else:
            console.print(content)


# ---------------------------------------------------------------------------
# serve
# ---------------------------------------------------------------------------


@main.command()
@click.option("--db", required=True, help="Path to .graphify.db file.")
@click.option("--host", default="127.0.0.1", help="Bind host.")
@click.option("--port", default=5004, type=int, help="Bind port.")
def serve(db: str, host: str, port: int) -> None:
    """Start the Graphify REST API server."""
    from graphify.api.server import run_server  # pylint: disable=C0415

    console.print(f"[bold green]Graphify API[/bold green] → http://{host}:{port}")
    run_server(db, host=host, port=port)


# ---------------------------------------------------------------------------
# hotspots
# ---------------------------------------------------------------------------


@main.command()
@click.argument("path", default=".")
@click.option("--db", default=None, help="Database path.")
@click.option("--top", "-n", default=20, type=int, help="Number of hotspots.")
def hotspots(path: str, db: str | None, top: int) -> None:
    """Show complexity hotspot files."""
    resolved = _resolve_path(path)
    with _get_store(resolved, db) as store:
        query_engine = QueryEngine(store)
        pid = _get_project_id(resolved)

        spots = query_engine.complexity_hotspots(pid, top)
        if not spots:
            console.print("[yellow]No data. Run 'graphify scan' first.[/yellow]")
            return

        table = Table(title="🔥 Complexity Hotspots", show_header=True)
        table.add_column("#", style="dim", width=4)
        table.add_column("File", style="blue")
        table.add_column("Lines", justify="right")
        table.add_column("Classes", justify="right")
        table.add_column("Functions", justify="right")
        table.add_column("Score", justify="right", style="red")

        for i, s in enumerate(spots, 1):
            table.add_row(
                str(i),
                s["file"][:60],
                str(s["lines"]),
                str(s["classes"]),
                str(s["functions"]),
                str(s["score"]),
            )

        console.print(table)


# ---------------------------------------------------------------------------
# god-nodes
# ---------------------------------------------------------------------------


@main.command("god-nodes")
@click.argument("path", default=".")
@click.option("--db", default=None, help="Database path.")
@click.option("--top", "-n", default=20, type=int, help="Number of god nodes.")
def god_nodes(path: str, db: str | None, top: int) -> None:
    """Show highest-degree nodes (god nodes) in the graph."""
    resolved = _resolve_path(path)
    with _get_store(resolved, db) as store:
        pid = _get_project_id(resolved)

        gods = store.god_nodes(pid, top_n=top)
        if not gods:
            console.print("[yellow]No data. Run 'graphify scan' first.[/yellow]")
            return

        table = Table(title="🏛️ God Nodes", show_header=True)
        table.add_column("#", style="dim", width=4)
        table.add_column("Name", style="green")
        table.add_column("Type", style="cyan", width=14)
        table.add_column("File", style="blue")
        table.add_column("Degree", justify="right", style="red")

        for i, g in enumerate(gods, 1):
            node = g["node"]
            table.add_row(
                str(i),
                node.name[:50],
                node.node_type.value,
                node.file_path[:40],
                str(g["degree"]),
            )

        console.print(table)
