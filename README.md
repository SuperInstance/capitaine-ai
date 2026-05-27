# Capitaine.ai

> AI captain orchestration — coordinate agent crews with task delegation and progress tracking.

**Part of the Lucineer ecosystem.**

## Install

```bash
pip install capitaine-ai
```

## Quick Start

```python
from capitaine_ai import Agent, Captain, Task, TaskPriority

# Create a captain
captain = Captain(name="Hook")

# Register agents with skills
captain.crew.register(Agent(name="Alice", skills=["python", "testing"]))
captain.crew.register(Agent(name="Bob", skills=["rust", "systems"]))
captain.crew.register(Agent(name="Carol", skills=["python", "docs"]))

# Add tasks with skill requirements and dependencies
write_code = captain.add_task(
    Task(name="Write API module", required_skills=["python"], priority=TaskPriority.HIGH)
)
write_tests = captain.add_task(
    Task(name="Write tests", required_skills=["testing"], dependencies=[write_code.id])
)
write_docs = captain.add_task(
    Task(name="Write documentation", required_skills=["docs"], dependencies=[write_code.id])
)

# Run orchestration
result = captain.run()
print(result)
# {'total': 3, 'completed': 3, 'failed': 0, 'in_progress': 0, 'pending': 0, ...}
```

## Core Concepts

### Agent

An agent has skills, availability status, and a concurrency limit:

```python
from capitaine_ai import Agent

agent = Agent(
    name="Alice",
    skills=["python", "testing", "docker"],
    max_concurrent_tasks=3,
)
print(agent.is_available)       # True
print(agent.has_skills(["python", "testing"]))  # True
```

### Crew

A crew is a named collection of agents:

```python
from capitaine_ai import Crew, Agent

crew = Crew(name="engineering")
crew.register(Agent(name="Alice", skills=["python"]))
crew.register(Agent(name="Bob", skills=["rust"]))

# Find available agents with specific skills
candidates = crew.find_available_with_skills(["python"])
```

### Task

Tasks have a full lifecycle — pending → ready → assigned → running → completed/failed:

```python
from capitaine_ai import Task, TaskPriority

task = Task(
    name="Deploy to production",
    required_skills=["devops"],
    priority=TaskPriority.CRITICAL,
    dependencies=["task-id-abc"],
)

task.mark_ready()
task.assign("agent-id")
task.start()
task.complete(result={"deployed_to": "prod-us-east"})
```

### Captain

The captain orchestrates everything — resolving dependencies, delegating to the best agent, and tracking progress:

```python
from capitaine_ai import Captain, Agent, Task

captain = Captain(name="Hook")
captain.crew.register(Agent(name="Dev", skills=["python"]))
captain.add_task(Task(name="Build feature", required_skills=["python"]))

# Orchestrate
result = captain.run()

# Check progress anytime
print(captain.progress)
```

### Progress Tracking & Milestones

```python
from capitaine_ai import Captain, Agent, Task
from capitaine_ai.progress import Milestone

captain = Captain(name="Hook")
captain.crew.register(Agent(name="Worker", skills=["python"]))

t1 = captain.add_task(Task(name="Phase 1 work", required_skills=["python"]))
t2 = captain.add_task(Task(name="Phase 2 work", required_skills=["python"]))

milestone = captain.add_milestone("MVP", [t1.id, t2.id], "Minimum viable product")

captain.run()

print(captain.tracker.milestone_complete(milestone))  # True
print(captain.tracker.milestone_progress(milestone))  # 100.0

# Bottleneck detection
print(captain.tracker.find_bottlenecks())
```

## Architecture

```
capitaine_ai/
├── __init__.py        # Public API
├── captain.py         # Captain — top-level orchestrator
├── crew.py            # Crew & Agent — registration, skills, availability
├── task.py            # Task — lifecycle, dependencies, priority
├── delegation.py      # DelegationEngine — task-to-agent matching
└── progress.py        # ProgressTracker — milestones, ETA, bottlenecks
```

### Design Principles

- **Zero external dependencies** — only stdlib + pytest for testing
- **Dataclasses throughout** — clean, typed, no magic
- **Composable** — use individual components or the full Captain orchestrator
- **Synchronous core** — easy to understand, easy to wrap in async

## License

MIT
