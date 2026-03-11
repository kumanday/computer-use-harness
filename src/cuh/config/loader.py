"""Configuration system for CUH."""

from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml
from pydantic_settings import BaseSettings, SettingsConfigDict

from cuh.core.models import ProviderConfig, ProviderKind, TargetConfig, TargetKind


class Settings(BaseSettings):
    """Global settings for CUH."""

    model_config = SettingsConfigDict(
        env_prefix="CUH_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    default_provider: ProviderKind = ProviderKind.OPENAI
    default_model: str = "gpt-5.4"
    default_target: str = "local-host"
    telemetry_enabled: bool = False
    log_level: str = "INFO"
    runs_dir: Path = Path("runs")
    configs_dir: Path = Path("configs")


class ConfigLoader:
    """Loader for YAML configuration files."""

    def __init__(self, configs_dir: Path | None = None) -> None:
        self.configs_dir = configs_dir or Path("configs")

    def load_target(self, name: str) -> TargetConfig:
        """Load a target configuration."""
        target_path = self.configs_dir / "targets" / f"{name}.yaml"
        if not target_path.exists():
            target_path = self.configs_dir / "targets" / f"{name}.yml"

        if target_path.exists():
            data = self._load_yaml(target_path)
            return TargetConfig(**data)

        return TargetConfig(
            kind=TargetKind.CUA_HOST,
            name=name,
        )

    def load_provider(self, name: str) -> ProviderConfig:
        """Load a provider configuration."""
        provider_path = self.configs_dir / "providers" / f"{name}.yaml"
        if not provider_path.exists():
            provider_path = self.configs_dir / "providers" / f"{name}.yml"

        if provider_path.exists():
            data = self._load_yaml(provider_path)
            return ProviderConfig(**data)

        kind = ProviderKind.OPENAI if name == "openai" else ProviderKind.QWEN
        return ProviderConfig(
            provider=kind,
            model="gpt-5.4" if kind == ProviderKind.OPENAI else "Qwen/Qwen3.5-35B-A3B",
        )

    def load_task_suite(self, name: str) -> dict[str, Any]:
        """Load a task suite configuration."""
        suite_path = self.configs_dir / "task_suites" / f"{name}.yaml"
        if not suite_path.exists():
            suite_path = self.configs_dir / "task_suites" / f"{name}.yml"

        if suite_path.exists():
            return self._load_yaml(suite_path)

        return {"tasks": []}

    def _load_yaml(self, path: Path) -> dict[str, Any]:
        """Load a YAML file."""
        with path.open() as f:
            data = yaml.safe_load(f)
            return data if data else {}


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


def get_config_loader() -> ConfigLoader:
    """Get a configuration loader."""
    settings = get_settings()
    return ConfigLoader(settings.configs_dir)
