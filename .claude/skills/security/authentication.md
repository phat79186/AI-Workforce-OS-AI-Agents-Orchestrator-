# Skill: Authentication & Authorization

Implement secure authentication and authorization patterns.

## Capabilities
- JWT token handling
- API key authentication
- Role-based access control (RBAC)
- Session management
- Password hashing
- OAuth integration

## Patterns

### JWT Authentication
```python
from datetime import datetime, timedelta
from typing import Optional
import jwt
from pydantic import BaseModel

class TokenPayload(BaseModel):
    sub: str  # Subject (user ID)
    exp: datetime  # Expiration
    iat: datetime  # Issued at
    roles: list[str] = []

def create_access_token(
    user_id: str,
    roles: list[str],
    secret: str,
    expires_minutes: int = 30
) -> str:
    """Create JWT access token."""
    now = datetime.utcnow()
    payload = TokenPayload(
        sub=user_id,
        exp=now + timedelta(minutes=expires_minutes),
        iat=now,
        roles=roles
    )
    return jwt.encode(payload.dict(), secret, algorithm="HS256")

def verify_token(token: str, secret: str) -> Optional[TokenPayload]:
    """Verify and decode JWT token."""
    try:
        payload = jwt.decode(token, secret, algorithms=["HS256"])
        return TokenPayload(**payload)
    except jwt.ExpiredSignatureError:
        return None  # Token expired
    except jwt.InvalidTokenError:
        return None  # Invalid token
```

### API Key Authentication
```python
import hashlib
import secrets
from functools import wraps

def generate_api_key() -> tuple[str, str]:
    """Generate API key and its hash for storage."""
    key = secrets.token_urlsafe(32)
    key_hash = hashlib.sha256(key.encode()).hexdigest()
    return key, key_hash

def verify_api_key(key: str, stored_hash: str) -> bool:
    """Verify API key against stored hash."""
    key_hash = hashlib.sha256(key.encode()).hexdigest()
    return secrets.compare_digest(key_hash, stored_hash)

def require_api_key(f):
    """Decorator to require valid API key."""
    @wraps(f)
    def decorated(*args, **kwargs):
        api_key = request.headers.get('X-API-Key')
        if not api_key:
            return jsonify({"error": "API key required"}), 401

        key_hash = hashlib.sha256(api_key.encode()).hexdigest()
        if not db.verify_api_key(key_hash):
            return jsonify({"error": "Invalid API key"}), 401

        return f(*args, **kwargs)
    return decorated
```

### Role-Based Access Control
```python
from enum import Enum
from functools import wraps

class Role(str, Enum):
    ADMIN = "admin"
    USER = "user"
    READONLY = "readonly"

class Permission(str, Enum):
    READ = "read"
    WRITE = "write"
    DELETE = "delete"
    ADMIN = "admin"

ROLE_PERMISSIONS = {
    Role.ADMIN: {Permission.READ, Permission.WRITE, Permission.DELETE, Permission.ADMIN},
    Role.USER: {Permission.READ, Permission.WRITE},
    Role.READONLY: {Permission.READ},
}

def require_permission(permission: Permission):
    """Decorator to require specific permission."""
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            user = get_current_user()
            if not user:
                return jsonify({"error": "Not authenticated"}), 401

            user_permissions = set()
            for role in user.roles:
                user_permissions.update(ROLE_PERMISSIONS.get(role, set()))

            if permission not in user_permissions:
                return jsonify({"error": "Permission denied"}), 403

            return f(*args, **kwargs)
        return decorated
    return decorator
```

### Password Hashing
```python
import bcrypt

def hash_password(password: str) -> str:
    """Hash password with bcrypt."""
    salt = bcrypt.gensalt(rounds=12)
    return bcrypt.hashpw(password.encode(), salt).decode()

def verify_password(password: str, hashed: str) -> bool:
    """Verify password against hash."""
    return bcrypt.checkpw(password.encode(), hashed.encode())
```

### Secure Session Management
```python
import secrets
from datetime import datetime, timedelta

class SessionManager:
    def __init__(self, ttl_minutes: int = 60):
        self.sessions = {}
        self.ttl = timedelta(minutes=ttl_minutes)

    def create_session(self, user_id: str) -> str:
        """Create new session."""
        session_id = secrets.token_urlsafe(32)
        self.sessions[session_id] = {
            "user_id": user_id,
            "created_at": datetime.utcnow(),
            "last_activity": datetime.utcnow()
        }
        return session_id

    def validate_session(self, session_id: str) -> Optional[str]:
        """Validate session and return user_id."""
        session = self.sessions.get(session_id)
        if not session:
            return None

        if datetime.utcnow() - session["last_activity"] > self.ttl:
            del self.sessions[session_id]
            return None

        session["last_activity"] = datetime.utcnow()
        return session["user_id"]

    def invalidate_session(self, session_id: str) -> None:
        """Invalidate session (logout)."""
        self.sessions.pop(session_id, None)
```

## Checklist
- [ ] Passwords hashed with bcrypt (cost >= 12)
- [ ] Tokens have expiration
- [ ] Constant-time comparison for secrets
- [ ] API keys hashed before storage
- [ ] Sessions invalidated on logout
- [ ] RBAC enforced at endpoint level
- [ ] Failed auth attempts rate-limited
- [ ] Sensitive headers not logged
