"""OpenClaw Provider for Context-Aware raw prompt refinement, project theme scanning, and Playwright Visual QA."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional
from providers.base_provider import BaseProvider, ProviderMetadata, ProviderType
from providers.prompt_optimizer import PromptOptimizerEngine


class OpenClawProvider(BaseProvider):
    """OpenClaw open-source AI provider for context-aware prompt enrichment and code pre-processing (Aegis V5.5 + linshenkx Prompt Optimizer)."""

    def __init__(self) -> None:
        self.prompt_optimizer = PromptOptimizerEngine()
        metadata = ProviderMetadata(
            name="openclaw",
            provider_type=ProviderType.OPEN_SOURCE,
            cost_per_1k_tokens=0.0,
            is_local=True,
            capabilities=[
                "raw_prompt_refinement",
                "code_preprocessing",
                "prompt_enrichment",
                "context_aware_scan",
                "playwright_visual_qa",
                "single_lead_contract_checkpoint",
                "linshenkx_prompt_optimization",
            ],
            context_limit=16384,
            priority=10,  # High priority for pre-processing
            requires_approval=False,
            is_available=True,
        )
        super().__init__(metadata)

    def check_availability(self) -> bool:
        """Check if OpenClaw engine is available."""
        return self.metadata.is_available

    def scan_project_context(self, project_root: Optional[str] = None) -> Dict[str, Any]:
        """Scan project directory to detect existing design system, framework, and configuration files."""
        root = Path(project_root).resolve() if project_root else Path.cwd()

        # Target theme and design config files
        tailwind_config = root / "tailwind.config.js"
        tailwind_ts = root / "tailwind.config.ts"
        theme_ts = root / "theme.ts"
        theme_json = root / "theme.json"
        globals_css = root / "src" / "index.css"
        package_json = root / "package.json"

        detected_framework = None
        has_existing_theme = False
        detected_colors = []

        if package_json.exists():
            try:
                pkg_data = json.loads(package_json.read_text(encoding="utf-8"))
                deps = {**pkg_data.get("dependencies", {}), **pkg_data.get("devDependencies", {})}
                if "tailwindcss" in deps:
                    detected_framework = "TailwindCSS"
                elif "react" in deps or "vue" in deps:
                    detected_framework = "Modern Web Framework"
            except Exception:
                pass

        for cfg in (tailwind_config, tailwind_ts, theme_ts, theme_json, globals_css):
            if cfg.exists():
                has_existing_theme = True
                content = cfg.read_text(encoding="utf-8", errors="ignore")
                if "colors" in content or "--primary" in content or "theme" in content:
                    detected_colors.append(cfg.name)

        if has_existing_theme:
            theme_status = "EXISTING_THEME_DETECTED"
            palette_summary = f"Preserve existing project design system tokens ({', '.join(detected_colors) if detected_colors else 'Theme files present'})"
        else:
            theme_status = "FALLBACK_SMART_DEFAULT"
            palette_summary = "Dark Glassmorphism (Primary: #6366f1, Secondary: #a855f7) [Fallback Smart Default]"

        return {
            "project_root": str(root),
            "theme_status": theme_status,
            "detected_framework": detected_framework or "Standard Project",
            "has_existing_theme": has_existing_theme,
            "palette_summary": palette_summary,
        }

    def execute_prompt(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: int = 2048,
        temperature: float = 0.7,
        **kwargs: Any,
    ) -> str:
        """Execute prompt against OpenClaw processing engine."""
        project_root = kwargs.get("project_root")
        refined = self.refine_raw_prompt(prompt, project_root=project_root)
        return refined["enriched_specification"]

    def refine_raw_prompt(
        self,
        raw_prompt: str,
        project_root: Optional[str] = None,
        domain_context: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Context-Aware refinement of raw/brief user input (e.g. 'sửa UX UI') using Aegis V5.5 Architecture."""
        raw_lower = raw_prompt.lower().strip()
        context = self.scan_project_context(project_root)
        
        # Domain detection and specification enrichment
        if "ux" in raw_lower or "ui" in raw_lower or "giao diện" in raw_lower or "design" in raw_lower:
            domain = "ui_ux_refinement"
            title = "UI/UX Visual Polish & Accessibility Refinement"
            objectives = [
                f"Design System Policy: {context['palette_summary']}",
                "Audit typography, spacing, micro-interactions, and WCAG AA contrast compliance (4.5:1 ratio)",
                "Enhance component visual hierarchy, hover states, and responsive layout math",
                "Implement keyboard navigation accessibility and aria-labels for interactive elements",
            ]
            # Aegis Pattern: Single Primary Lead Agent to prevent Role Bloat & Race Conditions
            recommended_roles = ["LeadUIUXDesigner"]
            # Hybrid Visual QA: Playwright Headless Browser Pixel-Diff / Overflow Check
            testing_criteria = [
                "Playwright E2E Headless Visual Check (Pixel-Diff / Layout Overflow Audit)",
                "WCAG AA accessibility contrast pass",
                "Pytest DOM & logic test",
            ]
        elif "bug" in raw_lower or "fix" in raw_lower or "sửa lỗi" in raw_lower:
            domain = "bugfix_refinement"
            title = "Autonomous Code Bugfix & Self-Healing Loop"
            objectives = [
                "Execute automated test suite to isolate breaking assertions",
                "Analyze runtime error logs to pinpoint root cause",
                "Apply targeted code patch preserving API contracts",
                "Re-run unit tests until 100% GREEN pass rate",
            ]
            recommended_roles = ["LeadSoftwareEngineer"]
            testing_criteria = ["Pytest assertion pass rate 100%", "Regression check pass"]
        elif "security" in raw_lower or "bảo mật" in raw_lower or "liveness" in raw_lower:
            domain = "security_audit"
            title = "Zero-Trust Security & Threat Model Compliance"
            objectives = [
                "Conduct vulnerability audit on input boundaries and API contracts",
                "Enforce anti-spoofing validation and secure token handling",
                "Record security findings into Organizational Memory Obsidian Vault",
            ]
            recommended_roles = ["LeadSecurityAuditor"]
            testing_criteria = ["Zero high-severity vulnerability audit", "Anti-spoofing assertion pass"]
        else:
            domain = "general_engineering"
            title = f"Engineering Specification for: {raw_prompt}"
            objectives = [
                f"Analyze technical requirements for '{raw_prompt}'",
                "Design modular architecture and clean component interfaces",
                "Implement robust implementation with comprehensive automated unit tests",
            ]
            recommended_roles = ["LeadSoftwareEngineer"]
            testing_criteria = ["Automated unit test suite 100% GREEN"]

        # linshenkx/prompt-optimizer meta-prompt transformation stage
        optimization = self.prompt_optimizer.optimize_prompt(raw_prompt, domain=domain, context=context)

        enriched_spec = (
            f"# OpenClaw Processed Specification: {title}\n"
            f"**Raw User Input:** \"{raw_prompt}\"\n"
            f"**Refinement Domain:** {domain}\n"
            f"**Prompt Optimizer Clarity Score:** {optimization['clarity_score']} / 1.0 (linshenkx/prompt-optimizer)\n"
            f"**Context Theme Scan:** {context['theme_status']} ({context['palette_summary']})\n"
            f"**Execution Safety:** Aegis V5.5 Per-Node Contract Checkpoint Enabled\n\n"
            f"## Strategic Objectives\n"
            + "\n".join(f"- {obj}" for obj in objectives)
            + "\n\n## Assigned Primary Lead Agent\n"
            + "\n".join(f"- {role}" for role in recommended_roles)
            + "\n\n## Automated Verification Criteria\n"
            + "\n".join(f"- {crit}" for crit in testing_criteria)
            + f"\n\n## Meta-Prompting System Role\n{optimization['system_role']}\n\n"
            + "## Critical Negative Constraints\n"
            + "\n".join(f"- {nc}" for nc in optimization['negative_constraints'])
        )

        return {
            "raw_prompt": raw_prompt,
            "processed_by": "openclaw",
            "prompt_optimizer_source": optimization["source_repo"],
            "clarity_score": optimization["clarity_score"],
            "architecture": "aegis_v5_5",
            "domain": domain,
            "title": title,
            "context_scan": context,
            "objectives": objectives,
            "recommended_roles": recommended_roles,
            "testing_criteria": testing_criteria,
            "optimization": optimization,
            "enriched_specification": enriched_spec,
        }
