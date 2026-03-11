"""Orchestrator for CUH runs.

Manages the lifecycle of a run, coordinating between the provider adapter,
execution backend, policy engine, and artifact store.
"""

import asyncio
from datetime import UTC, datetime
from typing import Any

from cuh.backends.base import BaseBackend
from cuh.config.loader import Settings, get_settings
from cuh.core.events import (
    ActionEmittedEvent,
    ActionExecutedEvent,
    ObservationRecordedEvent,
    ProviderRequestEvent,
    ProviderResponseEvent,
    StepCompletedEvent,
    StepStartedEvent,
)
from cuh.core.models import RunConfig, StepRecord
from cuh.core.observations import ComputerObservation, ScreenshotObservation
from cuh.core.policy import PolicyDecision, PolicyEngine, PolicyError
from cuh.providers.base import ProviderAdapter, ProviderRunRequest
from cuh.runtime.artifact_store import ArtifactStore
from cuh.runtime.event_bus import EventBus
from cuh.runtime.session import RunSession


class Orchestrator:
    """Orchestrates CUH runs."""

    def __init__(
        self,
        backend: BaseBackend,
        provider: ProviderAdapter,
        event_bus: EventBus | None = None,
        artifact_store: ArtifactStore | None = None,
        policy_engine: PolicyEngine | None = None,
        settings: Settings | None = None,
    ) -> None:
        self.backend = backend
        self.provider = provider
        self.event_bus = event_bus or EventBus()
        self.artifact_store = artifact_store or ArtifactStore()
        self.policy_engine = policy_engine or PolicyEngine()
        self.settings = settings or get_settings()

        self._session: RunSession | None = None
        self._provider_state: dict[str, Any] = {}

    async def run(self, config: RunConfig) -> RunSession:
        """Execute a run with the given configuration."""
        self._session = RunSession(
            config=config,
            event_bus=self.event_bus,
            artifact_store=self.artifact_store,
            settings=self.settings,
        )

        try:
            await self._execute_run(config)
        except Exception as e:
            self._session.fail(str(e))

        return self._session

    async def _execute_run(self, config: RunConfig) -> None:
        """Execute the run loop."""
        assert self._session is not None

        self._session.start()

        initial_screenshot = await self._take_screenshot("step_0000")
        if initial_screenshot and initial_screenshot.image_base64:
            initial_screenshot_b64 = initial_screenshot.image_base64
        else:
            initial_screenshot_b64 = None

        request = ProviderRunRequest(
            task=config.task,
            max_steps=config.max_steps,
            initial_screenshot=initial_screenshot_b64,
        )

        self._provider_state = await self.provider.start_run(request)

        self.event_bus.publish(
            ProviderRequestEvent(
                run_id=self._session.run_id,
                request_type="start",
                message_count=1,
            )
        )

        observations: list[ComputerObservation] = []
        if initial_screenshot:
            observations.append(initial_screenshot)

        step_count = 0
        while step_count < config.max_steps and self._session.is_running:
            step_number = self._session.increment_step()
            step_id = f"step_{step_number:04d}"

            self.event_bus.publish(
                StepStartedEvent(
                    run_id=self._session.run_id,
                    step_id=step_id,
                    step_number=step_number,
                )
            )

            result = await self.provider.next_step(self._provider_state, observations)

            self.event_bus.publish(
                ProviderResponseEvent(
                    run_id=self._session.run_id,
                    step_id=step_id,
                    response_type="step",
                    has_actions=len(result.actions) > 0,
                    action_count=len(result.actions),
                    tokens_completion=result.usage.completion_tokens if result.usage else None,
                    tokens_total=result.usage.total_tokens if result.usage else None,
                    cost=result.usage.cost if result.usage else None,
                )
            )

            if result.usage:
                self._session.add_usage(result.usage)

            if result.error:
                self._session.fail(result.error)
                break

            if result.is_complete:
                self._session.complete(success=True)
                break

            observations = []

            for action in result.actions:
                action_data = action.to_dict()

                self.event_bus.publish(
                    ActionEmittedEvent(
                        run_id=self._session.run_id,
                        step_id=step_id,
                        action_type=action.action.value,
                        action_data=action_data,
                    )
                )

                if self.policy_engine.config.enabled:
                    decision = self.policy_engine.evaluate(
                        action.action.value,
                        action_data,
                        {"step_number": step_number},
                    )

                    if decision == PolicyDecision.DENY:
                        raise PolicyError(action.action.value, "Action denied by policy")
                    if decision == PolicyDecision.REQUIRE_CONFIRMATION:
                        confirmed = await self.policy_engine.confirm(
                            action.action.value, f"Allow {action.action.value}?"
                        )
                        if not confirmed:
                            raise PolicyError(action.action.value, "Action not confirmed")

                observation = await self.backend.execute(action, step_id)

                self.event_bus.publish(
                    ActionExecutedEvent(
                        run_id=self._session.run_id,
                        step_id=step_id,
                        action_type=action.action.value,
                        success=observation.success,
                    )
                )

                if observation.success:
                    self._session.record_success()
                else:
                    self._session.record_failure()

                if isinstance(observation, ScreenshotObservation) and observation.image_data:
                    screenshot_path = self.artifact_store.save_screenshot(
                        step_number, observation.image_data
                    )
                    observation.metadata["screenshot_path"] = str(screenshot_path)

                observations.append(observation)

                self.event_bus.publish(
                    ObservationRecordedEvent(
                        run_id=self._session.run_id,
                        step_id=step_id,
                        observation_type=observation.observation_type.value,
                        has_screenshot=isinstance(observation, ScreenshotObservation),
                    )
                )

            if result.needs_screenshot and observations:
                screenshot = await self._take_screenshot(step_id)
                if screenshot:
                    observations.append(screenshot)

            step_record = StepRecord(
                step_id=step_id,
                step_number=step_number,
                timestamp=datetime.now(UTC),
                provider_input={"step": step_count},
                provider_output=result.raw_response,
                action=action_data if result.actions else None,
                observation=observations[0].model_dump() if observations else None,
                usage=result.usage,
            )
            self.artifact_store.write_step(step_record)

            self.event_bus.publish(
                StepCompletedEvent(
                    run_id=self._session.run_id,
                    step_id=step_id,
                    step_number=step_number,
                    action_count=len(result.actions),
                )
            )

            step_count += 1

            await asyncio.sleep(config.screenshot_interval)

        if self._session.is_running:
            self._session.complete(success=True)

        await self.provider.close(self._provider_state)

    async def _take_screenshot(self, step_id: str) -> ScreenshotObservation | None:
        """Take a screenshot."""
        try:
            return await self.backend.screenshot(step_id)
        except Exception:
            return None

    async def cancel(self) -> None:
        """Cancel the current run."""
        if self._session and self._session.is_running:
            self._session.fail("Cancelled by user")


async def create_orchestrator(
    backend: BaseBackend,
    provider: ProviderAdapter,
    event_bus: EventBus | None = None,
    artifact_store: ArtifactStore | None = None,
    policy_engine: PolicyEngine | None = None,
) -> Orchestrator:
    """Create an orchestrator with default components."""
    return Orchestrator(
        backend=backend,
        provider=provider,
        event_bus=event_bus,
        artifact_store=artifact_store,
        policy_engine=policy_engine,
    )
