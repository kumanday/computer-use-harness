# Computer Use Harness (CUH)

**An open-source, provider-neutral computer-use platform for desktop and browser automation.**

CUH is a standalone runtime that allows AI agents to control real computers through screenshots and input actions. It combines the [Cua](https://github.com/trycua/cua) computer-control substrate with a provider-neutral adapter layer for models like GPT-5.4 and Qwen 3.5.

## Features

- **Provider-neutral core**: Canonical action schema independent of any model provider
- **GPT-5.4 support**: First-class support for OpenAI's computer-use model
- **Qwen 3.5 support**: Alternative provider for cost/capability benchmarking
- **Cua substrate**: Leverages `cua-computer` and `cua-computer-server` for desktop control
- **Replay by default**: Every run produces observable, diagnosable artifacts
- **Policy engine**: Safety boundaries for destructive or risky actions
- **CLI-first**: Command-line interface for automation and scripting

## Installation

```bash
# Clone the repository
git clone https://github.com/your-org/computer-use-harness.git
cd computer-use-harness

# Install with uv (recommended)
uv sync

# For development, install dev dependencies
uv sync --extra dev

# Or install with pip
pip install -e .
```

## Quick Start

### 1. Set up your API key

```bash
export OPENAI_API_KEY=sk-your-key-here
```

### 2. Start a local Cua computer-server

```bash
# Install cua-computer-server (in same environment)
uv pip install cua-computer-server

# Start the server
uv run python -m computer_server --host 127.0.0.1 --port 8000
```

### 3. Run a task

```bash
# Run a simple screenshot task
# --target host refers to configs/targets/host.yaml
uv run cuh run --provider openai --model gpt-5.4 --target host --task "Take a screenshot and describe what you see"

# Or use the short form
uv run cuh run -p openai -m gpt-5.4 -t host -k "Take a screenshot and describe what you see"
```

## CLI Commands

All CLI commands are run via `uv run cuh`. Use `--help` for details.

### `cuh run`

Run a task with CUH.

```bash
uv run cuh run [OPTIONS]

Options:
  -p, --provider TEXT     Provider to use (openai, qwen) [default: openai]
  -m, --model TEXT        Model to use [default: gpt-5.4]
  -t, --target TEXT       Target configuration name [default: host]
  -k, --task TEXT         Task to execute [required]
  -s, --max-steps INT     Maximum number of steps [default: 100]
  -o, --timeout FLOAT     Timeout in seconds [default: 300.0]
  -c, --config-dir PATH   Configuration directory
  -v, --verbose           Enable verbose output
  --dry-run              Show configuration without running
```

### `cuh runs`

List runs or show run details.

```bash
# List recent runs
uv run cuh runs

# Show details of a specific run
uv run cuh runs <run-id>

# Limit number of runs shown
uv run cuh runs --limit 20
```

### `cuh targets`

List or check target configurations.

```bash
# List all targets
uv run cuh targets

# Show details of a specific target
uv run cuh targets <target-name>
```

### `cuh bench run`

Run a benchmark suite across multiple providers.

```bash
# Run the smoke suite with both OpenAI and Qwen
uv run cuh bench run --suite smoke --providers openai,qwen --target host

# Save report to file
uv run cuh bench run --suite smoke -p openai,qwen -t host -o benchmark_report

# Specify output format
uv run cuh bench run --suite smoke -p openai -t host --format json
```

### `cuh profiles`

List available Qwen model profiles.

```bash
uv run cuh profiles
```

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `OPENAI_API_KEY` | OpenAI API key | Required for GPT-5.4 |
| `QWEN_API_KEY` | Qwen API key | Required for Qwen qwen-api backend |
| `OPENROUTER_API_KEY` | OpenRouter API key | Required for Qwen openrouter backend |
| `FIREWORKS_API_KEY` | Fireworks API key | Required for Qwen fireworks backend |
| `CUH_DEFAULT_PROVIDER` | Default provider | `openai` |
| `CUH_DEFAULT_MODEL` | Default model | `gpt-5.4` |
| `CUH_RUNS_DIR` | Directory for run artifacts | `runs/` |
| `CUH_LOG_LEVEL` | Log level | `INFO` |
| `CUH_TELEMETRY_ENABLED` | Enable telemetry | `false` |

### Target Configuration

Targets define where CUH executes actions. Create in `configs/targets/<name>.yaml`:

```yaml
# configs/targets/host.yaml
kind: cua_host        # cua_host = connect to local computer-server
name: local-host      # descriptive name
api_host: 127.0.0.1   # computer-server host
api_port: 8000        # computer-server port
os_type: macos        # macos, linux, or windows
```

Target kinds:
- `cua_host` - Connect to a local `cua-computer-server` (default for development)
- `cua_remote` - Connect to a remote computer-server
- `linux_sandbox` - VM-based Linux sandbox
- `windows_vm` - Windows VM
- `mock` - Simulated backend for testing (no display needed)

> **macOS Screen Recording Permission**: When using `cua_host`, the computer_server needs Screen Recording permission. Go to **System Settings → Privacy & Security → Screen Recording** and add your terminal app. If testing without a display, use `--target mock` instead.

### Provider Configuration

Create a provider configuration in `configs/providers/<name>.yaml`:

```yaml
# OpenAI GPT-5.4
provider: openai
model: gpt-5.4
api_key_env: OPENAI_API_KEY
mode: responses_computer
reasoning_effort: medium
```

```yaml
# Qwen 3.5 (via official API)
provider: qwen
model: Qwen/Qwen3.5-35B-A3B
backend: qwen-api
api_key_env: QWEN_API_KEY
mode: openai_compatible_tools
vision_enabled: true
```

```yaml
# Qwen 3.5 (via OpenRouter)
provider: qwen
model: qwen/qwen3.5-397b-a17b
backend: openrouter
api_key_env: OPENROUTER_API_KEY
```

```yaml
# Qwen 3.5 (via Fireworks)
provider: qwen
model: accounts/fireworks/models/qwen3p5-397b-a17b
backend: fireworks
api_key_env: FIREWORKS_API_KEY
```

Available backends for Qwen: `qwen-api`, `openrouter`, `fireworks`, `local`

## Run Artifacts

Each run produces a directory containing:

```
runs/2026-03-11_153045_gpt54_3f9e/
├── metadata.json        # Run metadata
├── config.json         # Configuration snapshot
├── summary.json        # Final summary
├── events.jsonl        # Event log
├── steps/
│   ├── 0001/
│   │   ├── step.json
│   │   ├── provider_input.json
│   │   ├── provider_output.json
│   │   ├── action.json
│   │   ├── observation.json
│   │   └── screenshot.png
│   └── ...
└── assets/
```

## Architecture

CUH follows a layered architecture:

```
User / CLI / API
        │
        ▼
┌─────────────────────────┐
│ CUH Orchestrator        │
│ - run manager           │
│ - policy engine         │
│ - event bus             │
│ - replay writer         │
└─────────────────────────┘
        │
        ▼
┌─────────────────────────┐
│ Provider Adapters       │
│ - OpenAI GPT-5.4        │
│ - Qwen 3.5              │
└─────────────────────────┘
        │
        ▼
┌─────────────────────────┐
│ Canonical CUH Tool API  │
│ - computer actions      │
│ - observations          │
└─────────────────────────┘
        │
        ▼
┌─────────────────────────┐
│ Execution Backends      │
│ - Cua backend           │
└─────────────────────────┘
        │
        ▼
┌─────────────────────────┐
│ Target Environment      │
│ - host desktop          │
│ - remote VM             │
└─────────────────────────┘
```

## Python API

Use CUH programmatically:

```python
import asyncio
from cuh.backends.cua_backend import create_backend
from cuh.core.models import ProviderConfig, ProviderKind, RunConfig, TargetConfig
from cuh.providers.openai_gpt54 import create_gpt54_adapter
from cuh.providers.qwen35 import create_qwen35_adapter, create_qwen_adapter_for_backend
from cuh.runtime.orchestrator import Orchestrator

async def main():
    # Configure target
    target = TargetConfig(
        kind="cua_host",
        name="local-host",
        api_host="127.0.0.1",
        api_port=8000,
    )
    
    # Create backend
    backend = await create_backend(target)
    
    # Choose provider: OpenAI GPT-5.4 or Qwen 3.5
    # OpenAI:
    provider = await create_gpt54_adapter()
    # Or Qwen (with backend config):
    # from cuh.providers.qwen35 import create_qwen_adapter_for_backend
    # provider = await create_qwen_adapter_for_backend(
    #     backend="openrouter",
    #     model="qwen/qwen3.5-397b-a17b",
    # )
    
    # Run task
    orchestrator = Orchestrator(backend=backend, provider=provider)
    config = RunConfig(
        provider=ProviderKind.OPENAI,
        model="gpt-5.4",
        target="local-host",
        task="Take a screenshot and describe what you see",
    )
    
    session = await orchestrator.run(config)
    print(f"Status: {session.state}")
    print(f"Steps: {session.total_steps}")
    
    await backend.disconnect()

asyncio.run(main())
```

## Safety and Security

- Desktop control endpoints default to localhost only
- Destructive actions can be blocked by policy
- Shell execution is clearly separated from GUI control
- Secrets are pulled from environment variables, never hardcoded
- Policy hooks exist for all risky operations

## Development

```bash
# Install dev dependencies
uv sync --extra dev

# Run linting
uv run ruff check src/

# Run type checking
uv run mypy src/

# Run tests
uv run pytest tests/
```

## Roadmap

- [x] Wave A: Core runtime, Cua backend, GPT-5.4 adapter
- [x] Wave B: Qwen 3.5 adapter, provider-neutral core, benchmarking
- [ ] Wave C: OpenHands integration
- [ ] Wave D: Advanced workflows, browser backend

## License

MIT License. See [LICENSE](LICENSE) and [NOTICE.md](NOTICE.md) for details.

## References

- [Cua Platform](https://github.com/trycua/cua)
- [OpenAI Computer Use Guide](https://developers.openai.com/api/docs/guides/tools-computer-use/)
- [OpenHands SDK](https://docs.openhands.dev/sdk)
- [Qwen 3.5](https://github.com/QwenLM/Qwen3.5)