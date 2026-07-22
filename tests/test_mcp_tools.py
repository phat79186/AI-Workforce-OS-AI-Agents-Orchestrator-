"""Tests for new MCP tools."""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class TestCodeAnalysisToolsImport:
    """Tests for code analysis MCP tool module imports."""

    def test_module_imports(self):
        """Should import the code_analysis module."""
        from mcp_server.tools import code_analysis

        assert code_analysis is not None

    def test_has_analyze_python_complexity(self):
        """Should have analyze_python_complexity function."""
        from mcp_server.tools import code_analysis

        assert hasattr(code_analysis, "analyze_python_complexity")

    def test_has_find_code_patterns(self):
        """Should have find_code_patterns function."""
        from mcp_server.tools import code_analysis

        assert hasattr(code_analysis, "find_code_patterns")

    def test_has_analyze_dependencies(self):
        """Should have analyze_dependencies function."""
        from mcp_server.tools import code_analysis

        assert hasattr(code_analysis, "analyze_dependencies")

    def test_has_generate_code_summary(self):
        """Should have generate_code_summary function."""
        from mcp_server.tools import code_analysis

        assert hasattr(code_analysis, "generate_code_summary")

    def test_has_register_function(self):
        """Should have register_code_analysis_tools function."""
        from mcp_server.tools.code_analysis import register_code_analysis_tools

        assert callable(register_code_analysis_tools)


class TestSecurityToolsImport:
    """Tests for security scanning MCP tool module imports."""

    def test_module_imports(self):
        """Should import the security_tools module."""
        from mcp_server.tools import security_tools

        assert security_tools is not None

    def test_has_scan_secrets(self):
        """Should have scan_secrets function."""
        from mcp_server.tools import security_tools

        assert hasattr(security_tools, "scan_secrets")

    def test_has_check_security_headers(self):
        """Should have check_security_headers function."""
        from mcp_server.tools import security_tools

        assert hasattr(security_tools, "check_security_headers")

    def test_has_audit_dependencies_security(self):
        """Should have audit_dependencies_security function."""
        from mcp_server.tools import security_tools

        assert hasattr(security_tools, "audit_dependencies_security")

    def test_has_scan_injection_risks(self):
        """Should have scan_injection_risks function."""
        from mcp_server.tools import security_tools

        assert hasattr(security_tools, "scan_injection_risks")

    def test_has_register_function(self):
        """Should have register_security_tools function."""
        from mcp_server.tools.security_tools import register_security_tools

        assert callable(register_security_tools)


class TestTestingToolsImport:
    """Tests for testing utility MCP tool module imports."""

    def test_module_imports(self):
        """Should import the testing_tools module."""
        from mcp_server.tools import testing_tools

        assert testing_tools is not None

    def test_has_generate_test_cases(self):
        """Should have generate_test_cases function."""
        from mcp_server.tools import testing_tools

        assert hasattr(testing_tools, "generate_test_cases")

    def test_has_analyze_test_coverage(self):
        """Should have analyze_test_coverage function."""
        from mcp_server.tools import testing_tools

        assert hasattr(testing_tools, "analyze_test_coverage")

    def test_has_generate_test_stub(self):
        """Should have generate_test_stub function."""
        from mcp_server.tools import testing_tools

        assert hasattr(testing_tools, "generate_test_stub")

    def test_has_parse_test_results(self):
        """Should have parse_test_results function."""
        from mcp_server.tools import testing_tools

        assert hasattr(testing_tools, "parse_test_results")

    def test_has_register_function(self):
        """Should have register_testing_tools function."""
        from mcp_server.tools.testing_tools import register_testing_tools

        assert callable(register_testing_tools)


class TestDevOpsToolsImport:
    """Tests for DevOps MCP tool module imports."""

    def test_module_imports(self):
        """Should import the devops_tools module."""
        from mcp_server.tools import devops_tools

        assert devops_tools is not None

    def test_has_analyze_dockerfile(self):
        """Should have analyze_dockerfile function."""
        from mcp_server.tools import devops_tools

        assert hasattr(devops_tools, "analyze_dockerfile")

    def test_has_analyze_compose_file(self):
        """Should have analyze_compose_file function."""
        from mcp_server.tools import devops_tools

        assert hasattr(devops_tools, "analyze_compose_file")

    def test_has_check_ci_config(self):
        """Should have check_ci_config function."""
        from mcp_server.tools import devops_tools

        assert hasattr(devops_tools, "check_ci_config")

    def test_has_generate_deploy_checklist(self):
        """Should have generate_deploy_checklist function."""
        from mcp_server.tools import devops_tools

        assert hasattr(devops_tools, "generate_deploy_checklist")

    def test_has_analyze_env_config(self):
        """Should have analyze_env_config function."""
        from mcp_server.tools import devops_tools

        assert hasattr(devops_tools, "analyze_env_config")

    def test_has_register_function(self):
        """Should have register_devops_tools function."""
        from mcp_server.tools.devops_tools import register_devops_tools

        assert callable(register_devops_tools)


class TestContextToolsImport:
    """Tests for context memory MCP tool module imports."""

    def test_module_imports(self):
        """Should import the context_tools module."""
        from mcp_server.tools import context_tools

        assert context_tools is not None

    def test_has_store_conversation(self):
        """Should have store_conversation function."""
        from mcp_server.tools import context_tools

        assert hasattr(context_tools, "store_conversation")

    def test_has_search_context(self):
        """Should have search_context function."""
        from mcp_server.tools import context_tools

        assert hasattr(context_tools, "search_context")

    def test_has_get_relevant_context(self):
        """Should have get_relevant_context function."""
        from mcp_server.tools import context_tools

        assert hasattr(context_tools, "get_relevant_context")

    def test_has_log_mistake(self):
        """Should have log_mistake function."""
        from mcp_server.tools import context_tools

        assert hasattr(context_tools, "log_mistake")

    def test_has_store_task_result(self):
        """Should have store_task_result function."""
        from mcp_server.tools import context_tools

        assert hasattr(context_tools, "store_task_result")

    def test_has_store_pattern(self):
        """Should have store_pattern function."""
        from mcp_server.tools import context_tools

        assert hasattr(context_tools, "store_pattern")

    def test_has_get_context_stats(self):
        """Should have get_context_stats function."""
        from mcp_server.tools import context_tools

        assert hasattr(context_tools, "get_context_stats")

    def test_has_register_function(self):
        """Should have register_context_tools function."""
        from mcp_server.tools.context_tools import register_context_tools

        assert callable(register_context_tools)


class TestToolRegistration:
    """Tests for tool registration with MCP server."""

    def test_register_code_analysis_tools(self):
        """Should register code analysis tools with MCP."""
        from mcp_server.tools.code_analysis import register_code_analysis_tools

        mock_mcp = MagicMock()
        register_code_analysis_tools(mock_mcp)

        # Should have called mcp.tool() decorator
        assert mock_mcp.tool.called

    def test_register_security_tools(self):
        """Should register security tools with MCP."""
        from mcp_server.tools.security_tools import register_security_tools

        mock_mcp = MagicMock()
        register_security_tools(mock_mcp)

        assert mock_mcp.tool.called

    def test_register_testing_tools(self):
        """Should register testing tools with MCP."""
        from mcp_server.tools.testing_tools import register_testing_tools

        mock_mcp = MagicMock()
        register_testing_tools(mock_mcp)

        assert mock_mcp.tool.called

    def test_register_devops_tools(self):
        """Should register devops tools with MCP."""
        from mcp_server.tools.devops_tools import register_devops_tools

        mock_mcp = MagicMock()
        register_devops_tools(mock_mcp)

        assert mock_mcp.tool.called

    def test_register_context_tools(self):
        """Should register context tools with MCP."""
        from mcp_server.tools.context_tools import register_context_tools

        mock_mcp = MagicMock()
        register_context_tools(mock_mcp)

        assert mock_mcp.tool.called


class TestToolsModuleStructure:
    """Test the tools module structure."""

    def test_tools_init_exports(self):
        """Should export all register functions from __init__."""
        from mcp_server.tools import (
            register_code_analysis_tools,
            register_context_tools,
            register_devops_tools,
            register_security_tools,
            register_testing_tools,
        )

        assert callable(register_code_analysis_tools)
        assert callable(register_security_tools)
        assert callable(register_testing_tools)
        assert callable(register_devops_tools)
        assert callable(register_context_tools)
