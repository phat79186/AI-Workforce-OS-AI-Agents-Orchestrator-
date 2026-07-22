# Skill: Input Validation

Validate and sanitize all user inputs to prevent injection and data corruption.

## Capabilities
- Type validation with Pydantic
- String sanitization
- Path traversal prevention
- SQL injection prevention
- Command injection prevention
- Content length limits

## Patterns

### Pydantic Validation
```python
from pydantic import BaseModel, Field, validator
from typing import Optional
import re

class TaskRequest(BaseModel):
    content: str = Field(..., min_length=1, max_length=10000)
    agent: str = Field(..., pattern=r'^[a-z][a-z0-9_-]*$')
    priority: int = Field(default=5, ge=1, le=10)
    tags: list[str] = Field(default_factory=list, max_items=10)

    @validator('content')
    def sanitize_content(cls, v):
        # Remove null bytes
        v = v.replace('\x00', '')
        # Normalize whitespace
        v = ' '.join(v.split())
        return v

    @validator('tags', each_item=True)
    def validate_tag(cls, v):
        if not re.match(r'^[a-z0-9-]+$', v):
            raise ValueError('Tags must be lowercase alphanumeric')
        return v
```

### Path Validation (Prevent Traversal)
```python
from pathlib import Path
import os

def safe_path(base_dir: str, user_path: str) -> Path:
    """Resolve path safely, preventing directory traversal."""
    base = Path(base_dir).resolve()
    target = (base / user_path).resolve()

    # Ensure target is within base directory
    if not str(target).startswith(str(base)):
        raise ValueError("Path traversal attempt detected")

    return target

# Usage
try:
    path = safe_path("/app/uploads", user_input)
except ValueError:
    return error_response("Invalid path")
```

### SQL Parameter Validation
```python
def validate_order_column(column: str, allowed: set[str]) -> str:
    """Validate column name for ORDER BY (can't be parameterized)."""
    if column not in allowed:
        raise ValueError(f"Invalid column: {column}")
    return column

# Usage
ALLOWED_SORT = {'created_at', 'updated_at', 'priority'}
order_col = validate_order_column(request.sort_by, ALLOWED_SORT)
query = f"SELECT * FROM tasks ORDER BY {order_col}"  # Safe
```

### Command Argument Validation
```python
import shlex
import re

def validate_agent_name(name: str) -> str:
    """Validate agent name for CLI usage."""
    if not re.match(r'^[a-z][a-z0-9_-]{0,30}$', name):
        raise ValueError("Invalid agent name format")
    return name

def safe_command(base_cmd: list[str], user_args: list[str]) -> list[str]:
    """Build command list safely (no shell=True needed)."""
    validated = []
    for arg in user_args:
        # Reject shell metacharacters
        if any(c in arg for c in ';&|`$(){}[]<>'):
            raise ValueError(f"Invalid character in argument: {arg}")
        validated.append(arg)

    return base_cmd + validated
```

### Content Type Validation
```python
import magic  # python-magic

ALLOWED_TYPES = {
    'text/plain',
    'application/json',
    'text/markdown',
}

def validate_file_content(data: bytes, filename: str) -> str:
    """Validate file content matches expected type."""
    detected = magic.from_buffer(data, mime=True)

    if detected not in ALLOWED_TYPES:
        raise ValueError(f"File type {detected} not allowed")

    return detected
```

## Anti-Patterns to Avoid

```python
# NEVER: String interpolation in SQL
f"SELECT * FROM users WHERE id = {user_id}"

# NEVER: Shell=True with user input
subprocess.run(f"process {user_input}", shell=True)

# NEVER: Unvalidated path joins
open(os.path.join(base, user_path))

# NEVER: eval/exec with user input
eval(user_expression)
```

## Checklist
- [ ] All inputs have type validation
- [ ] String lengths are bounded
- [ ] Paths validated against traversal
- [ ] SQL uses parameterized queries
- [ ] Commands use list form (no shell=True)
- [ ] File types validated by content
- [ ] Null bytes stripped
- [ ] Unicode normalized
