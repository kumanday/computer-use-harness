"""Canonical computer action schema for CUH.

This module defines the canonical action types that all providers must translate to.
The schema is provider-neutral and serves as the internal representation for all
computer control actions.

Based on OpenAI computer-use action types:
https://developers.openai.com/api/docs/guides/tools-computer-use/
"""

from enum import StrEnum
from typing import Annotated, Any

from pydantic import BaseModel, Field


class ActionType(StrEnum):
    """Canonical action types for computer control."""

    SCREENSHOT = "screenshot"
    CLICK = "click"
    DOUBLE_CLICK = "double_click"
    MOVE = "move"
    DRAG = "drag"
    SCROLL = "scroll"
    TYPE = "type"
    KEYPRESS = "keypress"
    WAIT = "wait"

    SHELL_EXEC = "shell_exec"
    BROWSER_VISIT = "browser_visit"
    BROWSER_SEARCH = "browser_search"
    WINDOW_FOCUS = "window_focus"
    CLIPBOARD_GET = "clipboard_get"
    CLIPBOARD_SET = "clipboard_set"


class MouseButton(StrEnum):
    """Mouse button types."""

    LEFT = "left"
    RIGHT = "right"
    MIDDLE = "middle"
    WHEEL = "wheel"
    BACK = "back"
    FORWARD = "forward"


class KeyModifier(StrEnum):
    """Key modifiers for keypress actions."""

    CTRL = "CTRL"
    ALT = "ALT"
    SHIFT = "SHIFT"
    META = "META"
    SUPER = "SUPER"


class DragPathPoint(BaseModel):
    """A point in a drag path."""

    x: int
    y: int


class ComputerAction(BaseModel):
    """Canonical computer action schema.

    All provider adapters must translate their native tool calls to this schema.
    """

    tool: str = "computer"
    action: ActionType
    x: int | None = None
    y: int | None = None
    button: MouseButton = MouseButton.LEFT
    path: list[DragPathPoint] | None = None
    scroll_x: int = 0
    scroll_y: int = 0
    text: str | None = None
    keys: list[str] | None = None
    seconds: float = 1.0
    command: str | None = None
    url: str | None = None
    query: str | None = None
    window_name: str | None = None
    clipboard_content: str | None = None
    meta: dict[str, Any] = Field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert action to dictionary, excluding None values."""
        data = self.model_dump(exclude_none=True, mode="json")
        return {k: v for k, v in data.items() if v is not None}


class ScreenshotAction(ComputerAction):
    """Take a screenshot."""

    action: ActionType = ActionType.SCREENSHOT


class ClickAction(ComputerAction):
    """Click at coordinates."""

    action: ActionType = ActionType.CLICK
    x: int
    y: int
    button: MouseButton = MouseButton.LEFT


class DoubleClickAction(ComputerAction):
    """Double-click at coordinates."""

    action: ActionType = ActionType.DOUBLE_CLICK
    x: int
    y: int


class MoveAction(ComputerAction):
    """Move mouse to coordinates."""

    action: ActionType = ActionType.MOVE
    x: int
    y: int


class DragAction(ComputerAction):
    """Drag along a path of coordinates."""

    action: ActionType = ActionType.DRAG
    path: list[DragPathPoint]

    @classmethod
    def from_points(cls, start: tuple[int, int], end: tuple[int, int]) -> "DragAction":
        """Create a simple drag from start to end point."""
        return cls(
            path=[
                DragPathPoint(x=start[0], y=start[1]),
                DragPathPoint(x=end[0], y=end[1]),
            ]
        )


class ScrollAction(ComputerAction):
    """Scroll at cursor location."""

    action: ActionType = ActionType.SCROLL
    x: int = 0
    y: int = 0
    scroll_x: int = 0
    scroll_y: int = 0


class TypeAction(ComputerAction):
    """Type text."""

    action: ActionType = ActionType.TYPE
    text: str


class KeyPressAction(ComputerAction):
    """Press key combination (supports chorded inputs)."""

    action: ActionType = ActionType.KEYPRESS
    keys: list[str]


class WaitAction(ComputerAction):
    """Wait for specified seconds."""

    action: ActionType = ActionType.WAIT
    seconds: float = 1.0


Action = Annotated[
    ScreenshotAction
    | ClickAction
    | DoubleClickAction
    | MoveAction
    | DragAction
    | ScrollAction
    | TypeAction
    | KeyPressAction
    | WaitAction
    | ComputerAction,
    Field(discriminator="action"),
]
