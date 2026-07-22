"""Comprehensive Integration Tests for Real Obsidian Vault Backend in AI Workforce OS v4.2."""

import os
import tempfile
from pathlib import Path
import pytest

from orchestrator.context.obsidian_config import resolve_obsidian_vault_path
from orchestrator.context.obsidian_rag import ObsidianVaultRAG
from orchestrator.security.permission_policy import ActionLevel, PermissionPolicy
from shared_knowledge import KnowledgeBridge
from v4_organization import (
    AutonomousAIOrganization,
    OrganizationalLearningRecord,
    OrganizationalMemory,
)


def test_obsidian_config_resolver_priority(monkeypatch):
    with tempfile.TemporaryDirectory() as tmpdir:
        vault_dir = Path(tmpdir) / "real_vault"
        vault_dir.mkdir()

        # 1. CLI Priority
        resolved = resolve_obsidian_vault_path(cli_vault_path=str(vault_dir))
        assert resolved == vault_dir.resolve()

        # 2. Env Var Priority
        monkeypatch.setenv("OBSIDIAN_VAULT_PATH", str(vault_dir))
        resolved_env = resolve_obsidian_vault_path()
        assert resolved_env == vault_dir.resolve()


def test_obsidian_config_non_existent_vault_warning(capsys):
    non_existent = Path("/non_existent_vault_path_abc_123")
    resolved = resolve_obsidian_vault_path(cli_vault_path=str(non_existent))

    assert resolved is None
    captured = capsys.readouterr()
    assert "Configured Obsidian Vault path does not exist" in captured.err


def test_obsidian_incremental_indexing():
    with tempfile.TemporaryDirectory() as tmpdir:
        vault_path = Path(tmpdir)
        rag = ObsidianVaultRAG(str(vault_path))

        # Initial index count
        assert rag.index_vault() == 0

        # Add new markdown file
        doc1 = vault_path / "Note1.md"
        doc1.write_text("# Note 1\nContent for note 1 with [[Note2]]", encoding="utf-8")

        assert rag.index_vault() == 1
        assert "note1" in rag._title_map

        # Modify file
        doc1.write_text("---\ntitle: Note 1 Updated\n---\n# Note 1 Updated\nUpdated content #tag1", encoding="utf-8")
        rag.index_vault()

        updated_doc = rag.get_document("Note 1 Updated")
        assert updated_doc is not None
        assert "tag1" in updated_doc["tags"]

        # Delete file
        doc1.unlink()
        assert rag.index_vault() == 0
        assert rag.get_document("Note 1 Updated") is None


def test_yaml_frontmatter_wikilinks_and_backlinks():
    with tempfile.TemporaryDirectory() as tmpdir:
        vault_path = Path(tmpdir)

        doc_a = vault_path / "Architecture.md"
        doc_a.write_text(
            "---\n"
            "title: Architecture ADR\n"
            "tags: [architecture, design]\n"
            "aliases: [ArchSpec]\n"
            "scope: ORGANIZATION\n"
            "---\n\n"
            "# Architecture Specification\n"
            "System layout using [[BackendService]].\n",
            encoding="utf-8",
        )

        doc_b = vault_path / "BackendService.md"
        doc_b.write_text(
            "# Backend Service\n"
            "Logic for backend microservice.\n",
            encoding="utf-8",
        )

        rag = ObsidianVaultRAG(str(vault_path))
        assert rag.index_vault() == 2

        doc_a_data = rag.get_document("Architecture ADR")
        assert doc_a_data is not None
        assert doc_a_data["frontmatter"]["scope"] == "ORGANIZATION"
        assert "architecture" in doc_a_data["tags"]
        assert "ArchSpec" in doc_a_data["aliases"]
        assert "BackendService" in doc_a_data["wikilinks"]

        doc_b_data = rag.get_document("BackendService")
        assert doc_b_data is not None
        assert "Architecture ADR" in doc_b_data["backlinks"]


def test_scoped_rag_retrieval():
    with tempfile.TemporaryDirectory() as tmpdir:
        vault_path = Path(tmpdir)

        (vault_path / "GlobalPolicy.md").write_text(
            "---\nscope: GLOBAL\n---\n# Global Security Policy\nEnforce Zero-Trust globally.",
            encoding="utf-8",
        )
        (vault_path / "DeptPolicy.md").write_text(
            "---\nscope: DEPARTMENT\n---\n# Department Policy\nDepartment guidelines.",
            encoding="utf-8",
        )

        rag = ObsidianVaultRAG(str(vault_path))

        # Query ORGANIZATION scope -> Should return GLOBAL scope doc as fallback, but filter out DEPARTMENT
        results = rag.query("Policy", scope="ORGANIZATION")
        scopes = [r["scope"] for r in results]
        assert "DEPARTMENT" not in scopes


def test_organizational_memory_write_and_read():
    with tempfile.TemporaryDirectory() as tmpdir:
        mem = OrganizationalMemory(vault_path=tmpdir)

        rec = OrganizationalLearningRecord(
            project_name="Payment Microservice",
            lessons_learned=["Enforce idempotent payment requests"],
            architecture_decisions=["ADR-02: Microservice API"],
            security_findings=["SEC-02: PCI-DSS Compliance"],
            failed_approaches=["Unencrypted token storage"],
            successful_patterns=["Pytest integration test suite"],
        )

        written_path = mem.save_project_learnings(rec)
        assert written_path is not None
        assert Path(written_path).exists()

        # Read back from Obsidian Vault
        learnings = mem.get_lessons_learned("Payment Microservice")
        assert len(learnings) >= 1
        assert "Payment_Microservice" in learnings[0]["title"] or "payment" in learnings[0]["content"].lower()


def test_research_to_obsidian_to_rag_to_coding_flow():
    with tempfile.TemporaryDirectory() as tmpdir:
        bridge = KnowledgeBridge(vault_path=tmpdir)

        # 1. Research Agent publishes knowledge to Real Obsidian Vault
        published_path = bridge.publish_research(
            title="OAuth2 Microservice ADR",
            content="Use OAuth2 Authorization Code flow with PKCE for microservices.",
            category="Security",
            tags=["oauth2", "security"],
        )
        assert published_path is not None

        # 2. Downstream Coding Agent queries context from RAG
        context = bridge.retrieve_context_for_agent("OAuth2 PKCE microservice")
        assert len(context) >= 1
        assert "OAuth2 Microservice ADR" in context[0]["title"]
        assert "oauth2" in context[0]["tags"]


def test_permission_policy_obsidian_protection():
    policy = PermissionPolicy()

    # Read/Create -> ALLOWED
    assert policy.classify_obsidian_action("read_knowledge", "Security/Note.md") == ActionLevel.ALLOWED
    assert policy.classify_obsidian_action("create_knowledge", "Research/Note.md") == ActionLevel.ALLOWED

    # Touch .obsidian/ -> BLOCKED
    assert policy.classify_obsidian_action("modify", ".obsidian/config.json") == ActionLevel.BLOCKED
    assert policy.classify_obsidian_action("read", "vault/.obsidian/plugins.json") == ActionLevel.BLOCKED

    # Modify ADR / Delete -> REQUIRES_APPROVAL
    assert policy.classify_obsidian_action("modify_adr", "Corporate_ADR/ADR-01.md") == ActionLevel.REQUIRES_APPROVAL
    assert policy.classify_obsidian_action("delete_knowledge", "Research/OldNote.md") == ActionLevel.REQUIRES_APPROVAL
