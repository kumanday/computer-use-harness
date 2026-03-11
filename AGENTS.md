# AGENTS.md

Guide for coding agents working on the Computer Use Harness (CUH) codebase.

## Project Overview

CUH is an open-source, provider-neutral computer-use platform for desktop and browser automation. It combines:
- **Cua substrate** (`cua-computer`, `cua-computer-server`) for low-level desktop control
- **Provider adapters** for model integration (GPT-5.4, Qwen 3.5)
- **Canonical action schema** independent of any provider
- **Replay system** for observability and debugging
- **Benchmark runner** for provider comparison

**Current State**: Wave B complete - core runtime, Cua backend, GPT-5.4 and Qwen 3.5 adapters, CLI, replay system, and benchmarking implemented.

**Next Waves** (see `plans/PRD.md`):
- Wave C: OpenHands integration
- Wave D: Advanced workflows, browser backend

## Repository Structure

```
computer-use-harness/
├── src/cuh/
│   ├── core/           # Canonical schemas (actions, observations, events, policy)
│   ├── backends/       # Execution backends (Cua, Mock)
│   ├── providers/      # Model provider adapters (GPT-5.4, Qwen 3.5)
│   ├── runtime/        # Orchestrator, session, event bus, artifact store
│   ├── cli/            # Click-based CLI
│   ├── config/         # Configuration loading
│   ├── api/            # FastAPI server (Wave B+)
│   ├── openhands/      # OpenHands integration (Wave C+)
│   └── bench/          # Benchmarking (Wave B+)
├── configs/
│   ├── providers/      # Provider YAML configs
│   ├── targets/        # Target YAML configs
│   └── task_suites/    # Task suite definitions
├── tests/
│   ├── unit/           # Unit tests (current focus)
│   ├── integration/    # Integration tests (planned)
│   └── smoke/          # Smoke tests (planned)
├── docs/               # Architecture and reference docs
├── examples/           # Example scripts
└── plans/PRD.md        # Full product requirements and implementation plan
```

## Coding Standards

### Language and Tooling
- **Python 3.12+**
- **uv** for dependency management (`uv sync`, `uv run`)
- **Ruff** for linting (`uv run ruff check src/ tests/`)
- **mypy** for type checking (`uv run mypy src/ --ignore-missing-imports`)
- **pytest** for testing (`uv run pytest tests/`)

### Style Conventions
- Line length: 100 characters
- Use `from __future__ import annotations` style (Python 3.12 handles this)
- Prefer `str | None` over `Optional[str]`
- Use Pydantic v2 models for all data structures
- Asyncio-first for all I/O operations

### Docstrings
- Module-level docstrings explaining purpose
- Class and method docstrings for public APIs
- No redundant comments - code should be self-documenting

### Type Hints
- All public functions must have type hints
- Use `Any` sparingly - prefer specific types or protocols
- Pydantic models handle validation, don't duplicate with runtime checks

## Key Architecture Patterns

### 1. Provider Neutrality
Never leak provider-specific types into core modules. All providers must:
1. Implement `BaseProviderAdapter` interface
2. Translate native tool calls to canonical `ComputerAction` schema
3. Store raw responses in replay artifacts for debugging

```python
# Good: Provider adapter translates to canonical action
action = ToolNameMapper.parse_action(provider_native_action)

# Bad: Using provider types directly in core
from openai.types import Response  # Don't do this in core/
```

### 2. Backend Abstraction
All desktop control flows through `BaseBackend` interface. The orchestrator never calls Cua directly:

```python
# Good: Through backend interface
observation = await backend.execute(action, step_id)

# Bad: Direct Cua calls
from computer import Computer  # Don't do this outside backends/
```

### 3. Canonical Action Schema
All actions use the schema defined in `core/actions.py`:

```python
# Canonical action format
{
    "tool": "computer",
    "action": "click",
    "x": 512,
    "y": 341,
    "button": "left"
}
```

When adding new action types:
1. Add to `ActionType` enum in `core/actions.py`
2. Create typed action class (e.g., `NewAction`)
3. Add parsing logic to `ToolNameMapper.parse_action()`
4. Add execution logic to `CuaBackend._execute_action()`

### 4. Coordinate Transformation
`ScreenGeometry` handles coordinate mapping between model-view and actual screen:

```python
# Always transform coordinates when executing
actual_x, actual_y = geometry.model_to_actual(model_x, model_y)
```

### 5. Event-Driven Observability
All significant events are published to `EventBus`:

```python
# Publishing events
event_bus.publish(ActionEmittedEvent(run_id=run_id, action_type="click"))

# Subscribing to events
event_bus.subscribe(None, my_callback)  # Subscribe to all events
event_bus.subscribe("action_executed", my_callback)  # Specific event type
```

## Running Tests and Checks

```bash
# Install dependencies
uv sync --extra dev

# Run linting
uv run ruff check src/ tests/

# Auto-fix linting issues
uv run ruff check src/ tests/ --fix

# Run type checking
uv run mypy src/ --ignore-missing-imports

# Run unit tests
uv run pytest tests/unit/ -v

# Run all tests
uv run pytest tests/ -v
```

## Adding a New Provider

1. Create `src/cuh/providers/<provider>.py`
2. Inherit from `BaseProviderAdapter`
3. Implement required methods:
   - `start_run(request: ProviderRunRequest) -> dict[str, Any]`
   - `next_step(state, observations) -> ProviderStepResult`
   - `close(state) -> None`
4. Add tool schema class if needed (see `OpenAIToolSchema`, `QwenToolSchema`)
5. Register in `src/cuh/providers/__init__.py`
6. Add config template to `configs/providers/<provider>.yaml`
7. Write unit tests in `tests/unit/test_<provider>.py`

## Adding a New Backend

1. Create `src/cuh/backends/<backend>.py`
2. Inherit from `BaseBackend`
3. Implement required methods:
   - `connect() -> None`
   - `disconnect() -> None`
   - `execute(action, step_id) -> ComputerObservation`
   - `screenshot(step_id) -> ScreenshotObservation`
   - `get_geometry() -> ScreenGeometry`
4. Register in `src/cuh/backends/__init__.py`
5. Add config loader support in `src/cuh/config/loader.py`

## Adding a New CLI Command

1. Add command function in `src/cuh/cli/main.py`
2. Use Click decorators: `@main.command()`, `@click.option()`
3. Use Rich for output formatting: `console.print()`, `Table`

## Replay Artifacts

Every run produces a directory in `runs/`:

```
runs/YYYY-MM-DD_HHMMSS_provider_runid/
├── metadata.json       # Run metadata
├── config.json        # Configuration snapshot
├── summary.json       # Final summary
├── events.jsonl       # Event log (line-delimited JSON)
└── steps/
    └── NNNN/
        ├── step.json
        ├── provider_input.json
        ├── provider_output.json
        ├── action.json
        ├── observation.json
        └── screenshot.png
```

Always write to artifact store during runs for replay capability.

## Safety and Security

- Desktop control endpoints default to localhost
- Use `PolicyEngine` to evaluate risky actions
- Never hardcode secrets - use environment variables
- Add policy checks for destructive operations

## Common Gotchas

1. **Don't use `asyncio.execute()`** - Use `asyncio.run()` instead
2. **Use `datetime.now(timezone.utc)`** - Not `datetime.utcnow()` (deprecated)
3. **ClassVar for mutable class attributes** - Annotate with `ClassVar` to avoid Ruff warnings
4. **Path.open() instead of open()** - Ruff prefers `path.open()` over `open(path)`

## Reference Documents

- `plans/PRD.md` - Full product requirements and implementation plan
- `docs/architecture.md` - Detailed architecture documentation
- `docs/provider-mapping.md` - Provider integration guide
- `docs/replay-format.md` - Artifact format specification

## Before Committing

1. Run linting: `uv run ruff check src/ tests/`
2. Run type checking: `uv run mypy src/ --ignore-missing-imports`
3. Run tests: `uv run pytest tests/`
4. Check dry-run works: `uv run cuh run --task "test" --dry-run`