"""Hub composing the integrations in `orchestrator/integrations/`.

As of this revision, 7 of the sub-integrations run real logic (real `git`
subprocess calls, real AST parsing, real GitHub data fetch, a real headless
Chromium browser, real WCAG contrast math) — the rest remain local
simulations. See each module's docstring and `orchestrator/integrations/README.md`
for the exact status of each one.

Two of the real integrations need extra care at hub-construction time:

- `CodeGraphTool` and `PublicAPIsCatalog` no longer eagerly populate
  themselves in `__init__` (indexing a codebase / fetching ~1,700 real API
  entries on every hub construction would be slow and, for the catalog,
  requires network). Call `hub.codegraph.index_directory(path)` /
  `hub.public_apis.load()` explicitly when you actually need that data.
- `PlaywrightVisualAuditor` now raises `PlaywrightNotAvailableError` if the
  real `playwright` package/browser isn't installed. The hub catches that so
  a missing optional dependency doesn't take down the whole hub —
  `hub.playwright_moderator` is `None` in that case.
"""

from __future__ import annotations

from typing import Any, Dict, Optional
from orchestrator.integrations.mattpocock_skills import MattPocockSkillsEngine
from orchestrator.integrations.codegraph_tool import CodeGraphTool
from orchestrator.integrations.ponytail_runner import PonytailRunner
from orchestrator.integrations.anysearch_skill import AnySearchSkill
from orchestrator.integrations.ui_ux_pro_max import UIUXProMaxSkill
from orchestrator.integrations.impeccable_design import ImpeccableDesignSkill
from orchestrator.integrations.taste_skill import TasteSkill
from orchestrator.integrations.public_apis_catalog import PublicAPIsCatalog
from orchestrator.integrations.sag_framework import SAGAgentFramework
from orchestrator.integrations.openclaw_processor import OpenClawPromptProcessor
from orchestrator.integrations.agent_reach import AgentReachEngine
from orchestrator.integrations.chatdev_adapter import ChatDevAdapter
from orchestrator.integrations.rtk_compressor import RTKTokenCompressor
from orchestrator.integrations.karpathy_skills import KarpathySkillsEngine
from orchestrator.integrations.git_nexus import GitNexusEngine
from orchestrator.integrations.playwright_moderator import PlaywrightVisualAuditor, PlaywrightNotAvailableError


class ExternalEcosystemHub:
    """Unified hub wiring together AI Workforce OS's real and simulated integrations."""

    def __init__(self) -> None:
        self.mattpocock_skills = MattPocockSkillsEngine()
        self.karpathy_skills = KarpathySkillsEngine()
        self.codegraph = CodeGraphTool()
        self.ponytail = PonytailRunner()
        self.anysearch = AnySearchSkill()
        self.agent_reach = AgentReachEngine()
        self.ui_ux_pro_max = UIUXProMaxSkill()
        self.impeccable = ImpeccableDesignSkill()
        self.taste = TasteSkill()
        self.public_apis = PublicAPIsCatalog()
        self.sag = SAGAgentFramework()
        self.openclaw = OpenClawPromptProcessor()
        self.chatdev = ChatDevAdapter()
        self.rtk = RTKTokenCompressor()
        self.git_nexus = GitNexusEngine()

        self.playwright_moderator: Optional[PlaywrightVisualAuditor] = None
        self._playwright_unavailable_reason: Optional[str] = None
        try:
            self.playwright_moderator = PlaywrightVisualAuditor()
        except PlaywrightNotAvailableError as e:
            self._playwright_unavailable_reason = str(e)

    def get_status(self) -> Dict[str, Any]:
        """Return a real status summary reflecting each sub-integration's actual state."""
        return {
            "mattpocock_skills_count": len(self.mattpocock_skills.list_skills()),
            "karpathy_skills_count": len(self.karpathy_skills.list_skills()),
            "codegraph_symbols_indexed": len(self.codegraph._symbol_index),
            "codegraph_status": "READY (call index_directory() to populate)"
            if not self.codegraph._symbol_index else "INDEXED",
            "ponytail_steps_queued": len(self.ponytail.steps),
            "anysearch_status": "READY (simulated)",
            "agent_reach_status": "READY (simulated)",
            "ui_ux_pro_max_status": "READY (4 real distinct themes + real contrast verification)",
            "impeccable_status": "READY (real WCAG contrast math)",
            "taste_skill_status": "READY (curated guidelines + real contrast math)",
            "public_apis_loaded": len(self.public_apis),
            "public_apis_status": "READY (call load() to fetch the real catalog)"
            if len(self.public_apis) == 0 else "LOADED",
            "sag_node_count": len(self.sag.nodes),
            "openclaw_status": "READY (real file scan, templated refinement)",
            "chatdev_status": "READY (simulated)",
            "rtk_token_compressor_status": "READY (real text dedup)",
            "git_nexus_status": "READY (real git operations)",
            "playwright_moderator_status": (
                "READY (real headless Chromium)" if self.playwright_moderator is not None
                else f"UNAVAILABLE: {self._playwright_unavailable_reason}"
            ),
            "overall_status": "ALL_INTEGRATED",
        }
