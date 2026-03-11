# CUH Architecture

## Overview

Computer Use Harness (CUH) is designed as a provider-neutral runtime for AI agents that need to control real computers. The architecture emphasizes:

1. **Provider neutrality**: The core runtime knows nothing about specific model providers
2. **Substrate abstraction**: Low-level computer control is hidden behind backend interfaces
3. **Replay by default**: Every action is logged and observable
4. **Safety boundaries**: Policy hooks for all risky operations

## Layered Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     User Interface Layer                     │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐  │
│  │     CLI     │  │  Python API │  │   FastAPI Server    │  │
│  └─────────────┘  └─────────────┘  └─────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                     Runtime Layer                            │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐  │
│  │ Orchestrator│  │   Session   │  │     EventBus        │  │
│  └─────────────┘  └─────────────┘  └─────────────────────┘  │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐  │
│  │Policy Engine│  │ArtifactStore│  │                     │  │
│  └─────────────┘  └─────────────┘  └─────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                   Provider Adapter Layer                     │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐  │
│  │GPT-5.4 Adptr│  │Qwen Adapter │  │  Future Providers   │  │
│  └─────────────┘  └─────────────┘  └─────────────────────┘  │
│                                                              │
│  ┌───────────────────────────────────────────────────────┐  │
│  │              Tool Name Mapper / Schema                 │  │
│  └───────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                   Core Schema Layer                          │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐  │
│  │   Actions   │  │Observations │  │      Events         │  │
│  └─────────────┘  └─────────────┘  └─────────────────────┘  │
│  ┌─────────────┐  ┌─────────────┐                           │
│  │ScreenGeomtry│  │   Policy    │                           │
│  └─────────────┘  └─────────────┘                           │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    Backend Layer                             │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐  │
│  │ Cua Backend │  │Mock Backend │  │ Future Backends     │  │
│  └─────────────┘  └─────────────┘  └─────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                   Target Environment                         │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐  │
│  │  Host PC    │  │ Windows VM  │  │   Linux Sandbox     │  │
│  └─────────────┘  └─────────────┘  └─────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

## Core Components

### Canonical Action Schema

All actions flow through a provider-neutral schema defined in `core/actions.py`:

```python
class ActionType(str, Enum):
    SCREENSHOT = "screenshot"
    CLICK = "click"
    DOUBLE_CLICK = "double_click"
    MOVE = "move"
    DRAG = "drag"
    SCROLL = "scroll"
    TYPE = "type"
    KEY_PRESS = "key_press"
    WAIT = "wait"
```

### Provider Adapter Interface

Providers implement a simple interface:

```python
class ProviderAdapter(Protocol):
    async def start_run(self, request: ProviderRunRequest) -> dict[str, Any]
    async def next_step(self, state, observations) -> ProviderStepResult
    async def close(self, state) -> None
```

### Backend Interface

Execution backends implement:

```python
class BaseBackend(ABC):
    async def connect(self) -> None
    async def disconnect(self) -> None
    async def execute(self, action: ComputerAction, step_id: str) -> ComputerObservation
    async def screenshot(self, step_id: str) -> ScreenshotObservation
    async def get_geometry(self) -> ScreenGeometry
```

## Event Flow

1. **Run Started**: Orchestrator initializes session, publishes `RunStartedEvent`
2. **Step Loop**:
   - Provider receives observations, returns actions
   - Each action emitted triggers `ActionEmittedEvent`
   - Policy engine evaluates action
   - Backend executes action, returns observation
   - `ActionExecutedEvent` and `ObservationRecordedEvent` published
3. **Run Completed**: `RunCompletedEvent` or `RunFailedEvent` published

## Coordinate Transformation

The `ScreenGeometry` model handles the mapping between:

- **Actual screen size**: Physical pixels on the target display
- **Model view size**: Resized image sent to the model

This prevents coordinate drift when models operate on resized screenshots.

## Policy Engine

The policy engine can:
- **ALLOW**: Action proceeds immediately
- **DENY**: Action is blocked with an error
- **REQUIRE_CONFIRMATION**: User must approve the action

Policies are configurable for:
- Destructive desktop actions
- Shell command execution
- Network calls
- Clipboard access
- File writes outside allowed directories

## Replay Artifacts

Every run produces a complete artifact bundle:

```
runs/YYYY-MM-DD_HHMMSS_provider_runid/
├── metadata.json       # Run metadata (provider, model, status)
├── config.json        # Configuration snapshot
├── summary.json       # Final summary (cost, steps, duration)
├── events.jsonl       # Chronological event log
└── steps/
    └── NNNN/
        ├── step.json          # Step metadata
        ├── provider_input.json # Request sent to provider
        ├── provider_output.json # Response from provider
        ├── action.json        # Canonical action executed
        ├── observation.json   # Observation returned
        └── screenshot.png     # Screenshot (if any)
```

This enables:
- Post-hoc debugging
- Run comparison
- Regression testing
- Cost analysis

## Future Extensions

### OpenHands Integration

CUH will provide custom tools for OpenHands:

```python
# OpenHands custom tool
class ComputerTool(ActionRequest):
    action: ComputerAction

class ComputerObservation(Observation):
    screenshot: str | None
    success: bool
    message: str | None
```

### Browser Backend

A future backend will support browser automation:

```python
class BrowserBackend(BaseBackend):
    async def navigate(self, url: str) -> Observation
    async def click_selector(self, selector: str) -> Observation
    async def type_selector(self, selector: str, text: str) -> Observation
```

### Semantic Backends

For OS-native accessibility:

- Windows UI Automation
- macOS Accessibility API
- Linux AT-SPI