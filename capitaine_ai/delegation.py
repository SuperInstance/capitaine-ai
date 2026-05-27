"""DelegationEngine — matches tasks to the best available agent."""

from __future__ import annotations

from .crew import Agent, Crew
from .task import Task, TaskPriority


class DelegationEngine:
    """Selects the best agent for a given task based on skills, availability, and load."""

    def __init__(self, crew: Crew) -> None:
        self.crew = crew

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def find_best_agent(self, task: Task) -> Agent | None:
        """Find the best available agent for *task*.

        Selection criteria (in order):
        1. Must have all required skills
        2. Must be available (idle with open slots)
        3. Prefer agents with more matching skills
        4. Prefer agents with fewer current tasks (lighter load)
        """
        required = task.required_skills
        candidates = self.crew.find_available_with_skills(required)
        if not candidates:
            # Fallback: try agents with partial skill match
            candidates = [a for a in self.crew.available_agents if a.skill_overlap(required) > 0]
        if not candidates:
            return None

        # Sort: most skill overlap first, then fewest current tasks
        candidates.sort(
            key=lambda a: (a.skill_overlap(required), -len(a.current_task_ids)),
            reverse=True,
        )
        return candidates[0]

    def delegate(self, task: Task) -> Agent | None:
        """Find the best agent and assign the task. Returns the agent or None."""
        agent = self.find_best_agent(task)
        if agent is None:
            return None
        agent.assign_task(task.id)
        task.assign(agent.id)
        return agent

    def release(self, task: Task) -> None:
        """Release the agent that was working on *task*."""
        if task.assigned_to is None:
            return
        agent = self.crew.get_agent(task.assigned_to)
        agent.release_task(task.id)
