# References

This document lists external projects and documentation referenced in CUH development.

## OpenAI

- [GPT-5.4 Model Docs](https://developers.openai.com/api/docs/models/gpt-5.4)
- [Computer Use Guide](https://developers.openai.com/api/docs/guides/tools-computer-use/)
- [GPT-5.4 Announcement](https://openai.com/index/introducing-gpt-5-4/)
- [GPT-5.4 CUA Sample App](https://github.com/openai/openai-cua-sample-app)

## Cua

- [Monorepo](https://github.com/trycua/cua)
- [Main Docs](https://cua.ai/docs/cua)
- [Using the Agent SDK](https://cua.ai/docs/cua/guide/get-started/using-agent-sdk)
- [Vision Language Models](https://cua.ai/docs/cua/guide/fundamentals/vlms)
- [Browser Tool](https://cua.ai/docs/cua/guide/fundamentals/browser-tool)
- [Local Computer Server](https://cua.ai/docs/cua/guide/advanced/local-computer-server)
- [Windows App behind VPN](https://cua.ai/docs/cua/examples/platform-specific/windows-app-behind-vpn)
- [Custom Tools](https://cua.ai/docs/cua/guide/advanced/custom-tools)
- [Interactive Shell](https://cua.ai/docs/cua/guide/advanced/interactive-shell)
- [Trajectories](https://cua.ai/docs/cua/guide/advanced/trajectories)
- [Demonstration-Guided Skills](https://cua.ai/docs/cua/guide/advanced/demonstration-guided-skills)
- [VNC Recorder](https://cua.ai/docs/cua/guide/advanced/vnc-recorder)
- [Telemetry](https://cua.ai/docs/cua/guide/advanced/telemetry)
- [OSWorld-Verified](https://cua.ai/docs/cua/guide/integrations/benchmarks/osworld-verified)

## OpenHands

- [SDK Repo](https://github.com/OpenHands/software-agent-sdk)
- [SDK Docs](https://docs.openhands.dev/sdk)
- [Getting Started](https://docs.openhands.dev/sdk/getting-started)
- [Architecture Overview](https://docs.openhands.dev/sdk/arch/overview)
- [SDK Package](https://docs.openhands.dev/sdk/arch/sdk)
- [Workspace Architecture](https://docs.openhands.dev/sdk/arch/workspace)
- [Agent Server Architecture](https://docs.openhands.dev/sdk/arch/agent-server)
- [Custom Tools](https://docs.openhands.dev/sdk/guides/custom-tools)
- [Metrics Tracking](https://docs.openhands.dev/sdk/guides/metrics)
- [Observability and Tracing](https://docs.openhands.dev/sdk/guides/observability)
- [Local Agent Server](https://docs.openhands.dev/sdk/guides/agent-server/local-server)
- [Context Condenser](https://docs.openhands.dev/sdk/guides/context-condenser)
- [Agent Skills](https://docs.openhands.dev/sdk/guides/skill)

## Qwen

- [Qwen 3.5 Repo](https://github.com/QwenLM/Qwen3.5)
- [Function Calling Docs](https://qwen.readthedocs.io/en/latest/framework/function_call.html)
- [Qwen API Platform](https://qwen.ai/apiplatform)
- [Qwen Blog](https://qwen.ai/blog?id=qwen3.5)
- [Qwen Agent](https://qwenlm.github.io/)

## Benchmarks

- [OSWorld Project](https://os-world.github.io/)
- [OSWorld Repo](https://github.com/xlang-ai/OSWorld)
- [OSWorld-G Repo](https://github.com/xlang-ai/OSWorld-G)
- [OpenCUA Repo](https://github.com/xlang-ai/OpenCUA)

## Attribution

CUH is an independent project that uses these projects as dependencies or references:

- **Cua**: Used as a dependency for `cua-computer` and `cua-computer-server`
- **OpenAI Python SDK**: Used as a dependency for GPT-5.4 integration
- **Pydantic**: Used for data validation
- **FastAPI**: Used for API server

No code was copied from these projects without attribution. All implementation is derived from documented APIs and public specifications.