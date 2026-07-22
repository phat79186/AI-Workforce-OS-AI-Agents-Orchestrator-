# Skill: Database Query Optimization

Write efficient, secure database queries with proper indexing and optimization.

## Capabilities
- Query optimization techniques
- Index design and usage
- SQL injection prevention
- Transaction management
- Connection pooling
- Query analysis with EXPLAIN

## Patterns

### Parameterized Queries (REQUIRED)
```python
# CORRECT - Parameterized
cursor.execute(
    "SELECT * FROM users WHERE id = ? AND status = ?",
    (user_id, status)
)

# NEVER DO THIS - SQL Injection vulnerable
cursor.execute(f"SELECT * FROM users WHERE id = {user_id}")
```

### Efficient Pagination
```sql
-- Offset pagination (slow for large offsets)
SELECT * FROM tasks ORDER BY id LIMIT 20 OFFSET 1000;

-- Keyset pagination (fast, recommended)
SELECT * FROM tasks
WHERE id > :last_id
ORDER BY id
LIMIT 20;
```

### Batch Operations
```python
# Batch insert with transaction
def batch_insert(items: List[dict]) -> None:
    with connection:
        cursor.executemany(
            "INSERT INTO items (name, value) VALUES (?, ?)",
            [(i['name'], i['value']) for i in items]
        )
```

### Index Strategy
```sql
-- Composite index for common queries
CREATE INDEX idx_tasks_status_created
ON tasks(status, created_at DESC);

-- Covering index (includes all needed columns)
CREATE INDEX idx_tasks_list
ON tasks(status, created_at DESC)
INCLUDE (title, priority);

-- Partial index for common filters
CREATE INDEX idx_tasks_active
ON tasks(created_at)
WHERE status = 'active';
```

### Connection Pooling
```python
from contextlib import contextmanager
import sqlite3
from queue import Queue

class ConnectionPool:
    def __init__(self, db_path: str, size: int = 5):
        self.pool = Queue(maxsize=size)
        for _ in range(size):
            self.pool.put(sqlite3.connect(db_path))

    @contextmanager
    def connection(self):
        conn = self.pool.get()
        try:
            yield conn
        finally:
            self.pool.put(conn)
```

### Query Analysis
```sql
-- SQLite
EXPLAIN QUERY PLAN SELECT * FROM tasks WHERE status = 'active';

-- PostgreSQL
EXPLAIN ANALYZE SELECT * FROM tasks WHERE status = 'active';
```

## Checklist
- [ ] All queries use parameterized statements
- [ ] Indexes exist for WHERE/ORDER BY columns
- [ ] Pagination uses keyset method for large tables
- [ ] Batch operations use transactions
- [ ] Connection pooling for multi-threaded access
- [ ] EXPLAIN used to verify query plans
- [ ] Appropriate isolation level selected
