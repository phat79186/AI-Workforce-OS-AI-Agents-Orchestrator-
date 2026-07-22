"""
Base adapter interface for AI coding assistants.
"""

import asyncio
import logging
import shlex
import shutil
import subprocess
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

import httpx

from .cli_communicator import AgentCLIRegistry, CLICommunicator


class AgentCapability(Enum):
    """Capabilities that an AI agent can have."""

    IMPLEMENTATION = "implementation"
    CODE_REVIEW = "code_review"
    REFACTORING = "refactoring"
    TESTING = "testing"
    DOCUMENTATION = "documentation"
    DEBUGGING = "debugging"
    ARCHITECTURE = "architecture"


@dataclass
class AgentResponse:
    """Response from an AI agent."""

    success: bool
    output: str
    error: Optional[str] = None
    files_modified: List[str] = field(default_factory=list)
    suggestions: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


class BaseAdapter(ABC):
    """Base class for AI agent adapters."""

    def __init__(self, config: Dict[str, Any]):
        """Initialize the adapter.

        Args:
            config: Configuration dictionary for the agent
        """
        self.config = config
        self.name = config.get("name", self.__class__.__name__)
        self.command = config.get("command", "")
        self.endpoint = str(config.get("endpoint", ""))
        self.enabled = config.get("enabled", True)
        self.timeout = config.get("timeout", 3600)  # 60 minutes default
        self.logger = logging.getLogger(f"adapter.{self.name}")

        # Initialize CLI communicator only if modal is not local llm
        self.cli_communicator = None
        if not self.config.get("offline", False):
            self.cli_communicator = CLICommunicator(self.command, self.logger)

        # Get communication pattern for this tool
        self.cli_pattern = AgentCLIRegistry.get_pattern(self.name)
        self.communication_method = self.cli_pattern.get("method", "stdin")

    @abstractmethod
    def get_capabilities(self) -> List[AgentCapability]:
        """Return the capabilities of this agent.

        Returns:
            List of capabilities
        """

    @abstractmethod
    def execute_task(self, task: str, context: Dict[str, Any]) -> AgentResponse:
        """Execute a task using this agent.

        Args:
            task: The task description
            context: Additional context (previous outputs, file paths, etc.)

        Returns:
            AgentResponse with results
        """

    async def execute_task_async(self, task: str, context: Dict[str, Any]) -> AgentResponse:
        """Async execution hook.

        Adapters can override this for native async transport. By default, this
        delegates to the synchronous implementation in a worker thread.
        """
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, self.execute_task, task, context)

    def is_available(self) -> bool:
        """Check if the agent CLI tool is available (platform-independent).

        Returns:
            True if available, False otherwise
        """
        if not self.enabled:
            return False

        try:
            command_to_check = self.command
            if isinstance(command_to_check, str):
                parts = shlex.split(command_to_check)
                if parts:
                    command_to_check = parts[0]

            return shutil.which(str(command_to_check)) is not None
        except Exception as e:
            self.logger.warning("Failed to check availability: %s", e)
            return False

    def _run_command_with_prompt(
        self, prompt: str, working_dir: Optional[str] = None, use_workspace: bool = True
    ) -> AgentResponse:
        """Run a CLI command with a prompt using the appropriate communication method.

        Args:
            prompt: The prompt to send to the CLI
            working_dir: Working directory for execution
            use_workspace: Whether to track file changes in workspace

        Returns:
            AgentResponse with command results
        """
        if self.cli_communicator is None:
            return AgentResponse(
                success=False,
                output="",
                error="CLI communicator not initialized (offline mode or missing command config)",
            )

        try:
            self.logger.info(
                "Executing %s with prompt (method: %s)",
                self.command,
                self.communication_method,
            )

            # If tool supports workspace and we want to track files
            if use_workspace and self.cli_pattern.get("supports_workspace", False):
                if not working_dir:
                    working_dir = "./workspace"

                (
                    success,
                    stdout,
                    stderr,
                    modified_files,
                ) = self.cli_communicator.execute_in_workspace(
                    prompt=prompt,
                    workspace_dir=working_dir,
                    timeout=self.timeout,
                    method=self.communication_method,
                )

                return AgentResponse(
                    success=success,
                    output=stdout,
                    error=stderr if not success else None,
                    files_modified=modified_files,
                    metadata={"method": self.communication_method, "working_dir": working_dir},
                )

            # Otherwise, use standard execution
            success, stdout, stderr = self.cli_communicator.execute_with_retry(
                prompt=prompt,
                method=self.communication_method,
                timeout=self.timeout,
                working_dir=working_dir,
                max_retries=2,
            )

            return AgentResponse(
                success=success,
                output=stdout,
                error=stderr if not success else None,
                metadata={"method": self.communication_method},
            )

        except Exception as e:
            self.logger.error("Command execution failed: %s", e, exc_info=True)
            return AgentResponse(success=False, output="", error=str(e))

    def _run_http_with_prompt(self, payload: Dict) -> AgentResponse:
        """Send http request to local endpoint and return AgentResponse"""
        try:
            with httpx.Client(timeout=self.timeout) as client:
                response = client.post(
                    self.endpoint,
                    json=payload,
                )

            response.raise_for_status()
            data = response.json()

            return AgentResponse(
                success=True,
                output=str(data) if not isinstance(data, str) else data,
                metadata=data if isinstance(data, dict) else {},
            )
        except httpx.HTTPStatusError as e:
            self.logger.error("%s returned error status: %s", self.name, e, exc_info=True)
            return AgentResponse(
                success=False,
                output="",
                error=f"HTTP error: {str(e)}",
            )
        except httpx.RequestError as e:
            self.logger.error("%s request failed: %s", self.name, e, exc_info=True)
            return AgentResponse(
                success=False,
                output="",
                error=f"Connection error: {str(e)}",
            )
        except Exception as e:
            self.logger.error("%s execution failed: %s", self.name, e, exc_info=True)
            return AgentResponse(
                success=False,
                output="",
                error=str(e),
            )

    def _run_command(self, args: List[str], stdin_input: Optional[str] = None) -> AgentResponse:
        """Run a CLI command with arguments (legacy method for backward compatibility).

        Args:
            args: Command arguments
            stdin_input: Optional input to pass via stdin

        Returns:
            AgentResponse with command results
        """
        try:
            self.logger.info("Executing: %s", " ".join(args))

            process = subprocess.Popen(  # pylint: disable=consider-using-with
                args,
                stdin=subprocess.PIPE if stdin_input else None,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )

            stdout, stderr = process.communicate(input=stdin_input, timeout=self.timeout)

            success = process.returncode == 0

            return AgentResponse(
                success=success,
                output=stdout,
                error=stderr if not success else None,
                metadata={"returncode": process.returncode, "command": " ".join(args)},
            )

        except subprocess.TimeoutExpired:
            self.logger.error("Command timed out after %ss", self.timeout)
            process.kill()
            process.wait(timeout=5)
            return AgentResponse(
                success=False, output="", error=f"Command timed out after {self.timeout} seconds"
            )

        except Exception as e:
            self.logger.error("Command failed: %s", e)
            return AgentResponse(success=False, output="", error=str(e))

    def format_task_prompt(self, task: str, context: Dict[str, Any]) -> str:
        """Format the task into a prompt suitable for the agent.

        Args:
            task: The task description
            context: Additional context

        Returns:
            Formatted prompt string
        """
        prompt_parts = [task]

        if context.get("previous_output"):
            prompt_parts.append(f"\n\nPrevious output:\n{context['previous_output']}")

        if context.get("feedback"):
            prompt_parts.append(f"\n\nFeedback to address:\n{context['feedback']}")

        if context.get("files"):
            files_str = ", ".join(context["files"])
            prompt_parts.append(f"\n\nRelevant files: {files_str}")

        return "\n".join(prompt_parts)

    def __str__(self) -> str:
        """Return the string representation of the adapter."""
        return f"{self.name} (command: {self.command})"

    def __repr__(self) -> str:
        """Return the detailed string representation of the adapter."""
        return f"<{self.__class__.__name__} name={self.name} enabled={self.enabled}>"

    def _build_local_llm_prompt(self, task: str, context: Dict[str, Any]) -> str:
        """Build a detailed prompt for llama.cpp."""
        parts: List[str] = []
        role = context.get("role", "general")

        if role == "implement":
            parts.append("You are an expert software engineer.")
            parts.append("Implement the following task with clean, production-ready code.")
            parts.append(f"\nTask:\n{task}")

        elif role == "review":
            parts.append("You are an expert code reviewer.")
            parts.append("Review the following implementation and provide actionable feedback.")
            parts.append(f"\nTask:\n{task}")

            if context.get("implementation"):
                parts.append("\nImplementation to Review:\n")
                parts.append("```")
                parts.append(context["implementation"])
                parts.append("```")

        elif role == "refine":
            parts.append("You are refining code based on review feedback.")
            parts.append(f"\nTask:\n{task}")

            if context.get("feedback"):
                parts.append("\nReview Feedback:\n")
                parts.append(context["feedback"])

            if context.get("implementation"):
                parts.append("\nCurrent Implementation:\n")
                parts.append("```")
                parts.append(context["implementation"])
                parts.append("```")

            parts.append("\nPlease improve the implementation while preserving functionality.")

        elif role == "test":
            parts.append("Write comprehensive tests for the following task.")
            parts.append(f"\nTask:\n{task}")

        elif role == "document":
            parts.append("Write clear documentation for the following implementation.")
            parts.append(f"\nTask:\n{task}")

        else:
            parts.append(task)

        parts.append("\n\nGeneral Requirements:")
        parts.append("- Follow clean code principles")
        parts.append("- Use proper error handling")
        parts.append("- Ensure readability and maintainability")
        parts.append("- Keep the solution concise but complete")

        if context.get("previous_output"):
            parts.append("\n\nPrevious Output:")
            parts.append(context["previous_output"])

        return "\n".join(parts)
