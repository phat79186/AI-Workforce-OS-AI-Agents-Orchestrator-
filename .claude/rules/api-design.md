# API Design Rules

## RESTful Conventions
- Use nouns for resources, verbs in HTTP methods
- GET: retrieve, POST: create, PUT: update, PATCH: partial update, DELETE: remove
- Use plural resource names: `/users`, `/orders`
- Nest related resources: `/users/{id}/orders`
- Use query parameters for filtering and sorting

## Response Format
- Return consistent JSON structure with `data`, `error`, `meta` fields
- Use appropriate HTTP status codes (200, 201, 400, 401, 403, 404, 500)
- Include pagination info in list responses
- Return meaningful error messages with error codes

## Versioning
- Version APIs: `/api/v1/resource` or `Accept: application/vnd.api+v1+json`
- Maintain backward compatibility within versions
- Deprecate gracefully with advance notice
- Document breaking changes clearly

## Authentication & Security
- Use Bearer tokens (JWT or opaque) for API authentication
- Implement OAuth 2.0 for third-party access
- Apply rate limiting per client/endpoint
- Validate Content-Type headers
- Return proper CORS headers for browser clients

## Documentation
- Provide OpenAPI/Swagger specifications
- Include request/response examples
- Document error codes and meanings
- Keep documentation in sync with implementation

## Performance
- Support pagination for list endpoints (cursor or offset)
- Allow field selection to reduce payload size
- Implement caching with ETags and Cache-Control
- Use compression (gzip, brotli) for responses
- Support batch operations for bulk updates

## Error Handling
```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Validation failed",
    "details": [
      {"field": "email", "message": "Invalid email format"}
    ]
  }
}
```
