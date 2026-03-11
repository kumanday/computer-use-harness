"""CLI for CUH."""

import asyncio
import contextlib
import json
from pathlib import Path
from typing import Any

import click
from rich.console import Console
from rich.table import Table

from cuh import __version__
from cuh.backends.cua_backend import create_backend
from cuh.bench import BenchmarkRunner
from cuh.config.loader import ConfigLoader, Settings, get_settings
from cuh.core.models import ProviderKind, RunConfig, TargetConfig
from cuh.core.policy import PolicyConfig, PolicyEngine
from cuh.providers.openai_gpt54 import create_gpt54_adapter
from cuh.providers.qwen35 import create_qwen35_adapter
from cuh.runtime.artifact_store import ArtifactStore
from cuh.runtime.event_bus import EventBus, create_stdout_handler
from cuh.runtime.orchestrator import Orchestrator

console = Console()


@click.group()
@click.version_option(version=__version__)
def main() -> None:
    """Computer Use Harness (CUH) - Desktop and browser automation for AI agents."""


@main.command()
@click.option("--provider", "-p", default="openai", help="Provider to use (openai, qwen)")
@click.option("--model", "-m", default="gpt-5.4", help="Model to use")
@click.option("--target", "-t", default="host", help="Target configuration name")
@click.option("--task", "-k", required=True, help="Task to execute")
@click.option("--max-steps", "-s", default=100, help="Maximum number of steps")
@click.option("--timeout", "-o", default=300.0, help="Timeout in seconds")
@click.option("--config-dir", "-c", type=click.Path(exists=True), help="Configuration directory")
@click.option("--verbose", "-v", is_flag=True, help="Enable verbose output")
@click.option("--dry-run", is_flag=True, help="Show configuration without running")
@click.option("--no-policy", is_flag=True, help="Disable policy checks for actions")
def run(
    provider: str,
    model: str,
    target: str,
    task: str,
    max_steps: int,
    timeout: float,
    config_dir: str | None,
    verbose: bool,
    dry_run: bool,
    no_policy: bool,
) -> None:
    """Run a task with CUH."""
    settings = get_settings()
    if config_dir:
        settings.configs_dir = Path(config_dir)

    loader = ConfigLoader(settings.configs_dir)

    target_config = loader.load_target(target)
    provider_config = loader.load_provider(provider)

    run_config = RunConfig(
        provider=ProviderKind(provider),
        model=model or provider_config.model,
        target=target,
        task=task,
        max_steps=max_steps,
        timeout_seconds=timeout,
    )

    if dry_run:
        console.print("[bold]Configuration:[/]")
        console.print(f"  Provider: {run_config.provider.value}")
        console.print(f"  Model: {run_config.model}")
        console.print(f"  Target: {run_config.target}")
        console.print(f"  Task: {run_config.task}")
        console.print(f"  Max steps: {run_config.max_steps}")
        console.print(f"  Timeout: {run_config.timeout_seconds}s")
        console.print(f"  Policy: {'disabled' if no_policy else 'enabled'}")
        return

    asyncio.run(
        _run_async(run_config, target_config, provider_config, settings, verbose, no_policy)
    )


async def _run_async(
    run_config: RunConfig,
    target_config: TargetConfig,
    provider_config: Any,
    settings: Settings,
    verbose: bool,
    no_policy: bool,
) -> None:
    """Execute the run asynchronously."""
    event_bus = EventBus()
    stdout_handler = create_stdout_handler()
    event_bus.subscribe(None, stdout_handler)

    artifact_store = ArtifactStore(settings.runs_dir)
    policy_engine = PolicyEngine(PolicyConfig(enabled=not no_policy))

    console.print("[bold blue]Starting CUH run[/]")
    console.print(f"  Target: {target_config.name} ({target_config.kind.value})")
    console.print(f"  Provider: {run_config.provider.value}")
    console.print(f"  Model: {run_config.model}")
    console.print()

    try:
        console.print("[dim]Connecting to backend...[/]")
        backend = await create_backend(target_config)

        console.print("[dim]Initializing provider...[/]")
        provider_adapter: Any
        if run_config.provider == ProviderKind.OPENAI:
            provider_adapter = await create_gpt54_adapter(provider_config)
        elif run_config.provider == ProviderKind.QWEN:
            provider_adapter = await create_qwen35_adapter(provider_config)
        else:
            raise click.ClickException(f"Provider {run_config.provider.value} not yet supported")

        console.print("[dim]Starting run...[/]")
        orchestrator = Orchestrator(
            backend=backend,
            provider=provider_adapter,
            event_bus=event_bus,
            artifact_store=artifact_store,
            policy_engine=policy_engine,
            settings=settings,
        )

        session = await orchestrator.run(run_config)

        console.print()
        if session.state.value == "completed":
            console.print("[bold green]Run completed successfully[/]")
        else:
            console.print(f"[bold red]Run failed: {session.error or 'Unknown error'}[/]")

        console.print(f"  Steps: {session.total_steps}")
        console.print(f"  Duration: {session.duration_seconds:.2f}s")
        if session.total_usage.cost:
            console.print(f"  Cost: ${session.total_usage.cost:.4f}")
        console.print(f"  Run directory: {session.run_directory}")

    except Exception as e:
        console.print(f"[bold red]Error: {e}[/]")
        raise click.ClickException(str(e)) from None
    finally:
        with contextlib.suppress(Exception):
            await backend.disconnect()


@main.command("runs")
@click.argument("run_id", required=False)
@click.option("--limit", "-l", default=10, help="Number of runs to show")
def runs(run_id: str | None, limit: int) -> None:
    """List runs or show run details."""
    settings = get_settings()
    artifact_store = ArtifactStore(settings.runs_dir)

    if run_id:
        _show_run(artifact_store, run_id)
    else:
        _list_runs(artifact_store, limit)


def _list_runs(artifact_store: ArtifactStore, limit: int) -> None:
    """List recent runs."""
    run_dirs = artifact_store.list_runs()[:limit]

    if not run_dirs:
        console.print("[dim]No runs found[/]")
        return

    table = Table(title="Recent Runs")
    table.add_column("Run ID", style="cyan")
    table.add_column("Status", style="bold")
    table.add_column("Provider", style="blue")
    table.add_column("Steps", justify="right")
    table.add_column("Duration", justify="right")
    table.add_column("Created", style="dim")

    for run_dir in run_dirs:
        metadata = artifact_store.load_run_metadata(run_dir)
        if metadata:
            status_style = "green" if metadata.state.value == "completed" else "red"
            duration = (
                f"{(metadata.completed_at or metadata.created_at).timestamp() - metadata.created_at.timestamp():.1f}s"
                if metadata.completed_at
                else "-"
            )
            table.add_row(
                run_dir.name,
                f"[{status_style}]{metadata.state.value}[/{status_style}]",
                metadata.provider,
                str(metadata.total_steps),
                duration,
                metadata.created_at.strftime("%Y-%m-%d %H:%M"),
            )

    console.print(table)


def _show_run(artifact_store: ArtifactStore, run_id: str) -> None:
    """Show details of a specific run."""
    run_dir = artifact_store.runs_dir / run_id
    if not run_dir.exists():
        matches = list(artifact_store.runs_dir.glob(f"*{run_id}*"))
        if matches:
            run_dir = matches[0]
        else:
            console.print(f"[red]Run not found: {run_id}[/]")
            return

    metadata = artifact_store.load_run_metadata(run_dir)
    if not metadata:
        console.print(f"[red]No metadata found for run: {run_id}[/]")
        return

    console.print(f"[bold]Run: {run_dir.name}[/]")
    console.print(f"  ID: {metadata.run_id}")
    console.print(f"  Status: {metadata.state.value}")
    console.print(f"  Provider: {metadata.provider}")
    console.print(f"  Model: {metadata.model}")
    console.print(f"  Target: {metadata.target}")
    console.print(f"  Task: {metadata.task}")
    console.print()
    console.print(f"  Created: {metadata.created_at}")
    if metadata.started_at:
        console.print(f"  Started: {metadata.started_at}")
    if metadata.completed_at:
        console.print(f"  Completed: {metadata.completed_at}")
    console.print()
    console.print(f"  Steps: {metadata.total_steps}")
    console.print(f"  Successful: {metadata.successful_actions}")
    console.print(f"  Failed: {metadata.failed_actions}")
    if metadata.total_cost:
        console.print(f"  Cost: ${metadata.total_cost:.4f}")
    if metadata.error_message:
        console.print(f"  Error: {metadata.error_message}")


@main.command()
@click.argument("target_name", required=False)
def targets(target_name: str | None) -> None:
    """List or check target configurations."""
    settings = get_settings()
    loader = ConfigLoader(settings.configs_dir)

    if target_name:
        config = loader.load_target(target_name)
        console.print(f"[bold]Target: {config.name}[/]")
        console.print(f"  Kind: {config.kind.value}")
        console.print(f"  Host: {config.api_host}")
        console.print(f"  Port: {config.api_port}")
        console.print(f"  OS: {config.os_type}")
    else:
        targets_dir = settings.configs_dir / "targets"
        if targets_dir.exists():
            table = Table(title="Targets")
            table.add_column("Name", style="cyan")
            table.add_column("Kind", style="blue")
            table.add_column("Host", style="dim")
            table.add_column("OS", style="dim")

            for config_file in targets_dir.glob("*.yaml"):
                name = config_file.stem
                config = loader.load_target(name)
                table.add_row(config.name, config.kind.value, config.api_host, config.os_type)

            console.print(table)
        else:
            console.print("[dim]No target configurations found[/]")


@main.group()
def bench() -> None:
    """Benchmark commands for CUH."""


@bench.command("run")
@click.option("--suite", "-s", required=True, help="Path to task suite YAML")
@click.option("--providers", "-p", default="openai,qwen", help="Comma-separated list of providers")
@click.option("--target", "-t", default="host", help="Target configuration name")
@click.option("--output", "-o", type=click.Path(), help="Output file for report (JSON or MD)")
@click.option(
    "--format",
    "-f",
    type=click.Choice(["json", "markdown", "both"]),
    default="markdown",
    help="Report format",
)
def bench_run(
    suite: str,
    providers: str,
    target: str,
    output: str | None,
    format: str,
) -> None:
    """Run a benchmark suite across providers."""
    settings = get_settings()
    loader = ConfigLoader(settings.configs_dir)

    suite_path = Path(suite)
    if not suite_path.exists():
        suite_path = settings.configs_dir / "task_suites" / f"{suite}.yaml"
        if not suite_path.exists():
            raise click.ClickException(f"Suite not found: {suite}")

    target_config = loader.load_target(target)
    provider_list = [p.strip() for p in providers.split(",")]

    provider_configs = {}
    for provider_name in provider_list:
        provider_configs[provider_name] = loader.load_provider(provider_name)

    console.print(f"[bold blue]Running benchmark: {suite_path.stem}[/]")
    console.print(f"  Target: {target_config.name}")
    console.print(f"  Providers: {', '.join(provider_list)}")
    console.print()

    asyncio.run(
        _run_benchmark(suite_path, provider_list, target_config, provider_configs, output, format)
    )


async def _run_benchmark(
    suite_path: Path,
    providers: list[str],
    target_config: TargetConfig,
    provider_configs: dict[str, Any],
    output: str | None,
    format: str,
) -> None:
    """Execute the benchmark asynchronously."""
    runner = BenchmarkRunner()
    suite_obj = runner.load_suite(suite_path)

    console.print(f"[dim]Running {len(suite_obj.tasks)} tasks...[/]")

    report = await runner.run_suite(suite_obj, providers, target_config, provider_configs)

    console.print()
    console.print("[bold]Benchmark Complete[/]")
    console.print()

    table = Table(title="Provider Comparison")
    table.add_column("Provider", style="cyan")
    table.add_column("Model", style="blue")
    table.add_column("Success Rate", justify="right")
    table.add_column("Avg Steps", justify="right")
    table.add_column("Avg Duration", justify="right")
    table.add_column("Total Cost", justify="right")

    for summary in report.summaries:
        table.add_row(
            summary.provider,
            summary.model,
            f"{summary.success_rate:.1f}%",
            f"{summary.avg_steps:.1f}",
            f"{summary.avg_duration:.1f}s",
            f"${summary.total_cost:.4f}",
        )

    console.print(table)

    if output:
        output_path = Path(output)
        if format in ("json", "both"):
            json_path = output_path.with_suffix(".json") if format == "both" else output_path
            with json_path.open("w") as f:
                json.dump(report.to_json(), f, indent=2, default=str)
            console.print(f"[dim]JSON report saved to: {json_path}[/]")

        if format in ("markdown", "both"):
            md_path = output_path.with_suffix(".md") if format == "both" else output_path
            with md_path.open("w") as f:
                f.write(report.to_markdown())
            console.print(f"[dim]Markdown report saved to: {md_path}[/]")


@bench.command("report")
@click.argument("report_file", type=click.Path(exists=True))
def bench_report(report_file: str) -> None:
    """Display a benchmark report."""
    report_path = Path(report_file)

    if report_path.suffix == ".json":
        with report_path.open() as f:
            data = json.load(f)
        console.print(f"[bold]Report: {report_path.stem}[/]")
        console.print(f"  Generated: {data.get('generated_at', 'unknown')}")
        console.print()

        table = Table(title="Results")
        table.add_column("Task", style="cyan")
        table.add_column("Provider", style="blue")
        table.add_column("Status", style="bold")
        table.add_column("Steps", justify="right")
        table.add_column("Duration", justify="right")

        for result in data.get("results", []):
            status_style = "green" if result.get("status") == "completed" else "red"
            table.add_row(
                result.get("task_id", ""),
                result.get("provider", ""),
                f"[{status_style}]{result.get('status', '')}[/{status_style}]",
                str(result.get("steps", 0)),
                f"{result.get('duration_seconds', 0):.1f}s",
            )

        console.print(table)
    else:
        with report_path.open() as f:
            console.print(f.read())


@main.command()
def profiles() -> None:
    """List available Qwen model profiles."""
    from cuh.providers.qwen35 import QwenModelProfile

    table = Table(title="Qwen Model Profiles")
    table.add_column("Profile", style="cyan")
    table.add_column("Model", style="blue")
    table.add_column("Max Tokens", justify="right")
    table.add_column("Temperature", justify="right")

    for name in QwenModelProfile.list_profiles():
        profile = QwenModelProfile.get_profile(name)
        table.add_row(
            name,
            profile.get("model", ""),
            str(profile.get("max_tokens", "")),
            str(profile.get("temperature", "")),
        )

    console.print(table)


if __name__ == "__main__":
    main()
