"""Tests for policy engine."""


from cuh.core.policy import (
    PolicyConfig,
    PolicyDecision,
    PolicyEngine,
    PolicyError,
    PolicyRule,
)


class TestPolicyDecision:
    def test_enum_values(self) -> None:
        assert PolicyDecision.ALLOW.value == "allow"
        assert PolicyDecision.DENY.value == "deny"
        assert PolicyDecision.REQUIRE_CONFIRMATION.value == "require_confirmation"


class TestPolicyRule:
    def test_create(self) -> None:
        rule = PolicyRule(
            action_types=["shell_exec"],
            decision=PolicyDecision.DENY,
            reason="Shell execution disabled",
        )
        assert rule.action_types == ["shell_exec"]
        assert rule.decision == PolicyDecision.DENY
        assert rule.reason == "Shell execution disabled"


class TestPolicyConfig:
    def test_defaults(self) -> None:
        config = PolicyConfig()
        assert config.enabled is True
        assert config.default_decision == PolicyDecision.ALLOW
        assert config.deny_public_network is True
        assert config.block_shell_calls is False


class TestPolicyEngine:
    def test_disabled_policy_allows_all(self) -> None:
        config = PolicyConfig(enabled=False)
        engine = PolicyEngine(config)
        assert engine.evaluate("shell_exec", {}) == PolicyDecision.ALLOW

    def test_default_allow(self) -> None:
        config = PolicyConfig(default_decision=PolicyDecision.ALLOW)
        engine = PolicyEngine(config)
        assert engine.evaluate("screenshot", {}) == PolicyDecision.ALLOW

    def test_rule_matching(self) -> None:
        config = PolicyConfig(
            rules=[
                PolicyRule(action_types=["shell_exec"], decision=PolicyDecision.DENY),
            ]
        )
        engine = PolicyEngine(config)
        assert engine.evaluate("shell_exec", {}) == PolicyDecision.DENY
        assert engine.evaluate("screenshot", {}) == PolicyDecision.ALLOW

    def test_block_shell_calls(self) -> None:
        config = PolicyConfig(block_shell_calls=True)
        engine = PolicyEngine(config)
        assert engine.evaluate("shell_exec", {}) == PolicyDecision.DENY

    def test_clipboard_requires_confirmation(self) -> None:
        config = PolicyConfig(require_confirmation_clipboard=True)
        engine = PolicyEngine(config)
        assert engine.evaluate("clipboard_get", {}) == PolicyDecision.REQUIRE_CONFIRMATION
        assert engine.evaluate("clipboard_set", {}) == PolicyDecision.REQUIRE_CONFIRMATION


class TestPolicyError:
    def test_create(self) -> None:
        error = PolicyError("shell_exec", "Shell execution disabled")
        assert error.action_type == "shell_exec"
        assert error.reason == "Shell execution disabled"
        assert "shell_exec" in str(error)
        assert "Shell execution disabled" in str(error)
