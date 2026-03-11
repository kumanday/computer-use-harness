# Provider Mapping

CUH uses a canonical action schema that all providers must translate to. This document describes how each provider maps to the canonical schema.

## Canonical Schema

The canonical action format:

```json
{
  "tool": "computer",
  "action": "click",
  "x": 512,
  "y": 341,
  "button": "left",
  "meta": {}
}
```

### Supported Actions

| Action | Required Fields | Optional Fields |
|--------|----------------|-----------------|
| `screenshot` | - | - |
| `click` | x, y | button |
| `double_click` | x, y | - |
| `move` | x, y | - |
| `drag` | from_x, from_y, to_x, to_y | - |
| `scroll` | delta_x, delta_y | - |
| `type` | text | - |
| `key_press` | keys | - |
| `wait` | seconds | - |

## OpenAI GPT-5.4

### Tool Schema

OpenAI uses the `computer_20241022` tool type:

```python
{
    "type": "computer_20241022",
    "display_width": 1280,
    "display_height": 720,
    "environment": "linux"
}
```

### Response Format

OpenAI returns actions via `computer_call` output blocks:

```json
{
  "type": "computer_call",
  "action": {
    "type": "click",
    "x": 512,
    "y": 341,
    "button": "left"
  }
}
```

### Mapping

| OpenAI Action | Canonical Action |
|---------------|------------------|
| `click` | `click` |
| `double_click` | `double_click` |
| `drag` | `drag` |
| `keypress` | `key_press` |
| `move` | `move` |
| `screenshot` | `screenshot` |
| `scroll` | `scroll` |
| `type` | `type` |
| `wait` | `wait` |

Coordinate format matches canonical (x, y as separate fields).

## Qwen 3.5

### Tool Schema

Qwen uses OpenAI-compatible function calling:

```python
{
    "type": "function",
    "function": {
        "name": "computer",
        "parameters": {
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": [...]},
                "x": {"type": "integer"},
                "y": {"type": "integer"},
                ...
            }
        }
    }
}
```

### Response Format

Qwen returns function calls:

```json
{
  "name": "computer",
  "arguments": "{\"action\": \"click\", \"x\": 512, \"y\": 341}"
}
```

### Mapping Notes

- Key names may vary by serving stack (vLLM, SGLang, Transformers)
- Some stacks use `key_press` vs `keypress`
- Some stacks use coordinate arrays vs separate x/y fields
- The `ToolNameMapper` handles these variations

## Tool Name Aliases

The mapper handles common aliases:

```python
ACTION_ALIASES = {
    "click": ActionType.CLICK,
    "double_click": ActionType.DOUBLE_CLICK,
    "doubleClick": ActionType.DOUBLE_CLICK,
    "mouse_move": ActionType.MOVE,
    "mousemove": ActionType.MOVE,
    "key_press": ActionType.KEY_PRESS,
    "keypress": ActionType.KEY_PRESS,
    "keyPress": ActionType.KEY_PRESS,
    ...
}
```

## Adding New Providers

To add a new provider:

1. Create `src/cuh/providers/<provider>.py`
2. Implement `BaseProviderAdapter`
3. Create a `ToolSchema` class if the provider needs custom schema
4. Add mapping logic in `ToolNameMapper` if needed
5. Register in `src/cuh/providers/__init__.py`

### Provider Checklist

- [ ] Implements `start_run(request) -> state`
- [ ] Implements `next_step(state, observations) -> ProviderStepResult`
- [ ] Implements `close(state) -> None`
- [ ] Handles screenshot input (base64)
- [ ] Returns canonical actions
- [ ] Captures usage/cost metrics
- [ ] Stores raw response for replay