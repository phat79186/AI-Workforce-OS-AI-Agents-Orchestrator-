# Skill: API Documentation

Write comprehensive API documentation with OpenAPI specs and examples.

## Capabilities
- OpenAPI/Swagger specifications
- Endpoint documentation
- Request/response examples
- Error documentation
- Authentication docs
- SDK generation support

## Patterns

### OpenAPI Specification
```yaml
openapi: 3.1.0
info:
  title: AI Orchestrator API
  description: |
    API for the AI Coding Tools Orchestrator.

    ## Authentication
    All endpoints require API key authentication via `X-API-Key` header.

    ## Rate Limiting
    - 100 requests per minute per API key
    - Rate limit headers included in responses
  version: 1.0.0
  contact:
    name: API Support
    email: support@example.com
  license:
    name: MIT
    url: https://opensource.org/licenses/MIT

servers:
  - url: http://localhost:8000/api/v1
    description: Local development
  - url: https://api.orchestrator.example.com/v1
    description: Production

security:
  - ApiKeyAuth: []

paths:
  /tasks/execute:
    post:
      operationId: executeTask
      summary: Execute a task
      description: |
        Submit a task for execution by an AI agent.

        The task will be routed to the specified agent and executed.
        Results are returned synchronously.
      tags:
        - Tasks
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/TaskRequest'
            examples:
              simple:
                summary: Simple task
                value:
                  content: "Write a hello world function"
                  agent: "claude"
              with_context:
                summary: Task with context
                value:
                  content: "Review this code for security issues"
                  agent: "claude"
                  context:
                    files:
                      - "src/auth.py"
                    additional_info: "Focus on SQL injection"
      responses:
        '200':
          description: Task executed successfully
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/TaskResponse'
        '400':
          $ref: '#/components/responses/BadRequest'
        '401':
          $ref: '#/components/responses/Unauthorized'
        '429':
          $ref: '#/components/responses/RateLimited'
        '500':
          $ref: '#/components/responses/InternalError'

components:
  securitySchemes:
    ApiKeyAuth:
      type: apiKey
      in: header
      name: X-API-Key
      description: API key for authentication

  schemas:
    TaskRequest:
      type: object
      required:
        - content
        - agent
      properties:
        content:
          type: string
          minLength: 1
          maxLength: 10000
          description: The task description
          example: "Write a Python function to parse JSON"
        agent:
          type: string
          enum: [claude, codex, gemini, copilot, ollama]
          description: The AI agent to use
        context:
          $ref: '#/components/schemas/TaskContext'
        priority:
          type: integer
          minimum: 1
          maximum: 10
          default: 5
          description: Task priority (1=lowest, 10=highest)

    TaskResponse:
      type: object
      properties:
        success:
          type: boolean
          description: Whether the task completed successfully
        output:
          type: string
          description: The task output/result
        agent:
          type: string
          description: The agent that processed the task
        execution_time:
          type: number
          format: float
          description: Execution time in seconds
        metadata:
          type: object
          additionalProperties: true
          description: Additional metadata

    Error:
      type: object
      required:
        - code
        - message
      properties:
        code:
          type: string
          description: Error code
        message:
          type: string
          description: Human-readable error message
        details:
          type: array
          items:
            type: object
            properties:
              field:
                type: string
              message:
                type: string

  responses:
    BadRequest:
      description: Invalid request
      content:
        application/json:
          schema:
            $ref: '#/components/schemas/Error'
          example:
            code: VALIDATION_ERROR
            message: Invalid request body
            details:
              - field: content
                message: Required field missing

    Unauthorized:
      description: Authentication required
      content:
        application/json:
          schema:
            $ref: '#/components/schemas/Error'
          example:
            code: UNAUTHORIZED
            message: Invalid or missing API key
```

### Endpoint Documentation Template
```markdown
## Execute Task

Execute a task using an AI agent.

### Request

`POST /api/v1/tasks/execute`

#### Headers

| Header | Required | Description |
|--------|----------|-------------|
| X-API-Key | Yes | Your API key |
| Content-Type | Yes | `application/json` |

#### Body

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| content | string | Yes | Task description (1-10000 chars) |
| agent | string | Yes | Agent to use: `claude`, `codex`, `gemini` |
| priority | integer | No | Priority 1-10 (default: 5) |

### Response

#### Success (200)

```json
{
  "success": true,
  "output": "def hello():\n    return 'Hello, World!'",
  "agent": "claude",
  "execution_time": 2.5
}
```

#### Error (400)

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Invalid request",
    "details": [
      {"field": "content", "message": "Cannot be empty"}
    ]
  }
}
```

### Example

```bash
curl -X POST https://api.example.com/v1/tasks/execute \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "content": "Write a hello world function",
    "agent": "claude"
  }'
```
```

## Checklist
- [ ] All endpoints documented
- [ ] Request/response schemas defined
- [ ] Examples for common use cases
- [ ] Error responses documented
- [ ] Authentication explained
- [ ] Rate limits documented
- [ ] Versioning strategy clear
- [ ] curl examples provided
