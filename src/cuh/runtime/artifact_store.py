"""Artifact store for CUH runs.

Manages the storage and retrieval of run artifacts including
screenshots, metadata, events, and replay bundles.
"""

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from cuh.core.events import RunEvent
from cuh.core.models import RunMetadata, StepRecord


class ArtifactStore:
    """Store for run artifacts."""

    def __init__(self, runs_dir: Path | None = None) -> None:
        self.runs_dir = runs_dir or Path("runs")
        self._current_run_dir: Path | None = None

    def create_run_directory(self, run_id: str) -> Path:
        """Create a directory for a new run."""
        timestamp = datetime.now(UTC).strftime("%Y-%m-%d_%H%M%S")
        run_name = f"{timestamp}_{run_id[:8]}"
        run_dir = self.runs_dir / run_name
        run_dir.mkdir(parents=True, exist_ok=True)

        steps_dir = run_dir / "steps"
        steps_dir.mkdir(exist_ok=True)

        assets_dir = run_dir / "assets"
        assets_dir.mkdir(exist_ok=True)

        self._current_run_dir = run_dir
        return run_dir

    def write_metadata(self, metadata: RunMetadata) -> None:
        """Write run metadata."""
        if not self._current_run_dir:
            raise RuntimeError("No active run directory")

        metadata_path = self._current_run_dir / "metadata.json"
        with metadata_path.open("w") as f:
            json.dump(metadata.model_dump(mode="json"), f, indent=2, default=str)

    def write_config(self, config: dict[str, Any]) -> None:
        """Write run configuration snapshot."""
        if not self._current_run_dir:
            raise RuntimeError("No active run directory")

        config_path = self._current_run_dir / "config.json"
        with config_path.open("w") as f:
            json.dump(config, f, indent=2, default=str)

    def append_event(self, event: RunEvent) -> None:
        """Append an event to the events log."""
        if not self._current_run_dir:
            raise RuntimeError("No active run directory")

        events_path = self._current_run_dir / "events.jsonl"
        with events_path.open("a") as f:
            f.write(json.dumps(event.model_dump(mode="json"), default=str) + "\n")

    def write_step(self, step: StepRecord) -> None:
        """Write a step record."""
        if not self._current_run_dir:
            raise RuntimeError("No active run directory")

        step_dir = self._current_run_dir / "steps" / f"{step.step_number:04d}"
        step_dir.mkdir(exist_ok=True)

        step_path = step_dir / "step.json"
        with step_path.open("w") as f:
            json.dump(step.model_dump(mode="json"), f, indent=2, default=str)

        if step.provider_input:
            input_path = step_dir / "provider_input.json"
            with input_path.open("w") as f:
                json.dump(step.provider_input, f, indent=2, default=str)

        if step.provider_output:
            output_path = step_dir / "provider_output.json"
            with output_path.open("w") as f:
                json.dump(step.provider_output, f, indent=2, default=str)

        if step.action:
            action_path = step_dir / "action.json"
            with action_path.open("w") as f:
                json.dump(step.action, f, indent=2, default=str)

        if step.observation:
            obs_path = step_dir / "observation.json"
            with obs_path.open("w") as f:
                json.dump(step.observation, f, indent=2, default=str)

    def save_screenshot(self, step_number: int, image_data: bytes, format: str = "png") -> Path:
        """Save a screenshot for a step."""
        if not self._current_run_dir:
            raise RuntimeError("No active run directory")

        step_dir = self._current_run_dir / "steps" / f"{step_number:04d}"
        step_dir.mkdir(exist_ok=True)

        screenshot_path = step_dir / f"screenshot.{format}"
        with screenshot_path.open("wb") as f:
            f.write(image_data)

        return screenshot_path

    def write_summary(self, summary: dict[str, Any]) -> None:
        """Write run summary."""
        if not self._current_run_dir:
            raise RuntimeError("No active run directory")

        summary_path = self._current_run_dir / "summary.json"
        with summary_path.open("w") as f:
            json.dump(summary, f, indent=2, default=str)

    def list_runs(self) -> list[Path]:
        """List all run directories."""
        if not self.runs_dir.exists():
            return []
        return sorted(self.runs_dir.iterdir(), key=lambda p: p.stat().st_mtime, reverse=True)

    def load_run_metadata(self, run_dir: Path) -> RunMetadata | None:
        """Load metadata for a run."""
        metadata_path = run_dir / "metadata.json"
        if not metadata_path.exists():
            return None

        with metadata_path.open() as f:
            data = json.load(f)
            return RunMetadata(**data)

    def load_run_events(self, run_dir: Path) -> list[dict[str, Any]]:
        """Load events for a run."""
        events_path = run_dir / "events.jsonl"
        if not events_path.exists():
            return []

        events = []
        with events_path.open() as f:
            for line in f:
                if line.strip():
                    events.append(json.loads(line))
        return events

    def get_screenshot_path(self, run_dir: Path, step_number: int) -> Path | None:
        """Get the path to a screenshot for a step."""
        step_dir = run_dir / "steps" / f"{step_number:04d}"
        for ext in ["png", "jpg", "jpeg"]:
            path = step_dir / f"screenshot.{ext}"
            if path.exists():
                return path
        return None
