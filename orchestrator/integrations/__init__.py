"""Integrations package for AI Workforce OS v4.2.

⚠️ READ THIS FIRST: every class exported below is a local SIMULATED/MOCK
stand-in named after a real external tool or GitHub repo — none of them make
a real network call, run a real external binary, or use the named project's
actual code. A few (`RTKTokenCompressor`, parts of `PonytailRunner`,
`SAGAgentFramework`) contain genuinely working local logic, but still are
NOT the real named integration. Instantiating almost any of these classes
emits a `UserWarning` at runtime as a reminder. Full details, per-module
status, and the reasoning behind this choice are in
`orchestrator/integrations/README.md`.
"""

from orchestrator.integrations.mattpocock_skills import MattPocockSkill, MattPocockSkillsEngine
from orchestrator.integrations.codegraph_tool import CodeSymbol, CodeGraphTool
from orchestrator.integrations.ponytail_runner import PonytailWorkflowStep, PonytailRunner
from orchestrator.integrations.anysearch_skill import AnySearchSkill
from orchestrator.integrations.ui_ux_pro_max import UIUXProMaxSkill
from orchestrator.integrations.impeccable_design import ImpeccableDesignSkill
from orchestrator.integrations.taste_skill import TasteSkill
from orchestrator.integrations.public_apis_catalog import PublicAPIEntry, PublicAPIsCatalog, PublicAPIsFetchError
from orchestrator.integrations.sag_framework import SAGNode, SAGAgentFramework
from orchestrator.integrations.openclaw_processor import OpenClawPromptProcessor
from orchestrator.integrations.agent_reach import AgentReachEngine
from orchestrator.integrations.chatdev_adapter import ChatDevAdapter
from orchestrator.integrations.rtk_compressor import RTKTokenCompressor
from orchestrator.integrations.karpathy_skills import KarpathySkill, KarpathySkillsEngine
from orchestrator.integrations.git_nexus import GitNexusEngine
from orchestrator.integrations.playwright_moderator import PlaywrightVisualAuditor, PlaywrightNotAvailableError
from orchestrator.integrations.ecosystem_hub import ExternalEcosystemHub

__all__ = [
    "MattPocockSkill",
    "MattPocockSkillsEngine",
    "KarpathySkill",
    "KarpathySkillsEngine",
    "GitNexusEngine",
    "PlaywrightVisualAuditor",
    "PlaywrightNotAvailableError",
    "CodeSymbol",
    "CodeGraphTool",
    "PonytailWorkflowStep",
    "PonytailRunner",
    "AnySearchSkill",
    "UIUXProMaxSkill",
    "ImpeccableDesignSkill",
    "TasteSkill",
    "PublicAPIEntry",
    "PublicAPIsCatalog",
    "PublicAPIsFetchError",
    "SAGNode",
    "SAGAgentFramework",
    "OpenClawPromptProcessor",
    "AgentReachEngine",
    "ChatDevAdapter",
    "RTKTokenCompressor",
    "ExternalEcosystemHub",
]
