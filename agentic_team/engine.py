"""Standalone agentic-team engine with free inter-role communication."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable
from uuid import uuid4

import yaml

from agentic_team.adapters import (
    BaseAdapter,
    ClaudeAdapter,
    CodexAdapter,
    CopilotAdapter,
    GeminiAdapter,
    LlamaCppAdapter,
    OllamaAdapter,
)
from agentic_team.fallback import FallbackManager
from agentic_team.offline import OfflineDetector

from .config_utils import resolve_team_config, validate_team_bindings
from .constants import (
    DEFAULT_MAX_MESSAGE_CHARS,
    DEFAULT_REPEAT_ROUTE_LIMIT,
    DEFAULT_TEAM_MAX_TURNS,
    MAX_TASK_LENGTH,
)
from .decision_parser import DecisionParser


class AgenticTeamEngine:
    """Role-based team engine, intentionally separate from workflow orchestrator."""

    def __init__(
        self,
        config_path: str | None = None,
        force_offline: bool = False,
        offline_detector: OfflineDetector | None = None,
    ):
        self.logger = logging.getLogger("agentic_team")
        self.force_offline = force_offline
        self.offline_detector = offline_detector or OfflineDetector()
        self.decision_parser = DecisionParser()
        self.config_path = (
            Path(config_path)
            if config_path is not None
            else Path(__file__).parent / "config" / "agents.yaml"
        )

        self.config: dict[str, Any] = {}
        self.is_offline_mode = False
        self.adapters: dict[str, BaseAdapter] = {}
        self.fallback_manager = FallbackManager({}, logger=self.logger)
        self.context_manager = self._init_context_manager()
        self.reload()

    def reload(self) -> None:
        """Reload config, runtime flags, adapters, and fallback manager."""
        self.config = self._load_config(str(self.config_path))
        self.is_offline_mode = self._resolve_offline_mode()
        self.adapters = {}
        self.fallback_manager = FallbackManager(self.config, logger=self.logger)
        self._initialize_adapters()

    def _load_config(self, config_path: str | None) -> dict[str, Any]:
        config_path_obj = Path(config_path) if config_path else self.config_path
        if not config_path_obj.exists():
            self.logger.warning("Config not found: %s", config_path_obj)
            return {}

        try:
            with open(config_path_obj, encoding="utf-8") as f:
                loaded = yaml.safe_load(f) or {}
        except Exception as exc:
            self.logger.error("Failed to load config %s: %s", config_path_obj, exc)
            return {}

        if not isinstance(loaded, dict):
            self.logger.error("Config top-level must be mapping/object: %s", config_path_obj)
            return {}
        return loaded

    def _resolve_offline_mode(self) -> bool:
        if self.force_offline:
            return True
        offline_settings = self.config.get("settings", {}).get("offline", {})
        if isinstance(offline_settings, dict):
            if offline_settings.get("enabled", False):
                return True
            if offline_settings.get("auto_detect", False):
                return self.offline_detector.is_offline()
        return False

    def _resolve_adapter_class(self, agent_name: str, agent_config: dict[str, Any]):
        cli_adapter_classes = {
            "codex": CodexAdapter,
            "gemini": GeminiAdapter,
            "claude": ClaudeAdapter,
            "copilot": CopilotAdapter,
        }
        cli_command_aliases = {
            "gemini-cli": "gemini",
            "github-copilot-cli": "copilot",
            "gh-copilot": "copilot",
        }
        type_adapter_classes = {
            "ollama": OllamaAdapter,
            "llamacpp": LlamaCppAdapter,
            "localai": LlamaCppAdapter,
            "text-generation-webui": LlamaCppAdapter,
            "openai-compatible": LlamaCppAdapter,
        }

        agent_type = str(agent_config.get("type", "")).strip().lower()
        if agent_type:
            if agent_type == "cli":
                provider = (
                    str(
                        agent_config.get("provider")
                        or agent_config.get("adapter")
                        or agent_name
                        or ""
                    )
                    .strip()
                    .lower()
                )
                if provider in cli_adapter_classes:
                    return cli_adapter_classes[provider]
                command_name = str(agent_config.get("command", "")).strip().lower()
                command_name = command_name.rsplit("/", maxsplit=1)[-1]
                command_name = cli_command_aliases.get(command_name, command_name)
                return cli_adapter_classes.get(command_name)
            return type_adapter_classes.get(agent_type)

        return cli_adapter_classes.get(agent_name)

    def _is_local_agent(self, agent_config: dict[str, Any]) -> bool:
        agent_type = str(agent_config.get("type", "")).strip().lower()
        return bool(agent_config.get("offline", False)) or agent_type in {
            "ollama",
            "llamacpp",
            "localai",
            "text-generation-webui",
            "openai-compatible",
        }

    def _initialize_adapters(self):
        agents = self.config.get("agents", {})
        if not isinstance(agents, dict):
            self.logger.warning("Config section 'agents' is not a mapping")
            return

        for agent_name, agent_config in agents.items():
            if not isinstance(agent_config, dict):
                continue
            if not agent_config.get("enabled", True):
                continue
            if self.is_offline_mode and not self._is_local_agent(agent_config):
                continue

            adapter_class = self._resolve_adapter_class(agent_name, agent_config)
            if adapter_class is None:
                continue

            runtime_config = dict(agent_config)
            runtime_config["name"] = agent_name
            try:
                adapter = adapter_class(runtime_config)  # type: ignore[abstract]
                if adapter.is_available():
                    self.adapters[agent_name] = adapter
            except Exception as exc:
                self.logger.error("Failed to initialize agent %s: %s", agent_name, exc)

    def _pick_preferred_agent(self, preferred_agents: list[str]) -> str | None:
        configured_enabled_agents = [
            name
            for name, cfg in self.config.get("agents", {}).items()
            if isinstance(cfg, dict) and bool(cfg.get("enabled", True))
        ]

        for agent_name in preferred_agents:
            if agent_name in self.adapters:
                return agent_name
        for agent_name in preferred_agents:
            if agent_name in configured_enabled_agents:
                return agent_name
        if self.adapters:
            return next(iter(self.adapters))
        if configured_enabled_agents:
            return configured_enabled_agents[0]
        return None

    def _runtime_settings(self) -> dict[str, int]:
        raw = self.config.get("settings", {}).get("agentic_team", {})
        if not isinstance(raw, dict):
            raw = {}

        def _positive(raw_value: Any, default: int, minimum: int = 1) -> int:
            try:
                value = int(raw_value)
            except (TypeError, ValueError):
                value = default
            return max(minimum, value)

        return {
            "max_message_chars": _positive(
                raw.get("max_message_chars", DEFAULT_MAX_MESSAGE_CHARS),
                DEFAULT_MAX_MESSAGE_CHARS,
                minimum=256,
            ),
            "repeat_route_limit": _positive(
                raw.get("repeat_route_limit", DEFAULT_REPEAT_ROUTE_LIMIT),
                DEFAULT_REPEAT_ROUTE_LIMIT,
                minimum=2,
            ),
        }

    def get_team_config(self) -> dict[str, Any]:
        """Return effective team config with defaults merged into role mappings."""
        return resolve_team_config(self.config, self._pick_preferred_agent)

    def validate_team_bindings(self) -> dict[str, Any]:
        """Validate role-to-agent bindings against currently available adapters."""
        team_cfg = self.get_team_config()
        return validate_team_bindings(team_cfg, self.get_available_agents())

    def _validate_team_config(self, team_cfg: dict[str, Any]) -> None:
        payload = validate_team_bindings(team_cfg, self.get_available_agents())
        if payload.get("valid"):
            return

        reason = payload.get("reason") or ""
        if reason == "invalid_mappings":
            missing_roles = [
                f"{item.get('role')}:{item.get('agent')}"
                for item in payload.get("missing_roles", [])
            ]
            raise ValueError(
                f"Agentic team roles mapped to unavailable agents: {', '.join(missing_roles)}"
            )
        if reason == "no_available_agents":
            raise ValueError("No available agents detected for agentic team execution")

        raise ValueError(str(payload.get("error") or "Invalid agentic team configuration"))

    def _build_prompt(
        self,
        *,
        original_task: str,
        role_name: str,
        role_spec: dict[str, Any],
        lead_role: str,
        sender_role: str,
        incoming_message: str,
        transcript: list[dict[str, Any]],
        team_roles: dict[str, dict[str, Any]],
        turn: int,
        max_turns: int,
    ) -> str:
        from agentic_team.prompts.team_prompts import build_team_prompt

        return build_team_prompt(
            role_name=role_name,
            role_spec=role_spec,
            lead_role=lead_role,
            original_task=original_task,
            sender_role=sender_role,
            incoming_message=incoming_message,
            transcript=transcript,
            team_roles=team_roles,
            turn=turn,
            max_turns=max_turns,
        )

    def _extract_json_payload(self, output: str) -> dict[str, Any] | None:
        return self.decision_parser.extract_json_object(output)

    def _parse_decision(
        self, output: str, current_role: str, lead_role: str
    ) -> dict[str, str | None]:
        return self.decision_parser.parse_decision(
            output=output,
            current_role=current_role,
            lead_role=lead_role,
            default_to_role=lead_role,
        )

    def execute_task(  # pylint: disable=too-many-branches,too-many-statements
        self,
        task: str,
        max_turns: int | None = None,
        turn_callback: Callable[[dict[str, Any]], None] | None = None,
    ) -> dict[str, Any]:
        """Run a role-routed team execution and return full transcript + final output."""
        if not task or not task.strip():
            raise ValueError("Task is required")
        task = task.strip()
        if len(task) > MAX_TASK_LENGTH:
            raise ValueError(f"Task exceeds maximum length of {MAX_TASK_LENGTH} characters")

        execution_id = str(uuid4())
        started_at = datetime.now(timezone.utc)
        runtime = self._runtime_settings()
        max_message_chars = runtime["max_message_chars"]
        repeat_route_limit = runtime["repeat_route_limit"]

        team_cfg = self.get_team_config()
        self._validate_team_config(team_cfg)

        roles = team_cfg["roles"]
        lead_role = team_cfg["lead_role"]
        max_turns_effective = max(
            1, int(max_turns or team_cfg.get("max_turns", DEFAULT_TEAM_MAX_TURNS))
        )

        iteration: dict[str, Any] = {"steps": [], "final_output": None}
        current_role = lead_role
        sender_role = "user"
        incoming_message = task
        final_output = ""
        success = False
        termination_reason = "max_turns_reached_without_finalize"

        fallback_count = 0
        lead_escalation_count = 0
        repeated_route_counts: dict[str, int] = {}

        for turn in range(1, max_turns_effective + 1):
            if current_role not in roles:
                self.logger.warning(
                    "Role '%s' not found in team config, falling back to lead", current_role
                )
                current_role = lead_role
            role_spec = roles[current_role]
            prompt = self._build_prompt(
                original_task=task,
                role_name=current_role,
                role_spec=role_spec,
                lead_role=lead_role,
                sender_role=sender_role,
                incoming_message=incoming_message,
                transcript=iteration["steps"],
                team_roles=roles,
                turn=turn,
                max_turns=max_turns_effective,
            )

            # Resolve working dir: fall back to project root if configured dir missing.
            configured_dir = self.config.get("settings", {}).get("output_dir", "./output")
            _working_dir = str(configured_dir)
            if not Path(_working_dir).is_dir():
                _working_dir = str(Path(__file__).resolve().parent.parent)

            turn_context = {
                "role": "team_member",
                "team_role": current_role,
                "lead_role": lead_role,
                "sender_role": sender_role,
                "incoming_message": incoming_message,
                "working_dir": _working_dir,
                "offline_mode": self.is_offline_mode,
                "execution_id": execution_id,
            }
            primary_agent = str(role_spec.get("agent", ""))
            agent_used, response, fallback_from = self.fallback_manager.execute_with_fallback(
                primary_agent=primary_agent,
                adapters=self.adapters,
                task=prompt,
                context=turn_context,
                explicit_fallback=role_spec.get("fallback"),
            )
            if fallback_from:
                fallback_count += 1

            decision = self._parse_decision(response.output, current_role, lead_role)
            action = decision["action"] or "message"
            to_role = decision["to_role"] or lead_role
            message = str(decision["message"] or "")

            if len(message) > max_message_chars:
                message = (
                    message[: max_message_chars - 64].rstrip()
                    + "\n\n[System] Message truncated due to max_message_chars policy."
                )

            if not response.success:
                action = "message"
                to_role = lead_role
                message = (
                    f"Execution failed for role '{current_role}': "
                    f"{response.error or 'unknown error'}"
                )

            if to_role not in roles and to_role != "user":
                to_role = lead_role

            route_fingerprint = f"{current_role}->{to_role}:{message.strip().lower()[:240]}"
            repeated_route_counts[route_fingerprint] = (
                repeated_route_counts.get(route_fingerprint, 0) + 1
            )
            if (
                action == "message"
                and current_role != lead_role
                and repeated_route_counts[route_fingerprint] >= repeat_route_limit
            ):
                to_role = lead_role
                message = (
                    message + "\n\n[System] Repetition detected in team routing. "
                    "Escalating to lead for decision."
                ).strip()
                lead_escalation_count += 1

            if action == "finalize" and current_role == lead_role:
                final_output = str(decision["final_response"] or response.output or "").strip()
                success = bool(response.success)
                to_role = "user"
                termination_reason = "lead_finalize"

            step: dict[str, Any] = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "execution_id": execution_id,
                "turn": turn,
                "task": "team_message",
                "action": action,
                "agent": agent_used,
                "from_agent": agent_used,
                "team_role": current_role,
                "from_role": current_role,
                "to_role": to_role,
                "to_agent": (
                    str(roles[to_role].get("agent", ""))
                    if to_role in roles
                    else ("user" if to_role == "user" else "")
                ),
                "message": message,
                "success": response.success,
                "output": response.output,
                "error": response.error,
                "files_modified": response.files_modified,
                "suggestions": response.suggestions,
                "communication_type": (
                    "to_user"
                    if to_role == "user"
                    else ("self" if to_role == current_role else "inter_role")
                ),
            }
            if fallback_from:
                step["fallback_from"] = fallback_from

            iteration["steps"].append(step)
            self._store_turn_in_context(step)
            iteration["final_output"] = final_output or response.output

            if turn_callback is not None:
                try:
                    turn_callback(dict(step))
                except Exception as exc:
                    self.logger.warning("Agentic team turn callback failed: %s", exc)

            if action == "finalize" and current_role == lead_role:
                break

            sender_role = current_role
            incoming_message = message
            current_role = to_role if to_role in roles else lead_role

        if not final_output:
            fallback_output = iteration["steps"][-1]["output"] if iteration["steps"] else ""
            final_output = (
                "Team reached max turns without lead finalization. Last output:\n\n"
                f"{fallback_output}"
            )
            iteration["final_output"] = final_output

        completed_at = datetime.now(timezone.utc)
        duration_ms = int((completed_at - started_at).total_seconds() * 1000)
        turns_executed = len(iteration["steps"])

        result = {
            "task": task,
            "engine": "agentic_team",
            "execution_id": execution_id,
            "started_at": started_at.isoformat(),
            "completed_at": completed_at.isoformat(),
            "duration_ms": duration_ms,
            "termination_reason": termination_reason,
            "iterations": [iteration],
            "final_output": final_output,
            "success": success,
            "offline_mode": self.is_offline_mode,
            "stats": {
                "turns_executed": turns_executed,
                "fallback_count": fallback_count,
                "lead_escalation_count": lead_escalation_count,
            },
            "team": {
                "lead_role": lead_role,
                "max_turns": max_turns_effective,
                "roles": roles,
            },
        }

        # Store in context memory
        self._store_task_in_context(task, result, duration_ms / 1000.0)

        return result

    def get_available_agents(self) -> list[str]:
        """Return names of adapters currently available for execution."""
        return sorted(self.adapters.keys())

    def get_runtime_status(self) -> dict[str, Any]:
        """Return operational details useful for diagnostics and UI."""
        return {
            "engine": "agentic_team",
            "config_path": str(self.config_path),
            "offline_mode": self.is_offline_mode,
            "available_agents": self.get_available_agents(),
            "team_validation": self.validate_team_bindings(),
            "runtime_settings": self._runtime_settings(),
        }

    def _init_context_manager(self):
        """Initialize context manager if available."""
        try:
            import os

            from agentic_team.context import MemoryManager

            manager = MemoryManager()
            self.logger.info("Context manager initialized for agentic team")

            # Auto-register project if configured
            project_path = os.environ.get("PROJECT_PATH", "").strip()
            if not project_path:
                project_path = self.config.get("settings", {}).get("project_path", "")
            if project_path and Path(project_path).is_dir():
                try:
                    manager.register_project(project_path)
                except Exception as exc:
                    self.logger.debug("Project registration failed: %s", exc)

            return manager
        except ImportError:
            self.logger.debug("Context manager not available (agentic_team.context not found)")
            return None
        except Exception as e:
            self.logger.warning("Failed to initialize context manager: %s", e)
            return None

    def _resolve_project_id(self) -> str:
        """Resolve the active project_id from env or config."""
        import os

        project_path = os.environ.get("PROJECT_PATH", "").strip()
        if not project_path:
            project_path = self.config.get("settings", {}).get("project_path", "")
        if not project_path or not Path(project_path).is_dir():
            return ""
        try:
            from agentic_team.context.ops.project_scanner import generate_project_id

            return generate_project_id(project_path)
        except Exception:
            return ""

    def _store_task_in_context(
        self,
        task: str,
        result: dict[str, Any],
        duration_seconds: float,
    ) -> None:
        """Store completed task in the graph context base."""
        if not hasattr(self, "context_manager") or self.context_manager is None:
            return

        try:
            success = result.get("success", False)
            final_output = result.get("final_output", "")
            execution_id = result.get("execution_id", "")
            stats = result.get("stats", {})
            team_info = result.get("team", {})
            iterations = result.get("iterations", [])

            # Collect role names and communication counts
            roles_used: list[str] = sorted(team_info.get("roles", {}).keys())
            communications = 0
            for it in iterations:
                for step in it.get("steps", []):
                    if step.get("communication_type") == "inter_role":
                        communications += 1

            metadata = {
                "engine": "agentic_team",
                "execution_id": execution_id,
                "lead_role": team_info.get("lead_role", "unknown"),
                "roles": roles_used,
                "turns_executed": stats.get("turns_executed", 0),
                "fallback_count": stats.get("fallback_count", 0),
                "inter_role_communications": communications,
                "duration_seconds": duration_seconds,
                "offline_mode": result.get("offline_mode", False),
            }

            self.context_manager.store_task(
                task_description=task,
                outcome="completed" if success else "failed",
                success=success,
                duration_ms=int(duration_seconds * 1000),
                agents_involved=roles_used,
                metadata=metadata,
                project_id=self._resolve_project_id(),
            )

            if not success and final_output:
                self.context_manager.log_mistake(
                    error_description=f"Task failed: {task[:100]}",
                    context=final_output[:500] if final_output else "",
                    correction="Review team execution steps for improvement",
                )

            self.logger.debug("Stored task in context: %s (success=%s)", task[:50], success)
        except Exception as e:
            self.logger.warning("Failed to store task in context: %s", e)

    def _store_turn_in_context(self, step: dict[str, Any]) -> None:
        """Store a team turn in the context graph."""
        if not hasattr(self, "context_manager") or self.context_manager is None:
            return
        try:
            messages = [
                {"role": step.get("role", "unknown"), "content": step.get("output", "")[:2000]}
            ]
            metadata = {
                "engine": "agentic_team",
                "turn": step.get("turn", 0),
                "from_role": step.get("from_role", ""),
                "to_role": step.get("to_role", ""),
                "action": step.get("action", ""),
            }
            self.context_manager.store_conversation(
                messages=messages,
                session_id=step.get("execution_id", "unknown"),
                metadata=metadata,
            )
        except Exception as e:
            self.logger.debug("Failed to store turn in context: %s", e)

    def get_relevant_context(self, query: str, limit: int = 5) -> list[dict[str, Any]]:
        """Retrieve relevant context from the graph context base.

        Args:
            query: Search query for finding relevant context
            limit: Maximum number of results to return

        Returns:
            List of relevant context items with node data
        """
        if not hasattr(self, "context_manager") or self.context_manager is None:
            return []

        try:
            results = self.context_manager.search(query, limit=limit)
            return [
                {
                    "node_id": r.node.id,
                    "type": r.node.node_type.value,
                    "content": r.node.content,
                    "score": r.score,
                    "metadata": r.node.metadata,
                }
                for r in results
            ]
        except Exception as e:
            self.logger.warning("Failed to retrieve context: %s", e)
            return []
