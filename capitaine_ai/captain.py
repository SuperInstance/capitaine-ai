"""Captain — orchestrates a crew, delegates tasks, and tracks progress."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .crew import Agent, Crew
from .delegation import DelegationEngine
from .progress import Milestone, ProgressTracker
from .task import Task, TaskPriority, TaskStatus


@dataclass
class Captain:
    """Orchestrates a crew of agents.

    Usage::

        captain = Captain(name="Hook")
        captain.crew.register(Agent(name="Alice", skills=["python", "testing"]))
        captain.add_task(Task(name="Write tests", required_skills=["testing"]))
        captain.run()
    """

    name: str = "Captain"
    crew: Crew = field(default_factory=lambda: Crew(name="default-crew"))
    tracker: ProgressTracker = field(default_factory=ProgressTracker)
    delegation: DelegationEngine | None = None

    # Internal
    _tasks: dict[str, Task] = field(default_factory=dict)
    _task_order: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.delegation = DelegationEngine(self.crew)

    # ------------------------------------------------------------------
    # Task management
    # ------------------------------------------------------------------

    def add_task(self, task: Task) -> Task:
        """Add a task to the captain's backlog."""
        self._tasks[task.id] = task
        self._task_order.append(task.id)
        self.tracker.register_task(task)
        return task

    def add_tasks(self, tasks: list[Task]) -> list[Task]:
        return [self.add_task(t) for t in tasks]

    def get_task(self, task_id: str) -> Task:
        if task_id not in self._tasks:
            raise KeyError(f"No task with id={task_id}")
        return self._tasks[task_id]

    @property
    def tasks(self) -> list[Task]:
        return [self._tasks[tid] for tid in self._task_order]

    # ------------------------------------------------------------------
    # Milestone management
    # ------------------------------------------------------------------

    def add_milestone(self, name: str, task_ids: list[str], description: str = "") -> Milestone:
        m = Milestone(name=name, task_ids=task_ids, description=description)
        self.tracker.add_milestone(m)
        return m

    # ------------------------------------------------------------------
    # Dependency resolution
    # ------------------------------------------------------------------

    def _resolve_dependencies(self) -> None:
        """Move PENDING tasks to READY if all deps are satisfied."""
        for task in self._tasks.values():
            if task.status != TaskStatus.PENDING:
                continue
            if not task.dependencies:
                task.mark_ready()
                continue
            all_deps_done = all(
                self._tasks.get(dep_id, Task(name="unknown")).is_terminal
                for dep_id in task.dependencies
            )
            if all_deps_done:
                task.mark_ready()

    # ------------------------------------------------------------------
    # Execution
    # ------------------------------------------------------------------

    def delegate_ready(self) -> list[tuple[Task, Agent]]:
        """Delegate all READY tasks. Returns list of (task, agent) pairs."""
        self._resolve_dependencies()
        assigned: list[tuple[Task, Agent]] = []
        # Process higher priority first
        ready = sorted(
            [t for t in self._tasks.values() if t.status == TaskStatus.READY],
            key=lambda t: t.priority,
            reverse=True,
        )
        for task in ready:
            assert self.delegation is not None
            agent = self.delegation.delegate(task)
            if agent:
                assigned.append((task, agent))
        return assigned

    def run(self) -> dict[str, Any]:
        """Full orchestration pass: resolve deps, delegate, and simulate execution.

        In a real system each agent would execute asynchronously. Here we run
        a synchronous simulation that completes all delegated tasks instantly.

        Returns the tracker summary.
        """
        # Keep delegating until no more tasks can be assigned
        while True:
            assigned = self.delegate_ready()
            if not assigned:
                break
            for task, agent in assigned:
                task.start()
                # Simulate successful execution
                task.complete(result=f"completed by {agent.name}")
                assert self.delegation is not None
                self.delegation.release(task)

        # Final dependency resolution pass
        self._resolve_dependencies()
        # Try once more after completions unlocked deps
        while True:
            assigned = self.delegate_ready()
            if not assigned:
                break
            for task, agent in assigned:
                task.start()
                task.complete(result=f"completed by {agent.name}")
                assert self.delegation is not None
                self.delegation.release(task)

        return self.tracker.summary()

    # ------------------------------------------------------------------
    # Convenience
    # ------------------------------------------------------------------

    @property
    def progress(self) -> dict[str, Any]:
        return self.tracker.summary()
