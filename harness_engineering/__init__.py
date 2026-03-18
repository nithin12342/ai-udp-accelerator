"""
Harness Engineering Package
=============================
Specialized test environments for safely testing the AI
rate-controller with simulated network conditions.

Modules:
- test_harness: Comprehensive test harness with network simulation
- docker-compose: Docker Compose configuration for test environment

Key Features:
- Docker-based isolated environments
- Network simulation using Linux tc (traffic control)
- Configurable latency and packet loss
- Automated failure scenario testing
- Metrics collection and reporting

Usage:
    from harness_engineering import TestHarness, NetworkScenario
    
    harness = TestHarness()
    with harness.scenario_context(NetworkScenario.TRANSATLANTIC):
        # Run tests with simulated 200ms latency, 2% packet loss
        pass
"""

from .test_harness import (
    TestHarness,
    NetworkSimulator,
    NetworkScenario,
    NetworkConfig,
    TestMetrics,
    UDPTestClient
)

__all__ = [
    'TestHarness',
    'NetworkSimulator',
    'NetworkScenario',
    'NetworkConfig',
    'TestMetrics',
    'UDPTestClient'
]

__version__ = '1.0.0'
__author__ = 'NetVelocity Engineering'

# Predefined scenarios
SCENARIOS = {
    'local': NetworkScenario.LOCAL,
    'transatlantic': NetworkScenario.TRANSATLANTIC,
    'high_loss': NetworkScenario.HIGH_LOSS,
    'variable': NetworkScenario.VARIABLE_LATENCY,
    'congested': NetworkScenario.CONGESTED,
    'satellite': NetworkScenario.SATELLITE,
    'failure': NetworkScenario.FAILURE_RECOVERY,
}
