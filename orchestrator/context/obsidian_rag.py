"""Enterprise Obsidian Vault Incremental Indexer, AST Markdown Parser, and PageIndex RAG Integrator."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Set
from orchestrator.context.obsidian_config import resolve_obsidian_vault_path


@dataclass
class PageIndexPage:
    """A layout-preserved document page segment matching VectifyAI/PageIndex."""

    page_number: int
    parent_document_title: str
    layout_hierarchy: List[str]
    content: str
    tags: List[str]
    scope: str


@dataclass
class ObsidianDocument:
    """Rich parsed representation of an Obsidian markdown document."""

    title: str
    file_path: str
    full_path: str
    content: str
    mtime: float
    frontmatter: Dict[str, Any] = field(default_factory=dict)
    sections: List[Dict[str, str]] = field(default_factory=dict)
    tags: List[str] = field(default_factory=list)
    aliases: List[str] = field(default_factory=list)
    wikilinks: List[str] = field(default_factory=list)
    backlinks: List[str] = field(default_factory=list)
    scope: str = "ORGANIZATION"  # GLOBAL, ORGANIZATION, DEPARTMENT, PROJECT, TASK
    pages: List[PageIndexPage] = field(default_factory=list)

    def to_dict(self, score: float = 0.0, page_info: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Convert to structured dictionary for RAG query results."""
        res = {
            "title": self.title,
            "path": self.file_path,
            "file_path": self.file_path,
            "full_path": self.full_path,
            "content": self.content,
            "score": round(score, 2),
            "sections": self.sections,
            "tags": self.tags,
            "aliases": self.aliases,
            "wikilinks": self.wikilinks,
            "backlinks": self.backlinks,
            "frontmatter": self.frontmatter,
            "scope": self.scope,
            "is_page_index_enabled": True,
            "source_engine": "VectifyAI/PageIndex",
        }
        if page_info:
            res.update(page_info)
        return res


class ObsidianVaultRAG:
    """Enterprise PageIndex Document Indexer and Page-Scoped RAG Query Engine for Obsidian Vaults."""

    def __init__(self, vault_path: Optional[str] = None) -> None:
        self.vault_path: Optional[Path] = resolve_obsidian_vault_path(cli_vault_path=vault_path, create_if_missing=bool(vault_path))
        if not self.vault_path and vault_path:
            p = Path(vault_path)
            p.mkdir(parents=True, exist_ok=True)
            self.vault_path = p

        self._documents: Dict[str, ObsidianDocument] = {}  # full_path -> ObsidianDocument
        self._backlink_map: Dict[str, Set[str]] = {}  # title_lower -> set of source titles
        self._title_map: Dict[str, ObsidianDocument] = {}  # title_lower -> ObsidianDocument

        if self.vault_path and self.vault_path.exists():
            self.index_vault()

    def parse_markdown(self, full_path: Path, relative_path: str, content: str, mtime: float) -> ObsidianDocument:
        """Parse Markdown file extracting YAML Frontmatter, Headings, Wikilinks, Tags, Aliases, and PageIndex pages."""
        frontmatter: Dict[str, Any] = {}
        body = content

        # 1. Parse YAML Frontmatter
        if content.startswith("---"):
            parts = content.split("---", 2)
            if len(parts) >= 3:
                yaml_text = parts[1]
                body = parts[2]
                for line in yaml_text.splitlines():
                    if ":" in line:
                        k, v = line.split(":", 1)
                        k_clean = k.strip()
                        v_clean = v.strip().strip("\"'")
                        if v_clean.startswith("[") and v_clean.endswith("]"):
                            v_clean = [item.strip().strip("\"'") for item in v_clean[1:-1].split(",") if item.strip()]
                        frontmatter[k_clean] = v_clean

        title = frontmatter.get("title", full_path.stem)
        scope = frontmatter.get("scope", "ORGANIZATION")

        # 2. Extract Tags (#tag_name)
        tags: Set[str] = set()
        fm_tags = frontmatter.get("tags", [])
        if isinstance(fm_tags, list):
            tags.update(fm_tags)
        elif isinstance(fm_tags, str):
            tags.add(fm_tags)

        body_tags = re.findall(r"(?:^|\s)#([a-zA-Z0-9_\-/]+)", body)
        tags.update(body_tags)

        # 3. Extract Aliases
        aliases: List[str] = []
        fm_aliases = frontmatter.get("aliases", [])
        if isinstance(fm_aliases, list):
            aliases = fm_aliases
        elif isinstance(fm_aliases, str):
            aliases = [fm_aliases]

        # 4. Extract Wikilinks [[Target Note]]
        wikilinks: List[str] = []
        raw_wikilinks = re.findall(r"\[\[(.*?)\]\]", body)
        for wl in raw_wikilinks:
            target = wl.split("|")[0].strip()
            if target:
                wikilinks.append(target)

        # 5. Extract Headings & Sections
        sections: List[Dict[str, str]] = []
        current_heading = "Overview"
        current_text: List[str] = []

        for line in body.splitlines():
            if line.startswith("#"):
                if current_text:
                    sections.append({"heading": current_heading, "content": "\n".join(current_text).strip()})
                    current_text.clear()
                current_heading = line.lstrip("#").strip()
            else:
                current_text.append(line)

        if current_text:
            sections.append({"heading": current_heading, "content": "\n".join(current_text).strip()})

        # 6. PageIndex Layout-Preserving Page Chunking
        # Partition pages by '<!-- page -->', '<!-- slide -->', or by sections H1/H2.
        pages: List[PageIndexPage] = []
        raw_pages = re.split(r"<!--\s*(?:page|slide)\s*-->", body)
        
        page_num = 1
        for raw_page in raw_pages:
            trimmed_page = raw_page.strip()
            if not trimmed_page:
                continue

            # Further partition if page is exceptionally long (> 1000 characters)
            if len(trimmed_page) > 1000:
                sub_chunks = [trimmed_page[i:i+1000] for i in range(0, len(trimmed_page), 1000)]
                for chunk in sub_chunks:
                    pages.append(
                        PageIndexPage(
                            page_number=page_num,
                            parent_document_title=title,
                            layout_hierarchy=[current_heading],
                            content=chunk.strip(),
                            tags=sorted(list(tags)),
                            scope=scope if isinstance(scope, str) else "ORGANIZATION",
                        )
                    )
                    page_num += 1
            else:
                pages.append(
                    PageIndexPage(
                        page_number=page_num,
                        parent_document_title=title,
                        layout_hierarchy=[current_heading],
                        content=trimmed_page,
                        tags=sorted(list(tags)),
                        scope=scope if isinstance(scope, str) else "ORGANIZATION",
                    )
                )
                page_num += 1

        return ObsidianDocument(
            title=title,
            file_path=relative_path,
            full_path=str(full_path),
            content=content,
            mtime=mtime,
            frontmatter=frontmatter,
            sections=sections,
            tags=sorted(list(tags)),
            aliases=aliases,
            wikilinks=wikilinks,
            backlinks=[],
            scope=scope if isinstance(scope, str) else "ORGANIZATION",
            pages=pages,
        )

    def index_vault(self, vault_path: Optional[str] = None) -> int:
        """Incremental vault scanner ignoring .obsidian and cache folders."""
        if vault_path:
            self.vault_path = Path(vault_path)

        if not self.vault_path or not self.vault_path.exists():
            return 0

        current_files: Set[str] = set()

        for p in self.vault_path.rglob("*.md"):
            # Ignore .obsidian, .git, cache, and tmp folders
            rel_parts = p.relative_to(self.vault_path).parts
            if any(part.startswith(".") or part in ("__pycache__", "tmp", "temp") for part in rel_parts):
                continue

            full_path_str = str(p)
            current_files.add(full_path_str)
            mtime = p.stat().st_mtime

            # Incremental Check: Only re-parse if file is new or modified
            existing_doc = self._documents.get(full_path_str)
            if not existing_doc or existing_doc.mtime != mtime:
                try:
                    content = p.read_text(encoding="utf-8", errors="ignore")
                    rel_path = str(p.relative_to(self.vault_path))
                    doc = self.parse_markdown(p, rel_path, content, mtime)
                    self._documents[full_path_str] = doc
                    self._title_map[doc.title.lower()] = doc
                except Exception:
                    pass

        # Remove deleted files
        deleted_files = set(self._documents.keys()) - current_files
        for df in deleted_files:
            deleted_doc = self._documents.pop(df, None)
            if deleted_doc:
                self._title_map.pop(deleted_doc.title.lower(), None)

        # Re-build Backlink Graph
        self._rebuild_backlink_graph()
        return len(self._documents)

    def _rebuild_backlink_graph(self) -> None:
        """Build inbound backlink associations across documents."""
        self._backlink_map.clear()
        for doc in self._documents.values():
            doc.backlinks.clear()

        for doc in self._documents.values():
            for target in doc.wikilinks:
                target_lower = target.lower()
                if target_lower not in self._backlink_map:
                    self._backlink_map[target_lower] = set()
                self._backlink_map[target_lower].add(doc.title)

        for doc in self._documents.values():
            t_lower = doc.title.lower()
            if t_lower in self._backlink_map:
                doc.backlinks = sorted(list(self._backlink_map[t_lower]))

    def query(
        self, query_text: str, top_k: int = 5, scope: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Query knowledge base returning PageIndex page-scoped results with layout-preserving context."""
        if not self._documents:
            return []

        keywords = [k.lower() for k in query_text.split() if len(k) > 2]
        scored_pages = []

        for doc in self._documents.values():
            if scope and doc.scope.upper() != scope.upper() and doc.scope.upper() != "GLOBAL":
                continue

            for page in doc.pages:
                content_lower = page.content.lower()
                title_lower = page.parent_document_title.lower()

                score = 0.0
                for kw in keywords:
                    if kw in title_lower:
                        score += 5.0
                    if any(kw in tag.lower() for tag in page.tags):
                        score += 3.0
                    score += content_lower.count(kw) * 1.0

                if score > 0:
                    scored_pages.append((score, page, doc))

        scored_pages.sort(key=lambda x: x[0], reverse=True)
        
        # Deduplicate to avoid returning the exact same page segments multiple times if top_k is small
        seen_pages = set()
        results = []
        for score, page, doc in scored_pages:
            page_id = (page.parent_document_title, page.page_number)
            if page_id in seen_pages:
                continue
            seen_pages.add(page_id)

            page_info = {
                "page_number": page.page_number,
                "layout_hierarchy": page.layout_hierarchy,
                "page_content": page.content,
                "is_page_scoped": True,
            }
            results.append(doc.to_dict(score=score, page_info=page_info))
            if len(results) >= top_k:
                break

        return results

    def search_vault(self, query_text: str) -> List[Dict[str, Any]]:
        """Search vault pages matching query."""
        return self.query(query_text, top_k=10)

    def get_document(self, title: str) -> Optional[Dict[str, Any]]:
        """Get document by title."""
        doc = self._title_map.get(title.lower())
        return doc.to_dict() if doc else None

    def get_related_documents(self, title: str) -> List[Dict[str, Any]]:
        """Get documents linked via wikilinks or backlinks to the target document."""
        doc = self._title_map.get(title.lower())
        if not doc:
            return []

        related_titles = set(doc.wikilinks + doc.backlinks)
        related_docs = []
        for rt in related_titles:
            rd = self._title_map.get(rt.lower())
            if rd:
                related_docs.append(rd.to_dict())
        return related_docs
