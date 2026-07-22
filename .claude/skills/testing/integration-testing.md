# Skill: Integration Testing

Test component interactions, API endpoints, and system integration.

## Capabilities
- API endpoint testing
- Database integration tests
- Service mocking
- Test containers
- End-to-end workflows
- Async test patterns

## Patterns

### Flask API Testing
```python
import pytest
from flask import Flask

@pytest.fixture
def app():
    """Create test application."""
    app = create_app(testing=True)
    app.config['TESTING'] = True
    return app

@pytest.fixture
def client(app):
    """Create test client."""
    return app.test_client()

def test_execute_task(client):
    response = client.post('/api/v1/tasks/execute', json={
        'content': 'Test task',
        'agent': 'claude'
    })

    assert response.status_code == 200
    data = response.get_json()
    assert data['success'] is True
```

### Database Integration
```python
@pytest.fixture
def db_session(tmp_path):
    """Provide isolated database session."""
    db_path = tmp_path / "test.db"
    engine = create_engine(f"sqlite:///{db_path}")
    Base.metadata.create_all(engine)

    Session = sessionmaker(bind=engine)
    session = Session()

    yield session

    session.close()
    engine.dispose()

def test_task_persistence(db_session):
    # Create
    task = Task(content="Test", status="pending")
    db_session.add(task)
    db_session.commit()

    # Verify
    saved = db_session.query(Task).filter_by(content="Test").first()
    assert saved is not None
    assert saved.status == "pending"
```

### Async Integration Tests
```python
import pytest
import pytest_asyncio

@pytest_asyncio.fixture
async def async_client():
    async with AsyncClient(app, base_url="http://test") as client:
        yield client

@pytest.mark.asyncio
async def test_async_endpoint(async_client):
    response = await async_client.post('/api/tasks', json={
        'content': 'Async test'
    })
    assert response.status_code == 200
```

### Service Mocking with Responses
```python
import responses

@responses.activate
def test_external_api_call():
    responses.add(
        responses.GET,
        "https://api.example.com/data",
        json={"status": "ok"},
        status=200
    )

    result = call_external_api()

    assert result["status"] == "ok"
    assert len(responses.calls) == 1
```

### End-to-End Workflow
```python
@pytest.mark.integration
def test_full_task_workflow(client, mock_claude):
    # Create task
    create_resp = client.post('/api/v1/tasks', json={
        'content': 'E2E test task'
    })
    task_id = create_resp.get_json()['id']

    # Execute
    exec_resp = client.post(f'/api/v1/tasks/{task_id}/execute')
    assert exec_resp.status_code == 200

    # Verify completion
    status_resp = client.get(f'/api/v1/tasks/{task_id}')
    assert status_resp.get_json()['status'] == 'completed'
```

## Markers
```python
# conftest.py
def pytest_configure(config):
    config.addinivalue_line(
        "markers", "integration: integration tests (require services)"
    )
    config.addinivalue_line(
        "markers", "slow: slow tests (> 5 seconds)"
    )
```

## Checklist
- [ ] Test fixtures provide isolated environments
- [ ] External services mocked or containerized
- [ ] Database state cleaned between tests
- [ ] Async tests use pytest-asyncio
- [ ] Integration tests marked appropriately
- [ ] CI excludes slow/integration by default
- [ ] Error scenarios tested
