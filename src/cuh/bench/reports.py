"""Benchmark reports and result aggregation."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel


class TaskResult(BaseModel):
    """Result of a single task execution."""

    task_id: str
    provider: str
    model: str
    status: str
    steps: int = 0
    duration_seconds: float = 0.0
    cost: float | None = None
    tokens_prompt: int = 0
    tokens_completion: int = 0
    tokens_total: int = 0
    latency_avg_ms: float | None = None
    error: str | None = None
    run_id: str | None = None
    metadata: dict[str, Any] = {}


class ProviderSummary(BaseModel):
    """Summary statistics for a provider."""

    provider: str
    model: str
    total_tasks: int = 0
    successful: int = 0
    failed: int = 0
    errors: int = 0
    total_steps: int = 0
    avg_steps: float = 0.0
    total_duration: float = 0.0
    avg_duration: float = 0.0
    total_cost: float = 0.0
    avg_cost: float = 0.0
    total_tokens: int = 0
    avg_latency_ms: float = 0.0
    success_rate: float = 0.0


class BenchmarkReport(BaseModel):
    """Full benchmark report."""

    suite_name: str
    providers: list[str]
    results: list[TaskResult]
    generated_at: datetime
    summaries: list[ProviderSummary] = []

    def __init__(self, **data: Any) -> None:
        super().__init__(**data)
        if not self.summaries:
            self.summaries = self._compute_summaries()

    def _compute_summaries(self) -> list[ProviderSummary]:
        """Compute summary statistics for each provider."""
        summaries = []

        for provider_name in self.providers:
            provider_results = [r for r in self.results if r.provider == provider_name]

            if not provider_results:
                continue

            successful = sum(1 for r in provider_results if r.status == "completed")
            failed = sum(1 for r in provider_results if r.status == "failed")
            errors = sum(1 for r in provider_results if r.status == "error")
            total_tasks = len(provider_results)

            total_steps = sum(r.steps for r in provider_results)
            total_duration = sum(r.duration_seconds for r in provider_results)
            total_cost = sum(r.cost or 0 for r in provider_results)
            total_tokens = sum(r.tokens_prompt + r.tokens_completion for r in provider_results)

            latencies = [r.latency_avg_ms for r in provider_results if r.latency_avg_ms]

            summary = ProviderSummary(
                provider=provider_name,
                model=provider_results[0].model if provider_results else "",
                total_tasks=total_tasks,
                successful=successful,
                failed=failed,
                errors=errors,
                total_steps=total_steps,
                avg_steps=total_steps / total_tasks if total_tasks > 0 else 0,
                total_duration=total_duration,
                avg_duration=total_duration / total_tasks if total_tasks > 0 else 0,
                total_cost=total_cost,
                avg_cost=total_cost / total_tasks if total_tasks > 0 else 0,
                total_tokens=total_tokens,
                avg_latency_ms=sum(latencies) / len(latencies) if latencies else 0,
                success_rate=successful / total_tasks * 100 if total_tasks > 0 else 0,
            )
            summaries.append(summary)

        return summaries

    def get_provider_summary(self, provider: str) -> ProviderSummary | None:
        """Get summary for a specific provider."""
        for summary in self.summaries:
            if summary.provider == provider:
                return summary
        return None

    def to_markdown(self) -> str:
        """Generate a Markdown report."""
        lines = [
            f"# Benchmark Report: {self.suite_name}",
            "",
            f"**Generated**: {self.generated_at.strftime('%Y-%m-%d %H:%M:%S UTC')}",
            f"**Providers**: {', '.join(self.providers)}",
            "",
            "## Summary",
            "",
            "| Provider | Model | Success Rate | Avg Steps | Avg Duration | Total Cost |",
            "|----------|-------|--------------|-----------|--------------|------------|",
        ]

        for summary in self.summaries:
            lines.append(
                f"| {summary.provider} | {summary.model} | "
                f"{summary.success_rate:.1f}% | {summary.avg_steps:.1f} | "
                f"{summary.avg_duration:.1f}s | ${summary.total_cost:.4f} |"
            )

        lines.extend(
            [
                "",
                "## Detailed Results",
                "",
            ]
        )

        for result in self.results:
            status_emoji = "✅" if result.status == "completed" else "❌"
            lines.append(f"### {result.task_id} ({result.provider}) {status_emoji}")
            lines.append(f"- **Status**: {result.status}")
            lines.append(f"- **Steps**: {result.steps}")
            lines.append(f"- **Duration**: {result.duration_seconds:.2f}s")
            if result.cost:
                lines.append(f"- **Cost**: ${result.cost:.4f}")
            if result.error:
                lines.append(f"- **Error**: {result.error}")
            lines.append("")

        return "\n".join(lines)

    def to_json(self) -> dict[str, Any]:
        """Export as JSON-serializable dict."""
        return self.model_dump(mode="json")
