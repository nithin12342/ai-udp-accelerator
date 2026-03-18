"""
Intent Engineering: Intent Specifications
===========================================
Declarative intent definitions for the AI rate-controller.
Implements "what to achieve" rather than "how to do it".

Key Concepts:
- Intent: Declarative goal (e.g., "maximize throughput")
- Constraints: Hard limits that must be met
- Objectives: Optimization targets with weights
- Controller: Autonomous system that fulfills intents

Usage:
    intent = IntentSpec(
        intent_type=IntentType.MAXIMIZE_THROUGHPUT,
        constraints=[Constraint(packet_loss_percent < 1.0)],
        objectives=[Objective(throughput, weight=1.0)]
    )
"""

from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List, Callable
from enum import Enum
from datetime import datetime
import json


class IntentType(Enum):
    """Types of intents the system can fulfill."""
    MAXIMIZE_THROUGHPUT = "MAXIMIZE_THROUGHPUT"
    MINIMIZE_LATENCY = "MINIMIZE_LATENCY"
    BALANCED = "BALANCED"
    CUSTOM = "CUSTOM"
    MAINTAIN_CURRENT = "MAINTAIN_CURRENT"
    ENERGY_EFFICIENT = "ENERGY_EFFICIENT"


class ConstraintOperator(Enum):
    """Operators for constraint evaluation."""
    LESS_THAN = "<"
    LESS_EQUAL = "<="
    GREATER_THAN = ">"
    GREATER_EQUAL = ">="
    EQUAL = "=="
    NOT_EQUAL = "!="


@dataclass
class Constraint:
    """
    A constraint that must be satisfied.
    
    Constraints are hard limits that the system must not violate.
    Example: packet_loss_percent < 1.0
    """
    metric: str
    operator: ConstraintOperator
    value: float
    description: str = ""
    
    def evaluate(self, context: Dict[str, Any]) -> bool:
        """
        Evaluate constraint against current context.
        
        Args:
            context: Current telemetry context
            
        Returns:
            True if constraint is satisfied
        """
        current_value = context.get(self.metric, 0.0)
        
        ops = {
            ConstraintOperator.LESS_THAN: lambda a, b: a < b,
            ConstraintOperator.LESS_EQUAL: lambda a, b: a <= b,
            ConstraintOperator.GREATER_THAN: lambda a, b: a > b,
            ConstraintOperator.GREATER_EQUAL: lambda a, b: a >= b,
            ConstraintOperator.EQUAL: lambda a, b: a == b,
            ConstraintOperator.NOT_EQUAL: lambda a, b: a != b,
        }
        
        return ops[self.operator](current_value, self.value)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "metric": self.metric,
            "operator": self.operator.value,
            "value": self.value,
            "description": self.description
        }


@dataclass
class Objective:
    """
    An optimization objective with weight.
    
    Objectives are soft targets that the system tries to optimize.
    Example: maximize throughput with weight 1.0
    """
    metric: str
    weight: float = 1.0
    target_value: Optional[float] = None
    minimize: bool = False  # True = minimize, False = maximize
    
    def score(self, context: Dict[str, Any]) -> float:
        """
        Calculate objective score for current context.
        
        Args:
            context: Current telemetry context
            
        Returns:
            Score (higher is better, scaled by weight)
        """
        current_value = context.get(self.metric, 0.0)
        
        if self.target_value is not None:
            # Score based on proximity to target
            if self.minimize:
                score = 1.0 / (1.0 + abs(current_value - self.target_value))
            else:
                score = abs(current_value - self.target_value)
        else:
            # Score based on value itself
            score = current_value if not self.minimize else 1.0 / (1.0 + current_value)
        
        return score * self.weight
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "metric": self.metric,
            "weight": self.weight,
            "target_value": self.target_value,
            "minimize": self.minimize
        }


@dataclass
class IntentSpec:
    """
    Complete intent specification for the AI controller.
    
    This is the declarative "what" that the system will
    autonomously optimize to achieve.
    """
    intent_type: IntentType
    constraints: List[Constraint] = field(default_factory=list)
    objectives: List[Objective] = field(default_factory=list)
    priority_weights: Dict[str, float] = field(default_factory=dict)
    description: str = ""
    created_at: datetime = field(default_factory=datetime.utcnow)
    expires_at: Optional[datetime] = None
    
    # Target values (simplified)
    target_packet_loss_percent: float = 1.0
    target_latency_ms: float = 100.0
    target_throughput_mbps: float = 1000.0
    
    # Configuration
    adaptation_rate: float = 0.1  # How fast to adapt (0-1)
    exploration_rate: float = 0.1  # Exploration vs exploitation
    
    def validate(self) -> bool:
        """Validate the intent specification."""
        if not self.objectives and self.intent_type != IntentType.MAINTAIN_CURRENT:
            return False
        
        if self.adaptation_rate < 0 or self.adaptation_rate > 1:
            return False
            
        return True
    
    def is_expired(self) -> bool:
        """Check if intent has expired."""
        if self.expires_at is None:
            return False
        return datetime.utcnow() > self.expires_at
    
    def evaluate_constraints(self, context: Dict[str, Any]) -> Dict[str, bool]:
        """
        Evaluate all constraints.
        
        Args:
            context: Current telemetry context
            
        Returns:
            Dictionary of constraint results
        """
        results = {}
        for constraint in self.constraints:
            results[constraint.metric] = constraint.evaluate(context)
        return results
    
    def calculate_utility(self, context: Dict[str, Any]) -> float:
        """
        Calculate total utility score.
        
        Args:
            context: Current telemetry context
            
        Returns:
            Total utility score (higher is better)
        """
        total_score = 0.0
        for objective in self.objectives:
            total_score += objective.score(context)
        
        # Apply priority weights
        for metric, weight in self.priority_weights.items():
            if metric in context:
                total_score *= weight
        
        return total_score
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "intent_type": self.intent_type.value,
            "constraints": [c.to_dict() for c in self.constraints],
            "objectives": [o.to_dict() for o in self.objectives],
            "priority_weights": self.priority_weights,
            "description": self.description,
            "created_at": self.created_at.isoformat() + "Z",
            "target_packet_loss_percent": self.target_packet_loss_percent,
            "target_latency_ms": self.target_latency_ms,
            "target_throughput_mbps": self.target_throughput_mbps,
            "adaptation_rate": self.adaptation_rate,
            "exploration_rate": self.exploration_rate
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'IntentSpec':
        """Create IntentSpec from dictionary."""
        return cls(
            intent_type=IntentType(data.get('intent_type', 'BALANCED')),
            constraints=[Constraint(**c) for c in data.get('constraints', [])],
            objectives=[Objective(**o) for o in data.get('objectives', [])],
            priority_weights=data.get('priority_weights', {}),
            description=data.get('description', ''),
            target_packet_loss_percent=data.get('target_packet_loss_percent', 1.0),
            target_latency_ms=data.get('target_latency_ms', 100.0),
            target_throughput_mbps=data.get('target_throughput_mbps', 1000.0),
            adaptation_rate=data.get('adaptation_rate', 0.1),
            exploration_rate=data.get('exploration_rate', 0.1)
        )


# Predefined intent templates
class IntentTemplates:
    """Predefined intent templates for common scenarios."""
    
    @staticmethod
    def max_throughput() -> IntentSpec:
        """Maximum throughput intent."""
        return IntentSpec(
            intent_type=IntentType.MAXIMIZE_THROUGHPUT,
            constraints=[
                Constraint("packet_loss_percent", ConstraintOperator.LESS_THAN, 1.0),
                Constraint("latency_ms", ConstraintOperator.LESS_THAN, 200.0)
            ],
            objectives=[
                Objective("throughput_mbps", weight=1.0),
            ],
            target_packet_loss_percent=0.5,
            description="Maximize throughput while keeping packet loss below 1%"
        )
    
    @staticmethod
    def low_latency() -> IntentSpec:
        """Low latency intent."""
        return IntentSpec(
            intent_type=IntentType.MINIMIZE_LATENCY,
            constraints=[
                Constraint("packet_loss_percent", ConstraintOperator.LESS_THAN, 2.0),
                Constraint("throughput_mbps", ConstraintOperator.GREATER_THAN, 10.0)
            ],
            objectives=[
                Objective("latency_ms", weight=1.0, minimize=True),
            ],
            target_latency_ms=20.0,
            description="Minimize latency while maintaining minimum throughput"
        )
    
    @staticmethod
    def balanced() -> IntentSpec:
        """Balanced throughput and latency intent."""
        return IntentSpec(
            intent_type=IntentType.BALANCED,
            constraints=[
                Constraint("packet_loss_percent", ConstraintOperator.LESS_THAN, 1.0),
            ],
            objectives=[
                Objective("throughput_mbps", weight=0.5),
                Objective("latency_ms", weight=0.5, minimize=True),
            ],
            priority_weights={
                "throughput": 0.5,
                "latency": 0.5
            },
            target_packet_loss_percent=0.5,
            target_latency_ms=50.0,
            target_throughput_mbps=500.0,
            description="Balance throughput and latency"
        )
    
    @staticmethod
    def reliable() -> IntentSpec:
        """High reliability intent (minimal packet loss)."""
        return IntentSpec(
            intent_type=IntentType.BALANCED,
            constraints=[
                Constraint("packet_loss_percent", ConstraintOperator.LESS_THAN, 0.1),
                Constraint("latency_ms", ConstraintOperator.LESS_THAN, 500.0)
            ],
            objectives=[
                Objective("packet_loss_percent", weight=2.0, minimize=True),
                Objective("throughput_mbps", weight=0.5),
            ],
            target_packet_loss_percent=0.01,
            description="Maximize reliability with minimal packet loss"
        )


# Module exports
__all__ = [
    'IntentType',
    'ConstraintOperator',
    'Constraint',
    'Objective',
    'IntentSpec',
    'IntentTemplates'
]
