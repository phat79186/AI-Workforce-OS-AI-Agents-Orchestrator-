"""Own compressor named after rtk-ai/rtk (Redundant Token Killer).

Note (not a fake-data warning — this one actually works): the dedup /
whitespace-collapse logic below is a real, self-contained implementation
that genuinely processes whatever text you give it. It is NOT the real
rtk-ai/rtk library and `estimate_tokens()` uses a rough "~4 chars/token"
rule rather than a real tokenizer, so treat the token counts as approximate.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List


class RTKTokenCompressor:
    """Own simple text-dedup compressor (real logic) — not the rtk-ai/rtk library, and token counts are approximate."""

    def __init__(self) -> None:
        self.version = "1.0.0"
        self.source_repo = "rtk-ai/rtk"

    def estimate_tokens(self, text: str) -> int:
        """Estimate token count based on standard ~4 chars per token rule."""
        return max(1, len(text) // 4)

    def compress_prompt(self, raw_text: str) -> Dict[str, Any]:
        """Compress a single prompt or traceback by removing duplicate lines and excessive whitespace."""
        lines = raw_text.splitlines()
        seen = set()
        cleaned_lines = []

        for line in lines:
            trimmed = line.strip()
            # Collapse excessive whitespace within lines
            normalized = re.sub(r"\s+", " ", trimmed)
            # Remove repetitive empty lines or exact duplicate status lines
            if normalized and (normalized not in seen or len(normalized) < 15):
                cleaned_lines.append(normalized)
                seen.add(normalized)

        compressed_text = "\n".join(cleaned_lines)
        orig_tokens = self.estimate_tokens(raw_text)
        comp_tokens = self.estimate_tokens(compressed_text)
        saved = max(0, orig_tokens - comp_tokens)
        reduction = round((saved / orig_tokens * 100), 1) if orig_tokens > 0 else 0.0

        return {
            "source_repo": self.source_repo,
            "original_text_length": len(raw_text),
            "compressed_text_length": len(compressed_text),
            "original_token_estimate": orig_tokens,
            "compressed_token_estimate": comp_tokens,
            "saved_tokens": saved,
            "token_reduction_percentage": reduction,
            "compressed_text": compressed_text,
            "status": "COMPRESSED",
        }

    def compress_agent_dialog(self, messages: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Compress multi-turn inter-agent dialog messages to minimize context token overhead."""
        compressed_messages = []
        total_orig_tokens = 0
        total_comp_tokens = 0

        for msg in messages:
            content = str(msg.get("content", ""))
            role = msg.get("role", "agent")
            res = self.compress_prompt(content)

            total_orig_tokens += res["original_token_estimate"]
            total_comp_tokens += res["compressed_token_estimate"]

            compressed_messages.append(
                {
                    "role": role,
                    "content": res["compressed_text"],
                    "orig_tokens": res["original_token_estimate"],
                    "comp_tokens": res["compressed_token_estimate"],
                }
            )

        saved_total = max(0, total_orig_tokens - total_comp_tokens)
        overall_reduction = (
            round((saved_total / total_orig_tokens * 100), 1) if total_orig_tokens > 0 else 0.0
        )

        return {
            "source_repo": self.source_repo,
            "message_count": len(messages),
            "original_total_tokens": total_orig_tokens,
            "compressed_total_tokens": total_comp_tokens,
            "saved_total_tokens": saved_total,
            "token_reduction_percentage": overall_reduction,
            "compressed_dialog": compressed_messages,
            "status": "DIALOG_COMPRESSED",
        }
