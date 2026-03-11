"""Canonical observation schema for CUH.

This module defines the observation types returned from action execution.
Observations are the result of actions executed by the backend.
"""

from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class ObservationType(StrEnum):
    """Types of observations."""

    SCREENSHOT = "screenshot"
    ACTION_RESULT = "action_result"
    TEXT = "text"
    TERMINAL_OUTPUT = "terminal_output"
    ERROR = "error"
    POLICY_REQUEST = "policy_request"
    RUN_SUMMARY = "run_summary"


class ComputerObservation(BaseModel):
    """Base observation from action execution."""

    observation_type: ObservationType
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    step_id: str
    success: bool = True
    error: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class ScreenshotObservation(ComputerObservation):
    """Screenshot observation with image data."""

    observation_type: ObservationType = ObservationType.SCREENSHOT
    image_data: bytes | None = None
    image_base64: str | None = None
    width: int | None = None
    height: int | None = None
    format: str = "png"

    def model_dump(self, **kwargs: Any) -> dict[str, Any]:
        """Dump model, excluding binary image_data."""
        data = super().model_dump(**kwargs)
        data.pop("image_data", None)
        return data


class ActionResultObservation(ComputerObservation):
    """Result of an action execution."""

    observation_type: ObservationType = ObservationType.ACTION_RESULT
    action_type: str
    coordinates: tuple[int, int] | None = None
    message: str | None = None


class TextObservation(ComputerObservation):
    """Text message observation."""

    observation_type: ObservationType = ObservationType.TEXT
    content: str


class TerminalOutputObservation(ComputerObservation):
    """Terminal/shell output observation."""

    observation_type: ObservationType = ObservationType.TERMINAL_OUTPUT
    output: str
    exit_code: int | None = None


class ErrorObservation(ComputerObservation):
    """Error observation."""

    observation_type: ObservationType = ObservationType.ERROR
    success: bool = False
    error_type: str
    error_message: str
    error: str | None = None

    def __init__(self, **data: Any) -> None:
        if "error_message" in data and data.get("error") is None:
            data["error"] = data["error_message"]
        super().__init__(**data)


class PolicyRequestObservation(ComputerObservation):
    """Policy confirmation request."""

    observation_type: ObservationType = ObservationType.POLICY_REQUEST
    action_requested: str
    reason: str
    requires_confirmation: bool = True


class RunSummaryObservation(ComputerObservation):
    """Final run summary."""

    observation_type: ObservationType = ObservationType.RUN_SUMMARY
    total_steps: int
    successful_actions: int
    failed_actions: int
    total_cost: float | None = None
    total_tokens: int | None = None
    duration_seconds: float
    final_status: str
