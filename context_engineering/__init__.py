"""
Context Engineering Package
============================
Architectural practice for ensuring the AI rate-controller has
the exact right information at the exact right time.

Modules:
- telemetry_aggregator: Sliding window telemetry management
- state_manager: Redis-backed rapid state retrieval

Key Classes:
- TelemetryAggregator: Manages rolling window of network telemetry
- ContextPipeline: Formats data for ML model injection
- StateManager: Redis-backed state storage and retrieval
"""

from .telemetry_aggregator import (
    TelemetryPoint,
    AggregatedTelemetry,
    TelemetryAggregator,
    ContextPipeline
)

from .state_manager import (
    StateKey,
    ConnectionState,
    RateControllerState,
    StateManager
)

__all__ = [
    # Telemetry
    'TelemetryPoint',
    'AggregatedTelemetry', 
    'TelemetryAggregator',
    'ContextPipeline',
    # State Management
    'StateKey',
    'ConnectionState',
    'RateControllerState',
    'StateManager'
]

__version__ = '1.0.0'
__author__ = 'NetVelocity Engineering'
