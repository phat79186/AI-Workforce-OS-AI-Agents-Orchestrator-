"""v4.2 Organizational Learning Benchmark Runner Script."""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

from v4_organization import OrganizationalLearningBenchmark


def run_v4_2_benchmark_demo() -> None:
    print("=================================================================")
    print("[v4.2 DEMO] ORGANIZATIONAL LEARNING BENCHMARK (MEMORY ON vs OFF)")
    print("=================================================================")

    with tempfile.TemporaryDirectory(prefix="v4_2_bench_vault_") as tmp_vault:
        # 1. Initialize Benchmark Suite
        print("\n[BENCHMARK ENGINE] Initializing Organizational Learning Benchmark Suite...")
        bench = OrganizationalLearningBenchmark(vault_path=tmp_vault)

        # 2. Run Scenario A, B, and C Benchmark
        print("[SCENARIOS EXECUTED] Scenario A (Baseline) -> Scenario B (Memory ON) vs Scenario C (Memory OFF)...")
        results = bench.run_benchmark()

        # 3. Output Formatted Markdown Table for GitHub README.md
        print("\n[BENCHMARK RESULTS - GITHUB README SUMMARY]")
        table_md = bench.generate_markdown_table(results)
        print(table_md)

        print("[SUCCESS] v4.2 Organizational Learning Benchmark completed successfully!\n")


if __name__ == "__main__":
    run_v4_2_benchmark_demo()
