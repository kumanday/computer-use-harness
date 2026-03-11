"""Base provider interface for CUH.

Defines the interface that all model provider adapters must implement.
"""

import time
from abc import ABC, abstractmethod
from typing import Any, Protocol

from pydantic import BaseModel

from cuh.core.actions import ComputerAction
from cuh.core.models import ProviderConfig, UsageMetrics
from cuh.core.observations import ComputerObservation


class ProviderError(Exception):
    """Exception raised by provider operations."""

    def __init__(self, message: str, provider: str | None = None) -> None:
        self.provider = provider
        super().__init__(message)


class ProviderRunRequest(BaseModel):
    """Request to start a provider run."""

    task: str
    max_steps: int = 100
    system_prompt: str | None = None
    initial_screenshot: str | None = None
    extra: dict[str, Any] = {}

    model_config = {"arbitrary_types_allowed": True}


class ProviderStepResult(BaseModel):
    """Result from a provider step."""

    actions: list[ComputerAction] = []
    text: str | None = None
    is_complete: bool = False
    usage: UsageMetrics | None = None
    raw_response: dict[str, Any] | None = None
    error: str | None = None
    needs_screenshot: bool = True

    model_config = {"arbitrary_types_allowed": True}


class ProviderAdapter(Protocol):
    """Protocol for provider adapters."""

    async def start_run(self, request: ProviderRunRequest) -> dict[str, Any]:
        """Start a new run with the provider."""
        ...

    async def next_step(
        self, state: dict[str, Any], observations: list[ComputerObservation]
    ) -> ProviderStepResult:
        """Process observations and get next actions."""
        ...

    async def close(self, state: dict[str, Any]) -> None:
        """Close the provider run."""
        ...


class BaseProviderAdapter(ABC):
    """Abstract base class for provider adapters."""

    def __init__(self, config: ProviderConfig) -> None:
        self.config = config
        self._state: dict[str, Any] = {}

    @abstractmethod
    async def start_run(self, request: ProviderRunRequest) -> dict[str, Any]:
        """Start a new run with the provider."""

    @abstractmethod
    async def next_step(
        self, state: dict[str, Any], observations: list[ComputerObservation]
    ) -> ProviderStepResult:
        """Process observations and get next actions."""

    async def close(self, state: dict[str, Any]) -> None:
        """Close the provider run."""

    def get_api_key(self) -> str | None:
        """Get the API key from configuration."""
        return self.config.get_api_key()

    def _calculate_latency(self, start_time: float) -> float:
        """Calculate latency in milliseconds."""
        return (time.time() - start_time) * 1000
