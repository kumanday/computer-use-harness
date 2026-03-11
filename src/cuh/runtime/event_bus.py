"""Event bus for CUH runs.

Provides publish/subscribe functionality for run events,
enabling real-time observability and monitoring.
"""

import asyncio
import contextlib
from collections import defaultdict
from collections.abc import Callable, Iterator
from typing import Any

from cuh.core.events import RunEvent


class EventBus:
    """Event bus for publishing and subscribing to run events."""

    def __init__(self) -> None:
        self._subscribers: dict[str, list[Callable[[RunEvent], None]]] = defaultdict(list)
        self._async_subscribers: dict[str, list[Callable[[RunEvent], Any]]] = defaultdict(list)
        self._event_history: list[RunEvent] = []
        self._max_history: int = 1000

    def subscribe(
        self, event_type: str | None, callback: Callable[[RunEvent], None]
    ) -> Callable[[], None]:
        """Subscribe to events. If event_type is None, subscribes to all events."""
        key = event_type or "*"
        self._subscribers[key].append(callback)

        def unsubscribe() -> None:
            if callback in self._subscribers[key]:
                self._subscribers[key].remove(callback)

        return unsubscribe

    def subscribe_async(
        self, event_type: str | None, callback: Callable[[RunEvent], Any]
    ) -> Callable[[], None]:
        """Subscribe to events with an async callback."""
        key = event_type or "*"
        self._async_subscribers[key].append(callback)

        def unsubscribe() -> None:
            if callback in self._async_subscribers[key]:
                self._async_subscribers[key].remove(callback)

        return unsubscribe

    def publish(self, event: RunEvent) -> None:
        """Publish an event to all subscribers."""
        self._event_history.append(event)
        if len(self._event_history) > self._max_history:
            self._event_history.pop(0)

        event_type = event.event_type.value

        for callback in self._subscribers[event_type]:
            with contextlib.suppress(Exception):
                callback(event)

        for callback in self._subscribers["*"]:
            with contextlib.suppress(Exception):
                callback(event)

        for callback in self._async_subscribers[event_type]:
            with contextlib.suppress(Exception):
                asyncio.create_task(self._call_async(callback, event))

        for callback in self._async_subscribers["*"]:
            with contextlib.suppress(Exception):
                asyncio.create_task(self._call_async(callback, event))

    async def _call_async(self, callback: Callable[[RunEvent], Any], event: RunEvent) -> None:
        """Call an async callback safely."""
        try:
            result = callback(event)
            if asyncio.iscoroutine(result):
                await result
        except Exception:
            pass

    def get_history(self, run_id: str | None = None) -> Iterator[RunEvent]:
        """Get event history, optionally filtered by run_id."""
        for event in self._event_history:
            if run_id is None or event.run_id == run_id:
                yield event

    def clear_history(self) -> None:
        """Clear event history."""
        self._event_history.clear()


class StdoutEventFormatter:
    """Format events for stdout output."""

    def __init__(self, verbose: bool = False) -> None:
        self.verbose = verbose

    def format(self, event: RunEvent) -> str:
        """Format an event for output."""
        timestamp = event.timestamp.strftime("%H:%M:%S.%f")[:-3]
        prefix = f"[{timestamp}] [{event.event_type.value}]"

        if event.event_type.value == "run_started":
            task = getattr(event, "task", "") or event.metadata.get("task", "")
            return f"{prefix} Run started: {event.run_id[:8]} - {task[:50]}"
        if event.event_type.value == "run_completed":
            duration = getattr(event, "duration_seconds", 0) or event.metadata.get(
                "duration_seconds", 0
            )
            return f"{prefix} Run completed in {duration:.2f}s"
        if event.event_type.value == "run_failed":
            error = getattr(event, "error_message", None) or event.metadata.get(
                "error_message", "Unknown error"
            )
            return f"{prefix} Run failed: {error}"
        if event.event_type.value == "action_emitted":
            action_type = getattr(event, "action_type", None) or event.metadata.get(
                "action_type", "unknown"
            )
            return f"{prefix} Action: {action_type}"
        if event.event_type.value == "action_executed":
            action_type = getattr(event, "action_type", None) or event.metadata.get(
                "action_type", "unknown"
            )
            status = (
                "OK"
                if (getattr(event, "success", False) or event.metadata.get("success"))
                else "FAILED"
            )
            return f"{prefix} Action executed: {action_type} [{status}]"
        if event.event_type.value == "provider_response":
            tokens = event.metadata.get("tokens_total", 0)
            cost = event.metadata.get("cost", 0)
            return f"{prefix} Provider response: {tokens} tokens, ${cost:.4f}"
        if event.event_type.value == "error":
            error = getattr(event, "error_message", None) or event.metadata.get(
                "error_message", "Unknown"
            )
            return f"{prefix} ERROR: {error}"
        if self.verbose:
            return f"{prefix} {event.model_dump_json()}"
        return f"{prefix}"


def create_stdout_handler(
    formatter: StdoutEventFormatter | None = None,
) -> Callable[[RunEvent], None]:
    """Create a handler that prints events to stdout."""
    if formatter is None:
        formatter = StdoutEventFormatter()

    def handler(event: RunEvent) -> None:
        print(formatter.format(event))

    return handler
