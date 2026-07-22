"""Robust decision parsing for agentic team handoff messages."""

from __future__ import annotations

import json
import logging
import re
from typing import Any

from .config_utils import normalize_role

logger = logging.getLogger(__name__)

_FENCED_BLOCK_RE = re.compile(r"```(?:json)?\s*(.*?)```", re.IGNORECASE | re.DOTALL)
_LINE_TO_ROLE_RE = re.compile(
    r"^\s*(?:to_role|target_role|next_role)\s*:\s*(.+?)\s*$", re.IGNORECASE
)
_LINE_ACTION_RE = re.compile(r"^\s*action\s*:\s*(.+?)\s*$", re.IGNORECASE)
_LINE_FINAL_RE = re.compile(r"^\s*(?:final_response|user_response)\s*:\s*(.+?)\s*$", re.IGNORECASE)


class DecisionParser:
    """Parses model output into normalized action/to_role/message/final_response."""

    def extract_json_object(self, text: str) -> dict[str, Any] | None:
        """Public API for extracting the first JSON object from text."""
        return self._extract_first_json_object(text)

    def _extract_first_json_object(self, text: str) -> dict[str, Any] | None:
        candidate = (text or "").strip()
        if not candidate:
            return None

        # 1) Direct parse.
        try:
            parsed = json.loads(candidate)
            if isinstance(parsed, dict):
                return parsed
        except Exception:
            pass

        # 2) Parse fenced blocks.
        for match in _FENCED_BLOCK_RE.findall(candidate):
            block = str(match or "").strip()
            if not block:
                continue
            try:
                parsed = json.loads(block)
            except Exception:
                parsed = None
            if isinstance(parsed, dict):
                return parsed

        # 3) Streaming-style scan for JSON object starts.
        decoder = json.JSONDecoder()
        for idx, ch in enumerate(candidate):
            if ch != "{":
                continue
            try:
                parsed, _end = decoder.raw_decode(candidate[idx:])
            except Exception:
                parsed = None
            if isinstance(parsed, dict):
                return parsed
        return None

    def _extract_from_kv_lines(self, text: str) -> dict[str, str]:
        data: dict[str, str] = {}
        for line in str(text or "").splitlines():
            line = line.strip()
            if not line:
                continue
            action_match = _LINE_ACTION_RE.match(line)
            if action_match and "action" not in data:
                data["action"] = action_match.group(1).strip()
                continue
            to_role_match = _LINE_TO_ROLE_RE.match(line)
            if to_role_match and "to_role" not in data:
                data["to_role"] = to_role_match.group(1).strip()
                continue
            final_match = _LINE_FINAL_RE.match(line)
            if final_match and "final_response" not in data:
                data["final_response"] = final_match.group(1).strip()
                continue
        return data

    def parse_decision(
        self,
        *,
        output: str,
        current_role: str,
        lead_role: str,
        default_to_role: str,
    ) -> dict[str, str | None]:
        """Parse model output into normalized routing/finalization instructions."""
        payload = self._extract_first_json_object(output) or self._extract_from_kv_lines(output)
        action = str(payload.get("action") or "message").strip().lower()
        if action not in {"message", "finalize"}:
            action = "message"

        to_role = payload.get("to_role") or payload.get("target_role") or payload.get("next_role")
        to_role_norm: str | None = None
        if isinstance(to_role, str) and to_role.strip():
            to_role_norm = normalize_role(to_role)

        message = payload.get("message") or payload.get("instruction") or payload.get("deliverable")
        if not isinstance(message, str) or not message.strip():
            message = (output or "").strip()

        final_response = payload.get("final_response") or payload.get("user_response")
        if not isinstance(final_response, str):
            final_response = ""

        if action == "finalize" and current_role != lead_role:
            logger.info(
                "Non-lead role '%s' attempted finalize, redirecting to lead '%s'",
                current_role,
                lead_role,
            )
            action = "message"
            to_role_norm = lead_role

        if action == "message" and not to_role_norm:
            to_role_norm = default_to_role

        return {
            "action": action,
            "to_role": to_role_norm,
            "message": message,
            "final_response": final_response,
        }
