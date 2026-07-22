"""Configuration resolver for Real Obsidian Vault path across CLI, Environment Variables, and Config Files."""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Optional


def resolve_obsidian_vault_path(
    cli_vault_path: Optional[str] = None,
    config_vault_path: Optional[str] = None,
    create_if_missing: bool = False,
) -> Optional[Path]:
    """Resolve Real Obsidian Vault path following priority order:
    1. CLI Argument (`--vault-path`)
    2. Environment Variable (`OBSIDIAN_VAULT_PATH`)
    3. Configuration File (`config_vault_path`)
    4. Default Safe Behavior (Return None if unconfigured)
    """
    raw_path: Optional[str] = None

    # Priority 1: CLI Argument
    if cli_vault_path:
        raw_path = cli_vault_path
    # Priority 2: Environment Variable
    elif os.environ.get("OBSIDIAN_VAULT_PATH"):
        raw_path = os.environ.get("OBSIDIAN_VAULT_PATH")
    # Priority 3: Configuration File
    elif config_vault_path:
        raw_path = config_vault_path

    if not raw_path:
        return None

    resolved_path = Path(raw_path).expanduser().resolve()

    if not resolved_path.exists():
        if create_if_missing:
            resolved_path.mkdir(parents=True, exist_ok=True)
        else:
            print(f"[OBSIDIAN WARNING] Configured Obsidian Vault path does not exist: '{resolved_path}'", file=sys.stderr)
            return None

    if not resolved_path.is_dir():
        print(f"[OBSIDIAN ERROR] Configured Obsidian Vault path is not a directory: '{resolved_path}'", file=sys.stderr)
        return None

    return resolved_path
