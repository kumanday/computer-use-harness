"""Tests for benchmark module."""

from datetime import UTC, datetime

from cuh.bench.reports import BenchmarkReport, ProviderSummary, TaskResult
from cuh.bench.tasks import TaskDefinition, TaskSuite


class TestTaskDefinition:
    def test_create(self) -> None:
        task = TaskDefinition(
            id="test_task",
            prompt="Take a screenshot",
        )
        assert task.id == "test_task"
        assert task.prompt == "Take a screenshot"
        assert task.timeout == 300.0
        assert task.max_steps == 100

    def test_create_with_options(self) -> None:
        task = TaskDefinition(
            id="test_task",
            prompt="Take a screenshot",
            timeout=60.0,
            max_steps=10,
            success_heuristic="screenshot captured",
            target_requirements=["browser_access"],
        )
        assert task.timeout == 60.0
        assert task.max_steps == 10
        assert task.success_heuristic == "screenshot captured"
        assert "browser_access" in task.target_requirements


class TestTaskSuite:
    def test_create(self) -> None:
        task1 = TaskDefinition(id="task1", prompt="Task 1")
        task2 = TaskDefinition(id="task2", prompt="Task 2")
        suite = TaskSuite(
            name="test_suite",
            tasks=[task1, task2],
        )
        assert suite.name == "test_suite"
        assert len(suite.tasks) == 2


class TestTaskResult:
    def test_create_success(self) -> None:
        result = TaskResult(
            task_id="test_task",
            provider="openai",
            model="gpt-5.4",
            status="completed",
            steps=5,
            duration_seconds=10.5,
            cost=0.05,
        )
        assert result.task_id == "test_task"
        assert result.status == "completed"
        assert result.steps == 5
        assert result.cost == 0.05

    def test_create_failure(self) -> None:
        result = TaskResult(
            task_id="test_task",
            provider="qwen",
            model="Qwen/Qwen3.5-35B-A3B",
            status="failed",
            error="Connection timeout",
        )
        assert result.status == "failed"
        assert result.error == "Connection timeout"


class TestProviderSummary:
    def test_create(self) -> None:
        summary = ProviderSummary(
            provider="openai",
            model="gpt-5.4",
            total_tasks=10,
            successful=8,
            failed=2,
            errors=0,
            total_steps=50,
            avg_steps=5.0,
            total_duration=100.0,
            avg_duration=10.0,
            total_cost=0.50,
            avg_cost=0.05,
            total_tokens=10000,
            avg_latency_ms=1500.0,
            success_rate=80.0,
        )
        assert summary.provider == "openai"
        assert summary.successful == 8
        assert summary.success_rate == 80.0


class TestBenchmarkReport:
    def test_create_and_compute_summaries(self) -> None:
        results = [
            TaskResult(
                task_id="task1",
                provider="openai",
                model="gpt-5.4",
                status="completed",
                steps=5,
                duration_seconds=10.0,
                cost=0.05,
            ),
            TaskResult(
                task_id="task2",
                provider="openai",
                model="gpt-5.4",
                status="failed",
                steps=3,
                duration_seconds=8.0,
                cost=0.03,
            ),
            TaskResult(
                task_id="task1",
                provider="qwen",
                model="Qwen/Qwen3.5-35B-A3B",
                status="completed",
                steps=7,
                duration_seconds=12.0,
                cost=0.01,
            ),
        ]

        report = BenchmarkReport(
            suite_name="test_suite",
            providers=["openai", "qwen"],
            results=results,
            generated_at=datetime.now(UTC),
        )

        assert len(report.summaries) == 2

        openai_summary = report.get_provider_summary("openai")
        assert openai_summary is not None
        assert openai_summary.total_tasks == 2
        assert openai_summary.successful == 1
        assert openai_summary.success_rate == 50.0

        qwen_summary = report.get_provider_summary("qwen")
        assert qwen_summary is not None
        assert qwen_summary.total_tasks == 1
        assert qwen_summary.success_rate == 100.0

    def test_to_markdown(self) -> None:
        results = [
            TaskResult(
                task_id="task1",
                provider="openai",
                model="gpt-5.4",
                status="completed",
                steps=5,
                duration_seconds=10.0,
                cost=0.05,
            ),
        ]

        report = BenchmarkReport(
            suite_name="test_suite",
            providers=["openai"],
            results=results,
            generated_at=datetime.now(UTC),
        )

        md = report.to_markdown()
        assert "# Benchmark Report: test_suite" in md
        assert "openai" in md
        assert "gpt-5.4" in md
