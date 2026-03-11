"""GPT-5.4 provider adapter for CUH.

Implements the provider adapter for OpenAI's GPT-5.4 model using the Responses API
with computer tool support.
"""

import time
from typing import Any

from openai import OpenAI

from cuh.core.actions import ActionType
from cuh.core.models import ProviderConfig, ProviderKind, UsageMetrics
from cuh.core.observations import ComputerObservation, ScreenshotObservation
from cuh.providers.base import (
    BaseProviderAdapter,
    ProviderError,
    ProviderRunRequest,
    ProviderStepResult,
)
from cuh.providers.mapping import ToolNameMapper


class GPT54Adapter(BaseProviderAdapter):
    """Provider adapter for OpenAI GPT-5.4."""

    SYSTEM_PROMPT = """You are a helpful AI assistant that can control a computer.
You can see screenshots and perform actions like clicking, typing, scrolling, and more.
Always analyze the current screen state before deciding on the next action.
Be precise with your clicks and typing. If something doesn't work, try a different approach.
When you've completed the task, say 'DONE' and provide a summary of what you accomplished."""

    def __init__(self, config: ProviderConfig) -> None:
        if config.provider != ProviderKind.OPENAI:
            raise ProviderError("GPT54Adapter requires OpenAI provider config")

        super().__init__(config)

        api_key = self.get_api_key()
        if not api_key:
            raise ProviderError("OPENAI_API_KEY not set")

        self.client = OpenAI(api_key=api_key, base_url=config.api_base)
        self.model = config.model or "gpt-5.4"
        self.reasoning_effort = config.reasoning_effort

    async def start_run(self, request: ProviderRunRequest) -> dict[str, Any]:
        """Start a new run with GPT-5.4."""
        system_prompt = request.system_prompt or self.SYSTEM_PROMPT

        content: list[dict[str, Any]] = [{"type": "input_text", "text": request.task}]

        if request.initial_screenshot:
            content.append(
                {
                    "type": "input_image",
                    "image_url": f"data:image/png;base64,{request.initial_screenshot}",
                }
            )

        return {
            "instructions": system_prompt,
            "input": [
                {
                    "type": "message",
                    "role": "user",
                    "content": content,
                }
            ],
            "step_count": 0,
            "max_steps": request.max_steps,
            "run_id": None,
            "pending_call_id": None,
        }

    async def next_step(
        self, state: dict[str, Any], observations: list[ComputerObservation]
    ) -> ProviderStepResult:
        """Process observations and get next actions from GPT-5.4."""
        start_time = time.time()

        input_items: list[dict[str, Any]] = []

        pending_call_id = state.get("pending_call_id")

        for obs in observations:
            if isinstance(obs, ScreenshotObservation) and obs.image_base64:
                if pending_call_id:
                    input_items.append(
                        {
                            "type": "computer_call_output",
                            "call_id": pending_call_id,
                            "output": {
                                "type": "computer_screenshot",
                                "image_url": f"data:image/png;base64,{obs.image_base64}",
                            },
                        }
                    )
                    pending_call_id = None
            elif hasattr(obs, "message") and obs.message:
                input_items.append(
                    {
                        "type": "message",
                        "role": "user",
                        "content": [{"type": "input_text", "text": obs.message}],
                    }
                )

        if not input_items:
            input_items = state.get("input", [])

        try:
            response = self.client.responses.create(
                model=self.model,
                instructions=state.get("instructions"),
                input=input_items,
                previous_response_id=state.get("run_id"),
                tools=[{"type": "computer"}],
                reasoning={"effort": self.reasoning_effort},  # type: ignore[call-overload]
                max_output_tokens=4096,
            )

            state["run_id"] = response.id
            state["step_count"] = state.get("step_count", 0) + 1

            usage_obj = getattr(response, "usage", None)
            if usage_obj and hasattr(usage_obj, "get"):
                usage_data = usage_obj
            elif usage_obj and hasattr(usage_obj, "prompt_tokens"):
                usage_data = {
                    "prompt_tokens": getattr(usage_obj, "prompt_tokens", 0),
                    "completion_tokens": getattr(usage_obj, "completion_tokens", 0),
                    "total_tokens": getattr(usage_obj, "total_tokens", 0),
                }
            else:
                usage_data = {}

            usage = UsageMetrics(
                prompt_tokens=usage_data.get("prompt_tokens", 0),
                completion_tokens=usage_data.get("completion_tokens", 0),
                total_tokens=usage_data.get("total_tokens", 0),
                cost=self._calculate_cost(response),
                latency_ms=self._calculate_latency(start_time),
            )

            actions = []
            text = None
            is_complete = False

            for output in response.output:
                if output.type == "message":
                    for content in output.content:
                        if content.type == "output_text":
                            text = content.text
                            if text and ("DONE" in text.upper() or "COMPLETE" in text.upper()):
                                is_complete = True
                elif output.type == "computer_call":
                    call_id = getattr(output, "call_id", None)
                    state["pending_call_id"] = call_id

                    actions_list = getattr(output, "actions", [])
                    for action_obj in actions_list:
                        action_data = (
                            action_obj.model_dump() if hasattr(action_obj, "model_dump") else {}
                        )
                        action = ToolNameMapper.parse_action(action_data)
                        actions.append(action)

            raw_response = response.model_dump() if hasattr(response, "model_dump") else {}

            return ProviderStepResult(
                actions=actions,
                text=text,
                is_complete=is_complete,
                usage=usage,
                raw_response=raw_response,
                needs_screenshot=any(a.action != ActionType.SCREENSHOT for a in actions)
                if actions
                else True,
            )

        except Exception as e:
            return ProviderStepResult(
                error=str(e),
                is_complete=True,
            )

    async def close(self, state: dict[str, Any]) -> None:
        """Close the run."""

    def _calculate_cost(self, response: Any) -> float:
        """Calculate the cost of the API call."""
        usage = getattr(response, "usage", None)
        if usage is None:
            return 0.0

        if hasattr(usage, "prompt_tokens"):
            prompt_tokens = getattr(usage, "prompt_tokens", 0) or 0
            completion_tokens = getattr(usage, "completion_tokens", 0) or 0
        elif hasattr(usage, "get"):
            prompt_tokens = usage.get("prompt_tokens", 0)
            completion_tokens = usage.get("completion_tokens", 0)
        else:
            return 0.0

        prompt_cost = prompt_tokens * 0.00003
        completion_cost = completion_tokens * 0.00006

        return prompt_cost + completion_cost


async def create_gpt54_adapter(config: ProviderConfig | None = None) -> GPT54Adapter:
    """Create a GPT-5.4 adapter."""
    if config is None:
        config = ProviderConfig(provider=ProviderKind.OPENAI, model="gpt-5.4")
    return GPT54Adapter(config)
