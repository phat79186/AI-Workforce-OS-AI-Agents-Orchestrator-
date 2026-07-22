# Skill: Python Async Programming

Write efficient asynchronous Python code with asyncio, aiohttp, and async patterns.

## Capabilities
- Async/await syntax
- Concurrent task execution
- Async context managers
- Async generators
- Error handling in async code
- Bounded concurrency

## Patterns

### Basic Async Function
```python
import asyncio
from typing import List

async def fetch_data(url: str) -> dict:
    async with aiohttp.ClientSession() as session:
        async with session.get(url, timeout=30) as response:
            response.raise_for_status()
            return await response.json()
```

### Concurrent Execution
```python
async def fetch_all(urls: List[str]) -> List[dict]:
    """Fetch multiple URLs concurrently with bounded concurrency."""
    semaphore = asyncio.Semaphore(10)  # Max 10 concurrent

    async def bounded_fetch(url: str) -> dict:
        async with semaphore:
            return await fetch_data(url)

    tasks = [bounded_fetch(url) for url in urls]
    return await asyncio.gather(*tasks, return_exceptions=True)
```

### Async Context Manager
```python
from contextlib import asynccontextmanager

@asynccontextmanager
async def managed_resource():
    resource = await acquire_resource()
    try:
        yield resource
    finally:
        await release_resource(resource)
```

### Async Generator
```python
async def stream_results(query: str):
    """Stream results as they become available."""
    async with get_connection() as conn:
        async for row in conn.execute(query):
            yield transform(row)
```

### Timeout Pattern
```python
async def with_timeout(coro, timeout_seconds: float):
    try:
        return await asyncio.wait_for(coro, timeout=timeout_seconds)
    except asyncio.TimeoutError:
        raise TimeoutError(f"Operation timed out after {timeout_seconds}s")
```

### Error Handling
```python
async def safe_execute(tasks: List[Coroutine]) -> List[Result]:
    results = await asyncio.gather(*tasks, return_exceptions=True)

    successes = []
    for i, result in enumerate(results):
        if isinstance(result, Exception):
            logger.error(f"Task {i} failed: {result}")
        else:
            successes.append(result)

    return successes
```

## Checklist
- [ ] Use asyncio.gather for concurrent operations
- [ ] Bound concurrency with Semaphore
- [ ] Set timeouts on all I/O operations
- [ ] Handle exceptions from gather
- [ ] Use async context managers for resources
- [ ] Avoid blocking calls in async code
- [ ] Cancel tasks on shutdown
