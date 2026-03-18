"""
Intent Engineering Package
==========================
Declarative goal specification for autonomous rate control.

Implements the shift from imperative programming ("how to do it")
to declarative programming ("what the desired outcome is").

Modules:
- intent_spec: Declarative intent definitions and constraints
- intent_controller: Autonomous controller for intent fulfillment

Key Concepts:
- Intent: What to achieve (not how to achieve it)
- Constraints: Hard limits that must not be violated
- Objectives: Soft targets to optimize toward
- Controller: Autonomous system that experiments to fulfill intents

Usage:
    from intent_engineering import IntentTemplates, IntentController
    
    # Use predefined intent
    intent = IntentTemplates.max_throughput()
    
    # Or create custom
    intent = IntentSpec(
        intent_type=IntentType.BALANCED,
        constraints=[Constraint("packet_loss_percent", "<", 1.0)],
        objectives=[Objective("throughput_mbps", weight=1.0)]
    )
    
    # Autonomous controller
    controller = IntentController(current_intent=intent)
    controller.start()
"""

from .intent_spec import (
    IntentType,
    ConstraintOperator,
    Constraint,
    Objective,
    IntentSpec,
    IntentTemplates
)

from .intent_controller import (
    IntentController,
    RateControllerConfig,
    RateAction,
    Experience,
    optimize_rate
)

__all__ = [
    # Intent specifications
    'IntentType',
    'ConstraintOperator',
    'Constraint',
    'Objective',
    'IntentSpec',
    'IntentTemplates',
    # Controller
    'IntentController',
    'RateControllerConfig',
    'RateAction',
    'Experience',
    'optimize_rate'
]

__version__ = '1.0.0'
__author__ = 'NetVelocity Engineering'
