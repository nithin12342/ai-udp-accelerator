"""
NetVelocity AI UDP Accelerator
==============================
Main package for AI-powered UDP acceleration with intelligent rate control.

Subpackages:
- context: Telemetry and state management
- spec: Protocol specifications and validation
- harness: Test environment and simulation
- intent: Autonomous intent-driven control

Usage:
    from netvelocity.context import TelemetryAggregator
    from netvelocity.intent import IntentController, IntentTemplates
"""

__version__ = '1.0.0'
__author__ = 'NetVelocity Engineering'

from .context import (
    TelemetryAggregator,
    ContextPipeline,
    StateManager
)

from .intent import (
    IntentController,
    IntentSpec,
    IntentTemplates,
    IntentType
)

__all__ = [
    # Context
    'TelemetryAggregator',
    'ContextPipeline', 
    'StateManager',
    # Intent
    'IntentController',
    'IntentSpec',
    'IntentTemplates',
    'IntentType'
]
