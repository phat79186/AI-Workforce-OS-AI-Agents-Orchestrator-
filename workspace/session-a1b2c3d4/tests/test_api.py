"""Tests for the Blog Post REST API."""

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    from api.main import app

    return TestClient(app)


class TestBlogPostAPI:
    def test_create_post(self, client):
        resp = client.post(
            "/api/v1/posts",
            json={
                "title": "Test Post",
                "content": "Hello world",
                "author": "tester",
            },
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["title"] == "Test Post"
        assert "id" in data
        assert "created_at" in data

    def test_list_posts_empty(self, client):
        resp = client.get("/api/v1/posts")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_get_post_not_found(self, client):
        resp = client.get("/api/v1/posts/nonexistent")
        assert resp.status_code == 404

    def test_update_post(self, client):
        create = client.post(
            "/api/v1/posts",
            json={
                "title": "Original",
                "content": "Body",
                "author": "a",
            },
        )
        post_id = create.json()["id"]
        resp = client.put(f"/api/v1/posts/{post_id}", json={"title": "Updated"})
        assert resp.status_code == 200
        assert resp.json()["title"] == "Updated"

    def test_delete_post(self, client):
        create = client.post(
            "/api/v1/posts",
            json={
                "title": "ToDelete",
                "content": "Body",
                "author": "a",
            },
        )
        post_id = create.json()["id"]
        resp = client.delete(f"/api/v1/posts/{post_id}")
        assert resp.status_code == 204

    def test_title_validation_too_short(self, client):
        resp = client.post(
            "/api/v1/posts",
            json={
                "title": "ab",
                "content": "Body",
                "author": "a",
            },
        )
        assert resp.status_code == 422

    def test_pagination(self, client):
        resp = client.get("/api/v1/posts?offset=0&limit=5")
        assert resp.status_code == 200

    def test_health_endpoint(self, client):
        resp = client.get("/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "healthy"
