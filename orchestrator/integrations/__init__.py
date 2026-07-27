"""Integrations package for 8 external tools & skills in AI Workforce OS v4.2."""

from orchestrator.integrations.mattpocock_skills import MattPocockSkill, MattPocockSkillsEngine
from orchestrator.integrations.codegraph_tool import CodeSymbol, CodeGraphTool
from orchestrator.integrations.ponytail_runner import PonytailWorkflowStep, PonytailRunner
from orchestrator.integrations.anysearch_skill import AnySearchSkill
from orchestrator.integrations.ui_ux_pro_max import UIUXProMaxSkill
from orchestrator.integrations.impeccable_design import ImpeccableDesignSkill
from orchestrator.integrations.taste_skill import TasteSkill
from orchestrator.integrations.public_apis_catalog import PublicAPIEntry, PublicAPIsCatalog
from orchestrator.integrations.sag_framework import SAGNode, SAGAgentFramework
from orchestrator.integrations.openclaw_processor import OpenClawPromptProcessor
from orchestrator.integrations.agent_reach import AgentReachEngine
from orchestrator.integrations.chatdev_adapter import ChatDevAdapter
from orchestrator.integrations.rtk_compressor import RTKTokenCompressor
from orchestrator.integrations.karpathy_skills import KarpathySkill, KarpathySkillsEngine
from orchestrator.integrations.git_nexus import GitNexusEngine
from orchestrator.integrations.playwright_moderator import PlaywrightVisualAuditor
from orchestrator.integrations.ecosystem_hub import ExternalEcosystemHub

__all__ = [
    "MattPocockSkill",
    "MattPocockSkillsEngine",
    "KarpathySkill",
    "KarpathySkillsEngine",
    "GitNexusEngine",
    "PlaywrightVisualAuditor",
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
    "SAGNode",
    "SAGAgentFramework",
    "OpenClawPromptProcessor",
    "AgentReachEngine",
    "ChatDevAdapter",
    "RTKTokenCompressor",
    "ExternalEcosystemHub",
]
