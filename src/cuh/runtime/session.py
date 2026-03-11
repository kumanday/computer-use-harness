"""Session management for CUH runs."""

import uuid
from datetime import UTC, datetime

from cuh.config.loader import Settings
from cuh.core.events import RunCompletedEvent, RunEvent, RunFailedEvent, RunStartedEvent
from cuh.core.models import RunConfig, RunMetadata, RunState, ScreenGeometry, UsageMetrics
from cuh.runtime.artifact_store import ArtifactStore
from cuh.runtime.event_bus import EventBus


class RunSession:
    """Manages the state and lifecycle of a single run."""

    def __init__(
        self,
        config: RunConfig,
        event_bus: EventBus,
        artifact_store: ArtifactStore,
        settings: Settings | None = None,
    ) -> None:
        self.config = config
        self.event_bus = event_bus
        self.artifact_store = artifact_store
        self.settings = settings or Settings()

        self.run_id = str(uuid.uuid4())
        self.step_number = 0
        self.total_steps = 0
        self.successful_actions = 0
        self.failed_actions = 0
        self.total_usage = UsageMetrics()
        self.state = RunState.PENDING
        self.geometry: ScreenGeometry | None = None
        self.error: str | None = None
        self.metadata: RunMetadata | None = None

        self._started_at: datetime | None = None
        self._completed_at: datetime | None = None

    def start(self) -> None:
        """Start the run session."""
        self._started_at = datetime.now(UTC)
        self.state = RunState.RUNNING

        self.metadata = RunMetadata(
            run_id=self.run_id,
            started_at=self._started_at,
            provider=self.config.provider.value,
            model=self.config.model,
            target=self.config.target,
            task=self.config.task,
            state=self.state,
        )

        self.artifact_store.create_run_directory(self.run_id)
        self.artifact_store.write_metadata(self.metadata)
        self.artifact_store.write_config(self.config.model_dump(mode="json"))

        event = RunStartedEvent(
            run_id=self.run_id,
            task=self.config.task,
            provider=self.config.provider.value,
            model=self.config.model,
            target=self.config.target,
        )
        self.event_bus.publish(event)

    def complete(self, success: bool = True) -> None:
        """Complete the run session."""
        self._completed_at = datetime.now(UTC)
        self.state = RunState.COMPLETED if success else RunState.FAILED

        if self.metadata:
            self.metadata.completed_at = self._completed_at
            self.metadata.state = self.state
            self.metadata.total_steps = self.total_steps
            self.metadata.successful_actions = self.successful_actions
            self.metadata.failed_actions = self.failed_actions
            self.metadata.total_tokens_prompt = self.total_usage.prompt_tokens
            self.metadata.total_tokens_completion = self.total_usage.completion_tokens
            self.metadata.total_cost = self.total_usage.cost

            if not success and self.error:
                self.metadata.error_message = self.error

            self.artifact_store.write_metadata(self.metadata)

        summary = {
            "run_id": self.run_id,
            "status": self.state.value,
            "total_steps": self.total_steps,
            "successful_actions": self.successful_actions,
            "failed_actions": self.failed_actions,
            "total_tokens": self.total_usage.total_tokens,
            "total_cost": self.total_usage.cost,
            "duration_seconds": (self._completed_at - self._started_at).total_seconds()
            if self._started_at
            else 0,
        }
        self.artifact_store.write_summary(summary)

        if success:
            event: RunEvent = RunCompletedEvent(
                run_id=self.run_id,
                total_steps=self.total_steps,
                duration_seconds=float(summary["duration_seconds"] or 0),
            )
        else:
            event = RunFailedEvent(
                run_id=self.run_id,
                error_type="runtime_error",
                error_message=self.error or "Unknown error",
            )
        self.event_bus.publish(event)

    def fail(self, error: str) -> None:
        """Mark the session as failed."""
        self.error = error
        self.complete(success=False)

    def increment_step(self) -> int:
        """Increment and return the step number."""
        self.step_number += 1
        self.total_steps += 1
        return self.step_number

    def record_success(self) -> None:
        """Record a successful action."""
        self.successful_actions += 1

    def record_failure(self) -> None:
        """Record a failed action."""
        self.failed_actions += 1

    def add_usage(self, usage: UsageMetrics) -> None:
        """Add usage metrics to the total."""
        self.total_usage.prompt_tokens += usage.prompt_tokens
        self.total_usage.completion_tokens += usage.completion_tokens
        self.total_usage.total_tokens += usage.total_tokens
        if usage.cost is not None:
            if self.total_usage.cost is None:
                self.total_usage.cost = 0.0
            self.total_usage.cost += usage.cost

    def set_geometry(self, geometry: ScreenGeometry) -> None:
        """Set the screen geometry for the session."""
        self.geometry = geometry

    @property
    def duration_seconds(self) -> float:
        """Get the run duration in seconds."""
        if self._started_at is None:
            return 0.0
        end = self._completed_at or datetime.now(UTC)
        return (end - self._started_at).total_seconds()

    @property
    def is_running(self) -> bool:
        """Check if the session is still running."""
        return self.state == RunState.RUNNING

    @property
    def is_complete(self) -> bool:
        """Check if the session is complete."""
        return self.state in (RunState.COMPLETED, RunState.FAILED)

    @property
    def run_directory(self) -> str:
        """Get the run directory name."""
        if self._started_at:
            timestamp = self._started_at.strftime("%Y-%m-%d_%H%M%S")
            return f"{timestamp}_{self.run_id[:8]}"
        return f"unknown_{self.run_id[:8]}"
