# Replay Format

Every CUH run produces a replay bundle for observability and debugging.

## Directory Structure

```
runs/
└── 2026-03-11_153045_gpt54_3f9e/
    ├── metadata.json        # Run metadata
    ├── config.json         # Configuration snapshot
    ├── summary.json        # Final summary
    ├── events.jsonl        # Event log (line-delimited JSON)
    ├── steps/
    │   ├── 0001/
    │   │   ├── step.json
    │   │   ├── provider_input.json
    │   │   ├── provider_output.json
    │   │   ├── action.json
    │   │   ├── observation.json
    │   │   └── screenshot.png
    │   ├── 0002/
    │   │   └── ...
    │   └── ...
    └── assets/
        └── ...
```

## File Formats

### metadata.json

```json
{
  "run_id": "3f9e8a2b-4c5d-6e7f-8a9b-0c1d2e3f4a5b",
  "created_at": "2026-03-11T15:30:45.123Z",
  "started_at": "2026-03-11T15:30:45.456Z",
  "completed_at": "2026-03-11T15:35:12.789Z",
  "provider": "openai",
  "model": "gpt-5.4",
  "target": "local-host",
  "task": "Take a screenshot and describe what you see",
  "state": "completed",
  "total_steps": 5,
  "successful_actions": 12,
  "failed_actions": 0,
  "total_tokens_prompt": 15000,
  "total_tokens_completion": 3000,
  "total_cost": 0.63
}
```

### config.json

```json
{
  "provider": "openai",
  "model": "gpt-5.4",
  "target": "local-host",
  "task": "Take a screenshot and describe what you see",
  "max_steps": 100,
  "timeout_seconds": 300.0,
  "screenshot_interval": 0.5,
  "policy_enabled": true
}
```

### summary.json

```json
{
  "run_id": "3f9e8a2b-4c5d-6e7f-8a9b-0c1d2e3f4a5b",
  "status": "completed",
  "total_steps": 5,
  "successful_actions": 12,
  "failed_actions": 0,
  "total_tokens": 18000,
  "total_cost": 0.63,
  "duration_seconds": 267.33
}
```

### events.jsonl

Line-delimited JSON events:

```jsonl
{"event_type":"run_started","timestamp":"2026-03-11T15:30:45.456Z","run_id":"3f9e...","task":"Take a screenshot...","provider":"openai","model":"gpt-5.4"}
{"event_type":"step_started","timestamp":"2026-03-11T15:30:45.789Z","run_id":"3f9e...","step_number":1}
{"event_type":"provider_response","timestamp":"2026-03-11T15:30:47.123Z","run_id":"3f9e...","has_actions":true,"action_count":2}
{"event_type":"action_emitted","timestamp":"2026-03-11T15:30:47.124Z","run_id":"3f9e...","action_type":"click","action_data":{"x":512,"y":341}}
{"event_type":"action_executed","timestamp":"2026-03-11T15:30:47.456Z","run_id":"3f9e...","action_type":"click","success":true}
{"event_type":"observation_recorded","timestamp":"2026-03-11T15:30:47.789Z","run_id":"3f9e...","observation_type":"screenshot","has_screenshot":true}
{"event_type":"step_completed","timestamp":"2026-03-11T15:30:48.000Z","run_id":"3f9e...","step_number":1}
...
{"event_type":"run_completed","timestamp":"2026-03-11T15:35:12.789Z","run_id":"3f9e...","total_steps":5,"duration_seconds":267.33}
```

### step.json

```json
{
  "step_id": "step_0001",
  "step_number": 1,
  "timestamp": "2026-03-11T15:30:45.789Z",
  "usage": {
    "prompt_tokens": 3000,
    "completion_tokens": 500,
    "total_tokens": 3500,
    "cost": 0.12,
    "latency_ms": 1234.5
  }
}
```

### provider_output.json

Raw provider response (varies by provider):

```json
{
  "id": "resp_abc123",
  "model": "gpt-5.4",
  "output": [
    {
      "type": "computer_call",
      "action": {
        "type": "click",
        "x": 512,
        "y": 341
      }
    }
  ],
  "usage": {
    "prompt_tokens": 3000,
    "completion_tokens": 500
  }
}
```

### action.json

Canonical action:

```json
{
  "tool": "computer",
  "action": "click",
  "x": 512,
  "y": 341,
  "button": "left"
}
```

### observation.json

```json
{
  "observation_type": "action_result",
  "timestamp": "2026-03-11T15:30:47.456Z",
  "step_id": "step_0001",
  "success": true,
  "action_type": "click",
  "coordinates": [512, 341],
  "message": "Executed click"
}
```

## Using Replay Data

### Programmatic Access

```python
from cuh.runtime.artifact_store import ArtifactStore

store = ArtifactStore()

# List runs
runs = store.list_runs()

# Load metadata
metadata = store.load_run_metadata(runs[0])

# Load events
events = store.load_run_events(runs[0])

# Get screenshot
screenshot = store.get_screenshot_path(runs[0], step_number=1)
```

### CLI Access

```bash
# List runs
cuh runs

# Show run details
cuh runs 2026-03-11_153045_gpt54_3f9e
```

## Event Types

| Event | Description |
|-------|-------------|
| `run_started` | Run initialized |
| `run_completed` | Run finished successfully |
| `run_failed` | Run terminated with error |
| `provider_request` | Request sent to provider |
| `provider_response` | Response received from provider |
| `action_emitted` | Action parsed from provider response |
| `action_executed` | Action executed by backend |
| `observation_recorded` | Observation saved |
| `policy_check` | Policy evaluation performed |
| `policy_blocked` | Action blocked by policy |
| `step_started` | Step loop iteration started |
| `step_completed` | Step loop iteration completed |
| `error` | Error occurred |