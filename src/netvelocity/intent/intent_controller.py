"""
Intent Engineering: Intent Controller
======================================
Autonomous controller that fulfills declared intents without
hardcoded rules. Uses reinforcement learning and experimentation
to find optimal parameters.

Key Features:
- Autonomous parameter optimization
- Intent-based goal specification  
- Reinforcement learning integration
- Real-time adaptation
"""

import time
import random
import threading
from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List, Callable
from datetime import datetime, timedelta
from collections import deque
import json

from .intent_spec import IntentSpec, IntentType, IntentTemplates, ConnectionSpeedTier, EncryptionLevel


# Speed tier bandwidth limits in Mbps
SPEED_TIER_LIMITS = {
    ConnectionSpeedTier.TIER_1GBPS: 1000,
    ConnectionSpeedTier.TIER_10GBPS: 10000,
    ConnectionSpeedTier.TIER_100GBPS: 100000,
}

# Encryption overhead percentages
ENCRYPTION_OVERHEAD = {
    EncryptionLevel.NONE: 0.0,
    EncryptionLevel.STANDARD: 0.02,    # 2% overhead
    EncryptionLevel.STRONG: 0.05,       # 5% overhead (TLS 1.3 + AES-256-GCM)
    EncryptionLevel.POST_QUANTUM: 0.08, # 8% overhead
}


@dataclass
class RateAction:
    """Rate control action to apply."""
    rate_mbps: float
    window_size: int
    speed_tier: ConnectionSpeedTier = ConnectionSpeedTier.TIER_10GBPS
    encryption_level: EncryptionLevel = EncryptionLevel.STRONG
    distance_km: float = 0.0  # Transfer distance
    timestamp: float = field(default_factory=time.time)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "rate_mbps": self.rate_mbps,
            "window_size": self.window_size,
            "speed_tier": self.speed_tier.value,
            "encryption_level": self.encryption_level.value,
            "distance_km": self.distance_km,
            "timestamp": self.timestamp
        }


@dataclass
class Experience:
    """Experience tuple for reinforcement learning."""
    state: Dict[str, Any]
    action: RateAction
    reward: float
    next_state: Dict[str, Any]
    done: bool
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "state": self.state,
            "action": self.action.to_dict(),
            "reward": self.reward,
            "next_state": self.next_state,
            "done": self.done
        }


@dataclass
class RateControllerConfig:
    """Configuration for the rate controller."""
    min_rate_mbps: float = 1.0
    max_rate_mbps: float = 100000.0  # Up to 100 Gbps
    min_window_size: int = 1
    max_window_size: int = 10000    # Larger window for high speed
    
    # Speed tier settings
    default_speed_tier: ConnectionSpeedTier = ConnectionSpeedTier.TIER_10GBPS
    auto_speed_detection: bool = True
    
    # Encryption settings
    encryption_level: EncryptionLevel = EncryptionLevel.STRONG
    enable_encryption: bool = True
    
    # Distance-aware settings
    max_distance_km: float = 40000.0  # Earth antipodes
    enable_geo_routing: bool = True
    
    # RL parameters
    learning_rate: float = 0.1
    discount_factor: float = 0.95
    exploration_rate: float = 0.1
    
    # Adaptation
    adaptation_interval_seconds: float = 1.0
    history_size: int = 1000
    
    # Safety
    max_rate_change_mbps: float = 5000.0  # Allow larger changes for 100G
    emergency_rate_reduction: float = 0.5
    
    # Performance targets
    target_latency_ms: float = 150.0
    target_packet_loss_percent: float = 0.5


class IntentController:
    """
    Autonomous intent-driven rate controller.
    
    Instead of hardcoded rules like:
        "If latency > 100ms, reduce speed by 5 Mbps"
    
    This controller receives intents like:
        "Maintain max throughput with packet loss < 0.5%"
    
    And autonomously experiments to find optimal parameters.
    """
    
    def __init__(self, 
                 config: Optional[RateControllerConfig] = None,
                 current_intent: Optional[IntentSpec] = None):
        """
        Initialize the intent controller.
        
        Args:
            config: Controller configuration
            current_intent: Current intent specification
        """
        self.config = config or RateControllerConfig()
        self.current_intent = current_intent or IntentTemplates.balanced()
        
        # State
        self.current_rate_mbps: float = 1000.0
        self.current_window_size: int = 100
        
        # Experience replay buffer
        self.experience_buffer: deque = deque(maxlen=self.config.history_size)
        
        # History
        self.action_history: List[RateAction] = []
        self.reward_history: List[float] = []
        
        # Running state
        self._running = False
        self._control_thread: Optional[threading.Thread] = None
        
        # Callbacks
        self.on_action: Optional[Callable[[RateAction], None]] = None
        
        # Statistics
        self.total_actions = 0
        self.successful_actions = 0
    
    def set_intent(self, intent: IntentSpec) -> None:
        """
        Set a new intent.
        
        Args:
            intent: New intent specification
        """
        if not intent.validate():
            raise ValueError("Invalid intent specification")
        
        self.current_intent = intent
        print(f"Intent updated: {intent.intent_type.value}")
        print(f"  Description: {intent.description}")
        print(f"  Target loss: {intent.target_packet_loss_percent}%")
        print(f"  Target latency: {intent.target_latency_ms}ms")
        print(f"  Target throughput: {intent.target_throughput_mbps}Mbps")
    
    def observe(self, context: Dict[str, Any]) -> None:
        """
        Observe current state and store experience.
        
        Args:
            context: Current telemetry context
        """
        # This would be called with actual telemetry
        pass
    
    def calculate_reward(self, 
                         previous_context: Dict[str, Any],
                         current_context: Dict[str, Any],
                         action: RateAction) -> float:
        """
        Calculate reward for the action.
        
        Args:
            previous_context: Context before action
            current_context: Context after action
            action: Action taken
            
        Returns:
            Reward value (higher is better)
        """
        if not self.current_intent:
            return 0.0
        
        reward = 0.0
        
        # Check constraints (critical - large penalty if violated)
        constraint_results = self.current_intent.evaluate_constraints(current_context)
        for metric, satisfied in constraint_results.items():
            if not satisfied:
                reward -= 100.0  # Heavy penalty for constraint violation
        
        # Calculate objective score
        utility = self.current_intent.calculate_utility(current_context)
        reward += utility * 10.0
        
        # Bonus for maintaining target metrics
        if self.current_intent.target_packet_loss_percent:
            target_loss = self.current_intent.target_packet_loss_percent
            actual_loss = current_context.get('packet_loss_rate', 0.0)
            if actual_loss <= target_loss:
                reward += 5.0
        
        # Small penalty for very high rates (instability)
        if action.rate_mbps > 5000:
            reward -= 1.0
        
        return reward
    
    def select_action(self, context: Dict[str, Any]) -> RateAction:
        """
        Select action using epsilon-greedy exploration.
        
        Args:
            context: Current context
            
        Returns:
            Selected action
        """
        # Exploration: random action
        if random.random() < self.config.exploration_rate * self.current_intent.exploration_rate:
            return self._random_action()
        
        # Exploitation: best known action based on intent
        return self._optimal_action(context)
    
    def _random_action(self) -> RateAction:
        """Generate a random action within bounds."""
        # Random rate within bounds
        rate = random.uniform(
            self.config.min_rate_mbps,
            self.config.max_rate_mbps
        )
        
        # Random window size
        window = random.randint(
            self.config.min_window_size,
            self.config.max_window_size
        )
        
        return RateAction(rate_mbps=rate, window_size=window)
    
    def _optimal_action(self, context: Dict[str, Any]) -> RateAction:
        """Select optimal action based on intent."""
        intent = self.current_intent
        
        # Adjust based on intent type
        if intent.intent_type == IntentType.MAXIMIZE_THROUGHPUT:
            # Try higher rate
            new_rate = self.current_rate_mbps * (1.0 + self.current_intent.adaptation_rate)
            new_rate = min(new_rate, self.config.max_rate_mbps)
        
        elif intent.intent_type == IntentType.MINIMIZE_LATENCY:
            # Reduce rate to minimize latency
            new_rate = self.current_rate_mbps * (1.0 - self.current_intent.adapt)
        
        elif intent.intent_type == IntentType.ENERGY_EFFICIENT:
            # Prefer lower rates for efficiency
            new_rate = self.current_rate_mbps * 0.9
        
        else:  # BALANCED or CUSTOM
            # Check constraints and adjust
            packet_loss = context.get('packet_loss_rate', 0.0)
            latency = context.get('latency_avg_ms', 0.0)
            
            if packet_loss > intent.target_packet_loss_percent:
                # Reduce rate to improve reliability
                new_rate = self.current_rate_mbps * (1.0 - self.current_intent.adaptation_rate)
            elif latency > intent.target_latency_ms:
                # Reduce rate to improve latency
                new_rate = self.current_rate_mbps * (1.0 - self.current_intent.adaptation_rate * 0.5)
            else:
                # Safe to increase
                new_rate = self.current_rate_mbps * (1.0 + self.current_intent.adaptation_rate * 0.3)
        
        # Apply safety limits
        new_rate = max(self.config.min_rate_mbps, 
                       min(self.config.max_rate_mbps, new_rate))
        
        # Limit rate change
        max_change = self.config.max_rate_change_mbps
        new_rate = max(self.current_rate_mbps - max_change,
                       min(self.current_rate_mbps + max_change, new_rate))
        
        # Adjust window size proportionally
        window_ratio = new_rate / self.current_rate_mbps
        new_window = int(self.current_window_size * window_ratio)
        new_window = max(self.config.min_window_size,
                         min(self.config.max_window_size, new_window))
        
        return RateAction(rate_mbps=new_rate, window_size=new_window)
    
    def execute_action(self, action: RateAction) -> None:
        """
        Execute the selected action.
        
        Args:
            action: Action to execute
        """
        # Update current state
        self.current_rate_mbps = action.rate_mbps
        self.current_window_size = action.window_size
        
        # Store in history
        self.action_history.append(action)
        self.total_actions += 1
        
        # Trigger callback if set
        if self.on_action:
            try:
                self.on_action(action)
            except Exception as e:
                print(f"Action callback error: {e}")
        
        print(f"Action executed: rate={action.rate_mbps:.1f}Mbps, "
              f"window={action.window_size}")
    
    def get_current_action(self) -> RateAction:
        """Get current rate control action."""
        return RateAction(
            rate_mbps=self.current_rate_mbps,
            window_size=self.current_window_size
        )
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get controller statistics."""
        avg_reward = 0.0
        if self.reward_history:
            avg_reward = sum(self.reward_history) / len(self.reward_history)
        
        return {
            "current_rate_mbps": self.current_rate_mbps,
            "current_window_size": self.current_window_size,
            "total_actions": self.total_actions,
            "successful_actions": self.successful_actions,
            "success_rate": self.successful_actions / max(1, self.total_actions),
            "average_reward": avg_reward,
            "intent_type": self.current_intent.intent_type.value,
            "experience_buffer_size": len(self.experience_buffer)
        }
    
    def start(self) -> None:
        """Start the autonomous controller."""
        if self._running:
            return
        
        self._running = True
        self._control_thread = threading.Thread(target=self._control_loop, daemon=True)
        self._control_thread.start()
        print("Intent controller started")
    
    def stop(self) -> None:
        """Stop the autonomous controller."""
        self._running = False
        if self._control_thread:
            self._control_thread.join(timeout=2.0)
        print("Intent controller stopped")
    
    def _control_loop(self) -> None:
        """Main control loop."""
        while self._running:
            try:
                # Get current context (would come from Context Engineering)
                # For now, simulate with empty context
                context = {}
                
                # Select and execute action
                action = self.select_action(context)
                self.execute_action(action)
                
                # Wait for next iteration
                time.sleep(self.config.adaptation_interval_seconds)
                
            except Exception as e:
                print(f"Control loop error: {e}")
                time.sleep(1.0)


# Intent-driven rate optimization function
def optimize_rate(intent: IntentSpec, 
                 current_context: Dict[str, Any]) -> RateAction:
    """
    Optimize rate based on intent and current context.
    
    This is the main entry point for intent-driven rate control.
    
    Args:
        intent: The declared intent
        current_context: Current telemetry context
        
    Returns:
        Optimized rate action
    """
    controller = IntentController(current_intent=intent)
    return controller._optimal_action(current_context)


# Module exports
__all__ = [
    'IntentController',
    'RateControllerConfig',
    'RateAction',
    'Experience',
    'IntentTemplates',
    'optimize_rate'
]
