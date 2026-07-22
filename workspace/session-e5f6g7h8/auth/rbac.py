"""Role-based access control decorator."""

from functools import wraps
from typing import List

from fastapi import HTTPException, Request


def require_roles(*required_roles: str):
    """Decorator that enforces role-based access on a route."""

    def decorator(func):
        @wraps(func)
        async def wrapper(*args, request: Request, **kwargs):
            user = getattr(request.state, "user", None)
            if not user:
                raise HTTPException(status_code=401, detail="Not authenticated")

            user_roles = set(user.get("roles", []))
            if not user_roles.intersection(set(required_roles)):
                raise HTTPException(
                    status_code=403,
                    detail=f"Requires one of: {', '.join(required_roles)}",
                )
            return await func(*args, request=request, **kwargs)

        return wrapper

    return decorator
