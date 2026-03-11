"""Benchmark runner for CUH.

Executes task suites across multiple providers and aggregates results.
"""

import time
from datetime import UTC, datetime
from pathlib import Path

import yaml

from cuh.backends.base import BaseBackend
from cuh.bench.reports import BenchmarkReport, TaskResult
from cuh.bench.tasks import TaskDefinition, TaskSuite
from cuh.config.loader import ConfigLoader
from cuh.core.models import ProviderConfig, ProviderKind, RunConfig, TargetConfig
from cuh.providers.base import BaseProviderAdapter
from cuh.providers.openai_gpt54 import create_gpt54_adapter
from cuh.providers.qwen35 import create_qwen35_adapter
from cuh.runtime.artifact_store import ArtifactStore
from cuh.runtime.event_bus import EventBus
from cuh.runtime.orchestrator import Orchestrator


class BenchmarkRunner:
    """Runner for benchmark task suites."""

    def __init__(
        self,
        artifact_store: ArtifactStore | None = None,
        event_bus: EventBus | None = None,
    ) -> None:
        self.artifact_store = artifact_store or ArtifactStore()
        self.event_bus = event_bus or EventBus()
        self._results: dict[str, TaskResult] = {}

    async def run_suite(
        self,
        suite: TaskSuite,
        providers: list[str],
        target_config: TargetConfig,
        provider_configs: dict[str, ProviderConfig] | None = None,
        parallel: bool = False,
    ) -> BenchmarkReport:
        """Run a task suite across multiple providers."""
        config_loader = ConfigLoader()
        provider_configs = provider_configs or {}

        for provider_name in providers:
            if provider_name not in provider_configs:
                provider_configs[provider_name] = config_loader.load_provider(provider_name)

        results: list[TaskResult] = []

        for task in suite.tasks:
            for provider_name in providers:
                provider_config = provider_configs[provider_name]

                if parallel:
                    result = await self._run_task_parallel(
                        task, provider_name, provider_config, target_config
                    )
                else:
                    result = await self._run_task(
                        task, provider_name, provider_config, target_config
                    )
                results.append(result)

        return BenchmarkReport(
            suite_name=suite.name,
            providers=providers,
            results=results,
            generated_at=datetime.now(UTC),
        )

    async def _run_task(
        self,
        task: TaskDefinition,
        provider_name: str,
        provider_config: ProviderConfig,
        target_config: TargetConfig,
    ) -> TaskResult:
        """Run a single task with a provider."""
        start_time = time.time()

        try:
            provider = await self._create_provider(provider_name, provider_config)
            backend = await self._create_backend(target_config)

            run_config = RunConfig(
                provider=ProviderKind(provider_name),
                model=provider_config.model,
                target=target_config.name,
                task=task.prompt,
                max_steps=task.max_steps,
                timeout_seconds=task.timeout,
            )

            orchestrator = Orchestrator(
                backend=backend,
                provider=provider,
                event_bus=self.event_bus,
                artifact_store=self.artifact_store,
            )

            session = await orchestrator.run(run_config)

            duration = time.time() - start_time

            result = TaskResult(
                task_id=task.id,
                provider=provider_name,
                model=provider_config.model,
                status="completed" if session.state.value == "completed" else "failed",
                steps=session.total_steps,
                duration_seconds=duration,
                cost=session.total_usage.cost,
                tokens_prompt=session.total_usage.prompt_tokens,
                tokens_completion=session.total_usage.completion_tokens,
                latency_avg_ms=session.total_usage.latency_ms,
                error=session.error,
                run_id=session.run_id,
            )

            await backend.disconnect()
            await provider.close({})

            return result

        except Exception as e:
            duration = time.time() - start_time
            return TaskResult(
                task_id=task.id,
                provider=provider_name,
                model=provider_config.model,
                status="error",
                steps=0,
                duration_seconds=duration,
                error=str(e),
            )

    async def _run_task_parallel(
        self,
        task: TaskDefinition,
        provider_name: str,
        provider_config: ProviderConfig,
        target_config: TargetConfig,
    ) -> TaskResult:
        """Run task in parallel (for future multi-target support)."""
        return await self._run_task(task, provider_name, provider_config, target_config)

    async def _create_provider(
        self, provider_name: str, config: ProviderConfig
    ) -> BaseProviderAdapter:
        """Create a provider adapter."""
        if provider_name == "openai":
            return await create_gpt54_adapter(config)
        if provider_name == "qwen":
            return await create_qwen35_adapter(config)
        raise ValueError(f"Unknown provider: {provider_name}")

    async def _create_backend(self, config: TargetConfig) -> BaseBackend:
        """Create a backend."""
        from cuh.backends.cua_backend import create_backend

        return await create_backend(config)

    def load_suite(self, path: Path) -> TaskSuite:
        """Load a task suite from YAML."""
        with path.open() as f:
            data = yaml.safe_load(f)

        tasks = []
        for task_data in data.get("tasks", []):
            tasks.append(
                TaskDefinition(
                    id=task_data.get("id", "unknown"),
                    prompt=task_data.get("prompt", ""),
                    timeout=task_data.get("timeout", 300.0),
                    max_steps=task_data.get("max_steps", 100),
                    success_heuristic=task_data.get("success_heuristic"),
                    target_requirements=task_data.get("target_requirements", []),
                    policy_requirements=task_data.get("policy_requirements", {}),
                    metadata=task_data.get("metadata", {}),
                )
            )

        return TaskSuite(
            name=data.get("name", "unnamed"),
            description=data.get("description"),
            tasks=tasks,
            default_timeout=data.get("default_timeout", 300.0),
            default_max_steps=data.get("default_max_steps", 100),
            metadata=data.get("metadata", {}),
        )


async def run_benchmark(
    suite_path: Path,
    providers: list[str],
    target_config: TargetConfig,
    provider_configs: dict[str, ProviderConfig] | None = None,
) -> BenchmarkReport:
    """Run a benchmark suite."""
    runner = BenchmarkRunner()
    suite = runner.load_suite(suite_path)
    return await runner.run_suite(suite, providers, target_config, provider_configs)
