"""Dynamic workflow planner agent using metrics-based routing."""

import json
import logging
from typing import Any, Dict, List, Optional

from orchestrator.adapters import BaseAdapter
from orchestrator.observability.metrics import get_metrics_collector


class PlannerAgent:
    """Agent that plans workflows dynamically and routes tasks based on observability metrics."""

    def __init__(self, adapters: Dict[str, BaseAdapter], logger: Optional[logging.Logger] = None):
        self.adapters = adapters
        self.logger = logger or logging.getLogger("orchestrator.planner")
        self.metrics = get_metrics_collector()

    def get_agent_metrics(self) -> Dict[str, Dict[str, Any]]:
        """Get success rate metrics for each agent."""
        agent_stats = {}
        for agent_name in self.adapters.keys():
            try:
                # Retrieve current counter values
                success = self.metrics.agent_calls_total.labels(
                    agent=agent_name, status="success"
                )._value.get()
                failure = self.metrics.agent_calls_total.labels(
                    agent=agent_name, status="failure"
                )._value.get()
                total = success + failure
                success_rate = (success / total) if total > 0 else 1.0
                agent_stats[agent_name] = {
                    "success_rate": success_rate,
                    "total_calls": total,
                }
            except Exception as e:
                self.logger.debug("Failed to get metrics for %s: %s", agent_name, e)
                agent_stats[agent_name] = {
                    "success_rate": 1.0,
                    "total_calls": 0,
                }
        return agent_stats

    def plan_workflow(self, task: str) -> List[Dict[str, Any]]:
        """Dynamically break tasks down into steps.

        Chooses workflow and assigns agents based on their historical success rates.
        """
        stats = self.get_agent_metrics()

        # Policy: Deprioritize agents with success rate < 0.6
        available_agents = []
        for agent, data in stats.items():
            rate = data["success_rate"]
            if data["total_calls"] > 0 and rate < 0.6:
                self.logger.warning(
                    "Deprioritizing agent '%s' due to low success rate: %.2f", agent, rate
                )
            else:
                available_agents.append(agent)

        if not available_agents:
            self.logger.warning("All agents have low success rates. Falling back to all adapters.")
            available_agents = list(self.adapters.keys())

        if not available_agents:
            self.logger.error("No agents available at all for planning.")
            return []

        # Choose the best LLM adapter to act as the planner
        planner_name = None
        for pref in ["claude", "gemini", "codex", "local-instruct"]:
            if pref in available_agents:
                planner_name = pref
                break

        if not planner_name:
            planner_name = available_agents[0]

        planner_adapter = self.adapters[planner_name]

        prompt = f"""
You are the Orchestrator Planner Agent. Your job is to break down the following task into sequential steps and assign available agents.
Task: {task}
Available agents: {', '.join(available_agents)}

Respond ONLY with a raw JSON array of objects. Do not include markdown formatting like ```json ... ```. Each object must have:
- "agent": the name of the assigned agent
- "task": the task role type (e.g. 'implement', 'review', 'refine', 'test', 'document')
- "description": brief description of what the agent will do

Example output:
[
  {{"agent": "{available_agents[0]}", "task": "implement", "description": "Write initial code"}},
  {{"agent": "{available_agents[-1]}", "task": "review", "description": "Review code for best practices"}}
]
"""
        self.logger.info("Generating dynamic plan using planner agent '%s'...", planner_name)

        try:
            response = planner_adapter.execute_task(
                prompt, {"role": "planner", "agent": planner_name}
            )
            if not response.success:
                self.logger.error("Planner agent failed to generate plan: %s", response.error)
                return self._fallback_plan(available_agents)

            text = response.output.strip()
            # Clean markdown if accidentally included
            if text.startswith("```json"):
                text = text[7:]
            if text.startswith("```"):
                text = text[3:]
            if text.endswith("```"):
                text = text[:-3]
            text = text.strip()

            plan = json.loads(text)

            # Validate plan
            valid_plan = []
            if isinstance(plan, list):
                for step in plan:
                    if isinstance(step, dict) and "agent" in step and "task" in step:
                        if step["agent"] in self.adapters:
                            valid_plan.append(step)
                        else:
                            # Replace unavailable agent with a random available one
                            step["agent"] = available_agents[0]
                            valid_plan.append(step)

            if valid_plan:
                self.logger.info("Planner generated a workflow with %d steps.", len(valid_plan))
                return valid_plan
            else:
                self.logger.warning("Planner generated an invalid or empty plan. Using fallback.")
                return self._fallback_plan(available_agents)

        except Exception as e:
            self.logger.error("Failed to parse dynamic plan: %s", e)
            return self._fallback_plan(available_agents)

    def _fallback_plan(self, available_agents: List[str]) -> List[Dict[str, Any]]:
        agent1 = available_agents[0]
        agent2 = available_agents[-1] if len(available_agents) > 1 else agent1
        return [
            {"agent": agent1, "task": "implement", "description": "Create initial implementation"},
            {"agent": agent2, "task": "review", "description": "Review the code"},
        ]
