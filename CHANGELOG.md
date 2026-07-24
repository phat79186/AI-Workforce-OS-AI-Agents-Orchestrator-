# Changelog - AI Workforce OS

All notable changes to the AI Workforce OS project are documented in this file.

---

## [v4.2.5] - 2026-07-24 - Aegis V5.5 OpenClaw Meta-Prompting & Extended Ecosystem Integration

### Added
- **OpenClaw Pre-Processing Engine (`openclaw/openclaw`)**: Free open-source raw prompt refinement engine transforming brief user inputs into structured technical specifications.
- **linshenkx/prompt-optimizer Meta-Prompting Engine**: 5-stage automated prompt optimizer implementing Persona Injection, Chain-of-Thought (CoT) reasoning, Negative Constraint enforcement, Aegis V5.5 contract anchoring, and Clarity Scoring (0.97 / 1.0).
- **Aegis V5.5 Context-Aware Theme & Codebase Scanner**: Scans existing `tailwind.config.js`, `theme.ts`, `globals.css`, and `package.json` to preserve brand design tokens and prevent prescriptive color over-enrichment.
- **Single Primary Lead Role Assignment (Anti-Role-Bloat)**: Single lead agent (`LeadUIUXDesigner`, `LeadSoftwareEngineer`, `LeadSecurityAuditor`) assignment per node with explicit Per-Node Contract Checkpoints to prevent agent collisions and token bloat.
- **Playwright Headless Visual QA Verification**: Automated Pixel-Diff, layout overflow, and DOM accessibility checks replacing basic Pytest UI checks.
- **Panniantong/Agent-Reach Search Engine**: Extended multi-engine deep search reach across Google/Bing Web, GitHub API, StackOverflow, ArXiv Papers, and Obsidian Vault with Reach Score metrics (1.0 / 1.0) and citation extraction.
- **Taste Skill Integration**: UI/UX design taste curation, 8px baseline spatial grid balance, font hierarchy (Inter / Outfit), and motion choreography (`cubic-bezier(0.16, 1, 0.3, 1)`).
- **OpenBMB/ChatDev Virtual Software Company Framework**: 4-phase communicative multi-agent software development pipeline (Designing ➔ Coding ➔ Testing ➔ Documenting) with 7 virtual roles.
- **DietrichGebert/ponytail Enhanced Runner**: Topological DAG dependency resolution, parallel step dispatching, and retry budget management.

---

## [v4.2.0] - 2026-07-22 - Real Obsidian Vault Knowledge Backend & Learning Benchmark

### Added
- **Real Obsidian Vault Configuration Resolver**: Resolution hierarchy via CLI `--vault-path`, Environment Variable `OBSIDIAN_VAULT_PATH`, and config file with cross-platform `pathlib.Path` support.
- **Incremental AST Markdown Indexer**: `mtime` modification tracking, frontmatter parser, headings extractor, tags (`#tag`), aliases, wikilinks (`[[Note]]`), and inbound backlink graph.
- **Structured Metadata RAG Queries**: Rich RAG results containing Title, File Path, Full Path, Section, Relevance Score, Tags, Aliases, Wikilinks, Backlinks, and Scope.
- **Scoped Knowledge Access**: Hierarchical knowledge scopes (`GLOBAL`, `ORGANIZATION`, `DEPARTMENT`, `PROJECT`, `TASK`).
- **Obsidian Vault Security Protection**: Policy rules enforcing `ALLOWED` for Read/Create/Update, `REQUIRES_APPROVAL` for ADR modification and unlinks, and `BLOCKED` for `.obsidian/` alterations.
- **Experimental Organizational Learning Benchmark**: Comparative benchmark framework measuring Memory ON vs Memory OFF performance advantages.
- **8 External Ecosystem Integrations**: Full integration adapters for `mattpocock/skills`, `colbymchenry/codegraph`, `DietrichGebert/ponytail`, `anysearch-ai/anysearch-skill`, `nextlevelbuilder/ui-ux-pro-max-skill`, `pbakaus/impeccable`, `public-apis/public-apis`, and `Zleap-AI/SAG`.

---

## [v4.1] - 2026-07-22 - AI-to-AI Executive Delegation & Organizational Memory Learning

### Added
- **Multi-Tier AI-to-AI Delegation Engine**: Strategic delegation hierarchy from AI CEO ➔ AI CTO ➔ Directors (Research, Security) ➔ Managers (Engineering, DevOps) ➔ Team Specialists.
- **Cross-Project Organizational Learning Memory**: Automated extraction of Lessons Learned, ADRs, Security Findings, Failed Approaches Avoided, and Successful Test Patterns saved to Obsidian Vault for future project reference.

---

## [v4.0] - 2026-07-22 - Autonomous AI Organization

### Added
- **Executive Leadership Board**: `AICEOManager` (Strategic Goal formulation & executive summary reporting) and `AICTO` (Technical roadmap generation).
- **Department Hierarchy**: `EngineeringManager`, `ResearchManager`, and `OperationsManager`.
- **Master Autonomous AI Organization**: End-to-end corporate initiative execution engine.

---

## [v3.1] - 2026-07-22 - Workforce Intelligence & Budget Boundaries

### Added
- **Dynamic Performance Feedback Loop**: Dynamic tracking of `tasks_completed`, `success_rate`, `test_pass_count`, `review_pass_count`, `avg_time_sec`, and dynamic `reliability_score`.
- **Seniority Tiering & Candidate Ranking**: `INTERN`, `JUNIOR`, `MID`, `SENIOR`, `SPECIALIST` levels with multi-variable Candidate Match Scoring.
- **Workforce Resource Budget**: Caps on max total agents (10), max concurrent agents (4), max cost ($0.0), and max execution time (1800s).

---

## [v3.0] - 2026-07-22 - 4-Layer AI Workforce Ecosystem

### Added
- **Layer 1 OS Kernel**: Core orchestrator, 3-Layer Routers, Task DAG, Event Bus, Security Sandbox, Approval Manager, Memory.
- **Layer 2 Domain Ecosystems**: 7 department domains (`software_engineering`, `research`, `data_analysis`, `content_creation`, `documentation`, `devops`, `knowledge_management`).
- **Layer 3 Shared Knowledge Bridge**: Cross-agent learning bridge connecting Research findings to Obsidian Vault & RAG.
- **Layer 4 AI Workforce Registry**: `AIEmployee` profile registry and skill matching.

---

## [v2.0] - 2026-07-22 - Local-First AI Software Engineering OS

### Added
- **3-Layer Routing System**: Layer 1 `AgentRouter` (`WHO?`), Layer 2 `ModelRouter` (`THINK WITH WHAT?`), Layer 3 `ToolRouter` (`DO WITH WHAT?`).
- **Local-First Provider Strategy**: Preference order: Local/Self-Hosted (Ollama) ➔ Open-Source Agents (OpenHands) ➔ Free Tier ➔ Paid API (Requires explicit user approval).
- **Automated Verification & Debugging Loop**: Pytest runner integration, automated test failure detection, root cause analysis, patch application, re-test verification, code review, and git diff generation.
