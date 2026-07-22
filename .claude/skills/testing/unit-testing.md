# Skill: Unit Testing

Write comprehensive unit tests with pytest, mocking, and fixtures.

## Capabilities
- pytest test structure
- Fixtures and parametrization
- Mocking external dependencies
- Assertion patterns
- Test isolation
- Coverage analysis

## Patterns

### Test Structure (Arrange-Act-Assert)
```python
def test_task_execution_success():
    # Arrange
    engine = OrchestratorEngine()
    task = Task(content="Write tests", agent="claude")

    # Act
    result = engine.execute(task)

    # Assert
    assert result.success is True
    assert result.output is not None
```

### Fixtures
```python
import pytest

@pytest.fixture
def mock_adapter():
    """Provide a mock adapter for testing."""
    adapter = Mock(spec=BaseAdapter)
    adapter.execute.return_value = AgentResponse(
        success=True,
        output="Test output"
    )
    return adapter

@pytest.fixture
def engine(mock_adapter):
    """Provide engine with mocked adapter."""
    engine = OrchestratorEngine()
    engine.adapters['test'] = mock_adapter
    return engine
```

### Parametrized Tests
```python
@pytest.mark.parametrize("input,expected", [
    ("valid task", True),
    ("", False),
    (None, False),
    ("a" * 10001, False),  # Too long
])
def test_task_validation(input, expected):
    result = validate_task(input)
    assert result == expected
```

### Mocking
```python
from unittest.mock import Mock, patch, AsyncMock

def test_api_call():
    with patch('module.requests.get') as mock_get:
        mock_get.return_value.json.return_value = {"status": "ok"}

        result = fetch_status()

        assert result == "ok"
        mock_get.assert_called_once()

@pytest.mark.asyncio
async def test_async_call():
    with patch('module.fetch', new_callable=AsyncMock) as mock:
        mock.return_value = {"data": "test"}

        result = await process_data()

        assert result["data"] == "test"
```

### Exception Testing
```python
def test_invalid_input_raises():
    with pytest.raises(ValueError, match="cannot be empty"):
        process_task("")

def test_timeout_handling():
    with pytest.raises(TimeoutError):
        with patch('module.execute', side_effect=TimeoutError):
            run_with_timeout()
```

### Test Isolation
```python
@pytest.fixture(autouse=True)
def clean_state():
    """Reset global state before each test."""
    yield
    # Cleanup after test
    reset_global_state()

@pytest.fixture
def temp_db(tmp_path):
    """Provide temporary database for test."""
    db_path = tmp_path / "test.db"
    init_database(db_path)
    yield db_path
    # Automatic cleanup by tmp_path fixture
```

## Checklist
- [ ] Tests follow Arrange-Act-Assert
- [ ] External dependencies mocked
- [ ] Edge cases covered (empty, null, max)
- [ ] Error paths tested
- [ ] Tests are independent (no order dependency)
- [ ] Fixtures used for common setup
- [ ] Parametrize for multiple inputs
- [ ] Coverage > 80% for critical paths
