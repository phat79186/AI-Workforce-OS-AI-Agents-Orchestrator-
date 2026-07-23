"""Unit tests for OpenClaw (openclaw/openclaw) Aegis V5.5 Context-Aware Prompt Processor Integration."""

import tempfile
from pathlib import Path
import pytest
from providers import OpenClawProvider, ProviderRegistry, ProviderType
from orchestrator.integrations import OpenClawPromptProcessor, ExternalEcosystemHub
from v4_organization import AutonomousAIOrganization


def test_openclaw_provider_metadata():
    provider = OpenClawProvider()
    assert provider.metadata.name == "openclaw"
    assert provider.metadata.provider_type == ProviderType.OPEN_SOURCE
    assert provider.metadata.cost_per_1k_tokens == 0.0
    assert provider.metadata.is_local is True
    assert "context_aware_scan" in provider.metadata.capabilities
    assert "playwright_visual_qa" in provider.metadata.capabilities
    assert provider.check_availability() is True


def test_openclaw_context_aware_scan_with_existing_theme():
    provider = OpenClawProvider()
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create existing tailwind.config.js
        tw_file = Path(tmpdir) / "tailwind.config.js"
        tw_file.write_text("module.exports = { theme: { extend: { colors: { primary: '#ef4444' } } } };", encoding="utf-8")

        res = provider.refine_raw_prompt("sửa UX UI", project_root=tmpdir)

        assert res["context_scan"]["theme_status"] == "EXISTING_THEME_DETECTED"
        assert "Preserve existing project design system tokens" in res["context_scan"]["palette_summary"]
        assert "Preserve existing project design system tokens" in res["objectives"][0]
        # Verify Single Lead Agent to prevent Role Bloat
        assert res["recommended_roles"] == ["LeadUIUXDesigner"]
        # Verify Playwright E2E Visual QA
        assert any("Playwright E2E Headless Visual Check" in crit for crit in res["testing_criteria"])


def test_openclaw_context_aware_scan_fallback_smart_default():
    provider = OpenClawProvider()
    with tempfile.TemporaryDirectory() as empty_dir:
        res = provider.refine_raw_prompt("sửa UX UI", project_root=empty_dir)

        assert res["context_scan"]["theme_status"] == "FALLBACK_SMART_DEFAULT"
        assert "Fallback Smart Default" in res["context_scan"]["palette_summary"]


def test_openclaw_refine_raw_prompt_bugfix():
    provider = OpenClawProvider()
    res = provider.refine_raw_prompt("sửa lỗi backend")

    assert res["domain"] == "bugfix_refinement"
    assert "Bugfix" in res["title"]
    assert res["recommended_roles"] == ["LeadSoftwareEngineer"]


def test_openclaw_provider_registry_integration():
    registry = ProviderRegistry()
    openclaw = registry.get_provider("openclaw")

    assert openclaw is not None
    assert isinstance(openclaw, OpenClawProvider)
    assert openclaw in registry.list_providers(ProviderType.OPEN_SOURCE)


def test_openclaw_prompt_processor_and_ecosystem_hub():
    processor = OpenClawPromptProcessor()
    processed = processor.process_raw_input("sửa UX UI")
    assert processed["domain"] == "ui_ux_refinement"

    hub = ExternalEcosystemHub()
    status = hub.get_status()
    assert status["openclaw_status"] == "READY"
    assert hub.openclaw is not None


def test_autonomous_organization_with_openclaw_refinement():
    with tempfile.TemporaryDirectory() as tmpdir:
        org = AutonomousAIOrganization(vault_path=tmpdir)

        # Raw user input "sửa UX UI" refined by OpenClaw with Aegis Context Scan
        res = org.execute_corporate_initiative("sửa UX UI", use_openclaw=True)

        assert res["executive_report"]["status"] == "SUCCESS"
        assert "UI/UX" in res["goal"].title
        assert len(res["goal"].key_objectives) >= 3
