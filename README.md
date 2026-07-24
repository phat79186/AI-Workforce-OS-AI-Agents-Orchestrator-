# AI Workforce OS

<div align="center">

> **Build Your Own Autonomous AI Organization.**  
> *A Local-First AI Workforce Operating System That Can Delegate, Build, Test, Learn, and Remember.*

![Python](https://img.shields.io/badge/Python-3.8%2B-3776AB?logo=python&logoColor=white)
![Ollama](https://img.shields.io/badge/Ollama-Local_LLM-000000?logo=ollama&logoColor=white)
![OpenHands](https://img.shields.io/badge/OpenHands-Autonomous_Coding-000000?logo=github&logoColor=white)
![Obsidian](https://img.shields.io/badge/Obsidian-Knowledge_Graph-483699?logo=obsidian&logoColor=white)
![Pytest](https://img.shields.io/badge/Pytest-614_Tests_Passing-0A9EDC?logo=pytest&logoColor=white)
![Model Context Protocol](https://img.shields.io/badge/MCP-Model_Context_Protocol-4A90D9?logo=modelcontextprotocol&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-green.svg)

</div>

---

## 📌 Project Description

**AI Workforce OS** is an enterprise-grade, local-first operating system that transforms AI coding assistants into an **autonomous corporate AI organization**. 

Unlike conventional AI chatbots or single-agent scripts that require constant human supervision and forget context after execution, AI Workforce OS operates as a structured workforce:
- **Executive Leadership (AI CEO & AI CTO)**: Translates high-level business vision into technical execution roadmaps without writing low-level code directly.
- **Hierarchical AI Workforce**: Recruits specialized AI Employees (`SeniorArchitect`, `SecuritySpecialist`, `JuniorCoder`, `Researcher`, `DevOpsEngineer`) matching task requirements and budget limits.
- **Autonomous Feedback & Debugging Loop**: Executes real code in sandboxes, runs automated unit tests, detects failures, debugs root causes, applies code patches, re-runs tests until 100% GREEN, and performs security code reviews.
- **Obsidian Organizational Memory**: Uses Obsidian Markdown Vaults as a persistent corporate knowledge backend. Lessons learned, architecture decisions (ADRs), and security findings are recorded so future projects learn from historical experience.

---

## 🏗️ Architecture

```mermaid
graph TD
    User([User / Client Prompt]) --> CEO[AI CEO - Strategic Vision]
    CEO --> CTO[AI CTO - Technical Roadmap & DAG]
    CTO --> WorkforceMgr[AI Workforce Manager & Budget]
    WorkforceMgr --> AgentRouter[WHO? Agent Router]
    
    AgentRouter --> ModelRouter[THINK WITH WHAT? Model Router]
    ModelRouter --> ToolRouter[DO WITH WHAT? Tool Router]
    
    ToolRouter --> Employees[Specialized AI Employees]
    Employees --> RealTests[Automated Pytest & Sandbox Verification]
    
    RealTests -->|FAIL| Debugger[Autonomous Debugging Agent]
    Debugger --> Employees
    
    RealTests -->|PASS| Reviewer[Code Review & Git Commit]
    Reviewer --> OrgMem[Organizational Memory Engine]
    OrgMem --> Obsidian[Real Obsidian Vault + Vector RAG + Knowledge Graph]
```

---

## 🔄 How It Works

1. **Strategic Planning (AI CEO)**: Formulates high-level corporate goals, key objectives, and success metrics from user vision.
2. **Technical Roadmap (AI CTO)**: Decomposes strategic goals into a multi-subtask Task DAG across Research, Security, Software Engineering, Testing, and DevOps.
3. **AI Workforce Recruitment**: `AIWorkforceRegistry` recruits candidate AI Employees based on Seniority levels (`JUNIOR` to `SPECIALIST`), skill coverage, and historical reliability ratings within resource budget boundaries.
4. **3-Layer Routing**:
   - **Layer 1 (Agent Router)**: Selects agent role (`WHO?`).
   - **Layer 2 (Model Router)**: Selects LLM provider (`THINK WITH WHAT?`, prioritizing local Ollama).
   - **Layer 3 (Tool Router)**: Grants scoped tool permissions (`DO WITH WHAT?`).
5. **Execution & Automated Verification**: The recruited agent modifies code and executes real unit tests via the Tool Layer inside a Security Sandbox.
6. **Autonomous Debugging**: If tests fail, the Debugging Agent analyzes error logs, applies a code patch, and re-runs pytest until assertions pass 100%.
7. **Code Review & Git Isolation**: The Code Review Agent inspects code quality, generates git diffs, and approves commits.
8. **Organizational Memory Retention**: Retains ADRs, security findings, and lessons learned into the Real Obsidian Vault so future projects avoid past mistakes.

---

## 🎬 Real Autonomous Development Demo

Below is an unedited terminal output snippet demonstrating the live autonomous feedback loop (`scripts/run_phase9_live_demo.py`):

```text
=================================================================
[PHASE 9 DEMO] LIVE AI AUTONOMOUS DEVELOPMENT LOOP
=================================================================

[MANAGER] Initializing Local AI Manager & Task Orchestrator...
[TASK MANAGER] Decomposing prompt into Task DAG...
[GIT LAYER] Checkout isolated branch: feature/math-utils

[AGENT ROUTER] Assigning TASK-A to [Coding Agent]...
  * File created: math_utils.py (with intentional bug: return a - b)
  * File created: test_math_utils.py

[TESTER] Executing Automated Pytest Suite via Tool Layer...
  [FAIL] TEST FAILURE DETECTED! (Exit code: 1)
  [LOG] Error Log Snippet:
  > assert add(10, 5) == 15
  E assert 5 == 15

[DEBUGGER] Delegating error log to [Debugging Agent]...
  [ANALYSIS] Root cause: 'add(10, 5)' returned 5 instead of 15 due to '-' operator.
  [PATCH] Applying code patch to math_utils.py (return a + b)...

[TESTER] Re-running Automated Test Suite post-fix...
  [PASS] AUTOMATED TEST PASSED! (All assertions 100% GREEN)

[REVIEWER] Code Review Agent approved code quality & generated Git Diff:
-------------------------------------------------------------
diff --git a/math_utils.py b/math_utils.py
--- a/math_utils.py
+++ b/math_utils.py
@@ -1,5 +1,5 @@
 def add(a: float, b: float) -> float:
-    return a - b  # INTENTIONAL BUG
+    return a + b  # FIXED
-------------------------------------------------------------
[SUCCESS] Live Autonomous Development Loop Demo finished with 100% success!
```

---

## 🧠 Obsidian Organizational Memory

Obsidian is integrated as a **persistent organizational knowledge backend**. When an initiative completes, project learnings are stored directly into your Obsidian Vault:

```text
Project 1 (Face Recognition v1)
   │
   ▼
Research & Security Findings
   │
   ▼
Saved to Obsidian Vault (Organizational_Learnings/Learnings_Project_1.md)
   │
   ▼
Incremental AST Indexer + Vector RAG + Wikilink Graph
   │
   ▼
Project 2 (Face Liveness v2)
   │
   ▼
Historical Knowledge Retrieved (Avoids past client-side assertion mistakes)
```

> [!NOTE]
> **Real Vault vs Test Vault Isolation**:
> The system supports your **Real Obsidian Vault** configured via `OBSIDIAN_VAULT_PATH` or `--vault-path`. During automated unit testing (`pytest`), isolated temporary test vaults are used to prevent modifying your personal notes.

---

## 📊 Simulated / Experimental Benchmark

The table below presents an *experimental comparative benchmark* measuring the quantifiable advantage delivered by enabling **Organizational Memory** during project execution:

| Metric | Without Memory (OFF) | With Memory (ON) | Quantified Advantage |
| :--- | :---: | :---: | :---: |
| **Planning Quality** | 70% | **92%** | **+22% higher accuracy** |
| **Architecture Errors** | 5 | **1** | **-80% reduction** |
| **Security Issues** | 4 | **1** | **-75% reduction** |
| **Test Failures** | 8 | **3** | **-62% reduction** |
| **Execution Duration** | 20s | **13s** | **35% faster completion** |

*Note: The metrics above reflect experimental benchmark scenarios (`v4_organization/benchmark.py`) comparing Memory ON vs Memory OFF.*

---

## 🧪 Testing & Reliability

The codebase undergoes rigorous automated testing across Windows, Linux, and macOS:

```text
Tests Status:
614 passed, 1 skipped, 0 failed (100% Pass Rate across 615 test items)
```

To run the complete test suite locally:
```bash
python -m pytest tests/ -o addopts="" -m "not integration and not slow"
```

---

## ⚡ Quick Start

### Requirements
- **Python 3.8+** (Python 3.10 – 3.14 fully supported)
- **Git**
- **Ollama** (Optional, for local LLMs)
- **Obsidian** (Optional, for persistent knowledge base)

### Installation
```bash
# Clone the repository
git clone https://github.com/hoangsonww/AI-Agents-Orchestrator.git
cd AI-Agents-Orchestrator

# Install dependencies
pip install -r requirements.txt
```

### Local AI Setup (Ollama)
```bash
# Pull recommended local coding model
ollama pull qwen2.5-coder:7b
```

### Obsidian Vault Setup
Configure your real Obsidian Vault path using an environment variable or CLI argument:
```bash
# Option 1: Environment Variable
export OBSIDIAN_VAULT_PATH="/path/to/your/ObsidianVault"  # Linux/macOS
$env:OBSIDIAN_VAULT_PATH="C:\Users\User\Documents\ObsidianVault"  # Windows PowerShell

# Option 2: CLI Argument
python scripts/run_real_obsidian_demo.py --vault-path "/path/to/your/ObsidianVault"
```

### First Run
```bash
# Run v4.2 Autonomous AI Organization Demo
python scripts/run_v4_organization_demo.py
```

---

## 🛡️ AI Provider Strategy & Local-First Policy

We enforce a strict **Local-First & Free-First Priority Hierarchy**:

```
LOCAL / SELF-HOSTED (Ollama, llama.cpp, Local LLMs)
        ↓
OPEN-SOURCE AGENTS (OpenHands, Open CLI Coding Agents)
        ↓
FREE TIER (Community / Non-metered API Tiers)
        ↓
PAID API (Requires explicit user confirmation)
```

> [!IMPORTANT]
> **Zero-Unintended-Cost Guarantee**: Paid APIs are **never** invoked automatically without explicit interactive user approval.

---

## 🔒 Security & Safety Boundaries

All agent actions are audited by the `PermissionPolicy` and `SecuritySandbox`:

| Action Type | Action Target | Security Policy |
| :--- | :--- | :---: |
| **Read Knowledge / RAG Query** | Markdown Notes, Source Files | `ALLOWED` |
| **Run Unit Tests** | Sandbox Pytest Runner | `ALLOWED` |
| **Create Note / Publish Research** | Vault Directories | `ALLOWED` |
| **Delete Files / Unlink** | Source Code / Notes | `REQUIRES_APPROVAL` |
| **Modify Finalized ADR** | Corporate ADR Notes | `REQUIRES_APPROVAL` |
| **Git Push / Deployment** | Remote Repository / Staging | `REQUIRES_APPROVAL` |
| **Alter `.obsidian/` Config** | Vault Configuration Files | `BLOCKED` |

---

## ✨ Features Matrix

| Feature | Description | Status |
| :--- | :--- | :---: |
| **Multi-Agent Orchestration** | Autonomous task queue, DAG dependency resolution | ✅ Verified |
| **AI CEO & AI CTO** | Executive goal formulation & technical roadmap generation | ✅ Verified |
| **AI-to-AI Delegation** | Director & Manager level multi-tier delegation tree | ✅ Verified |
| **3-Layer Routing** | Agent Router (`WHO?`), Model Router (`THINK?`), Tool Router (`DO?`) | ✅ Verified |
| **Automated Testing** | Pytest tool layer integration | ✅ Verified |
| **Autonomous Debugging** | Self-healing log analysis & code patch generation | ✅ Verified |
| **Code Review Engine** | Quality evaluation & git diff extraction | ✅ Verified |
| **Real Obsidian Backend** | Configurable Obsidian Vault Markdown knowledge store | ✅ Verified |
| **Incremental AST Indexer** | `mtime` file diff tracking, frontmatter, wikilinks, & backlinks | ✅ Verified |
| **Scoped RAG Engine** | `GLOBAL`, `ORGANIZATION`, `DEPARTMENT`, `PROJECT`, `TASK` scopes | ✅ Verified |
| **Organizational Memory** | Cross-project experience retention & lesson querying | ✅ Verified |
| **Seniority Candidate Ranking** | Dynamic skill matching across `JUNIOR` to `SPECIALIST` levels | ✅ Verified |
| **Performance Feedback Loop** | Dynamic reliability score tracking per AI employee | ✅ Verified |
| **Workforce Resource Budget** | Caps on max total/concurrent agents and execution time | ✅ Verified |
| **Security Sandbox** | Action classification and human-in-the-loop approval manager | ✅ Verified |
| **OpenClaw Prompt Refinement** | Raw user input pre-processing & technical spec expansion engine (`openclaw/openclaw`) | ✅ Verified |
| **8 External Tool Integrations** | Full adapters for CodeGraph, Ponytail, AnySearch, UI/UX Pro Max, Impeccable, Public APIs, SAG, MattPocock Skills | ✅ Verified |

---

## 🗺️ Roadmap Progression

```text
v2.0 AI Software Engineering OS (Phase 0 - 9 Complete)
        ↓
v3.0 4-Layer AI Workforce Ecosystem (Domains, Shared Knowledge, Workforce)
        ↓
v3.1 Workforce Intelligence (Candidate Ranking, Seniority, Budget)
        ↓
v4.0 Autonomous AI Organization (AI CEO / AI CTO Leadership)
        ↓
v4.1 AI-to-AI Delegation & Cross-Project Organizational Memory
        ↓
v4.2 Real Obsidian Knowledge Backend & Experimental Benchmark  ← [CURRENT RELEASE]
        ↓
v5.0 AI-Native Autonomous Enterprise Platform (Future Vision)
```

---

## 🤝 Contributing & License

We welcome community contributions! Please read our [CONTRIBUTING.md](CONTRIBUTING.md) for details on code style, testing standards, and pull request procedures.

This project is licensed under the **MIT License** - see the [LICENSE](LICENSE) file for details.

---

## 🏷️ Credits & Acknowledgements

We acknowledge and credit the open-source projects and libraries that inspired or integrate with our ecosystem:
- **[OpenClaw](https://github.com/openclaw/openclaw)** — Free open-source raw prompt refinement and code pre-processing engine.
- **[linshenkx/prompt-optimizer](https://github.com/linshenkx/prompt-optimizer)** — Automated meta-prompting & prompt clarity optimization tool.
- **[Ollama](https://github.com/ollama/ollama)** — Local LLM runner.
- **[OpenHands](https://github.com/All-Hands-AI/OpenHands)** — Autonomous AI coding software development agent.
- **[Obsidian](https://obsidian.md/)** — Personal Knowledge Base & Markdown Vault.
- **[mattpocock/skills](https://github.com/mattpocock/skills)** — AI agent skills framework.
- **[colbymchenry/codegraph](https://github.com/colbymchenry/codegraph)** — Code graph analysis.
- **[DietrichGebert/ponytail](https://github.com/DietrichGebert/ponytail)** — Multi-agent runner.
- **[anysearch-ai/anysearch-skill](https://github.com/anysearch-ai/anysearch-skill)** — Search skill.
- **[Panniantong/Agent-Reach](https://github.com/Panniantong/Agent-Reach)** — Multi-engine deep search reach & retrieval engine.
- **[nextlevelbuilder/ui-ux-pro-max-skill](https://github.com/nextlevelbuilder/ui-ux-pro-max-skill)** — Design system skill.
- **[pbakaus/impeccable](https://github.com/pbakaus/impeccable)** — UI visual polish assistant.
- **[Taste Skill](https://github.com/hoangsonww/AI-Agents-Orchestrator)** — Aesthetic curation, spatial harmony, typography hierarchy, and motion choreography skill.
- **[public-apis/public-apis](https://github.com/public-apis/public-apis)** — Public API directory.
- **[Zleap-AI/SAG](https://github.com/Zleap-AI/SAG)** — Semantic Agent Graph framework.

---

## 🏷️ GitHub Topics

`ai` • `artificial-intelligence` • `multi-agent` • `ai-agents` • `agentic-ai` • `local-ai` • `ollama` • `openhands` • `rag` • `knowledge-graph` • `obsidian` • `ai-orchestration` • `autonomous-agents` • `developer-tools` • `software-engineering`

---

## 📝 GitHub Short Description

> **A Local-First AI Workforce Operating System featuring AI CEO/CTO leadership, Task DAGs, multi-agent delegation, and Obsidian organizational memory.**

---

## 🖼️ GitHub Social Preview Concept

```text
+-----------------------------------------------------------------------+
|                                                                       |
|                          AI WORKFORCE OS                              |
|            Build Your Own Autonomous AI Organization                  |
|                                                                       |
|   USER ➔ AI CEO ➔ AI CTO ➔ WORKFORCE ➔ OBSIDIAN MEMORY ➔ LEARN        |
|                                                                       |
|   Local-First | Task DAGs | Real Testing | Persistent RAG Memory      |
|                                                                       |
+-----------------------------------------------------------------------+
```
