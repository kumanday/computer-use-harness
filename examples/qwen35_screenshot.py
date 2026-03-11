"""Example: Basic Qwen 3.5 screenshot task."""

import asyncio

from cuh.backends.cua_backend import create_backend
from cuh.core.models import ProviderConfig, ProviderKind, RunConfig, TargetConfig, TargetKind
from cuh.providers.qwen35 import create_qwen35_adapter
from cuh.runtime.artifact_store import ArtifactStore
from cuh.runtime.event_bus import EventBus, create_stdout_handler
from cuh.runtime.orchestrator import Orchestrator


async def main() -> None:
    # Configure the target (local host computer-server)
    target_config = TargetConfig(
        kind=TargetKind.CUA_HOST,
        name="local-host",
        api_host="127.0.0.1",
        api_port=8000,
        os_type="linux",
    )

    # Create the backend (connects to Cua computer-server)
    print("Connecting to backend...")
    backend = await create_backend(target_config)
    print(f"Connected! Screen geometry: {backend.geometry}")

    # Configure Qwen 3.5 provider
    # Options:
    # - Use a local serving endpoint (vLLM, SGLang, Transformers)
    # - Use the Qwen API platform
    provider_config = ProviderConfig(
        provider=ProviderKind.QWEN,
        model="Qwen/Qwen3.5-35B-A3B",
        api_base="http://localhost:8000/v1",  # Local serving endpoint
        api_key_env="QWEN_API_KEY",
        extra={
            "max_tokens": 4096,
            "temperature": 0.7,
        },
    )

    # Create the Qwen 3.5 adapter
    provider = await create_qwen35_adapter(provider_config)

    # Set up event bus for logging
    event_bus = EventBus()
    event_bus.subscribe(None, create_stdout_handler())

    # Set up artifact store for replay
    artifact_store = ArtifactStore()

    # Create the orchestrator
    orchestrator = Orchestrator(
        backend=backend,
        provider=provider,
        event_bus=event_bus,
        artifact_store=artifact_store,
    )

    # Define the run configuration
    run_config = RunConfig(
        provider=ProviderKind.QWEN,
        model="Qwen/Qwen3.5-35B-A3B",
        target="local-host",
        task="Take a screenshot and describe what you see on the screen.",
        max_steps=10,
    )

    # Execute the run
    print("\nStarting run...")
    session = await orchestrator.run(run_config)

    # Print results
    print(f"\nRun completed!")
    print(f"  Status: {session.state.value}")
    print(f"  Steps: {session.total_steps}")
    print(f"  Duration: {session.duration_seconds:.2f}s")
    if session.total_usage.cost:
        print(f"  Cost: ${session.total_usage.cost:.4f}")

    # Disconnect from backend
    await backend.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
