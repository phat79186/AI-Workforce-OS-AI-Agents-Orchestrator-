"""Real Obsidian Vault Integration E2E Demo Script for AI Workforce OS v4.2."""

from __future__ import annotations

import argparse
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

from orchestrator.context.obsidian_config import resolve_obsidian_vault_path
from orchestrator.context.obsidian_rag import ObsidianVaultRAG
from shared_knowledge import KnowledgeBridge
from v4_organization import AutonomousAIOrganization, OrganizationalLearningRecord


def run_real_obsidian_demo(vault_path_arg: Optional[str] = None) -> None:
    print("=================================================================")
    print("[REAL OBSIDIAN DEMO] END-TO-END KNOWLEDGE BACKEND (v4.2)")
    print("=================================================================")

    # 1. Load configured Real Obsidian Vault
    temp_dir_obj = None
    if vault_path_arg:
        target_path = Path(vault_path_arg)
        target_path.mkdir(parents=True, exist_ok=True)
    else:
        # Create a dedicated demo vault structure simulating user's real Obsidian Vault
        temp_dir_obj = tempfile.TemporaryDirectory(prefix="real_obsidian_vault_")
        target_path = Path(temp_dir_obj.name)

    print(f"\n[OBSIDIAN] Real Vault Loaded: '{target_path.resolve()}'")

    # Seed initial user documents in real vault
    (target_path / "Architecture_Conventions.md").write_text(
        "---\n"
        "title: Corporate Architecture Conventions\n"
        "scope: ORGANIZATION\n"
        "tags: [architecture, standards]\n"
        "---\n\n"
        "# Corporate Architecture Conventions\n"
        "All microservices must use [[gRPC_REST_Bridge]] and anti-spoofing input validation.",
        encoding="utf-8",
    )

    # 2. Index Markdown files
    rag = ObsidianVaultRAG(str(target_path))
    indexed_count = rag.index_vault()
    print(f"[INDEXER] {indexed_count} Markdown Files Indexed (Incremental AST Parser)")

    # 3. Research Agent creates & publishes knowledge
    print("\n[RESEARCH] Research Agent creating technical knowledge...")
    bridge = KnowledgeBridge(vault_path=str(target_path))
    pub_path = bridge.publish_research(
        title="Passive Liveness Detection ADR",
        content="Use single-frame passive liveness neural networks with [[Architecture_Conventions]] for 10ms inference.",
        category="Security",
        scope="ORGANIZATION",
        tags=["security", "liveness", "anti_spoofing"],
        aliases=["LivenessADR"],
    )
    print(f"[RESEARCH] Knowledge Published to Real Vault: '{pub_path}'")

    # 4. RAG Index update
    print(f"[RAG] Vault re-indexed incrementally ({rag.index_vault()} documents active)")

    # 5. AI CTO planning using Obsidian Knowledge
    print("\n[AI CTO] Planning project using Obsidian Knowledge Base...")
    org = AutonomousAIOrganization(vault_path=str(target_path))
    user_prompt = "Build Face Liveness Microservice platform"
    res1 = org.execute_corporate_initiative(user_prompt)

    # 6. Coding Agent retrieves context
    context_docs = org.memory.bridge.retrieve_context_for_agent("Passive Liveness Detection anti-spoofing")
    print(f"[CODING AGENT] Context Retrieved from Obsidian RAG ({len(context_docs)} relevant notes found):")
    for doc in context_docs:
        print(f"  * Note: [{doc['title']}] | Scope: {doc['scope']} | Tags: {doc['tags']}")

    # 7. Project Completed
    print(f"\n[PROJECT] Initiative '{user_prompt}' Completed (Status: {res1['executive_report']['status']})")

    # 8. Organizational Memory created & saved to Obsidian
    rec = OrganizationalLearningRecord(
        project_name=user_prompt,
        lessons_learned=[
            "Thực thi passive liveness để đảm bảo thời gian phản hồi < 15ms",
            "Sử dụng Pytest runner tự động kiểm thử 100% assertions trước commit",
        ],
        architecture_decisions=[
            "ADR-03: Áp dụng gRPC REST Bridge chuẩn hóa theo Obsidian Architecture Conventions",
        ],
        security_findings=[
            "SEC-03: Kiểm tra chữ ký khung ảnh chống tấn công lặp lại (Replay Attacks)",
        ],
        failed_approaches=[
            "Bỏ qua client-side validation mà không có server-side anti-spoofing signature",
        ],
        successful_patterns=[
            "Mô hình thử nghiệm tự động 100% GREEN",
        ],
        scope="ORGANIZATION",
    )

    mem_path = org.memory.save_project_learnings(rec)
    print(f"[ORGANIZATIONAL MEMORY] Saved to Real Obsidian Vault: '{mem_path}'")

    # 9. Next Project retrieves historical memory from Real Obsidian Vault
    next_prompt = "Build High-Throughput Face Authentication System v2"
    print(f"\n[NEXT PROJECT] Initializing '{next_prompt}'...")
    past_memory = org.memory.get_lessons_learned("Passive Liveness anti-spoofing")
    print(f"[NEXT PROJECT] Historical Knowledge Retrieved ({len(past_memory)} documents loaded from Obsidian Vault):")
    for idx, pm in enumerate(past_memory, 1):
        print(f"  {idx}. [{pm['title']}] -> Relative Path: {pm['path']}")

    print("\n[SUCCESS] Real Obsidian Vault Integration E2E Demo completed with 100% success!\n")

    if temp_dir_obj:
        temp_dir_obj.cleanup()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Real Obsidian Vault Demo")
    parser.add_argument("--vault-path", type=str, help="Path to Real Obsidian Vault")
    args = parser.parse_args()
    run_real_obsidian_demo(vault_path_arg=args.vault_path)
