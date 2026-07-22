"""Tests for the authentication system."""

import pytest
from auth.jwt_handler import create_access_token, create_refresh_token, decode_token


class TestJWTHandler:
    def test_create_access_token(self):
        token = create_access_token("user-1", ["admin"])
        assert isinstance(token, str)
        payload = decode_token(token)
        assert payload is not None
        assert payload["sub"] == "user-1"
        assert payload["type"] == "access"
        assert "admin" in payload["roles"]

    def test_create_refresh_token(self):
        token = create_refresh_token("user-1", "family-abc")
        payload = decode_token(token)
        assert payload is not None
        assert payload["type"] == "refresh"
        assert payload["family"] == "family-abc"

    def test_decode_invalid_token(self):
        result = decode_token("invalid.token.here")
        assert result is None

    def test_access_token_contains_roles(self):
        token = create_access_token("u1", ["editor", "viewer"])
        payload = decode_token(token)
        assert set(payload["roles"]) == {"editor", "viewer"}


class TestRBAC:
    def test_require_roles_missing_user(self):
        from auth.rbac import require_roles

        decorator = require_roles("admin")
        assert callable(decorator)

    def test_require_roles_returns_decorator(self):
        from auth.rbac import require_roles

        @require_roles("admin", "superuser")
        async def protected_route(request):
            return {"ok": True}

        assert callable(protected_route)
