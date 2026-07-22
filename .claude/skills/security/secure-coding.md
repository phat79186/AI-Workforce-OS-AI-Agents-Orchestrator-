# Skill: Secure Coding Practices

Apply security best practices throughout the development lifecycle.

## Capabilities
- Secrets management
- Error handling (no info leakage)
- Logging security
- Dependency security
- Cryptographic best practices
- Defense in depth

## Patterns

### Secrets Management
```python
import os
from typing import Optional

def get_secret(name: str, default: Optional[str] = None) -> str:
    """Get secret from environment with validation."""
    value = os.environ.get(name, default)
    if value is None:
        raise ValueError(f"Required secret {name} not configured")
    return value

# Usage
API_KEY = get_secret("API_KEY")
DATABASE_URL = get_secret("DATABASE_URL")

# NEVER do this:
# API_KEY = "sk-hardcoded-secret"  # Committed to repo
# logger.info(f"Using API key: {API_KEY}")  # Logged secret
```

### Secure Error Handling
```python
import logging
import uuid

logger = logging.getLogger(__name__)

class SafeErrorHandler:
    """Handle errors without leaking sensitive information."""

    @staticmethod
    def handle_error(error: Exception, context: dict = None) -> dict:
        """Log error internally, return safe response."""
        error_id = str(uuid.uuid4())

        # Log full details internally
        logger.error(
            f"Error {error_id}: {type(error).__name__}: {error}",
            extra={"context": context, "error_id": error_id},
            exc_info=True
        )

        # Return safe response (no internal details)
        return {
            "error": {
                "message": "An error occurred processing your request",
                "error_id": error_id  # For support lookup
            }
        }

# In API endpoint
try:
    result = process_request(data)
except Exception as e:
    return SafeErrorHandler.handle_error(e, {"user_id": user_id}), 500
```

### Secure Logging
```python
import re
from typing import Any

SENSITIVE_PATTERNS = [
    (re.compile(r'password["\s:=]+["\']?[\w]+', re.I), 'password=***'),
    (re.compile(r'api[_-]?key["\s:=]+["\']?[\w-]+', re.I), 'api_key=***'),
    (re.compile(r'token["\s:=]+["\']?[\w.-]+', re.I), 'token=***'),
    (re.compile(r'secret["\s:=]+["\']?[\w]+', re.I), 'secret=***'),
]

def sanitize_log_message(message: str) -> str:
    """Remove sensitive data from log messages."""
    for pattern, replacement in SENSITIVE_PATTERNS:
        message = pattern.sub(replacement, message)
    return message

class SecureFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        record.msg = sanitize_log_message(str(record.msg))
        return super().format(record)
```

### Cryptographic Best Practices
```python
import secrets
import hashlib
from cryptography.fernet import Fernet

# Random token generation
def generate_token(length: int = 32) -> str:
    """Generate cryptographically secure random token."""
    return secrets.token_urlsafe(length)

# Secure comparison (constant time)
def secure_compare(a: str, b: str) -> bool:
    """Compare strings in constant time."""
    return secrets.compare_digest(a, b)

# Symmetric encryption
class DataEncryptor:
    def __init__(self, key: bytes = None):
        self.key = key or Fernet.generate_key()
        self.cipher = Fernet(self.key)

    def encrypt(self, data: str) -> str:
        """Encrypt string data."""
        return self.cipher.encrypt(data.encode()).decode()

    def decrypt(self, encrypted: str) -> str:
        """Decrypt encrypted data."""
        return self.cipher.decrypt(encrypted.encode()).decode()

# Hashing for integrity
def compute_hash(data: bytes) -> str:
    """Compute SHA-256 hash."""
    return hashlib.sha256(data).hexdigest()
```

### Dependency Security
```python
# requirements.txt - Pin versions
requests==2.31.0
pydantic==2.5.0
cryptography==41.0.0

# Check for vulnerabilities
# pip install pip-audit
# pip-audit

# In CI/CD:
# - name: Security audit
#   run: |
#     pip install pip-audit
#     pip-audit --strict
```

### Defense in Depth
```python
from functools import wraps

def defense_in_depth(f):
    """Apply multiple security layers."""
    @wraps(f)
    @require_authentication      # Layer 1: Auth
    @require_permission(WRITE)   # Layer 2: Authorization
    @rate_limit(100, 60)         # Layer 3: Rate limiting
    @validate_input              # Layer 4: Input validation
    @audit_log                   # Layer 5: Audit logging
    def decorated(*args, **kwargs):
        return f(*args, **kwargs)
    return decorated
```

## Security Anti-Patterns

```python
# NEVER: Hardcoded secrets
API_KEY = "sk-secret-key-here"

# NEVER: Detailed error messages to users
return {"error": f"SQL error: {e}"}

# NEVER: Logging sensitive data
logger.info(f"Login attempt for {user} with password {password}")

# NEVER: Weak random
import random
token = ''.join(random.choices('abc123', k=32))  # Use secrets instead

# NEVER: String comparison for secrets
if token == stored_token:  # Use secrets.compare_digest
```

## Checklist
- [ ] No hardcoded secrets
- [ ] Secrets from environment/vault
- [ ] Error messages don't leak internals
- [ ] Sensitive data not logged
- [ ] Dependencies pinned and audited
- [ ] Cryptographic operations use stdlib/cryptography
- [ ] Constant-time comparison for secrets
- [ ] Defense in depth applied
