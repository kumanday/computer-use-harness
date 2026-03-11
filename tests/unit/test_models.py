"""Tests for core models module."""


from cuh.core.models import (
    ProviderKind,
    RunConfig,
    RunState,
    ScreenGeometry,
    TargetConfig,
    TargetKind,
    UsageMetrics,
)


class TestScreenGeometry:
    def test_create(self) -> None:
        geometry = ScreenGeometry(
            actual_width=1920,
            actual_height=1080,
        )
        assert geometry.actual_width == 1920
        assert geometry.actual_height == 1080
        assert geometry.scale_ratio == 1.0

    def test_from_sizes_no_scaling(self) -> None:
        geometry = ScreenGeometry.from_sizes(1920, 1080)
        assert geometry.actual_width == 1920
        assert geometry.actual_height == 1080
        assert geometry.scale_ratio == 1.0

    def test_from_sizes_with_scaling(self) -> None:
        geometry = ScreenGeometry.from_sizes(1920, 1080, 1280, 720)
        assert geometry.actual_width == 1920
        assert geometry.actual_height == 1080
        assert geometry.model_view_width == 1280
        assert geometry.model_view_height == 720
        assert geometry.scale_ratio == 1.5  # 1920 / 1280

    def test_model_to_actual(self) -> None:
        geometry = ScreenGeometry(
            actual_width=1920,
            actual_height=1080,
            model_view_width=1280,
            model_view_height=720,
            scale_ratio=1.5,
        )
        actual_x, actual_y = geometry.model_to_actual(100, 100)
        assert actual_x == 150  # 100 * 1.5
        assert actual_y == 150

    def test_actual_to_model(self) -> None:
        geometry = ScreenGeometry(
            actual_width=1920,
            actual_height=1080,
            model_view_width=1280,
            model_view_height=720,
            scale_ratio=1.5,
        )
        model_x, model_y = geometry.actual_to_model(150, 150)
        assert model_x == 100  # 150 / 1.5
        assert model_y == 100


class TestRunState:
    def test_enum_values(self) -> None:
        assert RunState.PENDING.value == "pending"
        assert RunState.RUNNING.value == "running"
        assert RunState.COMPLETED.value == "completed"
        assert RunState.FAILED.value == "failed"
        assert RunState.BLOCKED.value == "blocked"
        assert RunState.CANCELLED.value == "cancelled"


class TestTargetKind:
    def test_enum_values(self) -> None:
        assert TargetKind.CUA_HOST.value == "cua_host"
        assert TargetKind.CUA_REMOTE.value == "cua_remote"
        assert TargetKind.LINUX_SANDBOX.value == "linux_sandbox"
        assert TargetKind.WINDOWS_VM.value == "windows_vm"
        assert TargetKind.BROWSER.value == "browser"


class TestProviderKind:
    def test_enum_values(self) -> None:
        assert ProviderKind.OPENAI.value == "openai"
        assert ProviderKind.QWEN.value == "qwen"


class TestRunConfig:
    def test_create(self) -> None:
        config = RunConfig(
            provider=ProviderKind.OPENAI,
            model="gpt-5.4",
            target="local-host",
            task="Take a screenshot",
        )
        assert config.provider == ProviderKind.OPENAI
        assert config.model == "gpt-5.4"
        assert config.target == "local-host"
        assert config.task == "Take a screenshot"
        assert config.max_steps == 100


class TestTargetConfig:
    def test_create(self) -> None:
        config = TargetConfig(
            kind=TargetKind.CUA_HOST,
            name="local-host",
            api_host="127.0.0.1",
            api_port=8000,
        )
        assert config.kind == TargetKind.CUA_HOST
        assert config.name == "local-host"
        assert config.api_host == "127.0.0.1"
        assert config.api_port == 8000


class TestUsageMetrics:
    def test_create(self) -> None:
        metrics = UsageMetrics(
            prompt_tokens=1000,
            completion_tokens=500,
            total_tokens=1500,
            cost=0.05,
            latency_ms=1234.5,
        )
        assert metrics.prompt_tokens == 1000
        assert metrics.completion_tokens == 500
        assert metrics.total_tokens == 1500
        assert metrics.cost == 0.05
        assert metrics.latency_ms == 1234.5
