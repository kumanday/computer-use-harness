"""Tests for provider tool name mapping."""

from cuh.core.actions import ActionType
from cuh.providers.mapping import OpenAIToolSchema, QwenToolSchema, ToolNameMapper


class TestToolNameMapper:
    def test_normalize_action_type_screenshot(self) -> None:
        assert ToolNameMapper.normalize_action_type("screenshot") == ActionType.SCREENSHOT

    def test_normalize_action_type_click(self) -> None:
        assert ToolNameMapper.normalize_action_type("click") == ActionType.CLICK

    def test_normalize_action_type_aliases(self) -> None:
        assert ToolNameMapper.normalize_action_type("double_click") == ActionType.DOUBLE_CLICK
        assert ToolNameMapper.normalize_action_type("doubleClick") == ActionType.DOUBLE_CLICK
        assert ToolNameMapper.normalize_action_type("mouse_move") == ActionType.MOVE
        assert ToolNameMapper.normalize_action_type("keypress") == ActionType.KEYPRESS

    def test_parse_action_screenshot(self) -> None:
        action = ToolNameMapper.parse_action({"action": "screenshot"})
        assert action.action == ActionType.SCREENSHOT

    def test_parse_action_click(self) -> None:
        action = ToolNameMapper.parse_action({"action": "click", "x": 100, "y": 200})
        assert action.action == ActionType.CLICK
        assert action.x == 100
        assert action.y == 200

    def test_parse_action_click_with_coordinate_array(self) -> None:
        action = ToolNameMapper.parse_action({"action": "click", "coordinate": [100, 200]})
        assert action.action == ActionType.CLICK
        assert action.x == 100
        assert action.y == 200

    def test_parse_action_type(self) -> None:
        action = ToolNameMapper.parse_action({"action": "type", "text": "hello"})
        assert action.action == ActionType.TYPE
        assert action.text == "hello"

    def test_parse_action_keypress(self) -> None:
        action = ToolNameMapper.parse_action({"action": "keypress", "keys": ["CTRL", "S"]})
        assert action.action == ActionType.KEYPRESS
        assert action.keys == ["CTRL", "S"]

    def test_parse_action_keypress_single_key(self) -> None:
        action = ToolNameMapper.parse_action({"action": "keypress", "key": "ENTER"})
        assert action.action == ActionType.KEYPRESS
        assert action.keys == ["ENTER"]

    def test_parse_action_drag_with_path(self) -> None:
        action = ToolNameMapper.parse_action(
            {"action": "drag", "path": [{"x": 100, "y": 200}, {"x": 400, "y": 500}]}
        )
        assert action.action == ActionType.DRAG
        assert len(action.path) == 2

    def test_parse_action_scroll(self) -> None:
        action = ToolNameMapper.parse_action(
            {"action": "scroll", "x": 100, "y": 200, "scroll_x": 0, "scroll_y": 500}
        )
        assert action.action == ActionType.SCROLL
        assert action.scroll_y == 500


class TestOpenAIToolSchema:
    def test_get_schema(self) -> None:
        schema = OpenAIToolSchema.get_schema()
        assert schema["type"] == "computer"


class TestQwenToolSchema:
    def test_get_schema(self) -> None:
        schema = QwenToolSchema.get_schema()
        assert schema["type"] == "function"
        assert schema["function"]["name"] == "computer"
        assert "action" in schema["function"]["parameters"]["properties"]
        assert schema["function"]["parameters"]["required"] == ["action"]
