# Skill: Error Handling Patterns

Implement robust error handling with proper logging, recovery, and user feedback.

## Capabilities
- Exception hierarchies
- Error boundaries
- Graceful degradation
- Error logging
- User-friendly messages
- Recovery strategies

## Patterns

### Custom Exception Hierarchy
```python
class OrchestratorError(Exception):
    """Base exception for all orchestrator errors."""

    def __init__(self, message: str, code: str = None, details: dict = None):
        super().__init__(message)
        self.message = message
        self.code = code or "UNKNOWN_ERROR"
        self.details = details or {}

    def to_dict(self) -> dict:
        return {
            "code": self.code,
            "message": self.message,
            "details": self.details
        }

class ValidationError(OrchestratorError):
    """Invalid input data."""
    def __init__(self, field: str, message: str):
        super().__init__(
            message=f"Validation error on {field}: {message}",
            code="VALIDATION_ERROR",
            details={"field": field}
        )

class AgentError(OrchestratorError):
    """Error from an AI agent."""
    def __init__(self, agent: str, message: str, recoverable: bool = False):
        super().__init__(
            message=f"Agent {agent} error: {message}",
            code="AGENT_ERROR",
            details={"agent": agent, "recoverable": recoverable}
        )
        self.recoverable = recoverable

class TimeoutError(OrchestratorError):
    """Operation timed out."""
    def __init__(self, operation: str, timeout_seconds: float):
        super().__init__(
            message=f"Operation {operation} timed out after {timeout_seconds}s",
            code="TIMEOUT_ERROR",
            details={"operation": operation, "timeout": timeout_seconds}
        )
```

### Context Manager for Error Handling
```python
from contextlib import contextmanager
import logging

logger = logging.getLogger(__name__)

@contextmanager
def error_boundary(operation: str, reraise: bool = True):
    """Handle errors with logging and optional re-raise."""
    try:
        yield
    except OrchestratorError:
        raise  # Already handled
    except Exception as e:
        logger.error(f"Unexpected error in {operation}: {e}", exc_info=True)
        if reraise:
            raise OrchestratorError(
                message=f"Unexpected error in {operation}",
                code="INTERNAL_ERROR"
            ) from e

# Usage
def process_task(task):
    with error_boundary("task processing"):
        validate_task(task)
        result = execute_task(task)
        return result
```

### Retry with Fallback
```python
from typing import TypeVar, Callable, List
import time

T = TypeVar('T')

def retry_with_fallback(
    primary: Callable[[], T],
    fallbacks: List[Callable[[], T]],
    max_retries: int = 3,
    delay: float = 1.0
) -> T:
    """Try primary, then fallbacks, with retries."""
    last_error = None

    # Try primary with retries
    for attempt in range(max_retries):
        try:
            return primary()
        except Exception as e:
            last_error = e
            if attempt < max_retries - 1:
                time.sleep(delay * (2 ** attempt))

    # Try fallbacks
    for fallback in fallbacks:
        try:
            return fallback()
        except Exception as e:
            last_error = e
            continue

    raise last_error

# Usage
result = retry_with_fallback(
    primary=lambda: call_claude(task),
    fallbacks=[
        lambda: call_codex(task),
        lambda: call_gemini(task)
    ]
)
```

### API Error Response
```python
from flask import jsonify
import uuid

def handle_api_error(error: Exception):
    """Convert exception to API response."""
    error_id = str(uuid.uuid4())

    if isinstance(error, OrchestratorError):
        logger.warning(f"Error {error_id}: {error.code} - {error.message}")
        return jsonify({
            "error": error.to_dict(),
            "error_id": error_id
        }), get_status_code(error.code)

    # Unexpected error - don't leak details
    logger.error(f"Error {error_id}: {error}", exc_info=True)
    return jsonify({
        "error": {
            "code": "INTERNAL_ERROR",
            "message": "An unexpected error occurred",
        },
        "error_id": error_id
    }), 500

def get_status_code(code: str) -> int:
    return {
        "VALIDATION_ERROR": 400,
        "UNAUTHORIZED": 401,
        "FORBIDDEN": 403,
        "NOT_FOUND": 404,
        "AGENT_ERROR": 502,
        "TIMEOUT_ERROR": 504,
    }.get(code, 500)
```

## Checklist
- [ ] Custom exception hierarchy
- [ ] Errors have codes for programmatic handling
- [ ] Internal details not leaked to users
- [ ] All errors logged with context
- [ ] Error IDs for support lookup
- [ ] Retry logic for transient failures
- [ ] Fallback strategies where appropriate
- [ ] Graceful degradation when possible
