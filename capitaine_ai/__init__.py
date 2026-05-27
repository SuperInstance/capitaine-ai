"""Capitaine AI — AI captain orchestration for coordinating agent crews."""

from .captain import Captain
from .crew import Crew, Agent
from .task import Task, TaskStatus, TaskPriority
from .delegation import DelegationEngine
from .progress import ProgressTracker

__all__ = [
    "Captain",
    "Crew",
    "Agent",
    "Task",
    "TaskStatus",
    "TaskPriority",
    "DelegationEngine",
    "ProgressTracker",
]
__version__ = "0.1.0"
