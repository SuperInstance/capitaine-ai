"""Task model with dependencies, priority, assignment, and status lifecycle."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import IntEnum
from typing import Any


class TaskStatus(IntEnum):
    """Lifecycle states for a task."""

    PENDING = 0
    READY = 1      # all dependencies met
    ASSIGNED = 2
    RUNNING = 3
    COMPLETED = 4
    FAILED = 5
    CANCELLED = 6


class TaskPriority(IntEnum):
    """Task priority levels (higher = more important)."""

    LOW = 0
    NORMAL = 1
    HIGH = 2
    CRITICAL = 3


@dataclass
class Task:
    """A unit of work that can be assigned to an agent."""

    name: str
    description: str = ""
    priority: TaskPriority = TaskPriority.NORMAL
    required_skills: list[str] = field(default_factory=list)
    dependencies: list[str] = field(default_factory=list)  # task IDs
    status: TaskStatus = TaskStatus.PENDING
    assigned_to: str | None = None  # agent ID
    result: Any = None
    error: str | None = None

    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    started_at: datetime | None = None
    completed_at: datetime | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    # ------------------------------------------------------------------
    # Lifecycle helpers
    # ------------------------------------------------------------------

    def mark_ready(self) -> None:
        if self.status == TaskStatus.PENDING:
            self.status = TaskStatus.READY

    def assign(self, agent_id: str) -> None:
        if self.status not in (TaskStatus.PENDING, TaskStatus.READY):
            raise ValueError(
                f"Cannot assign task '{self.name}' in status {self.status.name}"
            )
        self.assigned_to = agent_id
        self.status = TaskStatus.ASSIGNED

    def start(self) -> None:
        if self.status != TaskStatus.ASSIGNED:
            raise ValueError(
                f"Cannot start task '{self.name}' in status {self.status.name}"
            )
        self.status = TaskStatus.RUNNING
        self.started_at = datetime.now(timezone.utc)

    def complete(self, result: Any = None) -> None:
        if self.status != TaskStatus.RUNNING:
            raise ValueError(
                f"Cannot complete task '{self.name}' in status {self.status.name}"
            )
        self.status = TaskStatus.COMPLETED
        self.completed_at = datetime.now(timezone.utc)
        self.result = result

    def fail(self, error: str) -> None:
        if self.status not in (TaskStatus.ASSIGNED, TaskStatus.RUNNING):
            raise ValueError(
                f"Cannot fail task '{self.name}' in status {self.status.name}"
            )
        self.status = TaskStatus.FAILED
        self.completed_at = datetime.now(timezone.utc)
        self.error = error

    def cancel(self) -> None:
        if self.status in (TaskStatus.COMPLETED, TaskStatus.CANCELLED):
            raise ValueError(
                f"Cannot cancel task '{self.name}' in status {self.status.name}"
            )
        self.status = TaskStatus.CANCELLED
        self.completed_at = datetime.now(timezone.utc)

    @property
    def duration_seconds(self) -> float | None:
        """Elapsed time in seconds between start and completion (or now)."""
        if self.started_at is None:
            return None
        end = self.completed_at or datetime.now(timezone.utc)
        return (end - self.started_at).total_seconds()

    @property
    def is_terminal(self) -> bool:
        return self.status in (TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED)
