"""Event system for CUH runs.

Events are emitted throughout the run lifecycle for observability,
debugging, and real-time monitoring.
"""

from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class EventType(StrEnum):
    """Types of run events."""

    RUN_STARTED = "run_started"
    RUN_COMPLETED = "run_completed"
    RUN_FAILED = "run_failed"
    PROVIDER_REQUEST = "provider_request"
    PROVIDER_RESPONSE = "provider_response"
    ACTION_EMITTED = "action_emitted"
    ACTION_EXECUTED = "action_executed"
    OBSERVATION_RECORDED = "observation_recorded"
    POLICY_CHECK = "policy_check"
    POLICY_BLOCKED = "policy_blocked"
    POLICY_CONFIRMED = "policy_confirmed"
    ERROR = "error"
    STEP_STARTED = "step_started"
    STEP_COMPLETED = "step_completed"


class RunEvent(BaseModel):
    """Base event for run lifecycle."""

    event_type: EventType
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    run_id: str
    step_id: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class RunStartedEvent(RunEvent):
    """Run started event."""

    event_type: EventType = EventType.RUN_STARTED
    task: str
    provider: str
    model: str
    target: str


class RunCompletedEvent(RunEvent):
    """Run completed successfully."""

    event_type: EventType = EventType.RUN_COMPLETED
    total_steps: int
    duration_seconds: float
    final_status: str = "completed"


class RunFailedEvent(RunEvent):
    """Run failed."""

    event_type: EventType = EventType.RUN_FAILED
    error_type: str
    error_message: str
    step_failed: int | None = None


class ProviderRequestEvent(RunEvent):
    """Provider request sent."""

    event_type: EventType = EventType.PROVIDER_REQUEST
    request_type: str
    message_count: int
    tokens_prompt: int | None = None


class ProviderResponseEvent(RunEvent):
    """Provider response received."""

    event_type: EventType = EventType.PROVIDER_RESPONSE
    response_type: str
    has_actions: bool = False
    action_count: int = 0
    tokens_completion: int | None = None
    tokens_total: int | None = None
    cost: float | None = None
    latency_ms: float | None = None


class ActionEmittedEvent(RunEvent):
    """Action emitted by provider."""

    event_type: EventType = EventType.ACTION_EMITTED
    action_type: str
    action_data: dict[str, Any]


class ActionExecutedEvent(RunEvent):
    """Action executed by backend."""

    event_type: EventType = EventType.ACTION_EXECUTED
    action_type: str
    success: bool
    duration_ms: float | None = None


class ObservationRecordedEvent(RunEvent):
    """Observation recorded."""

    event_type: EventType = EventType.OBSERVATION_RECORDED
    observation_type: str
    has_screenshot: bool = False


class PolicyCheckEvent(RunEvent):
    """Policy check performed."""

    event_type: EventType = EventType.POLICY_CHECK
    action_type: str
    decision: str
    reason: str | None = None


class PolicyBlockedEvent(RunEvent):
    """Action blocked by policy."""

    event_type: EventType = EventType.POLICY_BLOCKED
    action_type: str
    reason: str


class PolicyConfirmedEvent(RunEvent):
    """Action confirmed by policy."""

    event_type: EventType = EventType.POLICY_CONFIRMED
    action_type: str
    confirmed_by: str = "user"


class ErrorEvent(RunEvent):
    """Error occurred."""

    event_type: EventType = EventType.ERROR
    error_type: str
    error_message: str
    recoverable: bool = False


class StepStartedEvent(RunEvent):
    """Step started."""

    event_type: EventType = EventType.STEP_STARTED
    step_number: int


class StepCompletedEvent(RunEvent):
    """Step completed."""

    event_type: EventType = EventType.STEP_COMPLETED
    step_number: int
    action_count: int
    duration_ms: float | None = None
