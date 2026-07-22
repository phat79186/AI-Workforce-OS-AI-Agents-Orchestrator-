# Specialized Agents

The AI Coding Tools Collaborative provides specialized agents for different development domains. These agents have domain-specific knowledge, best practices, and code patterns.

## Available Specialized Agents

### Web Frontend (`web-frontend`)
Expert in modern frontend development with React, Vue, Angular, and CSS frameworks.

**Capabilities:**
- React hooks and component patterns
- Vue 3 Composition API
- CSS-in-JS and Tailwind CSS
- Accessibility (WCAG compliance)
- Performance optimization (lazy loading, code splitting)

**Example Use:**
```bash
# Claude
claude -a web-frontend "Build a responsive dashboard with React"

# Codex
codex --agent web-frontend "Create an accessible form component"
```

### Backend API (`backend-api`)
Specialist in REST APIs, GraphQL, microservices, and backend architectures.

**Capabilities:**
- RESTful API design (OpenAPI/Swagger)
- GraphQL schema design
- Microservices patterns
- Database integration
- Authentication and authorization

**Example Use:**
```bash
claude -a backend-api "Design a REST API for user management"
```

### Security Specialist (`security-specialist`)
Expert in application security, OWASP compliance, and secure coding.

**Capabilities:**
- OWASP Top 10 vulnerability analysis
- Input validation and sanitization
- Secure authentication patterns
- Dependency vulnerability scanning
- Penetration testing guidance

**Example Use:**
```bash
claude -a security-specialist "Review this code for security vulnerabilities"
```

### DevOps Infrastructure (`devops-infrastructure`)
Specialist in CI/CD, containerization, and cloud infrastructure.

**Capabilities:**
- Docker and Kubernetes
- GitHub Actions, GitLab CI
- Terraform and IaC
- Cloud platforms (AWS, GCP, Azure)
- Monitoring and observability

**Example Use:**
```bash
claude -a devops-infrastructure "Create a Kubernetes deployment for our API"
```

### AI/ML Engineer (`ai-ml-engineer`)
Expert in machine learning pipelines, LLM integration, and data science.

**Capabilities:**
- ML pipeline design
- Model optimization (quantization, pruning)
- LLM integration (LangChain, LlamaIndex)
- Vector databases and RAG
- Feature engineering

**Example Use:**
```bash
claude -a ai-ml-engineer "Build a RAG pipeline with vector search"
```

### Database Architect (`database-architect`)
Specialist in database design, optimization, and data modeling.

**Capabilities:**
- Schema design and normalization
- Query optimization
- Index strategies
- Migration planning
- Data modeling (ER diagrams)

**Example Use:**
```bash
claude -a database-architect "Optimize this slow query"
```

### Mobile Developer (`mobile-developer`)
Expert in iOS, Android, and cross-platform mobile development.

**Capabilities:**
- React Native and Flutter
- Native iOS (Swift) and Android (Kotlin)
- Mobile UI patterns
- App performance optimization
- Push notifications

**Example Use:**
```bash
claude -a mobile-developer "Build a cross-platform authentication flow"
```

### Performance Engineer (`performance-engineer`)
Specialist in application performance, profiling, and optimization.

**Capabilities:**
- Profiling and benchmarking
- Memory optimization
- Load testing (k6, Locust)
- Caching strategies
- Database query optimization

**Example Use:**
```bash
claude -a performance-engineer "Profile and optimize this API endpoint"
```

### Documentation Writer (`documentation-writer`)
Expert in technical writing and documentation.

**Capabilities:**
- API documentation (OpenAPI)
- Architecture diagrams (Mermaid, PlantUML)
- README and onboarding docs
- Code comments and docstrings
- Changelogs

**Example Use:**
```bash
claude -a documentation-writer "Generate API documentation for this module"
```

## Agent File Locations

### Claude Agents
Located in `.claude/agents/`:
```
.claude/agents/
├── web-frontend.md
├── backend-api.md
├── security-specialist.md
├── devops-infrastructure.md
├── ai-ml-engineer.md
├── database-architect.md
├── mobile-developer.md
├── performance-engineer.md
└── documentation-writer.md
```

### Codex Agents
Located in `.codex/agents/`:
```
.codex/agents/
├── web-frontend.toml
├── backend-api.toml
├── security-specialist.toml
├── devops-infrastructure.toml
├── ai-ml-engineer.toml
├── database-architect.toml
├── mobile-developer.toml
├── performance-engineer.toml
└── documentation-writer.toml
```

## Creating Custom Agents

### Claude Agent Format (Markdown)
```markdown
# Agent Name

## Role
Description of the agent's expertise and role.

## Core Competencies
- Competency 1
- Competency 2

## Code Patterns
```python
# Example code patterns
```

## Checklists
- [ ] Checklist item 1
- [ ] Checklist item 2

## Project-Specific Guidelines
Guidelines for this specific project.
```

### Codex Agent Format (TOML)
```toml
model = "o4-mini"
approval_mode = "auto-edit"
nickname = "agent-name"

[developer]
preamble = """
Agent description and expertise.
"""

instructions = """
Detailed instructions for the agent.
"""
```

## Using Agents with Orchestrator

The orchestrator can route tasks to specialized agents:

```python
from orchestrator.core import OrchestratorEngine

engine = OrchestratorEngine()

# Execute with agent recommendation
result = engine.execute_task(
    "Build a secure REST API",
    agent_hints=["backend-api", "security-specialist"]
)
```

## Using Agents with Agentic Team

The agentic team assigns roles that can leverage specialized agents:

```python
from agentic_team import AgenticTeamEngine

engine = AgenticTeamEngine()

# The software_developer role can use specialized agents
result = engine.execute_task(
    "Implement user authentication with OAuth",
    lead_role="software_developer"
)
```

## Best Practices

1. **Choose the right agent**: Match agent expertise to the task
2. **Combine agents**: Complex tasks may need multiple agents
3. **Provide context**: Agents work better with clear requirements
4. **Review output**: Verify agent suggestions before implementing
5. **Customize for your project**: Add project-specific guidelines to agent definitions
