"""Enhanced CLI communication utilities for robust agent interaction."""

import logging
import os
import shlex
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


class CLICommunicator:
    """Robust CLI communication handler that supports multiple interaction patterns.

    This class handles:
    - Non-interactive command execution
    - File-based input/output (for CLIs that prefer files)
    - Streaming output capture
    - Proper error handling and retries
    """

    def __init__(self, command: str, logger: Optional[logging.Logger] = None):
        """Initializes the CLI communicator."""
        self.command = command
        parsed_command = shlex.split(command) if isinstance(command, str) else []
        self.command_parts = parsed_command if parsed_command else [str(command)]
        self.command_name = Path(self.command_parts[0]).name if self.command_parts else ""
        self.logger = logger or logging.getLogger(__name__)
        self.temp_dir = tempfile.mkdtemp(prefix="ai-orchestrator-")

    def execute_with_prompt(
        self,
        prompt: str,
        method: str = "stdin",
        timeout: int = 3600,
        working_dir: Optional[str] = None,
    ) -> Tuple[bool, str, str]:
        """Execute CLI command with a prompt using the specified method.

        Args:
            prompt: The prompt to send to the CLI
            method: Communication method ('stdin', 'file', 'arg', 'heredoc')
            timeout: Timeout in seconds
            working_dir: Working directory for execution

        Returns:
            Tuple of (success, stdout, stderr)
        """
        valid_methods = {"stdin", "file", "arg", "heredoc"}
        if method not in valid_methods:
            self.logger.warning("Unknown method '%s', falling back to 'arg'", method)
            method = "arg"

        if method == "stdin":
            return self._execute_stdin(prompt, timeout, working_dir)
        if method == "file":
            return self._execute_file_based(prompt, timeout, working_dir)
        if method == "arg":
            return self._execute_argument(prompt, timeout, working_dir)
        return self._execute_heredoc(prompt, timeout, working_dir)

    def _execute_stdin(
        self, prompt: str, timeout: int, working_dir: Optional[str]
    ) -> Tuple[bool, str, str]:
        """Execute by passing prompt via stdin with TTY support using script command."""
        try:
            return self._run_script_command(prompt, timeout, working_dir)
        except Exception as script_error:
            self.logger.debug(
                "Script method failed, falling back to argument method: %s", script_error
            )
            return self._execute_argument(prompt, timeout, working_dir)

    def _run_script_command(
        self, prompt: str, timeout: int, working_dir: Optional[str]
    ) -> Tuple[bool, str, str]:
        """Run the script command with a prompt."""
        temp_file_path, input_file_path = None, None
        try:
            with tempfile.NamedTemporaryFile(mode="w+", delete=False, suffix=".txt") as temp_file:
                temp_file_path = temp_file.name
            with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt") as input_file:
                input_file_path = input_file.name
                input_file.write(prompt)

            script_cmd = (
                f"cat {shlex.quote(input_file_path)} | "
                f"script -q {shlex.quote(temp_file_path)} {shlex.quote(self.command)}"
            )
            process = subprocess.Popen(  # pylint: disable=consider-using-with
                ["bash", "-c", script_cmd],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                cwd=working_dir,
            )
            stdout, stderr = process.communicate(timeout=timeout)

            with open(temp_file_path, encoding="utf-8") as f:
                output_content = f.read()

            return process.returncode == 0, output_content or stdout, stderr
        finally:
            for path in (temp_file_path, input_file_path):
                if path:
                    try:
                        os.unlink(path)
                    except OSError:
                        pass

    def _execute_file_based(
        self, prompt: str, timeout: int, working_dir: Optional[str]
    ) -> Tuple[bool, str, str]:
        """Execute using file-based input/output.

        Many AI CLIs can read prompts from files and write output to files.
        """
        input_file = Path(self.temp_dir) / "input.txt"
        output_file = Path(self.temp_dir) / "output.txt"

        try:
            # Write prompt to input file
            input_file.write_text(prompt)

            self.logger.debug("Executing %s with file I/O", self.command)

            # Execute command
            # Common patterns: cli --input input.txt --output output.txt
            process = subprocess.Popen(  # pylint: disable=consider-using-with
                [*self.command_parts, "--input", str(input_file), "--output", str(output_file)],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                cwd=working_dir,
            )

            stdout, stderr = process.communicate(timeout=timeout)

            # Read output file if it exists
            if output_file.exists():
                output = output_file.read_text()
            else:
                output = stdout

            success = process.returncode == 0
            return success, output, stderr

        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)
            return False, "", f"Timeout after {timeout}s"

        except Exception as e:
            self.logger.error("File-based execution failed: %s", e)
            return False, "", str(e)

        finally:
            # Cleanup
            if input_file.exists():
                input_file.unlink()
            if output_file.exists():
                output_file.unlink()

    def _execute_argument(
        self, prompt: str, timeout: int, working_dir: Optional[str]
    ) -> Tuple[bool, str, str]:
        """Execute by passing prompt as command-line argument with live output streaming."""
        try:
            self.logger.debug("Executing %s with argument", self.command)

            env = os.environ.copy()
            if self.command_name in ["gemini", "gemini-cli"]:
                env["NODE_OPTIONS"] = "--no-warnings"

            cmd = self._build_command_for_tool(prompt)

            process = subprocess.Popen(  # pylint: disable=consider-using-with
                cmd,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                cwd=working_dir,
                env=env,
            )

            # Stream stdout line-by-line in real time
            stdout_lines: List[str] = []

            deadline = time.time() + timeout
            while True:
                remaining = deadline - time.time()
                if remaining <= 0:
                    process.kill()
                    process.wait(timeout=5)
                    return False, "".join(stdout_lines), f"Timeout after {timeout}s"

                # Check if process has finished
                retcode = process.poll()

                # Read available stdout
                if process.stdout:
                    line = process.stdout.readline()
                    if line:
                        stdout_lines.append(line)
                        # Stream to terminal in real time
                        sys.stdout.write(line)
                        sys.stdout.flush()
                    elif retcode is not None:
                        # Process done, no more output
                        break

                if retcode is not None and not line:
                    break

            # Drain any remaining output
            if process.stdout:
                remaining_out = process.stdout.read()
                if remaining_out:
                    stdout_lines.append(remaining_out)
                    sys.stdout.write(remaining_out)
                    sys.stdout.flush()

            stderr = process.stderr.read() if process.stderr else ""
            success = process.returncode == 0

            if not success:
                self.logger.error("Command failed with stderr: %s", stderr[:500])

            return success, "".join(stdout_lines), stderr
        except subprocess.TimeoutExpired:
            self.logger.error("Command timed out after %ds", timeout)
            process.kill()
            process.wait(timeout=5)
            return False, "", f"Timeout after {timeout}s"
        except Exception as e:
            self.logger.error("Execution failed: %s", e)
            return False, "", str(e)

    def _build_command_for_tool(self, prompt: str) -> List[str]:
        """Build the command and arguments for a specific CLI tool."""
        if self.command_name == "codex":
            # Support configured args/profiles and both `codex ...` or `codex exec ...`.
            if "exec" in self.command_parts[1:]:
                return [*self.command_parts, prompt]
            return [*self.command_parts, "exec", prompt]

        if self.command_name in ["gemini", "gemini-cli"]:
            # Gemini expects positional prompt.
            return [*self.command_parts, prompt]

        if self.command_name == "claude":
            # Claude expects positional prompt.
            return [*self.command_parts, prompt]

        if self.command_name in ["copilot", "github-copilot-cli"]:
            # Copilot CLI expects prompt with `-p`; allow all tools by default.
            has_prompt_flag = any(part in {"-p", "--prompt"} for part in self.command_parts[1:])
            has_allow_all_tools = "--allow-all-tools" in self.command_parts[1:]
            cmd = [*self.command_parts]
            if not has_prompt_flag:
                cmd.extend(["-p", prompt])
            else:
                cmd.append(prompt)
            if not has_allow_all_tools:
                cmd.append("--allow-all-tools")
            return cmd

        return [*self.command_parts, prompt]

    def _execute_heredoc(
        self, prompt: str, timeout: int, working_dir: Optional[str]
    ) -> Tuple[bool, str, str]:
        """Execute using heredoc (for bash-based CLIs)."""
        try:
            # Create a shell script with heredoc
            script = f"""{shlex.quote(self.command)} << 'EOF'
{prompt}
EOF
"""

            process = subprocess.Popen(  # pylint: disable=consider-using-with
                ["bash", "-c", script],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                cwd=working_dir,
            )

            stdout, stderr = process.communicate(timeout=timeout)
            success = process.returncode == 0

            return success, stdout, stderr

        except Exception as e:
            return False, "", str(e)

    def execute_in_workspace(
        self, prompt: str, workspace_dir: str, timeout: int = 3600, method: str = "arg"
    ) -> Tuple[bool, str, str, List[str]]:
        """Execute CLI in a workspace directory and track file changes.

        This is useful for tools that modify files directly.

        Args:
            prompt: The prompt to send
            workspace_dir: Directory to execute in
            timeout: Timeout in seconds
            method: Communication method to use (default: 'arg')

        Returns:
            Tuple of (success, stdout, stderr, modified_files)
        """
        workspace_path = Path(workspace_dir)
        workspace_path.mkdir(parents=True, exist_ok=True)

        # Get initial file state
        initial_files = self._get_file_state(workspace_path)

        # Execute command in workspace using the specified method
        success, stdout, stderr = self.execute_with_prompt(prompt, method, timeout, workspace_dir)

        # Get modified files
        modified_files = self._get_modified_files(workspace_path, initial_files)

        return success, stdout, stderr, modified_files

    def _get_file_state(self, directory: Path) -> Dict[str, float]:
        """Get modification times of all files in directory."""
        file_state = {}

        for file_path in directory.rglob("*"):
            if file_path.is_file():
                try:
                    file_state[str(file_path)] = file_path.stat().st_mtime
                except Exception:
                    pass

        return file_state

    def _get_modified_files(self, directory: Path, initial_state: Dict[str, float]) -> List[str]:
        """Determine which files were modified or created."""
        modified = []

        for file_path in directory.rglob("*"):
            if not file_path.is_file():
                continue

            file_str = str(file_path)

            # New file
            if file_str not in initial_state:
                modified.append(file_str)
                continue

            # Modified file
            try:
                current_mtime = file_path.stat().st_mtime
                if current_mtime > initial_state[file_str]:
                    modified.append(file_str)
            except Exception:
                pass

        return modified

    def execute_with_retry(
        self, prompt: str, max_retries: int = 3, backoff: float = 1.0, **kwargs
    ) -> Tuple[bool, str, str]:
        """Execute with automatic retry on failure and method fallback.

        Args:
            prompt: The prompt to send
            max_retries: Maximum number of retry attempts
            backoff: Backoff multiplier between retries
            **kwargs: Additional arguments for execute_with_prompt

        Returns:
            Tuple of (success, stdout, stderr)
        """
        last_error = ""
        method = kwargs.get("method", "stdin")

        fallback_methods = self._resolve_retry_methods(method)

        for attempt in range(max_retries):
            if attempt > 0:
                sleep_time = backoff * (2 ** (attempt - 1))
                self.logger.info(
                    "Retry attempt %d/%d after %ss", attempt + 1, max_retries, sleep_time
                )
                time.sleep(sleep_time)

            # Try current method
            current_method = fallback_methods[min(attempt, len(fallback_methods) - 1)]
            kwargs["method"] = current_method

            self.logger.debug("Trying method: %s", current_method)
            success, stdout, stderr = self.execute_with_prompt(prompt, **kwargs)

            if success:
                return success, stdout, stderr

            # Check if error is due to Node.js compatibility
            if "File is not defined" in stderr or "ReferenceError" in stderr:
                self.logger.warning("Node.js compatibility issue detected with %s", self.command)
                # Try to provide helpful error message
                if attempt == max_retries - 1:
                    last_error = (
                        f"Node.js compatibility error. "
                        f"Try upgrading Node.js to v20+: nvm install 20 && nvm use 20\n"
                        f"Original error: {stderr}"
                    )
                    break

            last_error = stderr

        return False, "", f"Failed after {max_retries} attempts. Last error: {last_error}"

    def _resolve_retry_methods(self, method: str) -> List[str]:
        """Resolve retry method order for this CLI tool."""
        # Codex should stay on non-interactive `exec` argument mode and never
        # fall back to stdin/heredoc interactive patterns.
        if self.command_name == "codex":
            return ["arg"]

        if method == "stdin":
            return ["stdin", "arg", "heredoc"]
        if method == "arg":
            return ["arg", "stdin", "heredoc"]
        return [method, "stdin", "arg"]

    def cleanup(self):
        """Clean up temporary directory."""
        try:
            import shutil as _shutil

            if os.path.exists(self.temp_dir):
                _shutil.rmtree(self.temp_dir, ignore_errors=True)
        except Exception:
            pass

    def __del__(self):
        """Cleanup on deletion. Silences errors during interpreter shutdown."""
        try:
            self.cleanup()
        except Exception:
            pass


class AgentCLIRegistry:
    """Registry of known CLI tool communication patterns.

    This helps adapters know how to communicate with each tool.
    """

    PATTERNS = {
        "claude": {
            "command": "claude",
            "method": "arg",
            "supports_workspace": True,
            "output_format": "text",
        },
        "codex": {
            "command": "codex",
            "method": "arg",
            "supports_workspace": True,
            "output_format": "text",
        },
        "gemini": {
            "command": "gemini",
            "method": "arg",
            "prompt_flag": "--prompt",
            "supports_workspace": False,
            "output_format": "text",
        },
        "copilot": {
            "command": "copilot",
            "method": "arg",
            "supports_workspace": False,
            "output_format": "text",
        },
        "openai": {
            "command": "openai",
            "method": "arg",
            "prompt_flag": "--prompt",
            "supports_workspace": False,
            "output_format": "json",
        },
    }

    @classmethod
    def get_pattern(cls, tool_name: str) -> Dict[str, Any]:
        """Get communication pattern for a tool."""
        return cls.PATTERNS.get(
            tool_name, {"method": "stdin", "supports_workspace": True, "output_format": "text"}
        )

    @classmethod
    def register_pattern(cls, tool_name: str, pattern: Dict[str, Any]):
        """Register a new tool pattern."""
        cls.PATTERNS[tool_name] = pattern
