"""Crew model — agent registration, skill matching, and availability tracking."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


class AgentStatus(str, Enum):
    IDLE = "idle"
    BUSY = "busy"
    OFFLINE = "offline"


@dataclass
class Agent:
    """An individual agent that can be assigned tasks."""

    name: str
    skills: list[str] = field(default_factory=list)
    status: AgentStatus = AgentStatus.IDLE
    max_concurrent_tasks: int = 3
    current_task_ids: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @property
    def available_slots(self) -> int:
        return max(0, self.max_concurrent_tasks - len(self.current_task_ids))

    @property
    def is_available(self) -> bool:
        return self.status == AgentStatus.IDLE and self.available_slots > 0

    def has_skills(self, required: list[str]) -> bool:
        """Return True if this agent has ALL required skills."""
        return set(required).issubset(set(self.skills))

    def skill_overlap(self, required: list[str]) -> int:
        """Count how many required skills this agent has."""
        return len(set(required) & set(self.skills))

    def assign_task(self, task_id: str) -> None:
        if not self.is_available:
            raise ValueError(f"Agent '{self.name}' is not available")
        self.current_task_ids.append(task_id)
        if self.available_slots == 0:
            self.status = AgentStatus.BUSY

    def release_task(self, task_id: str) -> None:
        if task_id in self.current_task_ids:
            self.current_task_ids.remove(task_id)
        if self.available_slots > 0:
            self.status = AgentStatus.IDLE


@dataclass
class Crew:
    """A collection of agents managed by a captain."""

    name: str
    agents: dict[str, Agent] = field(default_factory=dict)
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])

    # ------------------------------------------------------------------
    # Agent management
    # ------------------------------------------------------------------

    def register(self, agent: Agent) -> Agent:
        """Register an agent with the crew. Returns the agent."""
        if agent.id in self.agents:
            raise ValueError(f"Agent '{agent.name}' (id={agent.id}) already registered")
        self.agents[agent.id] = agent
        return agent

    def unregister(self, agent_id: str) -> Agent:
        """Remove an agent from the crew. Returns the removed agent."""
        if agent_id not in self.agents:
            raise KeyError(f"No agent with id={agent_id}")
        return self.agents.pop(agent_id)

    def get_agent(self, agent_id: str) -> Agent:
        if agent_id not in self.agents:
            raise KeyError(f"No agent with id={agent_id}")
        return self.agents[agent_id]

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    @property
    def available_agents(self) -> list[Agent]:
        return [a for a in self.agents.values() if a.is_available]

    def find_agents_with_skills(self, skills: list[str]) -> list[Agent]:
        """Return agents that have ALL specified skills, sorted by skill overlap desc."""
        matched = [a for a in self.agents.values() if a.has_skills(skills)]
        matched.sort(key=lambda a: a.skill_overlap(skills), reverse=True)
        return matched

    def find_available_with_skills(self, skills: list[str]) -> list[Agent]:
        """Return available agents with ALL specified skills."""
        return [a for a in self.find_agents_with_skills(skills) if a.is_available]

    @property
    def size(self) -> int:
        return len(self.agents)
