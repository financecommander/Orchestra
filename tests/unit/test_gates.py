"""Tests for quality gates module."""

import pytest
from orchestra.core.gates import (
    QualityGate,
    GateResult,
    SecurityGate,
    ComplianceGate,
    PerformanceGate,
)


class TestGateResult:
    """Test cases for GateResult dataclass."""

    def test_gate_result_creation(self):
        """Test basic gate result creation."""
        result = GateResult(
            passed=True, gate_name="TestGate", message="Test passed"
        )
        assert result.passed is True
        assert result.gate_name == "TestGate"
        assert result.message == "Test passed"
        assert result.metrics == {}
        assert result.escalation_required is False

    def test_gate_result_with_metrics(self):
        """Test gate result with metrics."""
        result = GateResult(
            passed=False,
            gate_name="TestGate",
            message="Test failed",
            metrics={"score": 0.5, "threshold": 0.8},
            escalation_required=True,
        )
        assert result.passed is False
        assert result.metrics["score"] == 0.5
        assert result.escalation_required is True


class TestSecurityGate:
    """Test cases for SecurityGate."""

    def test_security_gate_creation(self):
        """Test basic security gate creation."""
        gate = SecurityGate()
        assert gate.name == "SecurityGate"
        assert gate.threshold == 0.8
        assert gate.escalation_enabled is True

    def test_security_gate_custom_threshold(self):
        """Test security gate with custom threshold."""
        gate = SecurityGate(threshold=0.9)
        assert gate.threshold == 0.9

    def test_security_gate_check_pass(self):
        """Test security gate check that passes."""
        gate = SecurityGate(threshold=0.8, escalation_enabled=False)
        data = {"security_score": 0.85}

        result = gate.check(data)

        assert result.passed is True
        assert result.gate_name == "SecurityGate"
        assert "passes" in result.message
        assert result.metrics["security_score"] == 0.85
        assert result.escalation_required is False

    def test_security_gate_check_fail(self):
        """Test security gate check that fails."""
        gate = SecurityGate(threshold=0.8, escalation_enabled=False)
        data = {"security_score": 0.6}

        result = gate.check(data)

        assert result.passed is False
        assert "fails" in result.message
        assert result.metrics["security_score"] == 0.6

    def test_security_gate_check_exact_threshold(self):
        """Test security gate check at exact threshold."""
        gate = SecurityGate(threshold=0.8)
        data = {"security_score": 0.8}

        result = gate.check(data)

        assert result.passed is True

    def test_security_gate_check_missing_score(self):
        """Test security gate with missing score."""
        gate = SecurityGate(threshold=0.8, escalation_enabled=False)
        data = {}

        result = gate.check(data)

        assert result.passed is False
        assert result.metrics["security_score"] == 0.0

    def test_security_gate_escalation(self):
        """Test security gate escalation."""
        escalation_called = []

        def escalation_callback(result):
            escalation_called.append(result)

        gate = SecurityGate(
            threshold=0.8, escalation_enabled=True, escalation_callback=escalation_callback
        )
        data = {"security_score": 0.5}

        result = gate.check(data)

        assert result.escalation_required is True
        assert len(escalation_called) == 1
        assert escalation_called[0].gate_name == "SecurityGate"

    def test_security_gate_repr(self):
        """Test security gate string representation."""
        gate = SecurityGate(threshold=0.85)
        repr_str = repr(gate)
        assert "SecurityGate" in repr_str
        assert "0.85" in repr_str


class TestComplianceGate:
    """Test cases for ComplianceGate."""

    def test_compliance_gate_creation(self):
        """Test basic compliance gate creation."""
        gate = ComplianceGate()
        assert gate.name == "ComplianceGate"
        assert gate.threshold == 0.9

    def test_compliance_gate_check_pass(self):
        """Test compliance gate check that passes."""
        gate = ComplianceGate(threshold=0.9, escalation_enabled=False)
        data = {"compliance_score": 0.95}

        result = gate.check(data)

        assert result.passed is True
        assert "passes" in result.message

    def test_compliance_gate_check_fail(self):
        """Test compliance gate check that fails."""
        gate = ComplianceGate(threshold=0.9, escalation_enabled=False)
        data = {"compliance_score": 0.7}

        result = gate.check(data)

        assert result.passed is False
        assert "fails" in result.message

    def test_compliance_gate_escalation(self):
        """Test compliance gate escalation."""
        escalation_called = []

        def escalation_callback(result):
            escalation_called.append(result)

        gate = ComplianceGate(
            threshold=0.9, escalation_callback=escalation_callback
        )
        data = {"compliance_score": 0.6}

        result = gate.check(data)

        assert result.escalation_required is True
        assert len(escalation_called) == 1

    def test_compliance_gate_repr(self):
        """Test compliance gate string representation."""
        gate = ComplianceGate(threshold=0.95)
        assert "ComplianceGate" in repr(gate)


class TestPerformanceGate:
    """Test cases for PerformanceGate."""

    def test_performance_gate_creation(self):
        """Test basic performance gate creation."""
        gate = PerformanceGate()
        assert gate.name == "PerformanceGate"
        assert gate.threshold == 1000.0

    def test_performance_gate_check_pass(self):
        """Test performance gate check that passes."""
        gate = PerformanceGate(threshold=500.0, escalation_enabled=False)
        data = {"latency": 350.5}

        result = gate.check(data)

        assert result.passed is True
        assert "passes" in result.message
        assert result.metrics["latency"] == 350.5

    def test_performance_gate_check_fail(self):
        """Test performance gate check that fails."""
        gate = PerformanceGate(threshold=500.0, escalation_enabled=False)
        data = {"latency": 750.0}

        result = gate.check(data)

        assert result.passed is False
        assert "exceeds" in result.message

    def test_performance_gate_check_missing_latency(self):
        """Test performance gate with missing latency."""
        gate = PerformanceGate(threshold=500.0, escalation_enabled=False)
        data = {}

        result = gate.check(data)

        assert result.passed is False
        assert result.metrics["latency"] == float("inf")

    def test_performance_gate_escalation(self):
        """Test performance gate escalation."""
        escalation_called = []

        def escalation_callback(result):
            escalation_called.append(result)

        gate = PerformanceGate(
            threshold=500.0, escalation_callback=escalation_callback
        )
        data = {"latency": 1200.0}

        result = gate.check(data)

        assert result.escalation_required is True
        assert len(escalation_called) == 1

    def test_performance_gate_repr(self):
        """Test performance gate string representation."""
        gate = PerformanceGate(threshold=300.0)
        assert "PerformanceGate" in repr(gate)


class TestQualityGateEscalation:
    """Test escalation system across all gates."""

    def test_escalation_disabled(self):
        """Test that escalation can be disabled."""
        escalation_called = []

        def escalation_callback(result):
            escalation_called.append(result)

        gate = SecurityGate(
            threshold=0.8,
            escalation_enabled=False,
            escalation_callback=escalation_callback,
        )
        data = {"security_score": 0.5}

        result = gate.check(data)

        assert result.escalation_required is False
        assert len(escalation_called) == 0

    def test_default_escalation_handler(self, capsys):
        """Test default escalation handler prints to stdout."""
        gate = SecurityGate(threshold=0.8, escalation_enabled=True)
        data = {"security_score": 0.5}

        result = gate.check(data)

        captured = capsys.readouterr()
        assert "ESCALATION" in captured.out
        assert "SecurityGate" in captured.out

    def test_custom_escalation_callback(self):
        """Test custom escalation callback with multiple gates."""
        escalations = []

        def custom_escalation(result):
            escalations.append(
                {
                    "gate": result.gate_name,
                    "passed": result.passed,
                    "metrics": result.metrics,
                }
            )

        security_gate = SecurityGate(
            threshold=0.8, escalation_callback=custom_escalation
        )
        compliance_gate = ComplianceGate(
            threshold=0.9, escalation_callback=custom_escalation
        )

        security_gate.check({"security_score": 0.6})
        compliance_gate.check({"compliance_score": 0.7})

        assert len(escalations) == 2
        assert escalations[0]["gate"] == "SecurityGate"
        assert escalations[1]["gate"] == "ComplianceGate"
