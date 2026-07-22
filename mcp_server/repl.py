#!/usr/bin/env python3
"""
MCP Tools REPL - Interactive terminal for AI Coding Tools MCP server.

Usage:
    python -m mcp_server repl
    python mcp_server/repl.py
"""

from __future__ import annotations

import asyncio
import inspect
import json
import os
try:
    import readline
except ImportError:
    try:
        import pyreadline3 as readline
    except ImportError:
        readline = None
import sys
import time
from pathlib import Path
from typing import Any, Callable

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from rich import box  # noqa: E402
from rich.console import Console  # noqa: E402
from rich.panel import Panel  # noqa: E402
from rich.syntax import Syntax  # noqa: E402
from rich.table import Table  # noqa: E402
from rich.text import Text  # noqa: E402
from rich.tree import Tree  # noqa: E402

console = Console()

HISTORY_FILE = os.path.expanduser("~/.mcp_repl_history")

BANNER = r"""[bold cyan]
.------------------------------------------------------------.
| _____ ______    ________   ________                        |
||\   _ \  _   \ |\   ____\ |\   __  \                       |
|\ \  \\\__\ \  \\ \  \___| \ \  \|\  \                      |
| \ \  \\|__| \  \\ \  \     \ \   ____\                     |
|  \ \  \    \ \  \\ \  \____ \ \  \___|                     |
|   \ \__\    \ \__\\ \_______\\ \__\                        |
|    \|__|     \|__| \|_______| \|__|                        |
| _________   ________   ________   ___        ________      |
||\___   ___\|\   __  \ |\   __  \ |\  \      |\   ____\     |
|\|___ \  \_|\ \  \|\  \\ \  \|\  \\ \  \     \ \  \___|_    |
|     \ \  \  \ \  \\\  \\ \  \\\  \\ \  \     \ \_____  \   |
|      \ \  \  \ \  \\\  \\ \  \\\  \\ \  \____ \|____|\  \  |
|       \ \__\  \ \_______\\ \_______\\ \_______\ ____\_\  \ |
|        \|__|   \|_______| \|_______| \|_______||\_________\|
|                                                \|_________||
'------------------------------------------------------------'

   AI Coding Tools — Interactive MCP Console
   Type 'help' for commands, 'tools' to list tools
[/bold cyan]"""


# ---------------------------------------------------------------------------
# Dummy context so tool functions don't need a running MCP server
# ---------------------------------------------------------------------------


class DummyContext:
    """Minimal context for REPL tool calls."""

    async def info(self, msg: str) -> None:  # noqa: D102
        console.print(f"[dim]ℹ {msg}[/dim]")

    async def warning(self, msg: str) -> None:  # noqa: D102
        console.print(f"[yellow]⚠ {msg}[/yellow]")

    async def error(self, msg: str) -> None:  # noqa: D102
        console.print(f"[red]✗ {msg}[/red]")


_ctx = DummyContext()

# ---------------------------------------------------------------------------
# Tool registry
# ---------------------------------------------------------------------------


def _build_registry() -> dict[str, dict[str, Any]]:
    """Import tool functions and build a name → metadata mapping."""
    from mcp_server.tools import (  # noqa: F401
        code_analysis,
        context_tools,
        devops_tools,
        security_tools,
        testing_tools,
    )

    registry: dict[str, dict[str, Any]] = {
        # -- Code Analysis --
        "code_complexity": {
            "fn": code_analysis.analyze_python_complexity,
            "category": "Code Analysis",
            "desc": "Analyze Python code complexity metrics",
        },
        "find_patterns": {
            "fn": code_analysis.find_code_patterns,
            "category": "Code Analysis",
            "desc": "Find code patterns and anti-patterns",
        },
        "analyze_deps": {
            "fn": code_analysis.analyze_dependencies,
            "category": "Code Analysis",
            "desc": "Analyze dependency issues",
        },
        "code_summary": {
            "fn": code_analysis.generate_code_summary,
            "category": "Code Analysis",
            "desc": "Generate code file summary",
        },
        # -- Security --
        "scan_secrets": {
            "fn": security_tools.scan_secrets,
            "category": "Security",
            "desc": "Scan for hardcoded secrets",
        },
        "detect_injection": {
            "fn": security_tools.detect_injection_vulnerabilities,
            "category": "Security",
            "desc": "Detect injection vulnerabilities",
        },
        "check_headers": {
            "fn": security_tools.check_security_headers,
            "category": "Security",
            "desc": "Check security headers",
        },
        "security_audit": {
            "fn": security_tools.run_security_audit,
            "category": "Security",
            "desc": "Run comprehensive security audit",
        },
        # -- Testing --
        "test_cases": {
            "fn": testing_tools.generate_test_cases,
            "category": "Testing",
            "desc": "Generate test case suggestions",
        },
        "mock_stubs": {
            "fn": testing_tools.generate_mock_stubs,
            "category": "Testing",
            "desc": "Generate mock stubs",
        },
        "coverage": {
            "fn": testing_tools.analyze_test_coverage,
            "category": "Testing",
            "desc": "Analyze test coverage",
        },
        "test_results": {
            "fn": testing_tools.parse_test_results,
            "category": "Testing",
            "desc": "Parse test results",
        },
        # -- DevOps --
        "dockerfile": {
            "fn": devops_tools.generate_dockerfile,
            "category": "DevOps",
            "desc": "Generate Dockerfile",
        },
        "compose": {
            "fn": devops_tools.generate_docker_compose,
            "category": "DevOps",
            "desc": "Generate docker-compose.yml",
        },
        "ci_config": {
            "fn": devops_tools.generate_ci_config,
            "category": "DevOps",
            "desc": "Generate CI/CD config",
        },
        "deploy_config": {
            "fn": devops_tools.analyze_deployment_config,
            "category": "DevOps",
            "desc": "Analyze deployment config",
        },
        "env_config": {
            "fn": devops_tools.check_environment_config,
            "category": "DevOps",
            "desc": "Check environment config",
        },
        "deploy_checklist": {
            "fn": devops_tools.generate_deploy_checklist,
            "category": "DevOps",
            "desc": "Generate deployment checklist",
        },
        # -- Context --
        "context_search": {
            "fn": context_tools.search_context,
            "category": "Context",
            "desc": "Search context memory",
        },
        "context_stats": {
            "fn": context_tools.get_context_stats,
            "category": "Context",
            "desc": "Get memory statistics",
        },
    }

    # Attach introspected parameter info to each entry
    for _, entry in registry.items():
        fn: Callable[..., Any] = entry["fn"]
        sig = inspect.signature(fn)
        params: list[dict[str, Any]] = []
        for pname, p in sig.parameters.items():
            if pname == "ctx":
                continue
            info: dict[str, Any] = {"name": pname}
            info["type"] = getattr(p.annotation, "__name__", str(p.annotation))
            if p.default is not inspect.Parameter.empty:
                info["default"] = p.default
            params.append(info)
        entry["params"] = params

    return registry


# Lazy-initialised so the module can be imported without side-effects
_REGISTRY: dict[str, dict[str, Any]] | None = None


def _get_registry() -> dict[str, dict[str, Any]]:
    global _REGISTRY
    if _REGISTRY is None:
        _REGISTRY = _build_registry()
    return _REGISTRY


# ---------------------------------------------------------------------------
# Output formatting helpers
# ---------------------------------------------------------------------------

CATEGORY_ORDER = ["Code Analysis", "Security", "Testing", "DevOps", "Context"]


def _render_tree(data: Any, tree: Tree, depth: int = 0) -> None:
    """Recursively render nested dicts/lists as a Rich Tree."""
    if depth > 6:
        tree.add("[dim]…[/dim]")
        return
    if isinstance(data, dict):
        for key, value in data.items():
            if isinstance(value, (dict, list)):
                branch = tree.add(f"[bold]{key}[/bold]")
                _render_tree(value, branch, depth + 1)
            else:
                tree.add(f"[bold]{key}:[/bold] {value}")
    elif isinstance(data, list):
        for i, item in enumerate(data):
            if isinstance(item, (dict, list)):
                branch = tree.add(f"[dim][{i}][/dim]")
                _render_tree(item, branch, depth + 1)
            else:
                tree.add(str(item))
    else:
        tree.add(str(data))


def _format_findings_table(items: list[dict[str, Any]], title: str) -> Table:
    """Format a list of finding dicts as a Rich Table."""
    table = Table(title=title, box=box.ROUNDED, show_lines=True)

    if not items:
        table.add_column("(no results)")
        return table

    # Use the keys of the first item as columns
    columns = list(items[0].keys())
    for col in columns:
        table.add_column(col.replace("_", " ").title(), overflow="fold")
    for item in items[:50]:  # limit display
        row = [str(item.get(c, ""))[:120] for c in columns]
        table.add_row(*row)
    return table


def format_tool_output(tool_name: str, result: dict[str, Any]) -> None:
    """Intelligently format tool output using Rich components."""
    # Handle error results
    if "error" in result:
        console.print(
            Panel(
                f"[red bold]{result['error']}[/red bold]",
                title=f"[red]✗ {tool_name} — Error[/red]",
                border_style="red",
                box=box.HEAVY,
            )
        )
        return

    rendered_parts: list[Any] = []

    # ---- Lists of findings / issues / vulnerabilities → table ----
    list_keys = [
        "findings",
        "issues",
        "vulnerabilities",
        "patterns",
        "functions",
        "classes",
        "dependencies",
        "variables",
        "mock_suggestions",
        "tests",
        "failed_tests",
        "files",
        "low_coverage_files",
        "recommendations",
        "found_headers",
        "missing_headers",
        "test_cases",
        "results",
    ]

    for key in list_keys:
        items = result.get(key)
        if items and isinstance(items, list):
            if items and isinstance(items[0], dict):
                rendered_parts.append(_format_findings_table(items, key.replace("_", " ").title()))
            elif items and isinstance(items[0], str):
                # Simple list of strings
                text = Text()
                for item in items:
                    text.append("  • ", style="green")
                    text.append(f"{item}\n")
                rendered_parts.append(
                    Panel(text, title=key.replace("_", " ").title(), box=box.ROUNDED)
                )

    # ---- Summary / stats → key-value panel ----
    summary_keys = ["summary", "score", "total_coverage", "documentation_coverage"]
    summary_parts: list[str] = []
    for key in summary_keys:
        val = result.get(key)
        if val is not None:
            if isinstance(val, dict):
                for sk, sv in val.items():
                    summary_parts.append(f"[bold]{sk.replace('_', ' ').title()}:[/bold] {sv}")
            else:
                summary_parts.append(f"[bold]{key.replace('_', ' ').title()}:[/bold] {val}")

    if summary_parts:
        rendered_parts.append(
            Panel(
                "\n".join(summary_parts),
                title="[bold cyan]Summary[/bold cyan]",
                box=box.ROUNDED,
                border_style="cyan",
            )
        )

    # ---- Code blocks (dockerfile, docker_compose, config, etc.) ----
    code_keys = ["dockerfile", "docker_compose", "config"]
    for key in code_keys:
        code_val = result.get(key)
        if code_val and isinstance(code_val, str) and len(code_val) > 40:
            lang = "yaml" if key in ("docker_compose", "config") else "dockerfile"
            rendered_parts.append(
                Panel(
                    Syntax(code_val, lang, theme="monokai", line_numbers=True),
                    title=f"[bold]{key.replace('_', ' ').title()}[/bold]",
                    box=box.ROUNDED,
                )
            )

    # ---- Checklist sections (for deploy_checklist) ----
    checklist_keys = [
        "pre_deployment",
        "deployment",
        "post_deployment",
        "rollback_plan",
        "additional_checks",
    ]
    for key in checklist_keys:
        items = result.get(key)
        if items and isinstance(items, list) and isinstance(items[0], str):
            text = Text()
            for item in items:
                text.append("  ☐ ", style="yellow")
                text.append(f"{item}\n")
            rendered_parts.append(
                Panel(
                    text,
                    title=key.replace("_", " ").title(),
                    box=box.ROUNDED,
                    border_style="yellow",
                )
            )

    # ---- Fallback: tree view for anything not yet rendered ----
    shown_keys = set(list_keys + summary_keys + code_keys + checklist_keys + ["error"])
    remaining = {k: v for k, v in result.items() if k not in shown_keys and v}
    if remaining and not rendered_parts:
        # Nothing was rendered through specialised formatters — full tree
        tree = Tree(f"[bold]{tool_name}[/bold]")
        _render_tree(result, tree)
        rendered_parts.append(tree)
    elif remaining:
        tree = Tree("[bold]Details[/bold]")
        _render_tree(remaining, tree)
        rendered_parts.append(tree)

    # Print everything
    for part in rendered_parts:
        console.print(part)


# ---------------------------------------------------------------------------
# Command handlers
# ---------------------------------------------------------------------------


def _cmd_help() -> None:
    table = Table(title="MCP REPL Commands", box=box.SIMPLE_HEAVY, title_style="bold cyan")
    table.add_column("Command", style="green bold", min_width=30)
    table.add_column("Description")
    table.add_row("help", "Show this help message")
    table.add_row("tools", "List all available MCP tools")
    table.add_row(
        "call <tool> [JSON args]",
        'Call a tool  —  e.g. call code_complexity {"file_path": "app.py"}',
    )
    table.add_row("info <tool>", "Show detailed info about a tool")
    table.add_row("history", "Show command history")
    table.add_row("clear", "Clear screen")
    table.add_row("exit / quit", "Exit the REPL")
    console.print(table)


def _cmd_tools() -> None:
    registry = _get_registry()
    table = Table(title="Registered MCP Tools", box=box.ROUNDED, show_lines=False)
    table.add_column("#", style="dim", width=4)
    table.add_column("Name", style="green bold", min_width=20)
    table.add_column("Category", style="cyan", min_width=16)
    table.add_column("Description")

    idx = 1
    for cat in CATEGORY_ORDER:
        for name, entry in sorted(registry.items()):
            if entry["category"] == cat:
                table.add_row(str(idx), name, entry["category"], entry["desc"])
                idx += 1

    # Catch any categories not in CATEGORY_ORDER
    listed_cats = set(CATEGORY_ORDER)
    for name, entry in sorted(registry.items()):
        if entry["category"] not in listed_cats:
            table.add_row(str(idx), name, entry["category"], entry["desc"])
            idx += 1

    console.print(table)
    console.print(
        f"\n[dim]{idx - 1} tools available. Use [green]call <tool> [JSON][/green] to invoke.[/dim]\n"
    )


def _cmd_info(tool_name: str) -> None:
    registry = _get_registry()
    entry = registry.get(tool_name)
    if not entry:
        console.print(f"[red]Unknown tool: {tool_name}[/red]")
        _suggest_tool(tool_name)
        return

    # Build params table
    params_text = Text()
    for p in entry["params"]:
        default_str = f" = {p['default']!r}" if "default" in p else " [red](required)[/red]"
        params_text.append(f"  {p['name']}", style="bold green")
        params_text.append(f" : {p['type']}")
        params_text.append_text(Text.from_markup(default_str))
        params_text.append("\n")

    if not entry["params"]:
        params_text.append("  (no parameters)\n", style="dim")

    # Example JSON
    example_args: dict[str, Any] = {}
    for p in entry["params"]:
        if "default" in p:
            example_args[p["name"]] = p["default"]
        elif "file" in p["name"] or "path" in p["name"]:
            example_args[p["name"]] = "path/to/file.py"
        elif "dir" in p["name"]:
            example_args[p["name"]] = "src/"
        else:
            example_args[p["name"]] = "..."
    example_cmd = f"call {tool_name} {json.dumps(example_args)}"

    body = Text()
    body.append(f"{entry['desc']}\n\n", style="bold")
    body.append("Category: ", style="dim")
    body.append(f"{entry['category']}\n\n", style="cyan")
    body.append("Parameters:\n", style="dim")
    body.append_text(params_text)
    body.append("\nExample:\n", style="dim")
    body.append(f"  mcp> {example_cmd}\n", style="green")

    fn = entry["fn"]
    docstring = inspect.getdoc(fn)
    if docstring:
        body.append("\nDocstring:\n", style="dim")
        body.append(f"  {docstring}\n", style="italic")

    console.print(
        Panel(
            body, title=f"[bold cyan]🔧 {tool_name}[/bold cyan]", box=box.HEAVY, border_style="cyan"
        )
    )


def _suggest_tool(name: str) -> None:
    """Suggest similar tool names on typo."""
    registry = _get_registry()
    suggestions = [t for t in registry if name in t or t in name]
    if suggestions:
        console.print(f"[dim]Did you mean: {', '.join(suggestions)}?[/dim]")


async def _cmd_call(tool_name: str, args_json: str) -> None:
    registry = _get_registry()
    entry = registry.get(tool_name)
    if not entry:
        console.print(f"[red]Unknown tool: {tool_name}[/red]")
        _suggest_tool(tool_name)
        return

    # Parse JSON args
    kwargs: dict[str, Any] = {}
    if args_json.strip():
        try:
            kwargs = json.loads(args_json)
        except json.JSONDecodeError as e:
            console.print(f"[red]Invalid JSON: {e}[/red]")
            return

    fn: Callable[..., Any] = entry["fn"]

    console.print(f"[dim]⏳ Calling [bold]{tool_name}[/bold]…[/dim]")
    t0 = time.monotonic()

    try:
        result = await fn(_ctx, **kwargs)
    except TypeError as e:
        elapsed = time.monotonic() - t0
        console.print(
            Panel(
                f"[red]{e}[/red]\n\n[dim]Expected parameters:[/dim]\n"
                + "\n".join(
                    f"  [green]{p['name']}[/green]: {p['type']}"
                    + (f" = {p['default']!r}" if "default" in p else " (required)")
                    for p in entry["params"]
                ),
                title=f"[red]✗ {tool_name} — Argument Error[/red]",
                border_style="red",
                box=box.HEAVY,
                subtitle=f"[dim]{elapsed:.2f}s[/dim]",
            )
        )
        return
    except Exception as e:
        elapsed = time.monotonic() - t0
        console.print(
            Panel(
                f"[red bold]{type(e).__name__}: {e}[/red bold]",
                title=f"[red]✗ {tool_name} — Error[/red]",
                border_style="red",
                box=box.HEAVY,
                subtitle=f"[dim]{elapsed:.2f}s[/dim]",
            )
        )
        return

    elapsed = time.monotonic() - t0

    # If the function returns a JSON string, parse it
    if isinstance(result, str):
        try:
            result = json.loads(result)
        except (json.JSONDecodeError, TypeError):
            pass

    if isinstance(result, dict):
        console.print(
            Panel(
                f"[green bold]✓ {tool_name}[/green bold] completed",
                border_style="green",
                box=box.HEAVY,
                subtitle=f"[dim]{elapsed:.2f}s[/dim]",
            )
        )
        format_tool_output(tool_name, result)
    else:
        console.print(
            Panel(
                str(result),
                title=f"[green]✓ {tool_name}[/green]",
                border_style="green",
                box=box.HEAVY,
                subtitle=f"[dim]{elapsed:.2f}s[/dim]",
            )
        )

    console.print()


def _cmd_history() -> None:
    length = readline.get_current_history_length()
    if length == 0:
        console.print("[dim]No history yet.[/dim]")
        return
    table = Table(title="Command History", box=box.SIMPLE, show_lines=False)
    table.add_column("#", style="dim", width=6)
    table.add_column("Command")
    start = max(1, length - 49)
    for i in range(start, length + 1):
        item = readline.get_history_item(i)
        if item:
            table.add_row(str(i), item)
    console.print(table)


# ---------------------------------------------------------------------------
# Tab completion
# ---------------------------------------------------------------------------

COMMANDS = ["help", "tools", "call", "info", "history", "clear", "exit", "quit"]


class _Completer:
    """Readline completer for REPL commands and tool names."""

    def __init__(self) -> None:
        self._matches: list[str] = []

    def complete(self, text: str, state: int) -> str | None:
        if state == 0:
            line = readline.get_line_buffer().lstrip()
            parts = line.split()

            if len(parts) <= 1:
                # Complete commands and tool names after 'call'/'info'
                candidates = COMMANDS + list(_get_registry().keys())
                self._matches = [c + " " for c in candidates if c.startswith(text)]
            elif parts[0] in ("call", "info"):
                # Complete tool names
                self._matches = [t + " " for t in _get_registry() if t.startswith(text)]
            else:
                self._matches = []

        return self._matches[state] if state < len(self._matches) else None


# ---------------------------------------------------------------------------
# Main REPL loop
# ---------------------------------------------------------------------------


def _load_history() -> None:
    try:
        readline.read_history_file(HISTORY_FILE)
    except (FileNotFoundError, OSError):
        pass


def _save_history() -> None:
    try:
        readline.set_history_length(1000)
        readline.write_history_file(HISTORY_FILE)
    except OSError:
        pass


async def _repl_loop() -> None:
    console.print(BANNER)
    console.print("[dim]Working directory:[/dim]", os.getcwd())
    console.print()

    _load_history()

    # Setup readline
    completer = _Completer()
    readline.set_completer(completer.complete)
    readline.set_completer_delims(" \t\n")
    if "libedit" in readline.__doc__:  # type: ignore[operator]
        readline.parse_and_bind("bind ^I rl_complete")
    else:
        readline.parse_and_bind("tab: complete")

    try:
        while True:
            try:
                line = input("\033[1;36mmcp>\033[0m ").strip()
            except KeyboardInterrupt:
                console.print()
                continue
            except EOFError:
                console.print("\n[dim]Goodbye![/dim]")
                break

            if not line:
                continue

            parts = line.split(None, 1)
            cmd = parts[0].lower()
            rest = parts[1] if len(parts) > 1 else ""

            if cmd in ("exit", "quit"):
                console.print("[dim]Goodbye![/dim]")
                break
            if cmd == "help":
                _cmd_help()
            elif cmd == "tools":
                _cmd_tools()
            elif cmd == "clear":
                console.clear()
                console.print(BANNER)
            elif cmd == "history":
                _cmd_history()
            elif cmd == "info":
                if not rest.strip():
                    console.print("[red]Usage: info <tool_name>[/red]")
                else:
                    _cmd_info(rest.strip())
            elif cmd == "call":
                call_parts = rest.split(None, 1)
                if not call_parts:
                    console.print("[red]Usage: call <tool_name> [JSON args][/red]")
                else:
                    tool_name = call_parts[0]
                    args_json = call_parts[1] if len(call_parts) > 1 else ""
                    await _cmd_call(tool_name, args_json)
            else:
                console.print(f"[red]Unknown command: {cmd}[/red]")
                console.print("[dim]Type 'help' for available commands.[/dim]")
    finally:
        _save_history()


def main() -> None:
    """Entry point for the MCP REPL."""
    try:
        asyncio.run(_repl_loop())
    except KeyboardInterrupt:
        console.print("\n[dim]Goodbye![/dim]")


if __name__ == "__main__":
    main()
