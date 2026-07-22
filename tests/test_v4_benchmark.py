"""Unit tests for v4.2 Organizational Learning Benchmark."""

import tempfile
import pytest
from v4_organization import OrganizationalLearningBenchmark


def test_organizational_learning_benchmark_execution():
    with tempfile.TemporaryDirectory() as tmpdir:
        bench = OrganizationalLearningBenchmark(vault_path=tmpdir)
        results = bench.run_benchmark()

        assert "memory_on" in results
        assert "memory_off" in results

        on = results["memory_on"]
        off = results["memory_off"]

        # Verify Memory ON outperforms Memory OFF across all metrics
        assert on.planning_quality_pct > off.planning_quality_pct
        assert on.architecture_errors < off.architecture_errors
        assert on.security_issues < off.security_issues
        assert on.test_failures < off.test_failures
        assert on.execution_time_sec < off.execution_time_sec


def test_benchmark_markdown_table_generation():
    with tempfile.TemporaryDirectory() as tmpdir:
        bench = OrganizationalLearningBenchmark(vault_path=tmpdir)
        results = bench.run_benchmark()
        table_md = bench.generate_markdown_table(results)

        assert "| Metric | Without Memory (OFF) | With Memory (ON) |" in table_md
        assert "Planning Quality" in table_md
        assert "Architecture Errors" in table_md
        assert "Security Issues" in table_md
        assert "Test Failures" in table_md
