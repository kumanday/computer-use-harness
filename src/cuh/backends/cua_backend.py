"""Cua backend for CUH.

Provides execution backend using the Cua computer-control substrate.
"""

import base64
import contextlib
import time
from typing import Any

from cuh.backends.base import BackendError, BaseBackend
from cuh.core.actions import ActionType, ComputerAction
from cuh.core.models import ScreenGeometry, TargetConfig, TargetKind
from cuh.core.observations import (
    ActionResultObservation,
    ComputerObservation,
    ErrorObservation,
    ScreenshotObservation,
)


class CuaBackend(BaseBackend):
    """Backend using Cua computer-control substrate."""

    def __init__(self, config: TargetConfig) -> None:
        super().__init__(config)
        self._computer: Any = None
        self._last_screenshot: bytes | None = None

    async def connect(self) -> None:
        """Connect to the Cua computer-server."""
        try:
            from computer import Computer

            if self.config.kind in (TargetKind.CUA_HOST, TargetKind.CUA_REMOTE):
                self._computer = Computer(
                    use_host_computer_server=True,
                    api_host=self.config.api_host,
                    api_port=self.config.api_port,
                    telemetry_enabled=self.config.telemetry_enabled,
                )
            else:
                self._computer = Computer(
                    telemetry_enabled=self.config.telemetry_enabled,
                )

            await self._computer.start()
            self._connected = True

            self.geometry = await self.get_geometry()

        except ImportError as e:
            raise BackendError(
                "cua-computer package not installed. Install with: pip install cua-computer"
            ) from e
        except Exception as e:
            raise BackendError(f"Failed to connect to Cua backend: {e}") from e

    async def disconnect(self) -> None:
        """Disconnect from the Cua computer-server."""
        if self._computer:
            with contextlib.suppress(Exception):
                await self._computer.stop()
        self._connected = False
        self._computer = None

    async def execute(self, action: ComputerAction, step_id: str) -> ComputerObservation:
        """Execute a computer action via Cua."""
        if not self._connected or self._computer is None:
            return ErrorObservation(
                step_id=step_id,
                error_type="backend_error",
                error_message="Backend not connected",
            )

        try:
            start_time = time.time()

            if action.action == ActionType.SCREENSHOT:
                return await self.screenshot(step_id)

            if action.action == ActionType.WAIT:
                return await self.wait(action.seconds, step_id)

            result = await self._execute_action(action)

            duration_ms = (time.time() - start_time) * 1000

            return ActionResultObservation(
                step_id=step_id,
                action_type=action.action.value,
                coordinates=self._get_coordinates(action),
                message=f"Executed {action.action.value}",
                metadata={"duration_ms": duration_ms, **result},
            )

        except Exception as e:
            return ErrorObservation(
                step_id=step_id,
                error_type="execution_error",
                error_message=str(e),
            )

    async def _execute_action(self, action: ComputerAction) -> dict[str, Any]:
        """Execute a specific action via Cua."""
        interface = self._computer.interface

        if action.action == ActionType.CLICK:
            x, y = self._get_actual_coordinates(action.x, action.y)
            button = action.button.value if hasattr(action, "button") else "left"
            if button == "left":
                await interface.left_click(x=x, y=y)
            elif button == "right":
                await interface.right_click(x=x, y=y)
            return {"x": x, "y": y, "button": button}

        if action.action == ActionType.DOUBLE_CLICK:
            x, y = self._get_actual_coordinates(action.x, action.y)
            await interface.double_click(x=x, y=y)
            return {"x": x, "y": y}

        if action.action == ActionType.MOVE:
            x, y = self._get_actual_coordinates(action.x, action.y)
            await interface.move_cursor(x=x, y=y)
            return {"x": x, "y": y}

        if action.action == ActionType.DRAG:
            path = action.path or []
            if len(path) >= 2:  # noqa: PLR2004
                start = path[0]
                end = path[-1]
                from_x, from_y = self._get_actual_coordinates(start.x, start.y)
                to_x, to_y = self._get_actual_coordinates(end.x, end.y)
                await interface.drag(from_x=from_x, from_y=from_y, to_x=to_x, to_y=to_y)
                return {"path": [{"x": p.x, "y": p.y} for p in path]}
            return {"error": "Drag path needs at least 2 points"}

        if action.action == ActionType.SCROLL:
            scroll_x, scroll_y = action.scroll_x, action.scroll_y
            if action.x is not None and action.y is not None:
                x, y = self._get_actual_coordinates(action.x, action.y)
                await interface.move_cursor(x=x, y=y)
                await interface.scroll(delta_x=scroll_x, delta_y=scroll_y)
                return {"scroll_x": scroll_x, "scroll_y": scroll_y, "x": x, "y": y}
            await interface.scroll(delta_x=scroll_x, delta_y=scroll_y)
            return {"scroll_x": scroll_x, "scroll_y": scroll_y}

        if action.action == ActionType.TYPE:
            await interface.type_text(text=action.text)
            return {"text_length": len(action.text or "")}

        if action.action == ActionType.KEYPRESS:
            keys = action.keys or []
            for key in keys:
                await interface.press_key(key)
            return {"keys": keys}

        raise BackendError(f"Unknown action type: {action.action}")

    def _get_actual_coordinates(self, x: int | None, y: int | None) -> tuple[int, int]:
        """Transform model coordinates to actual screen coordinates."""
        if x is None or y is None:
            raise BackendError("Coordinates required for this action")

        if self.geometry:
            return self.geometry.model_to_actual(x, y)
        return (x, y)

    def _get_coordinates(self, action: ComputerAction) -> tuple[int, int] | None:
        """Get coordinates from action if applicable."""
        if action.x is not None and action.y is not None:
            return (action.x, action.y)
        if action.path and len(action.path) > 0:
            return (action.path[0].x, action.path[0].y)
        return None

    async def screenshot(self, step_id: str) -> ScreenshotObservation:
        """Take a screenshot via Cua."""
        if not self._connected or self._computer is None:
            return ScreenshotObservation(
                step_id=step_id,
                success=False,
                error="Backend not connected",
            )

        try:
            image_data = await self._computer.interface.screenshot()
            self._last_screenshot = image_data

            width, height = self._get_image_dimensions(image_data)

            return ScreenshotObservation(
                step_id=step_id,
                image_data=image_data,
                image_base64=base64.b64encode(image_data).decode("utf-8"),
                width=width,
                height=height,
            )

        except Exception as e:
            return ScreenshotObservation(
                step_id=step_id,
                success=False,
                error=str(e),
            )

    def _get_image_dimensions(self, image_data: bytes) -> tuple[int, int]:
        """Get image dimensions from PNG/JPEG data."""
        try:
            from io import BytesIO

            from PIL import Image

            img = Image.open(BytesIO(image_data))
            return img.size
        except Exception:
            if self.geometry:
                return (
                    self.geometry.model_view_width or 1280,
                    self.geometry.model_view_height or 720,
                )
            return (1280, 720)

    async def get_geometry(self) -> ScreenGeometry:
        """Get the screen geometry from Cua."""
        if self.geometry:
            return self.geometry

        if not self._connected or self._computer is None:
            return ScreenGeometry(actual_width=1920, actual_height=1080)

        try:
            size = await self._computer.interface.get_screen_size()
            width = size.get("width", 1920) if isinstance(size, dict) else 1920
            height = size.get("height", 1080) if isinstance(size, dict) else 1080
            self.geometry = ScreenGeometry(actual_width=width, actual_height=height)
            return self.geometry
        except Exception:
            self.geometry = ScreenGeometry(actual_width=1920, actual_height=1080)
            return self.geometry


async def create_backend(config: TargetConfig) -> BaseBackend:
    """Create and connect to a backend."""
    from cuh.backends.base import MockBackend

    if config.kind == TargetKind.MOCK:
        backend: BaseBackend = MockBackend(config)
    elif config.kind in (
        TargetKind.CUA_HOST,
        TargetKind.CUA_REMOTE,
        TargetKind.LINUX_SANDBOX,
        TargetKind.WINDOWS_VM,
    ):
        backend = CuaBackend(config)
    else:
        backend = MockBackend(config)

    await backend.connect()
    return backend
