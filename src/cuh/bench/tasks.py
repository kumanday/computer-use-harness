"""Task definitions for benchmark suites."""

from typing import Any

from pydantic import BaseModel


class TaskDefinition(BaseModel):
    """Definition of a single benchmark task."""

    id: str
    prompt: str
    timeout: float = 300.0
    max_steps: int = 100
    success_heuristic: str | None = None
    target_requirements: list[str] = []
    policy_requirements: dict[str, Any] = {}
    metadata: dict[str, Any] = {}


class TaskSuite(BaseModel):
    """A suite of benchmark tasks."""

    name: str
    description: str | None = None
    tasks: list[TaskDefinition]
    default_timeout: float = 300.0
    default_max_steps: int = 100
    metadata: dict[str, Any] = {}
