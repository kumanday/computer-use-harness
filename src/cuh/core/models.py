"""Core models for CUH runtime.

This module defines the core data models for runs, configuration,
screen geometry, and other runtime concepts.
"""

from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class RunState(StrEnum):
    """Possible states of a run."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    BLOCKED = "blocked"
    CANCELLED = "cancelled"


class TargetKind(StrEnum):
    """Types of computer targets."""

    CUA_HOST = "cua_host"
    CUA_REMOTE = "cua_remote"
    LINUX_SANDBOX = "linux_sandbox"
    WINDOWS_VM = "windows_vm"
    BROWSER = "browser"
    MOCK = "mock"


class ProviderKind(StrEnum):
    """Types of model providers."""

    OPENAI = "openai"
    QWEN = "qwen"


class ScreenGeometry(BaseModel):
    """Screen geometry for coordinate transformation.

    Critical for preventing action drift between model-view image size
    and actual screen size.
    """

    actual_width: int
    actual_height: int
    model_view_width: int | None = None
    model_view_height: int | None = None
    scale_ratio: float = 1.0
    crop_offset_x: int = 0
    crop_offset_y: int = 0

    def model_to_actual(self, x: int, y: int) -> tuple[int, int]:
        """Transform model-view coordinates to actual screen coordinates."""
        actual_x = int(x * self.scale_ratio) + self.crop_offset_x
        actual_y = int(y * self.scale_ratio) + self.crop_offset_y
        return (actual_x, actual_y)

    def actual_to_model(self, x: int, y: int) -> tuple[int, int]:
        """Transform actual screen coordinates to model-view coordinates."""
        model_x = int((x - self.crop_offset_x) / self.scale_ratio)
        model_y = int((y - self.crop_offset_y) / self.scale_ratio)
        return (model_x, model_y)

    @classmethod
    def from_sizes(
        cls,
        actual_width: int,
        actual_height: int,
        model_view_width: int | None = None,
        model_view_height: int | None = None,
    ) -> "ScreenGeometry":
        """Create geometry from actual and model-view sizes."""
        if model_view_width is None or model_view_height is None:
            return cls(
                actual_width=actual_width,
                actual_height=actual_height,
                model_view_width=actual_width,
                model_view_height=actual_height,
            )

        scale_ratio = actual_width / model_view_width
        return cls(
            actual_width=actual_width,
            actual_height=actual_height,
            model_view_width=model_view_width,
            model_view_height=model_view_height,
            scale_ratio=scale_ratio,
        )


class RunMetadata(BaseModel):
    """Metadata for a run."""

    run_id: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    started_at: datetime | None = None
    completed_at: datetime | None = None
    provider: str
    model: str
    target: str
    task: str
    state: RunState = RunState.PENDING
    total_steps: int = 0
    successful_actions: int = 0
    failed_actions: int = 0
    total_tokens_prompt: int = 0
    total_tokens_completion: int = 0
    total_cost: float | None = None
    error_type: str | None = None
    error_message: str | None = None


class RunConfig(BaseModel):
    """Configuration for a run."""

    provider: ProviderKind = ProviderKind.OPENAI
    model: str = "gpt-5.4"
    target: str = "local-host"
    task: str
    max_steps: int = 100
    timeout_seconds: float = 300.0
    screenshot_interval: float = 0.5
    policy_enabled: bool = True
    telemetry_enabled: bool = False
    reasoning_effort: str = "medium"
    extra: dict[str, Any] = Field(default_factory=dict)


class TargetConfig(BaseModel):
    """Configuration for a computer target."""

    kind: TargetKind
    name: str
    api_host: str = "127.0.0.1"
    api_port: int = 8000
    os_type: str = "linux"
    telemetry_enabled: bool = False
    extra: dict[str, Any] = Field(default_factory=dict)


class ProviderConfig(BaseModel):
    """Configuration for a model provider."""

    provider: ProviderKind
    model: str
    api_key_env: str = "OPENAI_API_KEY"
    api_base: str | None = None
    mode: str = "responses_computer"
    reasoning_effort: str = "medium"
    tool_renderer: str | None = None
    tool_parser: str | None = None
    vision_enabled: bool = True
    extra: dict[str, Any] = Field(default_factory=dict)

    def get_api_key(self) -> str | None:
        """Get API key from environment."""
        import os

        return os.environ.get(self.api_key_env)


class UsageMetrics(BaseModel):
    """Usage metrics for a provider call."""

    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    cost: float | None = None
    latency_ms: float | None = None


class StepRecord(BaseModel):
    """Record of a single step in a run."""

    step_id: str
    step_number: int
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    provider_input: dict[str, Any] | None = None
    provider_output: dict[str, Any] | None = None
    action: dict[str, Any] | None = None
    observation: dict[str, Any] | None = None
    screenshot_path: str | None = None
    usage: UsageMetrics | None = None
    duration_ms: float | None = None
    error: str | None = None
