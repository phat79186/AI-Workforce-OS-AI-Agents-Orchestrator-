# Skill: Performance Testing

Load test, benchmark, and analyze application performance.

## Capabilities
- Load testing with Locust
- Benchmarking with pytest-benchmark
- Profiling Python code
- Performance metrics analysis
- Bottleneck identification

## Patterns

### Locust Load Test
```python
from locust import HttpUser, task, between

class OrchestratorUser(HttpUser):
    wait_time = between(1, 3)

    @task(3)
    def execute_task(self):
        self.client.post("/api/v1/tasks/execute", json={
            "content": "Test task",
            "agent": "claude"
        })

    @task(1)
    def list_agents(self):
        self.client.get("/api/v1/agents")

    def on_start(self):
        """Setup - authenticate if needed."""
        self.client.headers["X-API-Key"] = "test-key"

# Run: locust -f locustfile.py --host=http://localhost:8000
```

### pytest-benchmark
```python
import pytest

def test_search_performance(benchmark, search_index):
    """Benchmark search operation."""
    result = benchmark(
        search_index.search,
        query="test query",
        top_k=10
    )
    assert len(result) <= 10

def test_embedding_generation(benchmark, embedding_service):
    """Benchmark embedding generation."""
    texts = ["Sample text " * 100] * 10

    result = benchmark.pedantic(
        embedding_service.embed,
        args=(texts,),
        iterations=5,
        rounds=3
    )

    assert len(result) == 10
```

### Python Profiling
```python
import cProfile
import pstats
from io import StringIO

def profile_function(func, *args, **kwargs):
    """Profile a function and return stats."""
    profiler = cProfile.Profile()
    profiler.enable()

    result = func(*args, **kwargs)

    profiler.disable()

    # Format stats
    stream = StringIO()
    stats = pstats.Stats(profiler, stream=stream)
    stats.sort_stats('cumulative')
    stats.print_stats(20)

    print(stream.getvalue())
    return result

# Memory profiling
from memory_profiler import profile

@profile
def memory_intensive_function():
    data = [i ** 2 for i in range(1000000)]
    return sum(data)
```

### Performance Metrics Collection
```python
import time
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Dict, List
import statistics

@dataclass
class PerformanceMetrics:
    operation: str
    count: int
    total_time: float
    mean: float
    p50: float
    p95: float
    p99: float

class MetricsCollector:
    def __init__(self):
        self.timings: Dict[str, List[float]] = {}

    @contextmanager
    def measure(self, operation: str):
        start = time.perf_counter()
        try:
            yield
        finally:
            duration = time.perf_counter() - start
            if operation not in self.timings:
                self.timings[operation] = []
            self.timings[operation].append(duration)

    def get_metrics(self, operation: str) -> PerformanceMetrics:
        times = sorted(self.timings.get(operation, []))
        if not times:
            return None

        return PerformanceMetrics(
            operation=operation,
            count=len(times),
            total_time=sum(times),
            mean=statistics.mean(times),
            p50=times[len(times) // 2],
            p95=times[int(len(times) * 0.95)],
            p99=times[int(len(times) * 0.99)]
        )

# Usage
metrics = MetricsCollector()

with metrics.measure("task_execution"):
    execute_task(task)

print(metrics.get_metrics("task_execution"))
```

## Performance Targets

| Operation | Target p95 | Target p99 |
|-----------|-----------|-----------|
| API Response | < 200ms | < 500ms |
| Search | < 100ms | < 200ms |
| Embedding | < 50ms/text | < 100ms/text |
| Task Execution | < 30s | < 60s |

## Checklist
- [ ] Load test covers main flows
- [ ] Benchmarks for critical paths
- [ ] Profiling identifies bottlenecks
- [ ] Metrics collected in production
- [ ] Percentiles tracked (p50, p95, p99)
- [ ] Alerts set for degradation
- [ ] Regular performance reviews
