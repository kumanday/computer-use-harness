"""Policy engine for CUH.

The policy engine provides safety boundaries for computer control actions.
It can allow, deny, or require confirmation for actions based on configuration.
"""

from collections.abc import Callable
from enum import StrEnum
from typing import Any

from pydantic import BaseModel


class PolicyDecision(StrEnum):
    """Policy decisions for actions."""

    ALLOW = "allow"
    DENY = "deny"
    REQUIRE_CONFIRMATION = "require_confirmation"


class PolicyRule(BaseModel):
    """A policy rule for action filtering."""

    action_types: list[str] | None = None
    decision: PolicyDecision = PolicyDecision.ALLOW
    reason: str | None = None
    conditions: dict[str, Any] | None = None


class PolicyConfig(BaseModel):
    """Configuration for the policy engine."""

    enabled: bool = True
    default_decision: PolicyDecision = PolicyDecision.ALLOW
    rules: list[PolicyRule] = []
    deny_public_network: bool = True
    block_shell_calls: bool = False
    require_confirmation_destructive: bool = True
    require_confirmation_clipboard: bool = False
    require_confirmation_upload: bool = False
    allowed_hosts: list[str] = ["127.0.0.1", "localhost"]


class PolicyEngine:
    """Engine for evaluating action policies."""

    def __init__(self, config: PolicyConfig | None = None) -> None:
        self.config = config or PolicyConfig()
        self._confirmation_handlers: dict[str, Callable[[str, str], bool]] = {}

    def evaluate(
        self,
        action_type: str,
        action_data: dict[str, Any],
        context: dict[str, Any] | None = None,
    ) -> PolicyDecision:
        """Evaluate an action against policy rules."""
        if not self.config.enabled:
            return PolicyDecision.ALLOW

        context = context or {}

        for rule in self.config.rules:
            if self._matches_rule(rule, action_type, action_data, context):
                return rule.decision

        return self._evaluate_defaults(action_type, action_data, context)

    def _matches_rule(
        self,
        rule: PolicyRule,
        action_type: str,
        action_data: dict[str, Any],
        context: dict[str, Any],
    ) -> bool:
        """Check if an action matches a rule."""
        if rule.action_types and action_type not in rule.action_types:
            return False

        if rule.conditions:
            for key, value in rule.conditions.items():
                if action_data.get(key) != value:
                    return False

        return True

    def _evaluate_defaults(
        self,
        action_type: str,
        action_data: dict[str, Any],
        context: dict[str, Any],
    ) -> PolicyDecision:
        """Evaluate default policies for action types."""
        if action_type == "shell_exec" and self.config.block_shell_calls:
            return PolicyDecision.DENY

        if action_type in ("clipboard_get", "clipboard_set"):
            if self.config.require_confirmation_clipboard:
                return PolicyDecision.REQUIRE_CONFIRMATION

        if action_type in ("type", "key_press"):
            destructive_keys = ["delete", "backspace", "CTRL+A"]
            text = action_data.get("text", "")
            keys = action_data.get("keys", [])
            if any(k in destructive_keys for k in keys) or text:
                if self.config.require_confirmation_destructive:
                    return PolicyDecision.REQUIRE_CONFIRMATION

        if action_type == "browser_visit" and self.config.deny_public_network:
            url = action_data.get("url", "")
            if not any(host in url for host in self.config.allowed_hosts):
                return PolicyDecision.REQUIRE_CONFIRMATION

        return self.config.default_decision

    def register_confirmation_handler(
        self, action_type: str, handler: Callable[[str, str], bool]
    ) -> None:
        """Register a handler for confirmation requests."""
        self._confirmation_handlers[action_type] = handler

    async def confirm(self, action_type: str, reason: str) -> bool:
        """Request confirmation for an action."""
        handler = self._confirmation_handlers.get(action_type)
        if handler:
            return handler(action_type, reason)
        return False


class PolicyError(Exception):
    """Exception raised when an action is denied by policy."""

    def __init__(self, action_type: str, reason: str) -> None:
        self.action_type = action_type
        self.reason = reason
        super().__init__(f"Action '{action_type}' denied: {reason}")
