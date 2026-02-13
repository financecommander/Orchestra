"""Quality gates for Orchestra DSL workflows."""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
from dataclasses import dataclass, field


@dataclass
class GateResult:
    """Result of a quality gate check."""

    passed: bool
    gate_name: str
    message: str
    metrics: Dict[str, Any] = field(default_factory=dict)
    escalation_required: bool = False


class QualityGate(ABC):
    """Base class for quality gates.

    Quality gates validate workflow outputs against thresholds
    and trigger escalation when checks fail.
    """

    def __init__(
        self,
        name: str,
        threshold: float,
        escalation_enabled: bool = True,
        escalation_callback: Optional[callable] = None,
    ):
        """Initialize the quality gate.

        Args:
            name: Name of the gate
            threshold: Threshold value for the gate
            escalation_enabled: Whether to enable escalation on failure
            escalation_callback: Optional callback function for escalation
        """
        self.name = name
        self.threshold = threshold
        self.escalation_enabled = escalation_enabled
        self.escalation_callback = escalation_callback

    @abstractmethod
    def check(self, data: Dict[str, Any]) -> GateResult:
        """Check if data passes the gate.

        Args:
            data: Data to validate

        Returns:
            GateResult indicating pass/fail
        """
        pass

    def escalate(self, result: GateResult) -> None:
        """Trigger escalation for a failed gate.

        Args:
            result: Failed gate result
        """
        if self.escalation_callback:
            self.escalation_callback(result)
        else:
            # Default escalation: log the failure
            print(f"ESCALATION: {self.name} failed - {result.message}")

    def __repr__(self) -> str:
        """String representation of the gate."""
        return f"{self.__class__.__name__}(name='{self.name}', threshold={self.threshold})"


class SecurityGate(QualityGate):
    """Security quality gate.

    Validates that security_score meets or exceeds threshold.
    """

    def __init__(
        self,
        threshold: float = 0.8,
        escalation_enabled: bool = True,
        escalation_callback: Optional[callable] = None,
    ):
        """Initialize the security gate.

        Args:
            threshold: Minimum security score (0-1)
            escalation_enabled: Whether to enable escalation on failure
            escalation_callback: Optional callback function for escalation
        """
        super().__init__(
            name="SecurityGate",
            threshold=threshold,
            escalation_enabled=escalation_enabled,
            escalation_callback=escalation_callback,
        )

    def check(self, data: Dict[str, Any]) -> GateResult:
        """Check if security score passes the gate.

        Args:
            data: Data containing 'security_score' key

        Returns:
            GateResult with pass/fail status
        """
        security_score = data.get("security_score", 0.0)

        passed = security_score >= self.threshold
        message = (
            f"Security score {security_score:.2f} "
            f"{'passes' if passed else 'fails'} threshold {self.threshold:.2f}"
        )

        result = GateResult(
            passed=passed,
            gate_name=self.name,
            message=message,
            metrics={"security_score": security_score, "threshold": self.threshold},
            escalation_required=not passed and self.escalation_enabled,
        )

        if not passed and self.escalation_enabled:
            self.escalate(result)

        return result


class ComplianceGate(QualityGate):
    """Compliance quality gate.

    Validates that compliance_score meets or exceeds threshold.
    """

    def __init__(
        self,
        threshold: float = 0.9,
        escalation_enabled: bool = True,
        escalation_callback: Optional[callable] = None,
    ):
        """Initialize the compliance gate.

        Args:
            threshold: Minimum compliance score (0-1)
            escalation_enabled: Whether to enable escalation on failure
            escalation_callback: Optional callback function for escalation
        """
        super().__init__(
            name="ComplianceGate",
            threshold=threshold,
            escalation_enabled=escalation_enabled,
            escalation_callback=escalation_callback,
        )

    def check(self, data: Dict[str, Any]) -> GateResult:
        """Check if compliance score passes the gate.

        Args:
            data: Data containing 'compliance_score' key

        Returns:
            GateResult with pass/fail status
        """
        compliance_score = data.get("compliance_score", 0.0)

        passed = compliance_score >= self.threshold
        message = (
            f"Compliance score {compliance_score:.2f} "
            f"{'passes' if passed else 'fails'} threshold {self.threshold:.2f}"
        )

        result = GateResult(
            passed=passed,
            gate_name=self.name,
            message=message,
            metrics={
                "compliance_score": compliance_score,
                "threshold": self.threshold,
            },
            escalation_required=not passed and self.escalation_enabled,
        )

        if not passed and self.escalation_enabled:
            self.escalate(result)

        return result


class PerformanceGate(QualityGate):
    """Performance quality gate.

    Validates that latency is below threshold.
    """

    def __init__(
        self,
        threshold: float = 1000.0,
        escalation_enabled: bool = True,
        escalation_callback: Optional[callable] = None,
    ):
        """Initialize the performance gate.

        Args:
            threshold: Maximum latency in milliseconds
            escalation_enabled: Whether to enable escalation on failure
            escalation_callback: Optional callback function for escalation
        """
        super().__init__(
            name="PerformanceGate",
            threshold=threshold,
            escalation_enabled=escalation_enabled,
            escalation_callback=escalation_callback,
        )

    def check(self, data: Dict[str, Any]) -> GateResult:
        """Check if latency passes the gate.

        Args:
            data: Data containing 'latency' key (in milliseconds)

        Returns:
            GateResult with pass/fail status
        """
        latency = data.get("latency", float("inf"))

        passed = latency < self.threshold
        message = (
            f"Latency {latency:.2f}ms "
            f"{'passes' if passed else 'exceeds'} threshold {self.threshold:.2f}ms"
        )

        result = GateResult(
            passed=passed,
            gate_name=self.name,
            message=message,
            metrics={"latency": latency, "threshold": self.threshold},
            escalation_required=not passed and self.escalation_enabled,
        )

        if not passed and self.escalation_enabled:
            self.escalate(result)

        return result
