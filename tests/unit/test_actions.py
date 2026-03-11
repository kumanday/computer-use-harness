"""Tests for core actions module."""

from cuh.core.actions import (
    ActionType,
    ClickAction,
    ComputerAction,
    DoubleClickAction,
    DragAction,
    DragPathPoint,
    KeyPressAction,
    MouseButton,
    MoveAction,
    ScreenshotAction,
    ScrollAction,
    TypeAction,
    WaitAction,
)


class TestActionTypes:
    def test_action_type_enum_values(self) -> None:
        assert ActionType.SCREENSHOT.value == "screenshot"
        assert ActionType.CLICK.value == "click"
        assert ActionType.DOUBLE_CLICK.value == "double_click"
        assert ActionType.MOVE.value == "move"
        assert ActionType.DRAG.value == "drag"
        assert ActionType.SCROLL.value == "scroll"
        assert ActionType.TYPE.value == "type"
        assert ActionType.KEYPRESS.value == "keypress"
        assert ActionType.WAIT.value == "wait"

    def test_mouse_button_enum(self) -> None:
        assert MouseButton.LEFT.value == "left"
        assert MouseButton.RIGHT.value == "right"
        assert MouseButton.MIDDLE.value == "middle"
        assert MouseButton.WHEEL.value == "wheel"
        assert MouseButton.BACK.value == "back"
        assert MouseButton.FORWARD.value == "forward"


class TestScreenshotAction:
    def test_create(self) -> None:
        action = ScreenshotAction()
        assert action.action == ActionType.SCREENSHOT
        assert action.tool == "computer"

    def test_to_dict(self) -> None:
        action = ScreenshotAction()
        data = action.to_dict()
        assert data["tool"] == "computer"
        assert data["action"] == "screenshot"


class TestClickAction:
    def test_create(self) -> None:
        action = ClickAction(x=100, y=200)
        assert action.action == ActionType.CLICK
        assert action.x == 100
        assert action.y == 200
        assert action.button == MouseButton.LEFT

    def test_create_with_button(self) -> None:
        action = ClickAction(x=100, y=200, button=MouseButton.RIGHT)
        assert action.button == MouseButton.RIGHT

    def test_to_dict(self) -> None:
        action = ClickAction(x=100, y=200, button=MouseButton.RIGHT)
        data = action.to_dict()
        assert data["x"] == 100
        assert data["y"] == 200
        assert data["button"] == "right"


class TestDoubleClickAction:
    def test_create(self) -> None:
        action = DoubleClickAction(x=100, y=200)
        assert action.action == ActionType.DOUBLE_CLICK
        assert action.x == 100
        assert action.y == 200


class TestMoveAction:
    def test_create(self) -> None:
        action = MoveAction(x=100, y=200)
        assert action.action == ActionType.MOVE
        assert action.x == 100
        assert action.y == 200


class TestDragAction:
    def test_create(self) -> None:
        action = DragAction(
            path=[
                DragPathPoint(x=100, y=200),
                DragPathPoint(x=400, y=500),
            ]
        )
        assert action.action == ActionType.DRAG
        assert len(action.path) == 2
        assert action.path[0].x == 100
        assert action.path[0].y == 200
        assert action.path[1].x == 400
        assert action.path[1].y == 500

    def test_from_points(self) -> None:
        action = DragAction.from_points((100, 200), (400, 500))
        assert len(action.path) == 2
        assert action.path[0].x == 100
        assert action.path[1].x == 400


class TestScrollAction:
    def test_create(self) -> None:
        action = ScrollAction(x=100, y=200, scroll_x=0, scroll_y=500)
        assert action.action == ActionType.SCROLL
        assert action.x == 100
        assert action.y == 200
        assert action.scroll_x == 0
        assert action.scroll_y == 500


class TestTypeAction:
    def test_create(self) -> None:
        action = TypeAction(text="hello world")
        assert action.action == ActionType.TYPE
        assert action.text == "hello world"


class TestKeyPressAction:
    def test_create(self) -> None:
        action = KeyPressAction(keys=["CTRL", "S"])
        assert action.action == ActionType.KEYPRESS
        assert action.keys == ["CTRL", "S"]


class TestWaitAction:
    def test_create(self) -> None:
        action = WaitAction(seconds=1.5)
        assert action.action == ActionType.WAIT
        assert action.seconds == 1.5

    def test_default_seconds(self) -> None:
        action = WaitAction()
        assert action.seconds == 1.0


class TestComputerAction:
    def test_base_action(self) -> None:
        action = ComputerAction(action=ActionType.SCREENSHOT)
        assert action.tool == "computer"
        assert action.action == ActionType.SCREENSHOT

    def test_meta_field(self) -> None:
        action = ComputerAction(
            action=ActionType.CLICK,
            x=100,
            y=200,
            meta={"source_model": "gpt-5.4", "step_id": "step_0004"},
        )
        assert action.meta["source_model"] == "gpt-5.4"
