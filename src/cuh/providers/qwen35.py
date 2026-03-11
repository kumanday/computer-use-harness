"""Qwen 3.5 provider adapter for CUH.

Implements the provider adapter for Qwen 3.5 models using OpenAI-compatible
endpoints with function/tool calling support.

Supports multiple backends:
- openrouter: OpenRouter API aggregator
- fireworks: Fireworks AI serving platform
- local: Self-hosted vLLM/SGLang/Transformers
- qwen-api: Official Qwen API (default)
"""

import json
import time
from enum import StrEnum
from typing import Any, ClassVar

import httpx

from cuh.core.actions import ActionType, ComputerAction
from cuh.core.models import ProviderConfig, ProviderKind, UsageMetrics
from cuh.core.observations import ComputerObservation, ScreenshotObservation
from cuh.providers.base import (
    BaseProviderAdapter,
    ProviderError,
    ProviderRunRequest,
    ProviderStepResult,
)
from cuh.providers.mapping import QwenToolSchema, ToolNameMapper


class QwenBackend(StrEnum):
    """Supported backends for Qwen models."""

    OPENROUTER = "openrouter"
    FIREWORKS = "fireworks"
    LOCAL = "local"
    QWEN_API = "qwen-api"


class QwenBackendConfig:
    """Configuration for different Qwen backends."""

    CONFIGS: ClassVar[dict[str, dict[str, Any]]] = {
        QwenBackend.OPENROUTER: {
            "api_base": "https://openrouter.ai/api/v1",
            "api_key_env": "OPENROUTER_API_KEY",
            "model_prefix": "qwen/",
            "extra_headers": {
                "HTTP-Referer": "https://github.com/cuh",
                "X-Title": "CUH Computer Use Harness",
            },
            "cost_per_prompt_token": 0.0000003,
            "cost_per_completion_token": 0.0000006,
        },
        QwenBackend.FIREWORKS: {
            "api_base": "https://api.fireworks.ai/inference/v1",
            "api_key_env": "FIREWORKS_API_KEY",
            "model_prefix": "accounts/fireworks/models/",
            "extra_headers": {},
            "cost_per_prompt_token": 0.0000002,
            "cost_per_completion_token": 0.0000006,
        },
        QwenBackend.LOCAL: {
            "api_base": "http://localhost:8000/v1",
            "api_key_env": "QWEN_API_KEY",
            "model_prefix": "",
            "extra_headers": {},
            "cost_per_prompt_token": 0.0,
            "cost_per_completion_token": 0.0,
        },
        QwenBackend.QWEN_API: {
            "api_base": "https://api.qwen.ai/v1",
            "api_key_env": "QWEN_API_KEY",
            "model_prefix": "",
            "extra_headers": {},
            "cost_per_prompt_token": 0.000001,
            "cost_per_completion_token": 0.000002,
        },
    }

    @classmethod
    def get_config(cls, backend: str) -> dict[str, Any]:
        """Get configuration for a backend."""
        return cls.CONFIGS.get(backend, cls.CONFIGS[QwenBackend.QWEN_API])

    @classmethod
    def list_backends(cls) -> list[str]:
        """List available backends."""
        return list(cls.CONFIGS.keys())


class QwenToolRenderer:
    """Renders tools for Qwen in OpenAI-compatible format."""

    @staticmethod
    def render_computer_tool() -> dict[str, Any]:
        """Render the computer tool schema."""
        return QwenToolSchema.get_schema()


class QwenToolCallParser:
    """Parses tool calls from Qwen responses."""

    @staticmethod
    def parse_tool_call(tool_call: dict[str, Any]) -> ComputerAction | None:
        """Parse a single tool call into a canonical action."""
        function_name = tool_call.get("function", {}).get("name", "")
        if function_name != "computer":
            return None

        arguments = tool_call.get("function", {}).get("arguments", "{}")
        if isinstance(arguments, str):
            try:
                arguments = json.loads(arguments)
            except json.JSONDecodeError:
                return None

        return ToolNameMapper.parse_action(arguments)


class QwenModelProfile:
    """Profile configuration for Qwen models."""

    PROFILES: ClassVar[dict[str, dict[str, Any]]] = {
        "local-small": {
            "model": "Qwen/Qwen3.5-7B",
            "max_tokens": 2048,
            "temperature": 0.7,
        },
        "local-medium": {
            "model": "Qwen/Qwen3.5-14B",
            "max_tokens": 4096,
            "temperature": 0.7,
        },
        "local-large": {
            "model": "Qwen/Qwen3.5-32B",
            "max_tokens": 4096,
            "temperature": 0.7,
        },
        "openrouter-default": {
            "model": "qwen/qwen3.5-397b-a17b",
            "backend": QwenBackend.OPENROUTER,
            "max_tokens": 4096,
            "temperature": 0.7,
        },
        "openrouter-qwen-7b": {
            "model": "qwen/qwen-2.5-7b-instruct",
            "backend": QwenBackend.OPENROUTER,
            "max_tokens": 4096,
            "temperature": 0.7,
        },
        "openrouter-qwen-14b": {
            "model": "qwen/qwen-2.5-14b-instruct",
            "backend": QwenBackend.OPENROUTER,
            "max_tokens": 4096,
            "temperature": 0.7,
        },
        "openrouter-qwen-32b": {
            "model": "qwen/qwen-2.5-32b-instruct",
            "backend": QwenBackend.OPENROUTER,
            "max_tokens": 4096,
            "temperature": 0.7,
        },
        "openrouter-qwen-72b": {
            "model": "qwen/qwen-2.5-72b-instruct",
            "backend": QwenBackend.OPENROUTER,
            "max_tokens": 4096,
            "temperature": 0.7,
        },
        "fireworks-default": {
            "model": "accounts/fireworks/models/qwen3p5-397b-a17b",
            "backend": QwenBackend.FIREWORKS,
            "max_tokens": 4096,
            "temperature": 0.7,
        },
        "fireworks-qwen-7b": {
            "model": "accounts/fireworks/models/qwen2p5-7b-instruct",
            "backend": QwenBackend.FIREWORKS,
            "max_tokens": 4096,
            "temperature": 0.7,
        },
        "fireworks-qwen-14b": {
            "model": "accounts/fireworks/models/qwen2p5-14b-instruct",
            "backend": QwenBackend.FIREWORKS,
            "max_tokens": 4096,
            "temperature": 0.7,
        },
        "fireworks-qwen-32b": {
            "model": "accounts/fireworks/models/qwen2p5-32b-instruct",
            "backend": QwenBackend.FIREWORKS,
            "max_tokens": 4096,
            "temperature": 0.7,
        },
        "fireworks-qwen-72b": {
            "model": "accounts/fireworks/models/qwen2p5-72b-instruct",
            "backend": QwenBackend.FIREWORKS,
            "max_tokens": 4096,
            "temperature": 0.7,
        },
    }

    @classmethod
    def get_profile(cls, name: str) -> dict[str, Any]:
        """Get a model profile by name."""
        return cls.PROFILES.get(name, cls.PROFILES["local-medium"])

    @classmethod
    def list_profiles(cls) -> list[str]:
        """List available profile names."""
        return list(cls.PROFILES.keys())


class Qwen35Adapter(BaseProviderAdapter):
    """Provider adapter for Qwen 3.5 via OpenAI-compatible endpoint.

    Supports multiple backends: OpenRouter, Fireworks, local, and Qwen API.
    """

    SYSTEM_PROMPT = """You are a helpful AI assistant that can control a computer.
You have access to a 'computer' tool that allows you to interact with the screen.
Available actions: screenshot, click, double_click, move, drag, scroll, type, key_press, wait.

When you see a screenshot, analyze it and decide what action to take next.
Be precise with coordinates - the image resolution is 1280x720.
When you've completed the task, say 'DONE' and summarize what you accomplished."""

    def __init__(self, config: ProviderConfig) -> None:
        if config.provider != ProviderKind.QWEN:
            raise ProviderError("Qwen35Adapter requires Qwen provider config")

        super().__init__(config)

        # Determine backend from config
        self.backend = config.extra.get("backend", QwenBackend.QWEN_API)
        backend_config = QwenBackendConfig.get_config(self.backend)

        # Get API key - check backend-specific env var first, then fall back
        api_key_env = config.extra.get("api_key_env") or backend_config.get(
            "api_key_env", "QWEN_API_KEY"
        )
        api_key = self._get_env_var(api_key_env) or self.get_api_key()

        if not api_key and self.backend != QwenBackend.LOCAL:
            raise ProviderError(f"{api_key_env} required for {self.backend} backend")

        self.api_key = api_key or "sk-dummy"
        self.api_base = config.api_base or backend_config.get("api_base", "https://api.qwen.ai/v1")
        self.extra_headers = backend_config.get("extra_headers", {})

        # Model name handling - apply prefix if needed
        model = config.model or "Qwen/Qwen3.5-35B-A3B"
        model_prefix = backend_config.get("model_prefix", "")
        if model_prefix and not model.startswith(model_prefix):
            self.model = f"{model_prefix}{model}"
        else:
            self.model = model

        self.max_tokens = config.extra.get("max_tokens", 4096)
        self.temperature = config.extra.get("temperature", 0.7)

        # Cost tracking
        self.cost_per_prompt_token = backend_config.get("cost_per_prompt_token", 0.000001)
        self.cost_per_completion_token = backend_config.get("cost_per_completion_token", 0.000002)

        self._client = httpx.AsyncClient(timeout=300.0)

    def _get_env_var(self, name: str) -> str | None:
        """Get environment variable value."""
        import os

        return os.environ.get(name)

    async def start_run(self, request: ProviderRunRequest) -> dict[str, Any]:
        """Start a new run with Qwen 3.5."""
        messages: list[dict[str, Any]] = []

        system_prompt = request.system_prompt or self.SYSTEM_PROMPT
        messages.append({"role": "system", "content": system_prompt})

        user_content: list[dict[str, Any]] = [{"type": "text", "text": request.task}]

        if request.initial_screenshot:
            user_content.append(
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/png;base64,{request.initial_screenshot}",
                    },
                }
            )

        messages.append({"role": "user", "content": user_content})

        return {
            "messages": messages,
            "step_count": 0,
            "max_steps": request.max_steps,
            "run_id": None,
            "backend": self.backend,
        }

    async def next_step(
        self, state: dict[str, Any], observations: list[ComputerObservation]
    ) -> ProviderStepResult:
        """Process observations and get next actions from Qwen 3.5."""
        start_time = time.time()

        messages = state.get("messages", [])

        for obs in observations:
            if isinstance(obs, ScreenshotObservation) and obs.image_base64:
                messages.append(
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/png;base64,{obs.image_base64}",
                                },
                            }
                        ],
                    }
                )
            elif hasattr(obs, "message") and obs.message:
                messages.append({"role": "user", "content": obs.message})

        try:
            response = await self._call_api(messages)

            state["messages"] = messages
            state["step_count"] = state.get("step_count", 0) + 1

            usage = self._extract_usage(response, start_time)
            actions, text, is_complete = self._parse_response(response)

            return ProviderStepResult(
                actions=actions,
                text=text,
                is_complete=is_complete,
                usage=usage,
                raw_response=response,
                needs_screenshot=any(a.action != ActionType.SCREENSHOT for a in actions)
                if actions
                else True,
            )

        except Exception as e:
            return ProviderStepResult(
                error=str(e),
                is_complete=True,
            )

    async def _call_api(self, messages: list[dict[str, Any]]) -> dict[str, Any]:
        """Make API call to the configured backend."""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            **self.extra_headers,
        }

        payload = {
            "model": self.model,
            "messages": messages,
            "tools": [QwenToolRenderer.render_computer_tool()],
            "tool_choice": "auto",
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
        }

        response = await self._client.post(
            f"{self.api_base}/chat/completions",
            headers=headers,
            json=payload,
        )

        response.raise_for_status()
        return response.json()  # type: ignore[no-any-return]

    def _extract_usage(self, response: dict[str, Any], start_time: float) -> UsageMetrics:
        """Extract usage metrics from response."""
        usage_data = response.get("usage", {})

        prompt_tokens = usage_data.get("prompt_tokens", 0)
        completion_tokens = usage_data.get("completion_tokens", 0)
        total_tokens = usage_data.get("total_tokens", prompt_tokens + completion_tokens)

        cost = self._calculate_cost(prompt_tokens, completion_tokens)

        return UsageMetrics(
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            cost=cost,
            latency_ms=(time.time() - start_time) * 1000,
        )

    def _calculate_cost(self, prompt_tokens: int, completion_tokens: int) -> float:
        """Calculate cost based on backend pricing."""
        prompt_cost = prompt_tokens * self.cost_per_prompt_token
        completion_cost = completion_tokens * self.cost_per_completion_token
        return float(prompt_cost + completion_cost)

    def _parse_response(
        self, response: dict[str, Any]
    ) -> tuple[list[ComputerAction], str | None, bool]:
        """Parse response into actions, text, and completion status."""
        actions: list[ComputerAction] = []
        text: str | None = None
        is_complete = False

        choices = response.get("choices", [])
        if not choices:
            return actions, text, is_complete

        message = choices[0].get("message", {})

        content = message.get("content")
        if content:
            text = content
            if "DONE" in text.upper() or "COMPLETE" in text.upper():
                is_complete = True

        tool_calls = message.get("tool_calls", [])
        for tool_call in tool_calls:
            action = QwenToolCallParser.parse_tool_call(tool_call)
            if action:
                actions.append(action)

        return actions, text, is_complete

    async def close(self, state: dict[str, Any]) -> None:
        """Close the adapter."""
        await self._client.aclose()


async def create_qwen35_adapter(config: ProviderConfig | None = None) -> Qwen35Adapter:
    """Create a Qwen 3.5 adapter."""
    if config is None:
        config = ProviderConfig(
            provider=ProviderKind.QWEN,
            model="Qwen/Qwen3.5-35B-A3B",
            api_key_env="QWEN_API_KEY",
        )
    return Qwen35Adapter(config)


def create_qwen_adapter_for_backend(
    backend: str,
    model: str | None = None,
    api_key: str | None = None,
    api_base: str | None = None,
    **extra: Any,
) -> ProviderConfig:
    """Helper to create a ProviderConfig for a specific backend.

    Usage:
        # OpenRouter
        config = create_qwen_adapter_for_backend("openrouter", "qwen/qwen-2.5-32b-instruct")

        # Fireworks
        config = create_qwen_adapter_for_backend("fireworks", "qwen2p5-32b-instruct")

        # Local
        config = create_qwen_adapter_for_backend("local", "Qwen/Qwen3.5-32B", api_base="http://localhost:8000/v1")
    """
    backend_config = QwenBackendConfig.get_config(backend)

    api_key_env = backend_config.get("api_key_env", "QWEN_API_KEY")
    default_api_base = backend_config.get("api_base", "https://api.qwen.ai/v1")
    model_prefix = backend_config.get("model_prefix", "")

    # Use provided api_base or default from backend config
    final_api_base = api_base if api_base is not None else default_api_base

    if model and model_prefix and not model.startswith(model_prefix):
        full_model = f"{model_prefix}{model}"
    else:
        full_model = model or "Qwen/Qwen3.5-35B-A3B"

    return ProviderConfig(
        provider=ProviderKind.QWEN,
        model=full_model,
        api_base=final_api_base,
        api_key_env=api_key_env,
        extra={
            "backend": backend,
            **extra,
        },
    )
