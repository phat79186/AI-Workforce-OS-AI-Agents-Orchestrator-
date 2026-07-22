# Skill: LLM Integration

Integrate and orchestrate Large Language Models effectively and safely.

## Capabilities
- Multi-provider LLM integration
- Prompt engineering
- Token management
- Error handling and retries
- Streaming responses
- Cost optimization

## Patterns

### Multi-Provider Client
```python
from abc import ABC, abstractmethod
from typing import Optional, AsyncIterator
from dataclasses import dataclass
import httpx

@dataclass
class LLMResponse:
    content: str
    model: str
    tokens_used: int
    finish_reason: str

class BaseLLMClient(ABC):
    @abstractmethod
    async def generate(self, prompt: str, **kwargs) -> LLMResponse:
        pass

    @abstractmethod
    async def stream(self, prompt: str, **kwargs) -> AsyncIterator[str]:
        pass

class ClaudeClient(BaseLLMClient):
    def __init__(self, api_key: str, model: str = "claude-3-sonnet-20240229"):
        self.api_key = api_key
        self.model = model
        self.base_url = "https://api.anthropic.com/v1"

    async def generate(self, prompt: str, **kwargs) -> LLMResponse:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/messages",
                headers={
                    "x-api-key": self.api_key,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json"
                },
                json={
                    "model": self.model,
                    "max_tokens": kwargs.get("max_tokens", 1024),
                    "messages": [{"role": "user", "content": prompt}]
                },
                timeout=60.0
            )
            response.raise_for_status()
            data = response.json()

            return LLMResponse(
                content=data["content"][0]["text"],
                model=data["model"],
                tokens_used=data["usage"]["input_tokens"] + data["usage"]["output_tokens"],
                finish_reason=data["stop_reason"]
            )
```

### Retry with Exponential Backoff
```python
import asyncio
from typing import TypeVar, Callable
import random

T = TypeVar('T')

async def retry_with_backoff(
    func: Callable[..., T],
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    retryable_exceptions: tuple = (httpx.HTTPStatusError, httpx.TimeoutException)
) -> T:
    """Retry function with exponential backoff."""
    last_exception = None

    for attempt in range(max_retries):
        try:
            return await func()
        except retryable_exceptions as e:
            last_exception = e

            if attempt == max_retries - 1:
                raise

            # Exponential backoff with jitter
            delay = min(base_delay * (2 ** attempt), max_delay)
            delay = delay * (0.5 + random.random())

            await asyncio.sleep(delay)

    raise last_exception
```

### Prompt Template
```python
from string import Template
from typing import Dict, Any

class PromptTemplate:
    def __init__(self, template: str):
        self.template = template
        self._compiled = Template(template)

    def format(self, **kwargs: Any) -> str:
        """Format template with variables."""
        return self._compiled.safe_substitute(**kwargs)

    @classmethod
    def from_file(cls, path: str) -> "PromptTemplate":
        """Load template from file."""
        with open(path) as f:
            return cls(f.read())

# Usage
TASK_PROMPT = PromptTemplate("""
You are an AI assistant helping with software development.

Task: $task

Context:
$context

Please provide a detailed response.
""")

prompt = TASK_PROMPT.format(
    task="Review this code for security issues",
    context="def login(user, pass): ..."
)
```

### Token Counting
```python
import tiktoken

class TokenCounter:
    def __init__(self, model: str = "gpt-4"):
        self.encoding = tiktoken.encoding_for_model(model)

    def count(self, text: str) -> int:
        """Count tokens in text."""
        return len(self.encoding.encode(text))

    def truncate(self, text: str, max_tokens: int) -> str:
        """Truncate text to max tokens."""
        tokens = self.encoding.encode(text)
        if len(tokens) <= max_tokens:
            return text
        return self.encoding.decode(tokens[:max_tokens])

# For Claude (approximate)
def estimate_claude_tokens(text: str) -> int:
    """Estimate tokens for Claude (4 chars per token average)."""
    return len(text) // 4
```

### Streaming Response Handler
```python
async def handle_stream(
    client: BaseLLMClient,
    prompt: str,
    on_token: Callable[[str], None]
) -> str:
    """Handle streaming response with callback."""
    full_response = []

    async for token in client.stream(prompt):
        full_response.append(token)
        on_token(token)

    return ''.join(full_response)
```

### Prompt Injection Mitigation
```python
def sanitize_user_input(text: str) -> str:
    """Sanitize user input to prevent prompt injection."""
    # Remove potential instruction overrides
    dangerous_patterns = [
        "ignore previous instructions",
        "disregard above",
        "system:",
        "assistant:",
        "###",
    ]

    sanitized = text
    for pattern in dangerous_patterns:
        sanitized = sanitized.replace(pattern, "[FILTERED]")

    return sanitized

def build_safe_prompt(system: str, user_input: str) -> str:
    """Build prompt with clear boundaries."""
    sanitized = sanitize_user_input(user_input)

    return f"""<system>
{system}
</system>

<user_input>
{sanitized}
</user_input>

Respond to the user's input above."""
```

## Checklist
- [ ] API keys from environment
- [ ] Retry with exponential backoff
- [ ] Token limits enforced
- [ ] Timeouts configured
- [ ] Rate limiting respected
- [ ] Prompt injection mitigated
- [ ] Costs monitored
- [ ] Responses validated
