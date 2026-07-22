"""Layer 3: Shared Knowledge Bridge connecting Research, Obsidian, RAG, and Coding Agents with Scoped Access."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional
from orchestrator.context.obsidian_rag import ObsidianVaultRAG
from orchestrator.context.obsidian_config import resolve_obsidian_vault_path


class KnowledgeBridge:
    """Shared Knowledge Bridge enabling cross-agent learning via Real Obsidian Vault RAG with Scoped Access."""

    def __init__(self, vault_path: Optional[str] = None) -> None:
        resolved = resolve_obsidian_vault_path(cli_vault_path=vault_path, create_if_missing=bool(vault_path))
        self.vault_path: Optional[Path] = resolved
        if not self.vault_path and vault_path:
            p = Path(vault_path)
            p.mkdir(parents=True, exist_ok=True)
            self.vault_path = p

        self.rag = ObsidianVaultRAG(str(self.vault_path) if self.vault_path else None)

    def publish_research(
        self,
        title: str,
        content: str,
        category: str = "Research",
        scope: str = "ORGANIZATION",
        tags: Optional[List[str]] = None,
        aliases: Optional[List[str]] = None,
    ) -> Optional[str]:
        """Publish research or technical knowledge into the Real Obsidian Vault with YAML Frontmatter."""
        if not self.vault_path:
            # Safe default fallback
            self.vault_path = Path.cwd() / ".shared_vault"
            self.vault_path.mkdir(parents=True, exist_ok=True)
            self.rag = ObsidianVaultRAG(str(self.vault_path))

        cat_dir = self.vault_path / category
        cat_dir.mkdir(parents=True, exist_ok=True)

        filename = f"{title.replace(' ', '_')}.md"
        doc_path = cat_dir / filename

        tag_list = tags or [category.lower(), "knowledge_bridge"]
        alias_list = aliases or []

        tags_str = ", ".join(f'"{t}"' for t in tag_list)
        aliases_str = ", ".join(f'"{a}"' for a in alias_list)

        frontmatter_str = (
            "---\n"
            f'title: "{title}"\n'
            f'category: "{category}"\n'
            f'scope: "{scope}"\n'
            f"tags: [{tags_str}]\n"
            f"aliases: [{aliases_str}]\n"
            "---\n\n"
        )

        full_content = frontmatter_str + content
        doc_path.write_text(full_content, encoding="utf-8")

        # Incremental index update so published knowledge is immediately queryable
        self.rag.index_vault(str(self.vault_path))
        return str(doc_path)

    def retrieve_context_for_agent(
        self, task_description: str, top_k: int = 3, scope: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Retrieve relevant shared knowledge for a downstream agent with optional scope filtering."""
        return self.rag.query(task_description, top_k=top_k, scope=scope)
