#!/usr/bin/env python3
"""Demonstrates observability features: metrics, health checks, logging.

Usage:
    python examples/orchestrator/metrics_and_health.py
"""

import sys
from pathlib import Path

# Add project to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from orchestrator.core import Orchestrator  # noqa: E402
from orchestrator.infra import get_cache  # noqa: E402
from orchestrator.observability import get_metrics_collector  # noqa: E402
from orchestrator.observability.health import HealthChecker, HealthStatus  # noqa: E402
from orchestrator.resilience import CircuitBreaker  # noqa: E402


def main():
    """Demonstrate observability and health monitoring."""
    orch = Orchestrator()

    # --- Health Checks ---
    print("=== Health Checks ===")
    checker = HealthChecker()

    for agent_name, adapter in orch.adapters.items():
        result = checker.check_agent_availability(agent_name, adapter.command)
        status_icon = "OK" if result.status == HealthStatus.HEALTHY else "!!"
        print(f"  [{status_icon}] {agent_name}: {result.message} ({result.duration_ms:.0f}ms)")
    print()

    # --- Metrics ---
    print("=== Metrics ===")
    metrics = get_metrics_collector()
    metrics.update_active_agents(len(orch.adapters))
    metrics.record_task_start("default")
    metrics.record_task_complete("default", success=True, duration=1.5)
    metrics.record_agent_call("codex", success=True, duration=0.8)
    metrics.record_cache_hit()
    metrics.record_cache_miss()

    # Export Prometheus format
    output = metrics.get_metrics().decode("utf-8")
    for line in output.split("\n"):
        if line and not line.startswith("#"):
            print(f"  {line}")
    print()

    # --- Cache ---
    print("=== Cache ===")
    cache = get_cache()
    cache.set("demo_key", {"result": "cached value"}, ttl=60)
    value = cache.get("demo_key")
    stats = cache.get_stats()
    print(f"  Stored: demo_key = {value}")
    print(f"  Stats: {stats}")
    print()

    # --- Circuit Breaker ---
    print("=== Circuit Breaker ===")
    cb = CircuitBreaker(failure_threshold=3, recovery_timeout=5.0)
    print(f"  State: {cb.state.value}")
    print(f"  Failure threshold: {cb.failure_threshold}")
    print(f"  Recovery timeout: {cb.recovery_timeout}s")

    # Simulate failures
    for i in range(3):
        try:
            cb.call(lambda: (_ for _ in ()).throw(ConnectionError("simulated failure")))
        except ConnectionError:
            pass
    print(f"  After 3 failures: {cb.state.value}")

    # Successful call resets
    import time

    time.sleep(0.01)  # Wait for recovery timeout (set to 5s normally, but demo)
    cb.recovery_timeout = 0.01
    cb.last_failure_time = time.time() - 1
    result = cb.call(lambda: "recovered!")
    print(f"  After recovery: {cb.state.value} — result: {result}")


if __name__ == "__main__":
    main()
