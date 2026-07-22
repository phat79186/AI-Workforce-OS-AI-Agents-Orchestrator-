"""Permission Policy definitions for security classification, including Obsidian Vault protection rules."""

from __future__ import annotations

from enum import Enum
from typing import List


class ActionLevel(str, Enum):
    """Action security level classification."""

    ALLOWED = "ALLOWED"
    REQUIRES_APPROVAL = "REQUIRES_APPROVAL"
    BLOCKED = "BLOCKED"


class PermissionPolicy:
    """Evaluates requested tool actions against safety rules."""

    BLOCKED_PATTERNS: List[str] = [
        "rm -rf /",
        "rm -rf database",
        "drop database",
        "format c:",
        ":(){ :|:& };:",
        ".obsidian/",
        ".obsidian\\",
    ]

    APPROVAL_PATTERNS: List[str] = [
        "git push",
        "force push",
        "--force",
        "deploy",
        "drop table",
        "delete file",
        "modify secret",
        "modify adr",
        "delete knowledge",
    ]

    def classify(self, command: str) -> ActionLevel:
        """Classify command into ActionLevel."""
        cmd_lower = command.lower()

        for pattern in self.BLOCKED_PATTERNS:
            if pattern in cmd_lower:
                return ActionLevel.BLOCKED

        for pattern in self.APPROVAL_PATTERNS:
            if pattern in cmd_lower:
                return ActionLevel.REQUIRES_APPROVAL

        return ActionLevel.ALLOWED

    def classify_obsidian_action(self, action_type: str, target_path: str = "") -> ActionLevel:
        """Classify specific Obsidian Vault actions to protect user knowledge base."""
        target_lower = target_path.lower()
        action_lower = action_type.lower()

        if ".obsidian" in target_lower:
            return ActionLevel.BLOCKED

        if action_lower in ("delete_knowledge", "delete_file", "unlink"):
            return ActionLevel.REQUIRES_APPROVAL

        if action_lower in ("modify_adr", "overwrite_adr") or "corporate_adr" in target_lower:
            return ActionLevel.REQUIRES_APPROVAL

        if action_lower in ("read_knowledge", "query_rag", "create_knowledge", "update_project_memory"):
            return ActionLevel.ALLOWED

        return ActionLevel.ALLOWED
