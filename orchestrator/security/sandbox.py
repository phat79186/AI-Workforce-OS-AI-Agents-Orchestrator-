"""Security Sandbox wrapper integrating PermissionPolicy and ApprovalManager."""

from __future__ import annotations

from typing import Any, Dict, Optional
from orchestrator.security.permission_policy import PermissionPolicy, ActionLevel
from orchestrator.security.approval_manager import ApprovalManager


class SecuritySandbox:
    """Security Sandbox protecting against dangerous or unauthorized operations."""

    def __init__(
        self,
        policy: Optional[PermissionPolicy] = None,
        approval_mgr: Optional[ApprovalManager] = None,
    ) -> None:
        self.policy = policy or PermissionPolicy()
        self.approval_mgr = approval_mgr or ApprovalManager()

    def validate_and_execute(self, command: str, executor_fn: Any) -> Dict[str, Any]:
        """Validate command permissions and execute if safe or approved."""
        level = self.policy.classify(command)

        if level == ActionLevel.BLOCKED:
            return {
                "status": "blocked",
                "error": f"Command '{command}' is strictly BLOCKED by security policy.",
            }

        if level == ActionLevel.REQUIRES_APPROVAL:
            approved = self.approval_mgr.request_approval(
                action_description=f"Execute: {command}",
                rationale="Potentially dangerous command requires user confirmation",
            )
            if not approved:
                return {
                    "status": "rejected",
                    "error": "User rejected dangerous operation.",
                }

        # Execution allowed or approved
        res = executor_fn(command)
        return {
            "status": "success",
            "result": res,
        }
