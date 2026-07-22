"""
Interactive shell for AI Orchestrator.

Provides a REPL-style interface for multi-round conversations with AI agents,
similar to Claude Code and Codex CLIs.
"""

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
from typing import Any, Dict, List, Optional

from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.prompt import Confirm, Prompt
from rich.table import Table

from orchestrator.core.engine import Orchestrator


class ConversationHistory:
    """Manages conversation history and context."""

    def __init__(self):
        self.messages: List[Dict[str, Any]] = []
        self.current_agent: Optional[str] = None
        self.workflow: str = "default"
        self.context: Dict[str, Any] = {}

    def add_message(self, role: str, content: str, metadata: Optional[Dict] = None):
        """Add a message to conversation history."""
        message = {
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat(),
            "metadata": metadata or {},
        }
        self.messages.append(message)

    def get_context(self) -> Dict[str, Any]:
        """Get current conversation context."""
        return {
            "history": self.messages[-10:],  # Last 10 messages for context
            "current_agent": self.current_agent,
            "workflow": self.workflow,
            "context": self.context,
        }

    def clear(self):
        """Clear conversation history."""
        self.messages.clear()
        self.context.clear()

    def save(self, filepath: str):
        """Save conversation history to file."""
        data = {
            "messages": self.messages,
            "current_agent": self.current_agent,
            "workflow": self.workflow,
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
        """Load conversation history from file."""
        try:
            with open(filepath, encoding="utf-8") as f:
                data = json.load(f)
        except (OSError, json.JSONDecodeError) as e:
            raise OSError(f"Failed to load session: {e}") from e
        if not isinstance(data, dict):
            raise OSError("Invalid session file format")
        self.messages = data.get("messages", [])
        self.current_agent = data.get("current_agent")
        self.workflow = data.get("workflow", "default")
        self.context = data.get("context", {})


class InteractiveShell:
    """Interactive shell for AI Orchestrator."""

    def __init__(self, config_path: Optional[str] = None):
        self.console = Console()
        self._prompt_project_path()
        self.orchestrator = Orchestrator(config_path)
        self.history = ConversationHistory()
        self.running = True

        # Initialize session directory with robust error handling
        self.session_dir = self._init_session_dir()

        # Setup readline for better UX
        self._setup_readline()

        # Shell commands
        self.commands = {
            "/help": self.cmd_help,
            "/exit": self.cmd_exit,
            "/quit": self.cmd_exit,
            "/clear": self.cmd_clear,
            "/history": self.cmd_history,
            "/agents": self.cmd_agents,
            "/workflows": self.cmd_workflows,
            "/switch": self.cmd_switch_agent,
            "/workflow": self.cmd_set_workflow,
            "/save": self.cmd_save_session,
            "/load": self.cmd_load_session,
            "/context": self.cmd_show_context,
            "/reset": self.cmd_reset,
            "/info": self.cmd_info,
            "/followup": self.cmd_followup,
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
            "[dim]Point the orchestrator at your project so agents gain full codebase context.\n"
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
    def _resolve_path(raw: str) -> Optional[Path]:
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
        """Initialize session directory with robust error handling."""
        try:
            session_dir = Path.home() / ".ai-orchestrator" / "sessions"

            # Check if path exists and handle conflicts
            if session_dir.exists():
                if not session_dir.is_dir():
                    # Path exists but is a file, not a directory
                    # Backup the file and create directory
                    backup = session_dir.parent / f"{session_dir.name}.backup"
                    session_dir.rename(backup)
                    self.console.print(f"[yellow]Warning: Moved file to {backup}[/yellow]")
                    session_dir.mkdir(parents=True, exist_ok=True)
            else:
                # Create directory
                session_dir.mkdir(parents=True, exist_ok=True)

            # Verify we can write to the directory
            test_file = session_dir / ".test"
            try:
                test_file.touch(exist_ok=True)
                test_file.unlink()
            except (OSError, PermissionError) as e:
                self.console.print(f"[red]Warning: Cannot write to {session_dir}: {e}[/red]")
                # Fallback to temp directory
                import tempfile

                session_dir = Path(tempfile.gettempdir()) / "ai-orchestrator-sessions"
                session_dir.mkdir(parents=True, exist_ok=True)
                self.console.print(f"[yellow]Using temporary directory: {session_dir}[/yellow]")

            return session_dir

        except Exception as e:
            self.console.print(f"[red]Error initializing session directory: {e}[/red]")
            # Ultimate fallback to current directory
            fallback = Path.cwd() / ".sessions"
            fallback.mkdir(exist_ok=True)
            return fallback

    # Maximum number of history entries to keep.
    MAX_HISTORY_LINES = 1000

    def _setup_readline(self):
        """Setup readline for command history and completion with robust error handling."""
        try:
            history_file = self.session_dir / "history.txt"

            try:
                if history_file.exists() and not history_file.is_file():
                    backup = self.session_dir / "history.txt.invalid"
                    history_file.rename(backup)

                # Truncate oversized history file BEFORE loading to avoid
                # multi-GB reads that freeze the shell on startup.
                self._truncate_history_file(history_file, self.MAX_HISTORY_LINES)

                if history_file.exists():
                    readline.read_history_file(str(history_file))
            except (FileNotFoundError, PermissionError, OSError):
                pass  # History is non-critical

            readline.set_history_length(self.MAX_HISTORY_LINES)

            if history_file.parent.exists() and os.access(str(history_file.parent), os.W_OK):
                import atexit

                atexit.register(self._save_history_safe, str(history_file))

            try:
                readline.parse_and_bind("tab: complete")
                readline.set_completer(self._completer)
            except Exception:
                pass

            try:
                readline.parse_and_bind("set editing-mode emacs")
            except Exception:
                pass

        except Exception:
            pass  # Readline setup is entirely non-critical

    @staticmethod
    def _truncate_history_file(path: Path, max_lines: int) -> None:
        """Keep only the last *max_lines* of a history file on disk."""
        try:
            if not path.exists():
                return
            size = path.stat().st_size
            if size == 0:
                return
            # Only bother if file is suspiciously large (>512 KB).
            if size < 512 * 1024:
                return
            # Read the tail efficiently.
            with open(path, "rb") as fh:
                # Seek backwards from end to find enough newlines.
                chunk = min(size, max_lines * 200)  # generous estimate
                fh.seek(max(0, size - chunk))
                tail = fh.read().decode("utf-8", errors="replace")
            lines = tail.splitlines(keepends=True)[-max_lines:]
            with open(path, "w", encoding="utf-8", newline="") as fh:
                fh.writelines(lines)
        except Exception:
            pass  # Best-effort truncation

    def _save_history_safe(self, filename: str):
        """Safely save history file, capped to MAX_HISTORY_LINES."""
        try:
            readline.set_history_length(self.MAX_HISTORY_LINES)
            readline.write_history_file(filename)
        except Exception:
            pass

    def _completer(self, text: str, state: int):
        """Auto-completion for commands."""
        options = [cmd for cmd in self.commands if cmd.startswith(text)]

        # Also complete agent names
        if text.startswith("/switch "):
            agent_prefix = text.split()[-1] if len(text.split()) > 1 else ""
            agents = self.orchestrator.get_available_agents()
            options.extend(
                [f"/switch {agent}" for agent in agents if agent.startswith(agent_prefix)]
            )

        if state < len(options):
            return options[state]
        return None

    def start(self):
        """Start the interactive shell."""
        self._show_welcome()

        while self.running:
            try:
                # Get user input
                prompt_text = self._get_prompt()
                user_input = Prompt.ask(prompt_text).strip()

                if not user_input:
                    continue

                # Check if it's a command
                if user_input.startswith("/"):
                    self._handle_command(user_input)
                else:
                    # Regular message - check if this should be a follow-up
                    is_followup = self._should_follow_up(user_input)
                    if is_followup is not None:  # None means cancelled
                        self._handle_message(user_input, is_followup=is_followup)

            except KeyboardInterrupt:
                self.console.print("\n[yellow]Use /exit or /quit to exit[/yellow]")
                continue
            except EOFError:
                self.console.print("\n[yellow]Exiting...[/yellow]")
                break
            except Exception as e:
                self.console.print(f"[red]Error: {e}[/red]")
                if os.getenv("DEBUG"):
                    self.console.print_exception()

        self._show_goodbye()

    def _get_prompt(self) -> str:
        """Get the prompt string."""
        agent = self.history.current_agent or "orchestrator"
        workflow = self.history.workflow
        return f"[bold cyan]{agent}[/bold cyan] ([dim]{workflow}[/dim])"

    def _show_welcome(self):
        """Show welcome message."""
        welcome = """
# AI Orchestrator Interactive Shell

Welcome to the AI Orchestrator interactive shell!

This shell allows you to have multi-round conversations with AI coding assistants,
collaborate on tasks, and iterate on implementations.

**Available Commands:**
- `/help` - Show all commands
- `/followup <msg>` - Continue working on the previous task
- `/agents` - List available agents
- `/workflows` - List available workflows
- `/switch <agent>` - Switch to a specific agent
- `/project [path]` - Show or set the active project path
- `/exit` or `/quit` - Exit the shell

**Getting Started:**
Just type your request and press Enter. The system will coordinate the appropriate
AI agents to help you accomplish your task. After completion, use `/followup` to
continue iterating on the same task with additional requirements.

**Local model note:**
Ollama/llama.cpp adapters produce text responses only in this shell. They are best
for local drafts, review, and fallback; direct file edits come from CLI-backed agents.

Type `/help` for more information.
        """
        self.console.print(Panel(Markdown(welcome), border_style="cyan", title="Welcome"))

        # Show available agents
        agents = self.orchestrator.get_available_agents()
        if agents:
            self.console.print(f"\n[green]Available agents:[/green] {', '.join(agents)}")
        else:
            self.console.print("\n[yellow]⚠ No agents currently available[/yellow]")

        self.console.print()

    def _show_goodbye(self):
        """Show goodbye message."""
        self.console.print("\n[cyan]Thank you for using AI Orchestrator![/cyan]")
        if self.history.messages:
            save = Confirm.ask("Would you like to save this session?", default=False)
            if save:
                filename = f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                filepath = self.session_dir / filename
                self.history.save(str(filepath))
                self.console.print(f"[green]Session saved to:[/green] {filepath}")

    def _handle_command(self, command_str: str):
        """Handle shell commands."""
        parts = command_str.split(maxsplit=1)
        command = parts[0]
        args = parts[1] if len(parts) > 1 else ""

        if command in self.commands:
            self.commands[command](args)
        else:
            self.console.print(f"[red]Unknown command: {command}[/red]")
            self.console.print("[yellow]Type /help for available commands[/yellow]")

    def _should_follow_up(self, message: str) -> bool:
        """Determine if message should be treated as a follow-up."""
        # If we have a previous task, ask user
        if self.history.context.get("last_task"):
            # Check for obvious follow-up indicators
            followup_indicators = [
                "add",
                "also",
                "now",
                "then",
                "next",
                "additionally",
                "improve",
                "fix",
                "change",
                "update",
                "modify",
                "make it",
                "can you",
                "please",
                "try",
            ]

            message_lower = message.lower()
            has_indicator = any(word in message_lower for word in followup_indicators)

            # Auto follow-up if message is short and has indicators
            if len(message.split()) < 10 and has_indicator:
                self.console.print("[dim]💡 Detected as follow-up to previous task[/dim]")
                return True

            # Otherwise ask user
            self.console.print("\n[yellow]Continue previous task?[/yellow]")
            self.console.print(f"[dim]Previous: {self.history.context['last_task'][:60]}...[/dim]")

            response = Prompt.ask(
                "[cyan]Continue (c), New task (n), or Cancel (x)?[/cyan]",
                choices=["c", "n", "x"],
                default="c",
            )

            if response == "c":
                self.console.print("[dim]✓ Continuing previous task with context[/dim]\n")
                return True
            if response == "x":
                self.console.print("[yellow]Cancelled[/yellow]")
                return None  # Signal to skip

            self.console.print("[dim]✓ Starting new task[/dim]\n")
            return False

        return False

    def _handle_message(self, message: str, is_followup: bool = False):
        """Handle user message and execute with orchestrator."""
        # Add to history
        self.history.add_message("user", message, {"is_followup": is_followup})

        # Get context from history - include previous results for follow-ups
        _ = self.history.get_context()  # noqa: F841

        # For follow-ups, add previous task context
        if is_followup and self.history.context.get("last_task"):
            previous_task = self.history.context["last_task"]
            previous_output = self.history.context.get("last_output", "")
            message = (
                f"Previous task: {previous_task}\n"
                f"Previous result: {previous_output}\n\n"
                f"Follow-up: {message}"
            )

        # Show thinking indicator
        with self.console.status("[bold cyan]Orchestrating agents...[/bold cyan]"):
            try:
                # Execute with orchestrator
                results = self.orchestrator.execute_task(
                    task=message, workflow_name=self.history.workflow, max_iterations=3
                )

                # Display results
                self._display_results(results)

                # Add to history
                final_output = results.get("final_output", "")
                self.history.add_message(
                    "assistant",
                    final_output,
                    {
                        "workflow": results.get("workflow"),
                        "iterations": len(results.get("iterations", [])),
                    },
                )

                # Update context with results for future follow-ups
                self.history.context["last_task"] = message
                self.history.context["last_output"] = final_output
                self.history.context["last_success"] = results.get("success", False)

                # Store files from all iterations
                all_files = []
                if results.get("iterations"):
                    for iteration in results["iterations"]:
                        for step in iteration.get("steps", []):
                            if step.get("files_modified"):
                                all_files.extend(step["files_modified"])

                if all_files:
                    self.history.context["files"] = all_files
                    self.history.context["workspace"] = "./workspace"

            except Exception as e:
                self.console.print(f"[red]Error executing task: {e}[/red]")
                if os.getenv("DEBUG"):
                    self.console.print_exception()

    def _display_results(self, results: Dict[str, Any]):  # pylint: disable=too-many-branches
        """Display execution results with enhanced formatting."""
        self.console.print()

        # Show iteration summary
        iterations = results.get("iterations", [])
        for i, iteration in enumerate(iterations, 1):
            self.console.print(f"[bold]Iteration {i}:[/bold]")

            for step in iteration.get("steps", []):
                agent = step.get("agent")
                task = step.get("task")
                success = step.get("success", False)

                status = "✓" if success else "✗"
                color = "green" if success else "red"

                self.console.print(f"  [{color}]{status}[/{color}] {agent} - {task}")

                # Show suggestions count if available
                suggestions = step.get("suggestions", [])
                if suggestions:
                    self.console.print(f"     [dim]Suggestions: {len(suggestions)}[/dim]")

            self.console.print()

        # Collect all generated files
        all_files = []
        for iteration in iterations:
            for step in iteration.get("steps", []):
                if step.get("files_modified"):
                    all_files.extend(step["files_modified"])

        # Show generated files
        if all_files:
            self.console.print("[bold cyan]📁 Generated Files:[/bold cyan]")
            for file in all_files:
                self.console.print(f"  📄 [green]{file}[/green]")
            self.console.print("\n[dim]Workspace: ./workspace[/dim]\n")

        # Show final output
        final_output = results.get("final_output", "")
        if final_output:
            # Full output - no truncation, but offer paging for very long output
            if len(final_output) > 2000:
                show_full = Confirm.ask(
                    f"Output is {len(final_output)} characters. Show full output?", default=False
                )
                if not show_full:
                    final_output = (
                        final_output[:2000] + "\n\n[dim]... (use /context to see full output)[/dim]"
                    )

            self.console.print(
                Panel(
                    final_output, title="[bold cyan]Final Output[/bold cyan]", border_style="cyan"
                )
            )

        # Show success status
        if results.get("success"):
            self.console.print("[bold green]✓ Task completed successfully![/bold green]")
            self.console.print(
                "[dim]Type your next task, or use /followup to continue this task[/dim]\n"
            )
        else:
            self.console.print("[bold yellow]⚠ Task completed with issues[/bold yellow]\n")

    # Command implementations

    def cmd_help(self, args: str):
        """Show help information."""
        table = Table(title="Available Commands", show_header=True)
        table.add_column("Command", style="cyan")
        table.add_column("Description", style="white")

        table.add_row("/help", "Show this help message")
        table.add_row("/exit, /quit", "Exit the interactive shell")
        table.add_row("/clear", "Clear the screen")
        table.add_row(
            "/followup <msg>", "Continue working on the previous task with new instructions"
        )
        table.add_row("/history", "Show conversation history")
        table.add_row("/agents", "List available agents")
        table.add_row("/workflows", "List available workflows")
        table.add_row("/switch <agent>", "Switch to a specific agent for direct communication")
        table.add_row("/workflow <name>", "Change the workflow")
        table.add_row("/save [filename]", "Save current session")
        table.add_row("/load <filename>", "Load a previous session")
        table.add_row("/context", "Show current context")
        table.add_row("/reset", "Reset conversation and context")
        table.add_row("/info", "Show system information")
        table.add_row("/project [path]", "Show or set active project path")

        self.console.print(table)
        self.console.print(
            "\n[dim]Local model adapters (Ollama/llama.cpp) return text output only. "
            "Use them for offline drafting/review/fallback; CLI agents handle direct file edits.[/dim]"
        )

    def cmd_exit(self, args: str):
        """Exit the shell."""
        self.running = False

    def cmd_clear(self, args: str):
        """Clear the screen."""
        os.system("clear" if os.name != "nt" else "cls")  # noqa: S605 S607

    def cmd_history(self, args: str):
        """Show conversation history."""
        if not self.history.messages:
            self.console.print("[yellow]No conversation history[/yellow]")
            return

        self.console.print("\n[bold]Conversation History:[/bold]\n")

        for i, msg in enumerate(self.history.messages, 1):
            role = msg["role"]
            content = msg["content"]
            timestamp = msg.get("timestamp", "unknown")

            # Truncate long messages
            if len(content) > 200:
                content = content[:200] + "..."

            color = "cyan" if role == "user" else "green"
            self.console.print(f"{i}. [{color}]{role}[/{color}] ({timestamp})")
            self.console.print(f"   {content}\n")

    def cmd_agents(self, args: str):
        """List available agents."""
        agents = self.orchestrator.get_available_agents()

        if not agents:
            self.console.print("[yellow]No agents available[/yellow]")
            return

        table = Table(title="Available Agents")
        table.add_column("Agent", style="cyan")
        table.add_column("Status", style="green")

        for agent in agents:
            table.add_row(agent, "✓ Available")

        self.console.print(table)

    def cmd_workflows(self, args: str):
        """List available workflows."""
        workflows = self.orchestrator.get_workflows()

        table = Table(title="Available Workflows")
        table.add_column("Workflow", style="cyan")
        table.add_column("Current", style="green")

        for workflow in workflows:
            current = "✓" if workflow == self.history.workflow else ""
            table.add_row(workflow, current)

        self.console.print(table)

    def cmd_switch_agent(self, args: str):
        """Switch to a specific agent."""
        if not args:
            self.console.print("[yellow]Usage: /switch <agent_name>[/yellow]")
            self.cmd_agents("")
            return

        agent = args.strip()
        agents = self.orchestrator.get_available_agents()

        if agent not in agents:
            self.console.print(f"[red]Agent '{agent}' not available[/red]")
            self.cmd_agents("")
            return

        self.history.current_agent = agent
        self.console.print(f"[green]Switched to agent: {agent}[/green]")

    def cmd_set_workflow(self, args: str):
        """Change the workflow."""
        if not args:
            self.console.print("[yellow]Usage: /workflow <workflow_name>[/yellow]")
            self.cmd_workflows("")
            return

        workflow = args.strip()
        workflows = self.orchestrator.get_workflows()

        if workflow not in workflows:
            self.console.print(f"[red]Workflow '{workflow}' not found[/red]")
            self.cmd_workflows("")
            return

        self.history.workflow = workflow
        self.console.print(f"[green]Switched to workflow: {workflow}[/green]")

    def cmd_save_session(self, args: str):
        """Save current session."""
        if args:
            filename = args.strip()
        else:
            filename = f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

        filepath = self.session_dir / filename
        self.history.save(str(filepath))
        self.console.print(f"[green]Session saved to:[/green] {filepath}")

    def cmd_load_session(self, args: str):
        """Load a previous session."""
        if not args:
            # List available sessions
            sessions = list(self.session_dir.glob("*.json"))
            if not sessions:
                self.console.print("[yellow]No saved sessions found[/yellow]")
                return

            self.console.print("[bold]Available sessions:[/bold]")
            for i, session in enumerate(sessions, 1):
                self.console.print(f"{i}. {session.name}")

            self.console.print("\n[yellow]Usage: /load <filename>[/yellow]")
            return

        filename = args.strip()
        filepath = self.session_dir / filename

        if not filepath.exists():
            self.console.print(f"[red]Session file not found: {filename}[/red]")
            return

        self.history.load(str(filepath))
        self.console.print(f"[green]Session loaded from:[/green] {filepath}")
        self.console.print(f"[green]Loaded {len(self.history.messages)} messages[/green]")

    def cmd_show_context(self, args: str):
        """Show current context."""
        context = self.history.get_context()

        self.console.print("\n[bold]Current Context:[/bold]")
        self.console.print(f"Agent: {context['current_agent'] or 'orchestrator'}")
        self.console.print(f"Workflow: {context['workflow']}")
        self.console.print(f"Messages in history: {len(self.history.messages)}")

        if context["context"]:
            self.console.print("\n[bold]Context Data:[/bold]")
            for key, value in context["context"].items():
                if isinstance(value, list):
                    self.console.print(f"  {key}: {len(value)} items")
                else:
                    self.console.print(f"  {key}: {value}")

    def cmd_reset(self, args: str):
        """Reset conversation and context."""
        confirm = Confirm.ask("Are you sure you want to reset the conversation?", default=False)
        if confirm:
            self.history.clear()
            self.history.current_agent = None
            self.history.workflow = "default"
            self.console.print("[green]Conversation and context reset[/green]")
        else:
            self.console.print("[yellow]Reset cancelled[/yellow]")

    def cmd_info(self, args: str):
        """Show system information."""
        agents = self.orchestrator.get_available_agents()
        workflows = self.orchestrator.get_workflows()

        info = f"""
[bold cyan]AI Orchestrator Information[/bold cyan]

[bold]Available Agents:[/bold] {len(agents)}
{', '.join(agents) if agents else 'None'}

[bold]Available Workflows:[/bold] {len(workflows)}
{', '.join(workflows)}

[bold]Current Session:[/bold]
- Agent: {self.history.current_agent or 'orchestrator'}
- Workflow: {self.history.workflow}
- Messages: {len(self.history.messages)}

[bold]Session Directory:[/bold]
{self.session_dir}

[bold]Local Model Behavior:[/bold]
- Local adapters (Ollama/llama.cpp): prompt -> HTTP response text (no direct file writes)
- CLI adapters (Codex/Gemini/Claude/Copilot): can modify workspace files when supported
        """

        self.console.print(Panel(info.strip(), border_style="cyan"))

    def cmd_followup(self, args: str):
        """Continue working on the previous task."""
        if not self.history.context.get("last_task"):
            self.console.print(
                "[yellow]No previous task to follow up on. Start a new task first.[/yellow]"
            )
            return

        if not args:
            self.console.print("[yellow]Please provide instructions for the follow-up.[/yellow]")
            self.console.print("[dim]Example: /followup add error handling[/dim]")
            return

        # Show context
        last_task = self.history.context.get("last_task", "")
        files = self.history.context.get("files", [])

        self.console.print(f"\n[bold cyan]Following up on:[/bold cyan] {last_task[:100]}...")
        if files:
            files_str = ", ".join(files[:3])
            suffix = "..." if len(files) > 3 else ""
            self.console.print(f"[dim]Files in context: {files_str}{suffix}[/dim]\n")

        # Handle as a follow-up message
        self._handle_message(args, is_followup=True)

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
