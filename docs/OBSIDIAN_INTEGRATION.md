# Real Obsidian Vault Integration Guide (AI Workforce OS v4.2)

This document provides a comprehensive operational guide for integrating a **Real Obsidian Vault** as the persistent enterprise Knowledge Backend for the AI Workforce Operating System.

---

## Architecture Flow

```text
Obsidian Vault (User Configured)
            ↕
Obsidian Knowledge Indexer (Incremental AST Parser)
            ↕
RAG / Vector Retrieval (Structured Metadata)
            ↕
Knowledge Graph (Wikilinks & Inbound Backlinks)
            ↕
Organizational Memory (Corporate ADRs, Lessons Learned)
            ↕
AI CEO / AI CTO / Directors / Managers
            ↕
AI Employees / Domain Agents
```

---

## 1. Vault Path Configuration Hierarchy

The system resolves the target Obsidian Vault path using the following strict resolution priority:

```text
CLI Argument (--vault-path)
    ↓
Environment Variable (OBSIDIAN_VAULT_PATH)
    ↓
Configuration File (config_vault_path)
    ↓
Default Safe Behavior (Returns None with Warning if path is unconfigured or non-existent)
```

### Usage Examples

#### Via CLI Argument:
```bash
python scripts/run_real_obsidian_demo.py --vault-path "C:\Users\User\Documents\Obsidian\MyVault"
```

#### Via Environment Variable (Cross-Platform):
- **Windows (PowerShell)**:
  ```powershell
  $env:OBSIDIAN_VAULT_PATH="C:\Users\User\Documents\Obsidian\MyVault"
  python scripts/run_real_obsidian_demo.py
  ```
- **Linux / macOS**:
  ```bash
  export OBSIDIAN_VAULT_PATH="/home/user/Obsidian/MyVault"
  python scripts/run_real_obsidian_demo.py
  ```

---

## 2. Incremental AST Markdown Indexer (`obsidian_rag.py`)

- **Automatic Exclusion**: Skips `.obsidian/`, `.git/`, `__pycache__`, and temporary folders.
- **Incremental Indexing**: Uses file modification timestamp (`mtime`) to re-parse only added or updated `.md` files.
- **YAML Frontmatter Parser**: Parses custom attributes (`title`, `category`, `scope`, `tags`, `aliases`).
- **Wikilink & Backlink Graph**: Extracts `[[Target Note Title]]` outbound links and computes inbound backlink mappings across all vault notes.
- **Section Extraction**: Parses Markdown headings (`# H1`, `## H2`, `### H3`) and associated body text.

---

## 3. Scoped Knowledge Access & RAG Retrieval

Knowledge retrieval supports hierarchical scopes to ensure appropriate access boundaries across agent roles:

| Scope | Access Level | Description |
| :--- | :--- | :--- |
| **`GLOBAL`** | All Agents | System-wide security rules, global architecture standards |
| **`ORGANIZATION`** | CEO, CTO, Directors | Corporate ADRs, organizational lessons learned |
| **`DEPARTMENT`** | Department Managers | Engineering conventions, DevOps deployment specs |
| **`PROJECT`** | Assigned Team | Project-specific user stories & module contracts |
| **`TASK`** | Individual Employee | Subtask scratch notes & unit test requirements |

---

## 4. Security & Protection Model (`permission_policy.py`)

To protect user Obsidian Vault notes from unwanted modification or accidental deletion, actions are governed by strict safety rules:

```text
Read Knowledge / RAG Query       ──► ALLOWED
Create New Note                  ──► ALLOWED
Save Organizational Memory       ──► ALLOWED
Modify Existing Corporate ADR    ──► REQUIRES_APPROVAL
Delete Knowledge File            ──► REQUIRES_APPROVAL
Modify .obsidian/ Configuration  ──► BLOCKED
```

---

## 5. Bidirectional Knowledge Bridge Workflow

1. **Research Phase**: Research Agent publishes technical surveys and ADRs directly to Real Obsidian Vault under `Security/` or `Research/`.
2. **Indexing Phase**: Incremental AST Indexer updates RAG in-memory graph.
3. **Planning Phase**: AI CTO queries RAG for architectural conventions.
4. **Implementation Phase**: Coding Agent retrieves relevant Markdown notes with structured metadata.
5. **Memory Phase**: Upon project completion, `OrganizationalMemory` formats `Organizational_Learnings/Project_Name.md` with YAML frontmatter and saves it directly to Real Obsidian Vault.
6. **Cross-Project Learning Phase**: Future projects consult past organizational learnings to avoid repeating previous mistakes.
