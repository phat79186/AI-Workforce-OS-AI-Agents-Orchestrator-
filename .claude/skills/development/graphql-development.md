# Skill: GraphQL Development

Design and implement GraphQL APIs with proper schema design and resolvers.

## Capabilities
- Schema definition
- Resolver implementation
- Query optimization (N+1 prevention)
- Error handling
- Authentication/Authorization
- Subscriptions

## Patterns

### Schema Definition
```graphql
type Query {
  task(id: ID!): Task
  tasks(filter: TaskFilter, pagination: PaginationInput): TaskConnection!
}

type Mutation {
  createTask(input: CreateTaskInput!): TaskPayload!
  executeTask(id: ID!): ExecutionPayload!
}

type Subscription {
  taskStatusChanged(taskId: ID!): Task!
}

type Task {
  id: ID!
  content: String!
  status: TaskStatus!
  agent: Agent!
  createdAt: DateTime!
  result: TaskResult
}

type TaskConnection {
  edges: [TaskEdge!]!
  pageInfo: PageInfo!
  totalCount: Int!
}

type TaskEdge {
  node: Task!
  cursor: String!
}

input TaskFilter {
  status: TaskStatus
  agentId: ID
  createdAfter: DateTime
}

input PaginationInput {
  first: Int
  after: String
  last: Int
  before: String
}

enum TaskStatus {
  PENDING
  IN_PROGRESS
  COMPLETED
  FAILED
}
```

### DataLoader for N+1 Prevention
```python
from aiodataloader import DataLoader
from typing import List

class AgentLoader(DataLoader):
    async def batch_load_fn(self, agent_ids: List[str]) -> List[Agent]:
        """Batch load agents to prevent N+1 queries."""
        agents = await self.db.get_agents_by_ids(agent_ids)
        agent_map = {a.id: a for a in agents}
        return [agent_map.get(id) for id in agent_ids]

# In resolver context
@strawberry.type
class Query:
    @strawberry.field
    async def tasks(self, info) -> List[Task]:
        tasks = await db.get_tasks()
        # Use dataloader from context
        loader = info.context.agent_loader
        for task in tasks:
            task.agent = await loader.load(task.agent_id)
        return tasks
```

### Error Handling
```python
from graphql import GraphQLError

class TaskNotFoundError(GraphQLError):
    def __init__(self, task_id: str):
        super().__init__(
            message=f"Task not found: {task_id}",
            extensions={"code": "TASK_NOT_FOUND", "task_id": task_id}
        )

class ValidationError(GraphQLError):
    def __init__(self, field: str, message: str):
        super().__init__(
            message=message,
            extensions={"code": "VALIDATION_ERROR", "field": field}
        )
```

## Checklist
- [ ] Schema well-designed with proper types
- [ ] DataLoader prevents N+1 queries
- [ ] Pagination implemented (cursor-based)
- [ ] Errors have proper extensions
- [ ] Input validation on mutations
- [ ] Auth checks in resolvers
- [ ] Query complexity limits set
