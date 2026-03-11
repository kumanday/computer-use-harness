"""Base backend interface for CUH.

Defines the interface that all execution backends must implement.
"""

import asyncio
from abc import ABC, abstractmethod

from cuh.core.actions import ActionType, ComputerAction
from cuh.core.models import ScreenGeometry, TargetConfig
from cuh.core.observations import (
    ActionResultObservation,
    ComputerObservation,
    ObservationType,
    ScreenshotObservation,
)


class BackendError(Exception):
    """Exception raised by backend operations."""

    def __init__(self, message: str, action_type: str | None = None) -> None:
        self.action_type = action_type
        super().__init__(message)


class BaseBackend(ABC):
    """Abstract base class for execution backends."""

    def __init__(self, config: TargetConfig) -> None:
        self.config = config
        self.geometry: ScreenGeometry | None = None
        self._connected = False

    @abstractmethod
    async def connect(self) -> None:
        """Connect to the target."""

    @abstractmethod
    async def disconnect(self) -> None:
        """Disconnect from the target."""

    @abstractmethod
    async def execute(self, action: ComputerAction, step_id: str) -> ComputerObservation:
        """Execute a computer action."""

    @abstractmethod
    async def screenshot(self, step_id: str) -> ScreenshotObservation:
        """Take a screenshot."""

    @abstractmethod
    async def get_geometry(self) -> ScreenGeometry:
        """Get the screen geometry."""

    @property
    def is_connected(self) -> bool:
        """Check if the backend is connected."""
        return self._connected

    async def health_check(self) -> bool:
        """Check if the backend is healthy."""
        return self._connected

    async def wait(self, seconds: float, step_id: str) -> ActionResultObservation:
        """Wait for a specified duration."""
        await asyncio.sleep(seconds)
        return ActionResultObservation(
            observation_type=ObservationType.ACTION_RESULT,
            step_id=step_id,
            action_type=ActionType.WAIT.value,
            message=f"Waited {seconds} seconds",
        )


class MockBackend(BaseBackend):
    """Mock backend for testing."""

    def __init__(self, config: TargetConfig) -> None:
        super().__init__(config)
        self._actions: list[ComputerAction] = []
        self._screenshot_count = 0

    async def connect(self) -> None:
        self._connected = True
        self.geometry = ScreenGeometry(
            actual_width=1920,
            actual_height=1080,
            model_view_width=1280,
            model_view_height=720,
        )

    async def disconnect(self) -> None:
        self._connected = False

    async def execute(self, action: ComputerAction, step_id: str) -> ComputerObservation:
        self._actions.append(action)

        if action.action == ActionType.SCREENSHOT:
            return await self.screenshot(step_id)

        return ActionResultObservation(
            observation_type=ObservationType.ACTION_RESULT,
            step_id=step_id,
            action_type=action.action.value,
            message=f"Mock executed: {action.action.value}",
        )

    async def screenshot(self, step_id: str) -> ScreenshotObservation:
        self._screenshot_count += 1
        return ScreenshotObservation(
            observation_type=ObservationType.SCREENSHOT,
            step_id=step_id,
            image_base64="",
            width=1280,
            height=720,
        )

    async def get_geometry(self) -> ScreenGeometry:
        if self.geometry is None:
            return ScreenGeometry(actual_width=1920, actual_height=1080)
        return self.geometry
