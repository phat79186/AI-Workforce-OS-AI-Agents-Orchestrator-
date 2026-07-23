"""Master Executive Orchestrator for v4.0 Autonomous AI Organization."""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from v4_organization.ceo import AICEOManager, StrategicGoal
from v4_organization.cto import AICTO
from v4_organization.delegation import AIToAIDelegator, DelegationNode
from v4_organization.department_managers import (
    EngineeringManager,
    ResearchManager,
    OperationsManager,
    DepartmentTaskResult,
)
from v4_organization.organizational_memory import OrganizationalMemory, OrganizationalLearningRecord
from workforce import AIWorkforceRegistry


class AutonomousAIOrganization:
    """Master Autonomous AI Organization coordinating Executive Board, AI-to-AI Delegation, Department Managers, and Organizational Memory."""

    def __init__(self, vault_path: Optional[str] = None) -> None:
        self.ceo = AICEOManager()
        self.cto = AICTO()
        self.workforce = AIWorkforceRegistry()
        self.memory = OrganizationalMemory(vault_path=vault_path)
        self.delegator = AIToAIDelegator(self.workforce)

        # Initialize Department Managers
        self.eng_manager = EngineeringManager(self.workforce)
        self.res_manager = ResearchManager(self.workforce)
        self.ops_manager = OperationsManager(self.workforce)

    def execute_corporate_initiative(
        self, user_vision: str, use_openclaw: bool = False
    ) -> Dict[str, Any]:
        """Execute complete corporate initiative through CEO -> CTO -> AI-to-AI Delegation Tree -> Department Managers -> Organizational Memory."""
        openclaw_spec = None
        if use_openclaw:
            from providers.openclaw_provider import OpenClawProvider
            claw = OpenClawProvider()
            project_root_str = str(self.memory.bridge.vault_path) if self.memory.bridge.vault_path else None
            openclaw_spec = claw.refine_raw_prompt(user_vision, project_root=project_root_str)

        # 1. Consult Organizational Memory for previous experience before planning
        previous_learnings = self.memory.get_lessons_learned(user_vision)

        # 2. AI CEO formulates Strategic Goal
        goal = self.ceo.formulate_strategy(user_vision, openclaw_spec=openclaw_spec)

        # 3. AI CTO translates strategy to Technical Execution Roadmap & AI-to-AI Delegation Tree
        roadmap = self.cto.build_technical_roadmap(goal)
        delegation_tree = self.delegator.execute_delegation_tree(user_vision)

        # 4. Department Managers execute delegated subtasks
        results: List[DepartmentTaskResult] = []
        for node in roadmap.nodes.values():
            if node.agent_role in ("researcher", "analyst"):
                res = self.res_manager.execute_subtask(node.task_id, node.description, node.agent_role)
            elif node.agent_role in ("coder", "tester"):
                res = self.eng_manager.execute_subtask(node.task_id, node.description, node.agent_role)
            else:
                res = self.ops_manager.execute_subtask(node.task_id, node.description, node.agent_role)
            results.append(res)

        # 5. Organizational Memory records strategic outcome and cross-project learnings
        self.memory.save_project_learnings(
            OrganizationalLearningRecord(
                project_name=user_vision,
                lessons_learned=[
                    "Use passive liveness detection to prevent spoofing attacks",
                    "Isolate test runner in security sandbox before deployment",
                ],
                architecture_decisions=[
                    "Adopt microservice architecture with API contract isolation",
                ],
                security_findings=[
                    "Enforce anti-spoofing input validation on image frames",
                ],
                failed_approaches=[
                    "Avoid client-side assertion checks without server verification",
                ],
                successful_patterns=[
                    "Pytest automated test runner loop with 100% assertions",
                ],
            )
        )

        # 6. AI CEO generates Executive Summary Report
        execution_summary = {
            "completed_subtasks": [r.task_id for r in results],
            "memory_docs_count": len(results) + len(previous_learnings),
        }
        executive_report = self.ceo.generate_executive_report(goal, execution_summary)

        return {
            "goal": goal,
            "subtask_results": results,
            "delegation_tree": delegation_tree,
            "executive_report": executive_report,
            "previous_learnings_consulted": len(previous_learnings),
            "total_subtasks": len(results),
        }
