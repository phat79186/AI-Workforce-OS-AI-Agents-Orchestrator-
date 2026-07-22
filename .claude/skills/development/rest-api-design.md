# Skill: REST API Design

Design and implement RESTful APIs following best practices and OpenAPI standards.

## Capabilities
- Resource-oriented URL design
- HTTP method semantics
- Status code selection
- Pagination, filtering, sorting
- Error response formatting
- API versioning strategies

## Patterns

### Resource URLs
```
GET    /api/v1/tasks          # List tasks
POST   /api/v1/tasks          # Create task
GET    /api/v1/tasks/{id}     # Get task
PUT    /api/v1/tasks/{id}     # Replace task
PATCH  /api/v1/tasks/{id}     # Update task
DELETE /api/v1/tasks/{id}     # Delete task

# Nested resources
GET    /api/v1/tasks/{id}/logs
POST   /api/v1/tasks/{id}/execute
```

### Response Format
```json
{
  "data": { ... },
  "meta": {
    "request_id": "uuid",
    "timestamp": "ISO8601"
  }
}
```

### Error Response
```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Human readable message",
    "details": [
      { "field": "name", "message": "Required" }
    ]
  },
  "meta": {
    "request_id": "uuid"
  }
}
```

### Pagination
```
GET /api/v1/tasks?page=1&per_page=20&sort=-created_at

Response headers:
X-Total-Count: 100
X-Page: 1
X-Per-Page: 20
Link: <...?page=2>; rel="next", <...?page=5>; rel="last"
```

## Status Codes
| Code | Use Case |
|------|----------|
| 200 | Success with body |
| 201 | Created (POST) |
| 204 | Success no body (DELETE) |
| 400 | Bad request / validation |
| 401 | Not authenticated |
| 403 | Not authorized |
| 404 | Not found |
| 409 | Conflict |
| 422 | Unprocessable entity |
| 429 | Rate limited |
| 500 | Server error |

## Checklist
- [ ] Resource-oriented URLs (nouns, not verbs)
- [ ] Correct HTTP methods
- [ ] Consistent response format
- [ ] Proper status codes
- [ ] Pagination for lists
- [ ] Input validation
- [ ] Rate limiting headers
