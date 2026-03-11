"""Tests for Qwen 3.5 provider adapter."""

import os
from unittest.mock import patch

import pytest

from cuh.core.actions import ActionType
from cuh.core.models import ProviderConfig, ProviderKind
from cuh.providers.qwen35 import (
    Qwen35Adapter,
    QwenBackend,
    QwenBackendConfig,
    QwenModelProfile,
    QwenToolCallParser,
    QwenToolRenderer,
    create_qwen_adapter_for_backend,
)


class TestQwenToolRenderer:
    def test_render_computer_tool(self) -> None:
        tool = QwenToolRenderer.render_computer_tool()
        assert tool["type"] == "function"
        assert tool["function"]["name"] == "computer"
        assert "action" in tool["function"]["parameters"]["properties"]


class TestQwenToolCallParser:
    def test_parse_tool_call_click(self) -> None:
        tool_call = {
            "function": {
                "name": "computer",
                "arguments": '{"action": "click", "x": 100, "y": 200}',
            }
        }
        action = QwenToolCallParser.parse_tool_call(tool_call)
        assert action is not None
        assert action.action == ActionType.CLICK
        assert action.x == 100
        assert action.y == 200

    def test_parse_tool_call_type(self) -> None:
        tool_call = {
            "function": {
                "name": "computer",
                "arguments": {"action": "type", "text": "hello"},
            }
        }
        action = QwenToolCallParser.parse_tool_call(tool_call)
        assert action is not None
        assert action.action == ActionType.TYPE
        assert action.text == "hello"

    def test_parse_tool_call_wrong_function(self) -> None:
        tool_call = {
            "function": {
                "name": "other_function",
                "arguments": "{}",
            }
        }
        action = QwenToolCallParser.parse_tool_call(tool_call)
        assert action is None

    def test_parse_tool_call_invalid_json(self) -> None:
        tool_call = {
            "function": {
                "name": "computer",
                "arguments": "not valid json",
            }
        }
        action = QwenToolCallParser.parse_tool_call(tool_call)
        assert action is None


class TestQwenBackendConfig:
    def test_get_config_openrouter(self) -> None:
        config = QwenBackendConfig.get_config(QwenBackend.OPENROUTER)
        assert config["api_base"] == "https://openrouter.ai/api/v1"
        assert config["api_key_env"] == "OPENROUTER_API_KEY"
        assert config["model_prefix"] == "qwen/"

    def test_get_config_fireworks(self) -> None:
        config = QwenBackendConfig.get_config(QwenBackend.FIREWORKS)
        assert config["api_base"] == "https://api.fireworks.ai/inference/v1"
        assert config["api_key_env"] == "FIREWORKS_API_KEY"

    def test_get_config_local(self) -> None:
        config = QwenBackendConfig.get_config(QwenBackend.LOCAL)
        assert config["api_base"] == "http://localhost:8000/v1"
        assert config["cost_per_prompt_token"] == 0.0

    def test_list_backends(self) -> None:
        backends = QwenBackendConfig.list_backends()
        assert QwenBackend.OPENROUTER in backends
        assert QwenBackend.FIREWORKS in backends
        assert QwenBackend.LOCAL in backends
        assert QwenBackend.QWEN_API in backends


class TestQwenModelProfile:
    def test_get_profile_local(self) -> None:
        profile = QwenModelProfile.get_profile("local-small")
        assert profile["model"] == "Qwen/Qwen3.5-7B"
        assert profile["max_tokens"] == 2048

    def test_get_profile_openrouter(self) -> None:
        profile = QwenModelProfile.get_profile("openrouter-default")
        assert profile["model"] == "qwen/qwen3.5-397b-a17b"
        assert profile["backend"] == QwenBackend.OPENROUTER

    def test_get_profile_fireworks(self) -> None:
        profile = QwenModelProfile.get_profile("fireworks-default")
        assert profile["model"] == "accounts/fireworks/models/qwen3p5-397b-a17b"
        assert profile["backend"] == QwenBackend.FIREWORKS

    def test_get_profile_unknown(self) -> None:
        profile = QwenModelProfile.get_profile("unknown")
        assert profile["model"] == "Qwen/Qwen3.5-14B"

    def test_list_profiles(self) -> None:
        profiles = QwenModelProfile.list_profiles()
        assert "local-small" in profiles
        assert "local-medium" in profiles
        assert "openrouter-default" in profiles
        assert "fireworks-default" in profiles


class TestQwen35Adapter:
    def test_create_with_local_config(self) -> None:
        config = ProviderConfig(
            provider=ProviderKind.QWEN,
            model="Qwen/Qwen3.5-14B",
            api_base="http://localhost:8000/v1",
            api_key_env="QWEN_API_KEY",
            extra={"backend": QwenBackend.LOCAL},
        )
        adapter = Qwen35Adapter(config)
        assert adapter.model == "Qwen/Qwen3.5-14B"
        assert adapter.api_base == "http://localhost:8000/v1"
        assert adapter.backend == QwenBackend.LOCAL

    @patch.dict(os.environ, {"OPENROUTER_API_KEY": "test-key"})
    def test_create_with_openrouter_config(self) -> None:
        config = ProviderConfig(
            provider=ProviderKind.QWEN,
            model="qwen3.5-397b-a17b",
            api_key_env="OPENROUTER_API_KEY",
            extra={"backend": QwenBackend.OPENROUTER},
        )
        adapter = Qwen35Adapter(config)
        assert adapter.api_base == "https://openrouter.ai/api/v1"
        assert adapter.backend == QwenBackend.OPENROUTER
        assert adapter.model == "qwen/qwen3.5-397b-a17b"

    @patch.dict(os.environ, {"FIREWORKS_API_KEY": "test-key"})
    def test_create_with_fireworks_config(self) -> None:
        config = ProviderConfig(
            provider=ProviderKind.QWEN,
            model="qwen3p5-397b-a17b",
            api_key_env="FIREWORKS_API_KEY",
            extra={"backend": QwenBackend.FIREWORKS},
        )
        adapter = Qwen35Adapter(config)
        assert adapter.api_base == "https://api.fireworks.ai/inference/v1"
        assert adapter.backend == QwenBackend.FIREWORKS
        assert adapter.model == "accounts/fireworks/models/qwen3p5-397b-a17b"

    @patch.dict(os.environ, {"OPENROUTER_API_KEY": "test-key"})
    def test_model_prefix_applied_for_openrouter(self) -> None:
        config = ProviderConfig(
            provider=ProviderKind.QWEN,
            model="qwen-2.5-32b-instruct",
            extra={"backend": QwenBackend.OPENROUTER},
        )
        adapter = Qwen35Adapter(config)
        assert adapter.model == "qwen/qwen-2.5-32b-instruct"

    def test_cost_tracking_per_backend(self) -> None:
        config_local = ProviderConfig(
            provider=ProviderKind.QWEN,
            model="Qwen/Qwen3.5-14B",
            extra={"backend": QwenBackend.LOCAL},
        )
        adapter_local = Qwen35Adapter(config_local)
        assert adapter_local.cost_per_prompt_token == 0.0

        with patch.dict(os.environ, {"OPENROUTER_API_KEY": "test-key"}):
            config_openrouter = ProviderConfig(
                provider=ProviderKind.QWEN,
                model="qwen3.5-397b-a17b",
                extra={"backend": QwenBackend.OPENROUTER},
            )
            adapter_openrouter = Qwen35Adapter(config_openrouter)
            assert adapter_openrouter.cost_per_prompt_token > 0

    def test_wrong_provider_raises(self) -> None:
        config = ProviderConfig(
            provider=ProviderKind.OPENAI,
            model="gpt-5.4",
        )
        with pytest.raises(Exception):
            Qwen35Adapter(config)


class TestCreateQwenAdapterForBackend:
    def test_create_openrouter_config(self) -> None:
        config = create_qwen_adapter_for_backend(
            QwenBackend.OPENROUTER,
            "qwen3.5-397b-a17b",
        )
        assert config.provider == ProviderKind.QWEN
        assert config.model == "qwen/qwen3.5-397b-a17b"
        assert config.api_base == "https://openrouter.ai/api/v1"
        assert config.api_key_env == "OPENROUTER_API_KEY"
        assert config.extra["backend"] == QwenBackend.OPENROUTER

    def test_create_fireworks_config(self) -> None:
        config = create_qwen_adapter_for_backend(
            QwenBackend.FIREWORKS,
            "qwen3p5-397b-a17b",
        )
        assert config.provider == ProviderKind.QWEN
        assert config.model == "accounts/fireworks/models/qwen3p5-397b-a17b"
        assert config.api_base == "https://api.fireworks.ai/inference/v1"
        assert config.api_key_env == "FIREWORKS_API_KEY"

    def test_create_local_config(self) -> None:
        config = create_qwen_adapter_for_backend(
            QwenBackend.LOCAL,
            "Qwen/Qwen3.5-32B",
            api_base="http://my-server:8000/v1",
        )
        assert config.api_base == "http://my-server:8000/v1"
        assert config.extra["backend"] == QwenBackend.LOCAL
