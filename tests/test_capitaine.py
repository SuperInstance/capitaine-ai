"""Comprehensive tests for capitaine_ai."""

import pytest

from capitaine_ai import (
    Agent,
    Captain,
    Crew,
    DelegationEngine,
    ProgressTracker,
    Task,
    TaskPriority,
    TaskStatus,
)
from capitaine_ai.progress import Milestone


# ======================================================================
# Task tests
# ======================================================================

class TestTaskLifecycle:
    def test_create_task(self):
        t = Task(name="test", description="desc")
        assert t.status == TaskStatus.PENDING
        assert t.priority == TaskPriority.NORMAL
        assert t.assigned_to is None

    def test_lifecycle_happy_path(self):
        t = Task(name="test")
        t.mark_ready()
        assert t.status == TaskStatus.READY
        t.assign("agent-1")
        assert t.status == TaskStatus.ASSIGNED
        assert t.assigned_to == "agent-1"
        t.start()
        assert t.status == TaskStatus.RUNNING
        assert t.started_at is not None
        t.complete(result={"key": "value"})
        assert t.status == TaskStatus.COMPLETED
        assert t.result == {"key": "value"}
        assert t.completed_at is not None
        assert t.duration_seconds is not None
        assert t.duration_seconds >= 0

    def test_fail_task(self):
        t = Task(name="test")
        t.mark_ready()
        t.assign("agent-1")
        t.start()
        t.fail("something broke")
        assert t.status == TaskStatus.FAILED
        assert t.error == "something broke"

    def test_cancel_task(self):
        t = Task(name="test")
        t.cancel()
        assert t.status == TaskStatus.CANCELLED

    def test_cannot_assign_completed_task(self):
        t = Task(name="test")
        t.cancel()
        with pytest.raises(ValueError):
            t.assign("agent-1")

    def test_cannot_start_unassigned_task(self):
        t = Task(name="test")
        with pytest.raises(ValueError):
            t.start()

    def test_cannot_complete_non_running_task(self):
        t = Task(name="test")
        with pytest.raises(ValueError):
            t.complete()

    def test_cannot_cancel_completed_task(self):
        t = Task(name="test")
        t.mark_ready()
        t.assign("a")
        t.start()
        t.complete()
        with pytest.raises(ValueError):
            t.cancel()

    def test_task_priority_ordering(self):
        assert TaskPriority.CRITICAL > TaskPriority.HIGH > TaskPriority.NORMAL > TaskPriority.LOW

    def test_task_dependencies(self):
        t = Task(name="test", dependencies=["dep1", "dep2"])
        assert len(t.dependencies) == 2

    def test_is_terminal(self):
        t = Task(name="test")
        assert not t.is_terminal
        t.cancel()
        assert t.is_terminal


# ======================================================================
# Agent / Crew tests
# ======================================================================

class TestAgent:
    def test_create_agent(self):
        a = Agent(name="Alice", skills=["python", "testing"])
        assert a.is_available
        assert a.available_slots == 3

    def test_assign_and_release(self):
        a = Agent(name="Bob", skills=["rust"], max_concurrent_tasks=1)
        a.assign_task("t1")
        assert not a.is_available
        assert a.available_slots == 0
        a.release_task("t1")
        assert a.is_available

    def test_has_skills(self):
        a = Agent(name="C", skills=["python", "testing", "docker"])
        assert a.has_skills(["python", "testing"])
        assert not a.has_skills(["python", "rust"])

    def test_skill_overlap(self):
        a = Agent(name="D", skills=["python", "testing"])
        assert a.skill_overlap(["python", "rust", "docker"]) == 1
        assert a.skill_overlap(["python", "testing"]) == 2

    def test_cannot_assign_unavailable(self):
        a = Agent(name="E", max_concurrent_tasks=1)
        a.assign_task("t1")
        with pytest.raises(ValueError):
            a.assign_task("t2")


class TestCrew:
    def test_register_agent(self):
        crew = Crew(name="test-crew")
        a = crew.register(Agent(name="Alice", skills=["python"]))
        assert crew.size == 1
        assert crew.get_agent(a.id) is a

    def test_unregister_agent(self):
        crew = Crew(name="test-crew")
        a = crew.register(Agent(name="Alice"))
        crew.unregister(a.id)
        assert crew.size == 0

    def test_duplicate_registration(self):
        crew = Crew(name="test-crew")
        a = Agent(name="Alice")
        crew.register(a)
        with pytest.raises(ValueError):
            crew.register(a)

    def test_available_agents(self):
        crew = Crew(name="test-crew")
        a1 = crew.register(Agent(name="Alice"))
        a2 = crew.register(Agent(name="Bob", max_concurrent_tasks=1))
        a2.assign_task("some-task")
        assert len(crew.available_agents) == 1
        assert crew.available_agents[0] is a1

    def test_find_agents_with_skills(self):
        crew = Crew(name="test-crew")
        crew.register(Agent(name="Alice", skills=["python", "testing"]))
        crew.register(Agent(name="Bob", skills=["python"]))
        matched = crew.find_agents_with_skills(["python", "testing"])
        assert len(matched) == 1
        assert matched[0].name == "Alice"

    def test_find_available_with_skills(self):
        crew = Crew(name="test-crew")
        a1 = crew.register(Agent(name="Alice", skills=["python"]))
        a2 = crew.register(Agent(name="Bob", skills=["python"], max_concurrent_tasks=1))
        a2.assign_task("t1")
        result = crew.find_available_with_skills(["python"])
        assert len(result) == 1
        assert result[0] is a1


# ======================================================================
# DelegationEngine tests
# ======================================================================

class TestDelegationEngine:
    def test_find_best_agent(self):
        crew = Crew(name="test")
        a1 = crew.register(Agent(name="Alice", skills=["python", "testing"]))
        crew.register(Agent(name="Bob", skills=["python"]))
        engine = DelegationEngine(crew)
        task = Task(name="test", required_skills=["python", "testing"])
        best = engine.find_best_agent(task)
        assert best is a1

    def test_no_matching_agent(self):
        crew = Crew(name="test")
        crew.register(Agent(name="Alice", skills=["python"]))
        engine = DelegationEngine(crew)
        task = Task(name="test", required_skills=["rust"])
        assert engine.find_best_agent(task) is None

    def test_no_available_agent(self):
        crew = Crew(name="test")
        a = crew.register(Agent(name="Alice", skills=["python"], max_concurrent_tasks=1))
        a.assign_task("other")
        engine = DelegationEngine(crew)
        task = Task(name="test", required_skills=["python"])
        assert engine.find_best_agent(task) is None

    def test_delegate_assigns_task(self):
        crew = Crew(name="test")
        crew.register(Agent(name="Alice", skills=["python"]))
        engine = DelegationEngine(crew)
        task = Task(name="test", required_skills=["python"])
        agent = engine.delegate(task)
        assert agent is not None
        assert task.assigned_to == agent.id
        assert task.status == TaskStatus.ASSIGNED

    def test_release_agent(self):
        crew = Crew(name="test")
        crew.register(Agent(name="Alice", skills=["python"], max_concurrent_tasks=1))
        engine = DelegationEngine(crew)
        task = Task(name="test", required_skills=["python"])
        agent = engine.delegate(task)
        assert not agent.is_available
        engine.release(task)
        assert agent.is_available


# ======================================================================
# ProgressTracker tests
# ======================================================================

class TestProgressTracker:
    def test_empty_tracker(self):
        t = ProgressTracker()
        assert t.total == 0
        assert t.completion_pct == 0.0

    def test_track_tasks(self):
        tracker = ProgressTracker()
        t1 = Task(name="a")
        t2 = Task(name="b")
        tracker.register_tasks([t1, t2])
        assert tracker.total == 2

        t1.mark_ready()
        t1.assign("agent-1")
        t1.start()
        t1.complete()
        assert tracker.completed == 1
        assert tracker.overall_progress == 50.0

    def test_bottleneck_detection_blocked(self):
        tracker = ProgressTracker()
        dep = Task(name="dep")
        blocked = Task(name="blocked", dependencies=[dep.id])
        tracker.register_tasks([dep, blocked])
        bottlenecks = tracker.find_bottlenecks()
        assert len(bottlenecks) == 1
        assert bottlenecks[0]["reason"] == "blocked_by_dependencies"

    def test_milestones(self):
        tracker = ProgressTracker()
        t1 = Task(name="a")
        t2 = Task(name="b")
        tracker.register_tasks([t1, t2])
        m = Milestone(name="phase-1", task_ids=[t1.id, t2.id])
        tracker.add_milestone(m)
        assert tracker.milestone_progress(m) == 0.0

        t1.mark_ready(); t1.assign("a1"); t1.start(); t1.complete()
        assert tracker.milestone_progress(m) == 50.0
        assert not tracker.milestone_complete(m)

        t2.mark_ready(); t2.assign("a1"); t2.start(); t2.complete()
        assert tracker.milestone_complete(m)

    def test_eta_with_no_completed(self):
        tracker = ProgressTracker()
        tracker.register_task(Task(name="a"))
        assert tracker.estimate_eta_seconds() is None

    def test_summary(self):
        tracker = ProgressTracker()
        tracker.register_task(Task(name="a"))
        s = tracker.summary()
        assert "total" in s
        assert "bottlenecks" in s


# ======================================================================
# Captain integration tests
# ======================================================================

class TestCaptain:
    def test_simple_run(self):
        cap = Captain(name="Hook")
        cap.crew.register(Agent(name="Alice", skills=["python"]))
        cap.add_task(Task(name="Write code", required_skills=["python"]))
        result = cap.run()
        assert result["completed"] == 1
        assert result["total"] == 1

    def test_dependency_chain(self):
        cap = Captain(name="Hook")
        cap.crew.register(Agent(name="Alice", skills=["python", "testing"]))
        t1 = cap.add_task(Task(name="Write code", required_skills=["python"]))
        t2 = cap.add_task(Task(name="Test code", required_skills=["testing"], dependencies=[t1.id]))
        result = cap.run()
        assert result["completed"] == 2

    def test_multiple_agents(self):
        cap = Captain(name="Hook")
        cap.crew.register(Agent(name="Alice", skills=["python"]))
        cap.crew.register(Agent(name="Bob", skills=["rust"]))
        cap.add_task(Task(name="Py task", required_skills=["python"]))
        cap.add_task(Task(name="Rust task", required_skills=["rust"]))
        result = cap.run()
        assert result["completed"] == 2

    def test_priority_ordering(self):
        cap = Captain(name="Hook")
        alice = cap.crew.register(Agent(name="Alice", skills=["python", "testing"]))
        t1 = cap.add_task(Task(name="low", priority=TaskPriority.LOW, required_skills=["python"]))
        t2 = cap.add_task(Task(name="critical", priority=TaskPriority.CRITICAL, required_skills=["python"]))
        # With max_concurrent_tasks=3 both get assigned, but critical should be delegated first
        cap.delegate_ready()
        # Both should be assigned since agent has 3 slots
        assert t2.status == TaskStatus.ASSIGNED
        assert t1.status == TaskStatus.ASSIGNED

    def test_no_matching_agent_task_stays_pending(self):
        cap = Captain(name="Hook")
        cap.crew.register(Agent(name="Alice", skills=["python"]))
        cap.add_task(Task(name="Rust task", required_skills=["rust"]))
        result = cap.run()
        assert result["completed"] == 0
        assert result["pending"] == 1

    def test_milestone_tracking(self):
        cap = Captain(name="Hook")
        cap.crew.register(Agent(name="Alice", skills=["python"]))
        t1 = cap.add_task(Task(name="Step 1", required_skills=["python"]))
        t2 = cap.add_task(Task(name="Step 2", required_skills=["python"]))
        m = cap.add_milestone("Phase 1", [t1.id, t2.id])
        cap.run()
        assert cap.tracker.milestone_complete(m)

    def test_progress_property(self):
        cap = Captain(name="Hook")
        cap.crew.register(Agent(name="Alice", skills=["python"]))
        cap.add_task(Task(name="Task", required_skills=["python"]))
        cap.run()
        p = cap.progress
        assert p["overall_progress"] == 100.0
