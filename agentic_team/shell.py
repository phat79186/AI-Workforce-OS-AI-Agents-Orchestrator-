"""Interactive shell for the standalone Agentic Team engine."""

from __future__ import annotations

import json
import os
try:
    import readline
except ImportError:
    try:
        import pyreadline3 as readline
    except ImportError:
        readline = None
from datetime import datetime
from pathlib import Path
from typing import Any

from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.prompt import Confirm, Prompt
from rich.table import Table

from .engine import AgenticTeamEngine


class AgenticConversationHistory:
    """State container for the standalone agentic shell."""

    def __init__(self):
        self.messages: list[dict[str, Any]] = []
        self.max_turns: int = 12
        self.context: dict[str, Any] = {}

    def add_message(self, role: str, content: str, metadata: dict[str, Any] | None = None):
        """Append a message to in-memory history with timestamp and metadata."""
        self.messages.append(
            {
                "role": role,
                "content": content,
                "timestamp": datetime.now().isoformat(),
                "metadata": metadata or {},
            }
        )

    def clear(self):
        """Clear messages and contextual follow-up state."""
        self.messages.clear()
        self.context.clear()

    def save(self, filepath: str):
        """Persist history/context to a JSON session file."""
        data = {
            "messages": self.messages,
            "max_turns": self.max_turns,
            "context": self.context,
            "saved_at": datetime.now().isoformat(),
        }
        try:
            fd = os.open(filepath, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
            with os.fdopen(fd, "w") as f:
                json.dump(data, f, indent=2)
        except (OSError, TypeError) as e:
            raise OSError(f"Failed to save session: {e}") from e

    def load(self, filepath: str):
        """Load history/context from a JSON session file."""
        try:
            with open(filepath, encoding="utf-8") as f:
                data = json.load(f)
        except (OSError, json.JSONDecodeError) as e:
            raise OSError(f"Failed to load session: {e}") from e
        if not isinstance(data, dict):
            raise OSError("Invalid session file format")
        self.messages = data.get("messages", [])
        self.max_turns = int(data.get("max_turns", 12))
        self.context = data.get("context", {})


class AgenticInteractiveShell:
    """REPL for free agent-to-agent communication using AgenticTeamEngine."""

    def __init__(
        self,
        config_path: str | None = None,
        default_max_turns: int = 12,
        force_offline: bool = False,
    ):
        self.console = Console()
        self._prompt_project_path()
        self.engine = AgenticTeamEngine(config_path=config_path, force_offline=force_offline)
        self.history = AgenticConversationHistory()
        self.history.max_turns = max(1, int(default_max_turns))
        self.running = True
        self.session_dir = self._init_session_dir()
        self._setup_readline()
        self.commands = {
            "/help": self.cmd_help,
            "/exit": self.cmd_exit,
            "/quit": self.cmd_exit,
            "/clear": self.cmd_clear,
            "/history": self.cmd_history,
            "/agents": self.cmd_agents,
            "/team": self.cmd_team,
            "/maxturns": self.cmd_max_turns,
            "/followup": self.cmd_followup,
            "/save": self.cmd_save_session,
            "/load": self.cmd_load_session,
            "/reset": self.cmd_reset,
            "/info": self.cmd_info,
            "/reload": self.cmd_reload,
            "/validate": self.cmd_validate,
            "/project": self.cmd_project,
        }

    def _prompt_project_path(self) -> None:
        """Prompt user for a project path at startup.

        Sets the PROJECT_PATH environment variable if the user provides a valid
        directory. Accepts absolute or relative paths (relative paths are resolved
        to absolute automatically). If the user leaves the input empty or the env
        var / config already has a value, the prompt is skipped.
        Skipped entirely in non-interactive environments (no TTY, CI, tests).
        """
        existing = os.environ.get("PROJECT_PATH", "").strip()
        if existing:
            resolved = self._resolve_path(existing)
            if resolved and resolved.is_dir():
                self.console.print(
                    f"[dim]Using project path from environment:[/dim] [green]{resolved}[/green]"
                )
                os.environ["PROJECT_PATH"] = str(resolved)
                return
            self.console.print(
                f"[yellow]⚠ PROJECT_PATH env var is set but invalid: '{existing}'[/yellow]"
            )

        import sys

        if not sys.stdin.isatty():
            return

        self.console.print()
        self.console.print("[bold cyan]📁 Project Path Setup[/bold cyan]")
        self.console.print(
            "[dim]Point the agentic team at your project so agents gain full codebase context.\n"
            "Both absolute (/Users/you/project) and relative (../my-app) paths work.\n"
            "Press Enter to skip — agents will still work, just without project context.[/dim]"
        )

        max_attempts = 3
        for attempt in range(max_attempts):
            raw = Prompt.ask("[cyan]Project path[/cyan]", default="").strip()
            if not raw:
                self.console.print("[dim]No project path set — running in task-only mode.[/dim]\n")
                return

            resolved = self._resolve_path(raw)
            if resolved and resolved.is_dir():
                os.environ["PROJECT_PATH"] = str(resolved)
                self.console.print(f"[green]✓ Project registered:[/green] {resolved}\n")
                return

            display = str(resolved) if resolved else raw
            remaining = max_attempts - attempt - 1
            if remaining > 0:
                self.console.print(
                    f"[yellow]⚠ '{display}' is not a valid directory. "
                    f"{remaining} attempt(s) left, or press Enter to skip.[/yellow]"
                )
            else:
                self.console.print(
                    f"[yellow]⚠ '{display}' is not a valid directory — skipping.[/yellow]\n"
                )

    @staticmethod
    def _resolve_path(raw: str) -> Path | None:
        """Resolve a user-provided path string to an absolute Path.

        Handles tilde (~), relative paths, quoted strings, and trailing slashes.
        Returns None only if the path is completely unparseable.
        """
        cleaned = raw.strip().strip("'\"")
        if not cleaned:
            return None
        try:
            return Path(cleaned).expanduser().resolve()
        except (OSError, ValueError):
            return None

    def _init_session_dir(self) -> Path:
        session_dir = Path.home() / ".ai-orchestrator" / "agentic-sessions"
        session_dir.mkdir(parents=True, exist_ok=True)
        return session_dir

    MAX_HISTORY_LINES = 1000

    def _setup_readline(self):
        history_file = self.session_dir / "history.txt"
        try:
            if history_file.exists():
                # Truncate oversized history before loading.
                try:
                    if history_file.stat().st_size > 512 * 1024:
                        with open(history_file, "rb") as fh_r:
                            chunk = fh_r.read()[-self.MAX_HISTORY_LINES * 200 :]
                        lines = chunk.decode("utf-8", errors="replace").splitlines(keepends=True)
                        with open(history_file, "w", encoding="utf-8") as fh_w:
                            fh_w.writelines(lines[-self.MAX_HISTORY_LINES :])
                except Exception:
                    pass
                readline.read_history_file(str(history_file))
            readline.set_history_length(self.MAX_HISTORY_LINES)
            readline.parse_and_bind("tab: complete")
            readline.set_completer(self._completer)

            import atexit

            def _save():
                try:
                    readline.set_history_length(self.MAX_HISTORY_LINES)
                    readline.write_history_file(str(history_file))
                except Exception:
                    pass

            atexit.register(_save)
        except Exception:
            pass

    def _completer(self, text: str, state: int):
        options = [cmd for cmd in self.commands if cmd.startswith(text)]
        if state < len(options):
            return options[state]
        return None

    def _get_prompt(self) -> str:
        return (
            f"[bold cyan]agentic-team[/bold cyan] ([dim]max_turns={self.history.max_turns}[/dim])"
        )

    def _show_welcome(self):
        welcome = """
# Agentic Team Shell

Standalone REPL for the true agentic team engine.

- Team lead gates final response.
- Roles can hand off freely between each other.
- Use `/team` to inspect current role-to-model mappings.
- Local model adapters (Ollama/llama.cpp) return text output only in this REPL.
- Best use for local models: offline drafting, review, and fallback routing.
        """
        self.console.print(Panel(Markdown(welcome), border_style="cyan", title="Agentic Team"))
        self.cmd_agents("")
        self.cmd_team("")
        self.console.print()

    def _show_goodbye(self):
        self.console.print("\n[cyan]Exiting Agentic Team shell.[/cyan]")

    def start(self):
        """Start the interactive REPL loop."""
        self._show_welcome()
        while self.running:
            try:
                user_input = Prompt.ask(self._get_prompt()).strip()
                if not user_input:
                    continue
                if user_input.startswith("/"):
                    self._handle_command(user_input)
                    continue

                is_followup = self._should_follow_up(user_input)
                if is_followup is None:
                    continue
                self._handle_message(user_input, is_followup=is_followup)
            except KeyboardInterrupt:
                self.console.print("\n[yellow]Use /exit to exit[/yellow]")
            except EOFError:
                self.console.print("\n[yellow]Exiting...[/yellow]")
                break
            except Exception as exc:
                self.console.print(f"[red]Error: {exc}[/red]")
        self._show_goodbye()

    def _handle_command(self, raw: str):
        parts = raw.split(maxsplit=1)
        command = parts[0]
        args = parts[1] if len(parts) > 1 else ""
        handler = self.commands.get(command)
        if handler is None:
            self.console.print(f"[red]Unknown command: {command}[/red]")
            self.console.print("[yellow]Type /help for commands[/yellow]")
            return
        handler(args)

    def _should_follow_up(self, message: str) -> bool | None:
        if not self.history.context.get("last_task"):
            return False

        followup_indicators = [
            "add",
            "also",
            "now",
            "then",
            "next",
            "improve",
            "fix",
            "change",
            "update",
            "please",
            "can you",
        ]
        lowered = message.lower()
        if len(message.split()) < 10 and any(word in lowered for word in followup_indicators):
            self.console.print("[dim]Detected follow-up message[/dim]")
            return True

        choice = Prompt.ask(
            "[cyan]Continue previous task (c), start new (n), cancel (x)?[/cyan]",
            choices=["c", "n", "x"],
            default="c",
        )
        if choice == "c":
            return True
        if choice == "n":
            return False
        return None

    def _handle_message(self, message: str, is_followup: bool):
        self.history.add_message("user", message, {"is_followup": is_followup})

        task_input = message
        if is_followup and self.history.context.get("last_task"):
            task_input = (
                f"Previous task: {self.history.context.get('last_task')}\n"
                f"Previous result: {self.history.context.get('last_output', '')}\n\n"
                f"Follow-up: {message}"
            )

        turns: list[dict[str, Any]] = []

        def turn_callback(step: dict[str, Any]) -> None:
            turns.append(step)
            route = f"{step.get('from_role')} -> {step.get('to_role')}"
            agent_route = (
                f"{step.get('from_agent', step.get('agent'))} -> {step.get('to_agent', '')}"
            )
            action = step.get("action", "message")
            self.console.print(
                f"[dim]turn {step.get('turn')}: {route} [{action}] ({agent_route})[/dim]"
            )

        with self.console.status("[bold cyan]Running agentic team...[/bold cyan]"):
            results = self.engine.execute_task(
                task=task_input,
                max_turns=self.history.max_turns,
                turn_callback=turn_callback,
            )

        self._display_results(results, turns)

        final_output = results.get("final_output", "")
        self.history.add_message(
            "assistant",
            final_output,
            {"success": results.get("success"), "turns": len(turns)},
        )
        self.history.context["last_task"] = message
        self.history.context["last_output"] = final_output
        self.history.context["last_success"] = bool(results.get("success"))
        self.history.context["last_turns"] = turns

    def _display_results(self, results: dict[str, Any], turns: list[dict[str, Any]]):
        self.console.print()
        table = Table(title="Team Communication")
        table.add_column("Turn", style="cyan")
        table.add_column("From", style="white")
        table.add_column("To", style="white")
        table.add_column("Action", style="yellow")
        table.add_column("Model Route", style="magenta")

        for turn in turns:
            table.add_row(
                str(turn.get("turn", "")),
                str(turn.get("from_role", "")),
                str(turn.get("to_role", "")),
                str(turn.get("action", "")),
                f"{turn.get('from_agent', turn.get('agent', ''))} -> {turn.get('to_agent', '')}",
            )
        self.console.print(table)

        final_output = str(results.get("final_output", ""))
        self.console.print(
            Panel(final_output or "(empty output)", border_style="green", title="Lead Final Output")
        )
        if results.get("success"):
            self.console.print("[bold green]Task completed successfully[/bold green]\n")
        else:
            self.console.print(
                "[bold yellow]Task completed without lead finalization[/bold yellow]\n"
            )

    def cmd_help(self, _args: str):
        """Show command reference for the agentic shell."""
        table = Table(title="Agentic Team Commands")
        table.add_column("Command", style="cyan")
        table.add_column("Description", style="white")
        table.add_row("/help", "Show command help")
        table.add_row("/agents", "List available mapped agents")
        table.add_row("/team", "Show current team role mappings")
        table.add_row("/maxturns <n>", "Set max communication turns")
        table.add_row("/followup <message>", "Force follow-up on previous task")
        table.add_row("/history", "Show message history")
        table.add_row("/save [file]", "Save session")
        table.add_row("/load <file>", "Load session")
        table.add_row("/reset", "Clear history/context")
        table.add_row("/reload", "Reload config and adapters from config file")
        table.add_row("/validate", "Validate team role mappings against available agents")
        table.add_row("/project [path]", "Show or set active project path")
        table.add_row("/clear", "Clear terminal")
        table.add_row("/info", "Show shell summary")
        table.add_row("/exit", "Exit shell")
        self.console.print(table)
        self.console.print(
            "\n[dim]Local model adapters in agentic-team are advisory (text output). "
            "Direct file edits come from CLI-backed agents.[/dim]"
        )

    def cmd_exit(self, _args: str):
        """Exit the interactive shell loop."""
        self.running = False

    def cmd_clear(self, _args: str):
        """Clear terminal output."""
        os.system("clear" if os.name != "nt" else "cls")

    def cmd_agents(self, _args: str):
        """Display currently available executable agents."""
        available = self.engine.get_available_agents()
        if not available:
            self.console.print("[yellow]No available agents[/yellow]")
            return
        self.console.print(f"[green]Available agents:[/green] {', '.join(available)}")

    def cmd_team(self, _args: str):
        """Display current role-to-agent mappings."""
        team = self.engine.get_team_config()
        table = Table(title="Agentic Team Mapping")
        table.add_column("Role", style="cyan")
        table.add_column("Title", style="white")
        table.add_column("Agent", style="green")
        table.add_column("Responsibilities", style="yellow")
        for role, spec in team.get("roles", {}).items():
            table.add_row(
                role,
                str(spec.get("title", "")),
                str(spec.get("agent", "")),
                str(spec.get("responsibilities", "")),
            )
        self.console.print(table)
        self.console.print(
            f"[dim]Lead role: {team.get('lead_role')} | Max turns: {self.history.max_turns}[/dim]"
        )

    def cmd_max_turns(self, args: str):
        """Get or set max routing turns per task."""
        if not args:
            self.console.print(f"[yellow]Current max turns: {self.history.max_turns}[/yellow]")
            return
        try:
            value = max(1, int(args.strip()))
        except ValueError:
            self.console.print("[red]Usage: /maxturns <positive-integer>[/red]")
            return
        self.history.max_turns = value
        self.console.print(f"[green]Max turns set to {value}[/green]")

    def cmd_followup(self, args: str):
        """Run a message as an explicit follow-up to the previous task."""
        if not args.strip():
            self.console.print("[yellow]Usage: /followup <message>[/yellow]")
            return
        if not self.history.context.get("last_task"):
            self.console.print("[yellow]No previous task found[/yellow]")
            return
        self._handle_message(args.strip(), is_followup=True)

    def cmd_history(self, _args: str):
        """Print compact conversation history."""
        if not self.history.messages:
            self.console.print("[yellow]No messages yet[/yellow]")
            return
        for idx, msg in enumerate(self.history.messages, start=1):
            content = str(msg.get("content", ""))
            if len(content) > 160:
                content = content[:160] + "..."
            role_style = "cyan" if msg.get("role") == "user" else "green"
            self.console.print(
                f"{idx}. [{role_style}]{msg.get('role')}[/{role_style}]"
                f" ({msg.get('timestamp', '')})"
            )
            self.console.print(f"   {content}")

    def cmd_save_session(self, args: str):
        """Save current shell state to disk."""
        filename = (
            args.strip()
            if args.strip()
            else f"agentic_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        )
        filepath = self.session_dir / filename
        self.history.save(str(filepath))
        self.console.print(f"[green]Session saved:[/green] {filepath}")

    def cmd_load_session(self, args: str):
        """Load a previously saved shell session."""
        filename = args.strip()
        if not filename:
            sessions = sorted(self.session_dir.glob("*.json"))
            if not sessions:
                self.console.print("[yellow]No saved sessions found[/yellow]")
                return
            self.console.print("[bold]Available sessions:[/bold]")
            for item in sessions:
                self.console.print(f"- {item.name}")
            self.console.print("[yellow]Usage: /load <filename>[/yellow]")
            return
        filepath = self.session_dir / filename
        if not filepath.exists():
            self.console.print(f"[red]Session not found: {filename}[/red]")
            return
        self.history.load(str(filepath))
        self.console.print(f"[green]Session loaded:[/green] {filepath}")

    def cmd_reset(self, _args: str):
        """Clear history/context after confirmation."""
        if Confirm.ask("Reset conversation history?", default=False):
            self.history.clear()
            self.console.print("[green]Conversation reset[/green]")

    def cmd_info(self, _args: str):
        """Show shell/runtime summary information."""
        available = self.engine.get_available_agents()
        team = self.engine.get_team_config()
        validation = self.engine.validate_team_bindings()
        info = (
            f"Available agents: {len(available)}\n"
            f"Lead role: {team.get('lead_role')}\n"
            f"Configured roles: {len(team.get('roles', {}))}\n"
            f"Max turns: {self.history.max_turns}\n"
            f"Validation: {'ok' if validation.get('valid') else 'invalid'}\n"
            f"Messages: {len(self.history.messages)}\n"
            f"Session dir: {self.session_dir}\n"
            "Local models: text output only (best for offline draft/review/fallback)"
        )
        self.console.print(Panel(info, title="Agentic Team Info", border_style="cyan"))

    def cmd_reload(self, _args: str):
        """Reload engine configuration and refresh adapters."""
        try:
            self.engine.reload()
            self.console.print("[green]Engine reloaded from config[/green]")
            self.cmd_agents("")
            self.cmd_validate("")
        except Exception as exc:
            self.console.print(f"[red]Reload failed: {exc}[/red]")

    def cmd_validate(self, _args: str):
        """Validate current team mappings against available agents."""
        payload = self.engine.validate_team_bindings()
        if payload.get("valid"):
            self.console.print("[green]Team mappings are valid[/green]")
            return
        reason = payload.get("reason") or "unknown"
        self.console.print(f"[red]Team mappings invalid ({reason})[/red]")
        missing = payload.get("missing_roles", [])
        if missing:
            table = Table(title="Missing / Unavailable Role Mappings")
            table.add_column("Role", style="cyan")
            table.add_column("Agent", style="yellow")
            for item in missing:
                table.add_row(str(item.get("role", "")), str(item.get("agent", "")))
            self.console.print(table)

    def cmd_project(self, args: str):
        """Show or change the active project path."""
        current = os.environ.get("PROJECT_PATH", "").strip()
        if not args:
            if current and Path(current).is_dir():
                self.console.print(f"[green]Active project:[/green] {current}")
            else:
                self.console.print("[yellow]No project path set.[/yellow]")
            self.console.print(
                "[dim]Usage: /project /path/to/your/project  (or /project clear)[/dim]"
            )
            return

        if args.strip().lower() == "clear":
            os.environ.pop("PROJECT_PATH", None)
            self.console.print("[yellow]Project path cleared — running in task-only mode.[/yellow]")
            return

        resolved = self._resolve_path(args)
        if not resolved or not resolved.is_dir():
            display = str(resolved) if resolved else args.strip()
            self.console.print(f"[red]'{display}' is not a valid directory.[/red]")
            return

        os.environ["PROJECT_PATH"] = str(resolved)
        self.console.print(f"[green]✓ Project registered:[/green] {resolved}")
        self.console.print("[dim]Agents will use this project for context on future tasks.[/dim]")
