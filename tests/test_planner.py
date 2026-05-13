"""Tests for the Planner Agent (F-019)."""

import pytest

from cove.orchestration.planner import (
    Capability,
    DecompositionResult,
    PlannerAgent,
    SubTask,
    SubTaskStatus,
    TaskCategory,
    TaskClassifier,
)


# --------------------------------------------------------------------------
# TaskClassifier — classify()
# --------------------------------------------------------------------------


class TestClassify:
    def test_classify_simple_task(self):
        """'fix typo in readme' should be classified as SIMPLE."""
        result = TaskClassifier.classify("fix typo in readme")
        assert result == TaskCategory.SIMPLE

    def test_classify_software_engineering(self):
        """'refactor auth to JWT' should be classified as SOFTWARE_ENGINEERING."""
        result = TaskClassifier.classify("refactor auth to JWT")
        assert result == TaskCategory.SOFTWARE_ENGINEERING

    def test_classify_research(self):
        """'research database options' should be classified as RESEARCH."""
        result = TaskClassifier.classify("research database options")
        assert result == TaskCategory.RESEARCH

    def test_classify_unknown(self):
        """A description without recognized keywords should be UNKNOWN."""
        result = TaskClassifier.classify("plan a birthday party with friends")
        assert result == TaskCategory.UNKNOWN

    def test_classify_very_short(self):
        """A very short description (< 20 chars) is SIMPLE regardless of content."""
        result = TaskClassifier.classify("hi")
        assert result == TaskCategory.SIMPLE

    def test_classify_se_keyword_implement_feature(self):
        """'implement new feature X' is SOFTWARE_ENGINEERING."""
        result = TaskClassifier.classify("implement new feature X")
        assert result == TaskCategory.SOFTWARE_ENGINEERING

    def test_classify_se_keyword_add_endpoint(self):
        """'add API endpoint for users' is SOFTWARE_ENGINEERING."""
        result = TaskClassifier.classify("add API endpoint for users")
        assert result == TaskCategory.SOFTWARE_ENGINEERING

    def test_classify_se_keyword_migration(self):
        """'create database migration' is SOFTWARE_ENGINEERING."""
        result = TaskClassifier.classify("create database migration")
        assert result == TaskCategory.SOFTWARE_ENGINEERING

    def test_classify_research_keyword_investigate(self):
        """'investigate performance bottleneck' is RESEARCH."""
        result = TaskClassifier.classify("investigate performance bottleneck")
        assert result == TaskCategory.RESEARCH

    def test_classify_simple_keyword_rename(self):
        """'rename variable for clarity' is SIMPLE."""
        result = TaskClassifier.classify("rename variable for clarity")
        assert result == TaskCategory.SIMPLE

    def test_classify_simple_keyword_add_comment(self):
        """'add comment to function' is SIMPLE."""
        result = TaskClassifier.classify("add comment to function")
        assert result == TaskCategory.SIMPLE


# --------------------------------------------------------------------------
# TaskClassifier — should_skip()
# --------------------------------------------------------------------------


class TestShouldSkip:
    def test_should_skip_simple(self):
        """A SIMPLE task should skip Planner decomposition."""
        assert TaskClassifier.should_skip("fix typo in readme") is True

    def test_should_skip_complex(self):
        """A SOFTWARE_ENGINEERING task should NOT skip Planner decomposition."""
        assert TaskClassifier.should_skip("refactor auth to JWT") is False

    def test_should_skip_research(self):
        """A RESEARCH task should NOT skip Planner decomposition."""
        assert TaskClassifier.should_skip("research database options") is False

    def test_should_skip_unknown(self):
        """An UNKNOWN task should NOT skip Planner decomposition."""
        assert TaskClassifier.should_skip("plan a birthday party with friends") is False

    def test_should_skip_very_short(self):
        """A very short description is SIMPLE and should skip."""
        assert TaskClassifier.should_skip("hi") is True


# --------------------------------------------------------------------------
# SubTask & DecompositionResult dataclass basics
# --------------------------------------------------------------------------


class TestDataclasses:
    def test_subtask_defaults(self):
        """SubTask should have sensible defaults."""
        st = SubTask()
        assert st.id == ""
        assert st.status == SubTaskStatus.PENDING
        assert st.capability == Capability.READ_WRITE
        assert st.dependencies == []
        assert st.handoff is None

    def test_decomposition_result_defaults(self):
        """DecompositionResult should have sensible defaults."""
        dr = DecompositionResult(task_description="test", category=TaskCategory.UNKNOWN, subtasks=[])
        assert dr.quality_gate_passed is False
        assert dr.quality_message == ""


# --------------------------------------------------------------------------
# PlannerAgent — decompose()
# --------------------------------------------------------------------------


class TestDecompose:
    @pytest.mark.asyncio
    async def test_decompose_software_task(self):
        """An SE task should yield multiple SubTasks with appropriate capabilities."""
        agent = PlannerAgent()
        result = await agent.decompose("refactor auth to JWT")
        assert result.category == TaskCategory.SOFTWARE_ENGINEERING
        assert len(result.subtasks) >= 2  # at least 2 subtasks for any real pattern
        assert result.quality_gate_passed is True

        # Verify subtask structure
        for i, st in enumerate(result.subtasks, start=1):
            assert st.id == f"subtask-{i}"
            assert st.name
            assert st.description
            assert isinstance(st.capability, Capability)
            assert st.status == SubTaskStatus.PENDING

    @pytest.mark.asyncio
    async def test_decompose_simple_task_skips(self):
        """A SIMPLE task should yield a single direct-execution SubTask."""
        agent = PlannerAgent()
        result = await agent.decompose("fix typo in readme")
        assert result.category == TaskCategory.SIMPLE
        assert len(result.subtasks) == 1
        assert result.subtasks[0].name == "Direct execution"
        assert result.subtasks[0].id == "subtask-1"
        assert result.subtasks[0].capability == Capability.READ_WRITE
        assert result.quality_gate_passed is True

    @pytest.mark.asyncio
    async def test_decompose_unknown_task(self):
        """An UNKNOWN task still gets decomposition but category is UNKNOWN."""
        agent = PlannerAgent()
        result = await agent.decompose("plan a birthday party with friends")
        assert result.category == TaskCategory.UNKNOWN
        assert len(result.subtasks) >= 1

    @pytest.mark.asyncio
    async def test_decompose_implement_feature(self):
        """'implement feature X' should match the 'implement' pattern."""
        agent = PlannerAgent()
        result = await agent.decompose("implement user authentication")
        assert result.category == TaskCategory.SOFTWARE_ENGINEERING
        assert len(result.subtasks) == 4
        names = [st.name for st in result.subtasks]
        assert names == ["Design", "Implement", "Test", "Review"]

    @pytest.mark.asyncio
    async def test_decompose_fix_bug(self):
        """'fix bug in Y' should match the 'fix' pattern."""
        agent = PlannerAgent()
        result = await agent.decompose("fix bug in login flow")
        assert len(result.subtasks) == 3
        names = [st.name for st in result.subtasks]
        assert names == ["Reproduce bug", "Fix implementation", "Verify fix"]

    @pytest.mark.asyncio
    async def test_decompose_api_endpoint(self):
        """'add API endpoint' should match the 'api' pattern."""
        agent = PlannerAgent()
        result = await agent.decompose("add API endpoint for users")
        assert len(result.subtasks) == 4
        names = [st.name for st in result.subtasks]
        assert names == ["Define schema", "Implement handler", "Add tests", "Update docs"]

    @pytest.mark.asyncio
    async def test_decompose_add_test(self):
        """'add test for X' should match the 'add test' pattern."""
        agent = PlannerAgent()
        result = await agent.decompose("add test for auth module")
        assert len(result.subtasks) == 3
        names = [st.name for st in result.subtasks]
        assert names == ["Design test plan", "Write tests", "Run and verify"]

    @pytest.mark.asyncio
    async def test_decompose_with_context(self):
        """Passing a context dict should not affect decomposition (reserved)."""
        agent = PlannerAgent()
        result = await agent.decompose("refactor auth to JWT", context={"session_id": "abc"})
        assert result.category == TaskCategory.SOFTWARE_ENGINEERING
        assert len(result.subtasks) > 0


# --------------------------------------------------------------------------
# Quality gate
# --------------------------------------------------------------------------


class TestQualityGate:
    @pytest.mark.asyncio
    async def test_quality_gate_passes(self):
        """3 subtasks for an SE task should pass the quality gate."""
        agent = PlannerAgent()
        # 'implement' pattern yields 4 subtasks — within range
        result = await agent.decompose("implement user authentication")
        assert result.quality_gate_passed is True
        assert "OK" in result.quality_message

    @pytest.mark.asyncio
    async def test_quality_gate_warns(self):
        """7+ subtasks for an SE task should produce a warning."""
        agent = PlannerAgent()
        # Manually construct a result with 7 subtasks to test the threshold
        subtasks = [
            SubTask(id=f"subtask-{i}", name=f"Step {i}", description="...")
            for i in range(1, 8)
        ]
        result = DecompositionResult(
            task_description="complex task",
            category=TaskCategory.SOFTWARE_ENGINEERING,
            subtasks=subtasks,
        )
        result = agent.quality_check(result)
        assert result.quality_gate_passed is True
        assert "Warning" in result.quality_message
        assert "7" in result.quality_message

    def test_quality_gate_edge_exactly_six(self):
        """6 subtasks is the maximum without warning."""
        agent = PlannerAgent()
        subtasks = [
            SubTask(id=f"subtask-{i}", name=f"Step {i}", description="...")
            for i in range(1, 7)
        ]
        result = DecompositionResult(
            task_description="complex task",
            category=TaskCategory.SOFTWARE_ENGINEERING,
            subtasks=subtasks,
        )
        result = agent.quality_check(result)
        assert result.quality_gate_passed is True
        assert "Warning" not in result.quality_message

    def test_quality_gate_research(self):
        """RESEARCH tasks pass quality regardless of subtask count."""
        agent = PlannerAgent()
        subtasks = [SubTask(id="subtask-1", name="Research", description="...")]
        result = DecompositionResult(
            task_description="research topic",
            category=TaskCategory.RESEARCH,
            subtasks=subtasks,
        )
        result = agent.quality_check(result)
        assert result.quality_gate_passed is True
        assert "research" in result.quality_message


# --------------------------------------------------------------------------
# Handoff
# --------------------------------------------------------------------------


class TestHandoff:
    @pytest.mark.asyncio
    async def test_generate_handoff(self):
        """Handoff dict should have the correct structure with all fields."""
        agent = PlannerAgent()
        handoff = await agent.generate_handoff(
            result="Successfully implemented feature",
            files_created=["src/new_feature.py"],
            files_modified=["src/main.py"],
            warnings=["Deprecated API used"],
        )
        assert handoff["conclusion"] == "Successfully implemented feature"
        assert handoff["files_created"] == ["src/new_feature.py"]
        assert handoff["files_modified"] == ["src/main.py"]
        assert handoff["pending_decisions"] == []
        assert handoff["warnings"] == ["Deprecated API used"]

    @pytest.mark.asyncio
    async def test_generate_handoff_minimal(self):
        """Handoff with no files or warnings should still work."""
        agent = PlannerAgent()
        handoff = await agent.generate_handoff(result="Done")
        assert handoff["conclusion"] == "Done"
        assert handoff["files_created"] == []
        assert handoff["files_modified"] == []
        assert handoff["pending_decisions"] == []
        assert handoff["warnings"] == []

    @pytest.mark.asyncio
    async def test_generate_handoff_partial(self):
        """Handoff with only some optional fields filled."""
        agent = PlannerAgent()
        handoff = await agent.generate_handoff(
            result="Partial work",
            files_created=["a.py"],
        )
        assert handoff["files_created"] == ["a.py"]
        assert handoff["files_modified"] == []
        assert handoff["warnings"] == []


# --------------------------------------------------------------------------
# Integration — end-to-end flow
# --------------------------------------------------------------------------


class TestIntegration:
    @pytest.mark.asyncio
    async def test_full_simple_flow(self):
        """A simple task: classify -> skip -> direct execution -> handoff."""
        agent = PlannerAgent()

        # Decompose
        result = await agent.decompose("add comment to function")
        assert result.category == TaskCategory.SIMPLE
        assert len(result.subtasks) == 1

        # Simulate worker completing the subtask
        subtask = result.subtasks[0]
        subtask.status = SubTaskStatus.COMPLETED

        # Generate handoff
        handoff = await agent.generate_handoff(
            result="Comment added",
            files_modified=["src/file.py"],
        )
        assert handoff["conclusion"] == "Comment added"
        assert len(handoff["files_modified"]) == 1

    @pytest.mark.asyncio
    async def test_full_se_flow(self):
        """An SE task: classify -> decompose into subtasks -> quality gate -> handoff."""
        agent = PlannerAgent()

        # Decompose
        result = await agent.decompose("fix bug in payment processing")
        assert result.category == TaskCategory.SOFTWARE_ENGINEERING
        assert len(result.subtasks) == 3
        assert result.quality_gate_passed is True

        # Complete subtasks sequentially
        for i, subtask in enumerate(result.subtasks):
            assert subtask.status == SubTaskStatus.PENDING
            subtask.status = SubTaskStatus.COMPLETED
            subtask.handoff = {
                "conclusion": f"Step {i+1} done",
                "files_created": [],
                "files_modified": [],
                "pending_decisions": [],
                "warnings": [],
            }

        # All subtasks should now be completed
        assert all(st.status == SubTaskStatus.COMPLETED for st in result.subtasks)
