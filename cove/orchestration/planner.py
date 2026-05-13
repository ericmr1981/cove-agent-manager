"""Planner Agent — dynamic task decomposition and orchestration.

Phase 1 MVP: sequential execution, software-engineering tasks only,
with a structured handoff protocol.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from cove.session_store.service import SessionStoreService


class TaskCategory(Enum):
    SOFTWARE_ENGINEERING = "software_engineering"
    RESEARCH = "research"
    SIMPLE = "simple"
    UNKNOWN = "unknown"


class Capability(Enum):
    READ_ONLY = "ReadOnly"
    READ_WRITE = "ReadWrite"
    EXECUTE = "Execute"
    THINK = "Think"


class SubTaskStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class SubTask:
    id: str = ""
    name: str = ""
    description: str = ""
    capability: Capability = Capability.READ_WRITE
    status: SubTaskStatus = SubTaskStatus.PENDING
    dependencies: list[str] = field(default_factory=list)
    handoff: dict | None = None


@dataclass
class DecompositionResult:
    task_description: str
    category: TaskCategory
    subtasks: list[SubTask]
    quality_gate_passed: bool = False
    quality_message: str = ""


# ---------------------------------------------------------------------------
# Heuristic constants
# ---------------------------------------------------------------------------

_SIMPLE_KEYWORDS = ["fix typo", "rename", "add comment", "typo", "cosmetic"]
_SE_KEYWORDS = [
    "refactor",
    "implement",
    "feature",
    "test",
    "bug",
    "fix",
    "build",
    "deploy",
    "api",
    "endpoint",
    "schema",
    "migration",
    "function",
    "class",
    "module",
]
_RESEARCH_KEYWORDS = [
    "research",
    "investigate",
    "analyze",
    "compare",
    "document",
    "report",
]


class TaskClassifier:
    """Classify a task description into a TaskCategory."""

    @staticmethod
    def classify(task_description: str) -> TaskCategory:
        """Classify a task description using keyword/heuristic matching."""
        text = task_description.strip().lower()

        # Very short tasks are always SIMPLE
        if len(text) < 20:
            return TaskCategory.SIMPLE

        # Check simple keywords first
        for kw in _SIMPLE_KEYWORDS:
            if kw in text:
                return TaskCategory.SIMPLE

        # Check software engineering keywords
        for kw in _SE_KEYWORDS:
            if kw in text:
                return TaskCategory.SOFTWARE_ENGINEERING

        # Check research keywords
        for kw in _RESEARCH_KEYWORDS:
            if kw in text:
                return TaskCategory.RESEARCH

        return TaskCategory.UNKNOWN

    @staticmethod
    def should_skip(task_description: str) -> bool:
        """Return True if this task should skip Planner decomposition."""
        return TaskClassifier.classify(task_description) == TaskCategory.SIMPLE


# ---------------------------------------------------------------------------
# Decomposition pattern helpers
# ---------------------------------------------------------------------------

# Pattern => list of (name, description, capability)
_DECOMPOSITION_PATTERNS: dict[str, list[tuple[str, str, Capability]]] = {
    "refactor": [
        ("Analyze current code", "Review and understand the existing codebase structure and identify areas needing change.", Capability.READ_ONLY),
        ("Implement changes", "Make the necessary refactoring changes to the codebase.", Capability.READ_WRITE),
        ("Update tests", "Update existing tests and add new tests to cover the refactored code.", Capability.READ_WRITE),
        ("Verify", "Run tests and verify everything passes.", Capability.EXECUTE),
    ],
    "implement": [
        ("Design", "Design the implementation approach and plan the changes needed.", Capability.THINK),
        ("Implement", "Write the implementation code.", Capability.READ_WRITE),
        ("Test", "Write and run tests for the new implementation.", Capability.READ_WRITE),
        ("Review", "Review the implementation for quality and correctness.", Capability.THINK),
    ],
    "fix": [
        ("Reproduce bug", "Reproduce the bug and identify the root cause.", Capability.EXECUTE),
        ("Fix implementation", "Implement the fix for the identified issue.", Capability.READ_WRITE),
        ("Verify fix", "Verify the fix works and existing tests still pass.", Capability.EXECUTE),
    ],
    "api": [
        ("Define schema", "Define the API schema and data structures.", Capability.THINK),
        ("Implement handler", "Implement the API endpoint handler logic.", Capability.READ_WRITE),
        ("Add tests", "Add tests for the new API endpoint.", Capability.READ_WRITE),
        ("Update docs", "Update API documentation.", Capability.READ_ONLY),
    ],
    "add test": [
        ("Design test plan", "Design the test plan covering edge cases and expected behavior.", Capability.THINK),
        ("Write tests", "Write the test code.", Capability.READ_WRITE),
        ("Run and verify", "Run tests and verify they pass.", Capability.EXECUTE),
    ],
}

# Default pattern for software-engineering tasks that don't match a specific pattern
_DEFAULT_SE_PATTERN: list[tuple[str, str, Capability]] = [
    ("Analyze", "Analyze the task requirements and plan the approach.", Capability.THINK),
    ("Implement", "Implement the solution.", Capability.READ_WRITE),
    ("Test", "Write tests and verify correctness.", Capability.EXECUTE),
    ("Review", "Review the completed work for quality.", Capability.THINK),
]


def _match_decomposition_pattern(task_description: str) -> list[tuple[str, str, Capability]] | None:
    """Try to match a known decomposition pattern based on task keywords."""
    text = task_description.lower()
    for keyword, pattern in _DECOMPOSITION_PATTERNS.items():
        if keyword in text:
            return pattern
    return None


# ---------------------------------------------------------------------------
# Quality gate constants
# ---------------------------------------------------------------------------

_MAX_SUBTASKS_NO_WARN = 6
_MIN_SUBTASKS = 1


class PlannerAgent:
    """Planner Agent — decomposes high-level tasks into sequential subtasks."""

    def __init__(self, session_store: SessionStoreService | None = None) -> None:
        self._session_store = session_store

    async def decompose(
        self,
        task_description: str,
        context: dict | None = None,
    ) -> DecompositionResult:
        """Classify and decompose a task description into subtasks.

        Simple tasks skip decomposition and return a single direct-execution
        subtask. All other tasks are decomposed using keyword-matched patterns.
        """
        _ = context  # reserved for future enrichment

        category = TaskClassifier.classify(task_description)

        if TaskClassifier.should_skip(task_description):
            # Direct execution — no decomposition needed
            subtask = SubTask(
                id="subtask-1",
                name="Direct execution",
                description=f"Execute task directly: {task_description}",
                capability=Capability.READ_WRITE,
            )
            result = DecompositionResult(
                task_description=task_description,
                category=category,
                subtasks=[subtask],
            )
            return self.quality_check(result)

        pattern = _match_decomposition_pattern(task_description)

        if pattern is None:
            # Fall back to default SE pattern for all non-simple, non-matched tasks
            pattern = _DEFAULT_SE_PATTERN

        subtasks: list[SubTask] = []
        for i, (name, description, capability) in enumerate(pattern, start=1):
            subtasks.append(
                SubTask(
                    id=f"subtask-{i}",
                    name=name,
                    description=description,
                    capability=capability,
                )
            )

        result = DecompositionResult(
            task_description=task_description,
            category=category,
            subtasks=subtasks,
        )
        return self.quality_check(result)

    async def generate_handoff(
        self,
        result: str,
        files_created: list[str] | None = None,
        files_modified: list[str] | None = None,
        warnings: list[str] | None = None,
    ) -> dict:
        """Generate a structured handoff dict for Worker output."""
        return {
            "conclusion": result,
            "files_created": files_created or [],
            "files_modified": files_modified or [],
            "pending_decisions": [],
            "warnings": warnings or [],
        }

    def quality_check(self, result: DecompositionResult) -> DecompositionResult:
        """Validate the decomposition result against quality thresholds."""
        n = len(result.subtasks)

        if n < _MIN_SUBTASKS:
            result.quality_gate_passed = False
            result.quality_message = f"Decomposition produced {n} subtasks; expected at least {_MIN_SUBTASKS}."
            return result

        if result.category == TaskCategory.SIMPLE:
            # Simple tasks always pass with exactly 1 subtask
            result.quality_gate_passed = True
            result.quality_message = "OK — simple task, direct execution."
            return result

        if result.category == TaskCategory.SOFTWARE_ENGINEERING:
            if n > _MAX_SUBTASKS_NO_WARN:
                result.quality_gate_passed = True
                result.quality_message = (
                    f"Warning: decomposition produced {n} subtasks; "
                    f"recommended maximum is {_MAX_SUBTASKS_NO_WARN}."
                )
            else:
                result.quality_gate_passed = True
                result.quality_message = (
                    f"OK — {n} subtask(s), within the recommended range."
                )
        else:
            # RESEARCH and UNKNOWN tasks get a pass but note the category
            result.quality_gate_passed = True
            result.quality_message = (
                f"OK — task category '{result.category.value}' with {n} subtask(s)."
            )

        return result
