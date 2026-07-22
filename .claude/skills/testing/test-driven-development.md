# Skill: Test-Driven Development (TDD)

Practice TDD with red-green-refactor cycle for reliable, well-designed code.

## Capabilities
- Red-Green-Refactor cycle
- Test-first design
- Incremental development
- Behavior specification
- Emergent design

## TDD Cycle

### 1. Red: Write Failing Test
```python
def test_task_validator_rejects_empty_content():
    """Task with empty content should be invalid."""
    validator = TaskValidator()

    result = validator.validate(Task(content=""))

    assert result.is_valid is False
    assert "content cannot be empty" in result.errors
```

### 2. Green: Minimal Implementation
```python
class TaskValidator:
    def validate(self, task: Task) -> ValidationResult:
        errors = []
        if not task.content:
            errors.append("content cannot be empty")
        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors
        )
```

### 3. Refactor: Improve Design
```python
class TaskValidator:
    def __init__(self):
        self.rules = [
            self._check_content_not_empty,
            self._check_content_length,
        ]

    def validate(self, task: Task) -> ValidationResult:
        errors = []
        for rule in self.rules:
            if error := rule(task):
                errors.append(error)
        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors
        )

    def _check_content_not_empty(self, task: Task) -> Optional[str]:
        if not task.content:
            return "content cannot be empty"
        return None
```

## TDD Workflow

### Feature Development
```python
# Step 1: List test cases
"""
Test cases for TaskExecutor:
- [ ] Executes task with valid adapter
- [ ] Returns error for unknown adapter
- [ ] Handles adapter timeout
- [ ] Retries on transient failure
- [ ] Records execution in history
"""

# Step 2: Write first failing test
def test_executes_task_with_valid_adapter():
    executor = TaskExecutor(adapters={'test': MockAdapter()})
    task = Task(content="Do something", agent="test")

    result = executor.execute(task)

    assert result.success is True
    assert result.output is not None

# Step 3: Make it pass with minimal code
# Step 4: Refactor
# Step 5: Next test case
```

### Triangulation
```python
# First test - specific case
def test_add_two_numbers():
    assert add(2, 3) == 5

# Triangulate - more cases to drive general solution
def test_add_negative_numbers():
    assert add(-1, -1) == -2

def test_add_zero():
    assert add(0, 5) == 5
```

## Best Practices

### Test Naming
```python
# Pattern: test_<unit>_<scenario>_<expected_behavior>
def test_validator_empty_content_returns_error():
    ...

def test_executor_timeout_retries_three_times():
    ...
```

### One Assertion Per Test
```python
# GOOD - focused test
def test_task_created_with_pending_status():
    task = Task.create(content="Test")
    assert task.status == "pending"

def test_task_created_with_timestamp():
    task = Task.create(content="Test")
    assert task.created_at is not None

# AVOID - multiple concerns
def test_task_creation():
    task = Task.create(content="Test")
    assert task.status == "pending"
    assert task.created_at is not None
    assert task.id is not None
```

## Checklist
- [ ] Write test before implementation
- [ ] Test fails for the right reason
- [ ] Minimal code to pass test
- [ ] Refactor after green
- [ ] Tests document behavior
- [ ] One assertion per test (when practical)
- [ ] Tests are independent
