"""ProgressTracker — milestones, ETA estimation, and bottleneck detection."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from .task import Task, TaskStatus


@dataclass
class Milestone:
    """A named checkpoint over a group of tasks."""

    name: str
    task_ids: list[str] = field(default_factory=list)
    description: str = ""

    @property
    def is_complete(self) -> bool:
        # Checked against the tracker's task store at runtime
        return False  # overridden by ProgressTracker


class ProgressTracker:
    """Tracks progress across tasks with milestone support and bottleneck detection."""

    def __init__(self) -> None:
        self._tasks: dict[str, Task] = {}
        self._milestones: list[Milestone] = []

    # ------------------------------------------------------------------
    # Registration
    # ------------------------------------------------------------------

    def register_task(self, task: Task) -> None:
        self._tasks[task.id] = task

    def register_tasks(self, tasks: list[Task]) -> None:
        for t in tasks:
            self.register_task(t)

    def add_milestone(self, milestone: Milestone) -> None:
        self._milestones.append(milestone)

    # ------------------------------------------------------------------
    # Progress metrics
    # ------------------------------------------------------------------

    @property
    def total(self) -> int:
        return len(self._tasks)

    @property
    def completed(self) -> int:
        return sum(1 for t in self._tasks.values() if t.status == TaskStatus.COMPLETED)

    @property
    def failed(self) -> int:
        return sum(1 for t in self._tasks.values() if t.status == TaskStatus.FAILED)

    @property
    def in_progress(self) -> int:
        return sum(1 for t in self._tasks.values() if t.status == TaskStatus.RUNNING)

    @property
    def pending(self) -> int:
        return sum(1 for t in self._tasks.values() if t.status in (TaskStatus.PENDING, TaskStatus.READY))

    @property
    def completion_pct(self) -> float:
        """Percentage of terminal tasks (completed or failed) that are completed."""
        terminal = self.completed + self.failed
        if terminal == 0:
            return 0.0
        return (self.completed / terminal) * 100.0

    @property
    def overall_progress(self) -> float:
        """Percentage of all tasks that are completed."""
        if self.total == 0:
            return 0.0
        return (self.completed / self.total) * 100.0

    # ------------------------------------------------------------------
    # ETA estimation
    # ------------------------------------------------------------------

    def estimate_eta_seconds(self) -> float | None:
        """Rough ETA based on average throughput so far.

        Returns None if no tasks have completed yet.
        """
        done = [t for t in self._tasks.values() if t.status == TaskStatus.COMPLETED and t.duration_seconds is not None]
        if not done:
            return None
        avg_duration = sum(t.duration_seconds for t in done) / len(done)  # type: ignore[arg-type]
        remaining = self.total - self.completed - self.failed
        return avg_duration * remaining

    # ------------------------------------------------------------------
    # Bottleneck detection
    # ------------------------------------------------------------------

    def find_bottlenecks(self) -> list[dict[str, Any]]:
        """Identify bottleneck tasks: long-running or blocked by dependencies.

        Returns a list of dicts with ``task_id``, ``name``, and ``reason``.
        """
        bottlenecks: list[dict[str, Any]] = []

        # Find the average completed duration
        durations = [
            t.duration_seconds
            for t in self._tasks.values()
            if t.status == TaskStatus.COMPLETED and t.duration_seconds is not None
        ]
        avg_duration = sum(durations) / len(durations) if durations else 0

        for task in self._tasks.values():
            if task.status == TaskStatus.RUNNING and avg_duration > 0:
                if task.duration_seconds is not None and task.duration_seconds > avg_duration * 2:
                    bottlenecks.append({
                        "task_id": task.id,
                        "name": task.name,
                        "reason": "running_more_than_2x_avg",
                        "duration_seconds": task.duration_seconds,
                        "avg_seconds": avg_duration,
                    })
            elif task.status == TaskStatus.PENDING:
                # Check if blocked by incomplete dependencies
                blocked_by = [
                    dep_id
                    for dep_id in task.dependencies
                    if dep_id in self._tasks and not self._tasks[dep_id].is_terminal
                ]
                if blocked_by:
                    bottlenecks.append({
                        "task_id": task.id,
                        "name": task.name,
                        "reason": "blocked_by_dependencies",
                        "blocked_by": blocked_by,
                    })

        return bottlenecks

    # ------------------------------------------------------------------
    # Milestone progress
    # ------------------------------------------------------------------

    def milestone_progress(self, milestone: Milestone) -> float:
        """Return completion percentage for a milestone's tasks."""
        if not milestone.task_ids:
            return 0.0
        completed = sum(
            1 for tid in milestone.task_ids
            if tid in self._tasks and self._tasks[tid].status == TaskStatus.COMPLETED
        )
        return (completed / len(milestone.task_ids)) * 100.0

    def milestone_complete(self, milestone: Milestone) -> bool:
        return self.milestone_progress(milestone) == 100.0

    @property
    def milestones(self) -> list[Milestone]:
        return list(self._milestones)

    # ------------------------------------------------------------------
    # Summary
    # ------------------------------------------------------------------

    def summary(self) -> dict[str, Any]:
        return {
            "total": self.total,
            "completed": self.completed,
            "failed": self.failed,
            "in_progress": self.in_progress,
            "pending": self.pending,
            "completion_pct": round(self.completion_pct, 1),
            "overall_progress": round(self.overall_progress, 1),
            "eta_seconds": self.estimate_eta_seconds(),
            "bottlenecks": self.find_bottlenecks(),
        }
