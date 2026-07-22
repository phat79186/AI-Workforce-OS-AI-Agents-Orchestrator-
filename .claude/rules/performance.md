# Performance Rules

## Code Optimization
- Profile before optimizing (avoid premature optimization)
- Optimize hot paths identified through profiling
- Use appropriate data structures (O(1) lookups with dicts/sets)
- Avoid unnecessary object creation in loops
- Use generators for large data processing

## Database Performance
- Index frequently queried columns
- Use connection pooling
- Implement query caching for expensive queries
- Batch database operations when possible
- Monitor slow query logs

## Caching Strategy
- Cache at appropriate levels (memory, Redis, CDN)
- Use cache invalidation patterns (TTL, event-driven)
- Implement cache warming for critical paths
- Monitor cache hit rates and adjust
- Consider multi-tier caching (L1/L2)

## Async & Concurrency
- Use async I/O for network-bound operations
- Implement proper thread/process pooling
- Avoid blocking operations in async code
- Use message queues for background tasks
- Implement backpressure for high-load scenarios

## Memory Management
- Monitor memory usage and set limits
- Use streaming for large file processing
- Implement pagination for large result sets
- Clean up resources properly (context managers)
- Profile memory with tools (memory_profiler, tracemalloc)

## Load Testing
- Establish baseline performance metrics
- Test under realistic load patterns
- Identify bottlenecks before production
- Set performance budgets and alerts
- Test failure scenarios and recovery

## Metrics to Track
- Response time (p50, p95, p99)
- Throughput (requests/second)
- Error rate
- Resource utilization (CPU, memory, I/O)
- Database query times
- Cache hit/miss ratios
