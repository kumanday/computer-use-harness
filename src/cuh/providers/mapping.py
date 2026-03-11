"""Tool-name mapping for provider adapters.

Maps between provider-specific tool schemas and canonical CUH actions.
"""

from typing import Any, ClassVar

from cuh.core.actions import (
    ActionType,
    ClickAction,
    ComputerAction,
    DoubleClickAction,
    DragAction,
    DragPathPoint,
    KeyPressAction,
    MoveAction,
    ScreenshotAction,
    ScrollAction,
    TypeAction,
    WaitAction,
)


class ToolNameMapper:
    """Maps provider-specific tool names and schemas to canonical actions."""

    ACTION_ALIASES: ClassVar[dict[str, ActionType]] = {
        "click": ActionType.CLICK,
        "double_click": ActionType.DOUBLE_CLICK,
        "doubleclick": ActionType.DOUBLE_CLICK,
        "move": ActionType.MOVE,
        "mouse_move": ActionType.MOVE,
        "mousemove": ActionType.MOVE,
        "drag": ActionType.DRAG,
        "scroll": ActionType.SCROLL,
        "type": ActionType.TYPE,
        "keyboard_type": ActionType.TYPE,
        "key_press": ActionType.KEYPRESS,
        "keypress": ActionType.KEYPRESS,
        "wait": ActionType.WAIT,
        "screenshot": ActionType.SCREENSHOT,
    }

    @classmethod
    def normalize_action_type(cls, action_type: str) -> ActionType:
        """Normalize an action type string to canonical ActionType."""
        normalized = action_type.lower().replace("-", "_")
        return cls.ACTION_ALIASES.get(normalized, ActionType.SCREENSHOT)

    @classmethod
    def parse_action(cls, data: dict[str, Any]) -> ComputerAction:
        """Parse a provider action dict into a canonical ComputerAction."""
        action_type = cls.normalize_action_type(data.get("action", data.get("type", "screenshot")))

        if action_type == ActionType.SCREENSHOT:
            return ScreenshotAction(**data)

        if action_type == ActionType.CLICK:
            return ClickAction(
                x=data.get("x", data.get("coordinate", [0, 0])[0]),
                y=data.get("y", data.get("coordinate", [0, 0])[1]),
                button=data.get("button", "left"),
            )

        if action_type == ActionType.DOUBLE_CLICK:
            return DoubleClickAction(
                x=data.get("x", data.get("coordinate", [0, 0])[0]),
                y=data.get("y", data.get("coordinate", [0, 0])[1]),
            )

        if action_type == ActionType.MOVE:
            return MoveAction(
                x=data.get("x", data.get("coordinate", [0, 0])[0]),
                y=data.get("y", data.get("coordinate", [0, 0])[1]),
            )

        if action_type == ActionType.DRAG:
            path = data.get("path", [])
            if path:
                points = [DragPathPoint(x=p.get("x", 0), y=p.get("y", 0)) for p in path]
            else:
                from_x = data.get("from_x", data.get("startCoordinate", [0, 0])[0])
                from_y = data.get("from_y", data.get("startCoordinate", [0, 0])[1])
                to_x = data.get("to_x", data.get("endCoordinate", [0, 0])[0])
                to_y = data.get("to_y", data.get("endCoordinate", [0, 0])[1])
                points = [
                    DragPathPoint(x=from_x, y=from_y),
                    DragPathPoint(x=to_x, y=to_y),
                ]
            return DragAction(path=points)

        if action_type == ActionType.SCROLL:
            return ScrollAction(
                x=data.get("x", 0),
                y=data.get("y", 0),
                scroll_x=data.get("scroll_x", data.get("delta_x", 0)),
                scroll_y=data.get("scroll_y", data.get("delta_y", 0)),
            )

        if action_type == ActionType.TYPE:
            return TypeAction(text=data.get("text", ""))

        if action_type == ActionType.KEYPRESS:
            keys = data.get("keys", data.get("key", []))
            if isinstance(keys, str):
                keys = [keys]
            return KeyPressAction(keys=keys)

        if action_type == ActionType.WAIT:
            return WaitAction(seconds=data.get("seconds", data.get("duration", 1.0)))

        return ComputerAction(action=action_type, **data)


class OpenAIToolSchema:
    """OpenAI computer tool schema."""

    @staticmethod
    def get_schema() -> dict[str, Any]:
        """Get the OpenAI computer tool schema."""
        return {"type": "computer"}


class QwenToolSchema:
    """Qwen function tool schema for computer actions."""

    @staticmethod
    def get_schema() -> dict[str, Any]:
        """Get the Qwen function tool schema."""
        return {
            "type": "function",
            "function": {
                "name": "computer",
                "description": "Execute computer control actions like clicking, typing, scrolling, etc.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "action": {
                            "type": "string",
                            "enum": [
                                "screenshot",
                                "click",
                                "double_click",
                                "move",
                                "drag",
                                "scroll",
                                "type",
                                "keypress",
                                "wait",
                            ],
                            "description": "The action to perform",
                        },
                        "x": {
                            "type": "integer",
                            "description": "X coordinate for click/move actions",
                        },
                        "y": {
                            "type": "integer",
                            "description": "Y coordinate for click/move actions",
                        },
                        "button": {
                            "type": "string",
                            "enum": ["left", "right", "middle", "wheel", "back", "forward"],
                            "default": "left",
                            "description": "Mouse button for click action",
                        },
                        "path": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "x": {"type": "integer"},
                                    "y": {"type": "integer"},
                                },
                            },
                            "description": "Path of coordinates for drag action",
                        },
                        "scroll_x": {
                            "type": "integer",
                            "description": "Horizontal scroll amount",
                        },
                        "scroll_y": {
                            "type": "integer",
                            "description": "Vertical scroll amount",
                        },
                        "text": {"type": "string", "description": "Text to type"},
                        "keys": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Keys to press for keypress action",
                        },
                        "seconds": {"type": "number", "description": "Seconds to wait"},
                    },
                    "required": ["action"],
                },
            },
        }
