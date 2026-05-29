# capitaine-ai

**AI captain orchestration** — coordinate agent crews with task delegation, dependency resolution, and progress tracking. Pure Python.

## What This Gives You

- **Crew management** — register agents with skills and concurrency limits
- **Task delegation** — assign tasks by required skills with dependency ordering
- **Priority queues** — HIGH, MEDIUM, LOW priorities with fair scheduling
- **Progress tracking** — real-time task status across the crew
- **Zero dependencies** — stdlib only, pytest for tests

## Installation

```bash
pip install capitaine-ai
```

## Quick Start

```python
from capitaine_ai import Agent, Captain, Task, TaskPriority

captain = Captain(name="Hook")

captain.crew.register(Agent(name="Alice", skills=["python", "testing"]))
captain.crew.register(Agent(name="Bob", skills=["rust", "systems"]))

write_code = captain.add_task(
    Task(name="Write API", required_skills=["python"], priority=TaskPriority.HIGH)
)
write_tests = captain.add_task(
    Task(name="Write tests", required_skills=["testing"], dependencies=[write_code.id])
)

result = captain.run()
# {'total': 2, 'completed': 2, 'failed': 0}
```

## API Reference

| Class | Purpose |
|-------|---------|
| `Captain` | Orchestrator — manages crew, tasks, and delegation |
| `Agent` | Worker with skills, availability, concurrency limit |
| `Task` | Unit of work with skill requirements and dependencies |
| `Crew` | Agent registry with skill-based lookup |
| `DelegationEngine` | Assigns tasks to best-fit available agents |

## Testing

```bash
pip install -e ".[dev]"
pytest
```

## How It Fits

The orchestration engine behind `capitaine-agent`'s crew features. Part of the Cocapn Fleet.

## License

MIT
