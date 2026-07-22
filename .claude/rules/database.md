# Database Rules

## Schema Design
- Use descriptive, snake_case table and column names
- Always include `id` primary key (prefer UUID or auto-increment)
- Add `created_at` and `updated_at` timestamp columns
- Use appropriate data types (don't store numbers as strings)
- Normalize to 3NF, denormalize only for performance

## Indexing Strategy
- Index foreign keys and frequently queried columns
- Use composite indexes for multi-column queries
- Consider covering indexes for read-heavy workloads
- Avoid over-indexing (impacts write performance)
- Monitor slow queries and add indexes accordingly

## Query Best Practices
- Use parameterized queries to prevent SQL injection
- Prefer specific column names over `SELECT *`
- Limit result sets with `LIMIT` or pagination
- Use `EXPLAIN` to analyze query plans
- Avoid N+1 queries with proper JOINs or batching

## Migrations
- Use migration tools (Alembic, Flyway, Django migrations)
- Make migrations reversible when possible
- Test migrations on staging before production
- Keep migrations small and focused
- Document breaking schema changes

## Connection Management
- Use connection pooling (SQLAlchemy, PgBouncer)
- Set appropriate connection timeouts
- Handle connection failures gracefully
- Close connections properly (use context managers)

## Data Integrity
- Use foreign key constraints
- Apply CHECK constraints for valid ranges
- Use UNIQUE constraints for business rules
- Consider soft deletes for audit trails
- Implement optimistic locking for concurrent updates
