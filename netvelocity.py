#!/usr/bin/env python3
"""
NetVelocity AI UDP Accelerator
===============================
Main integration module that combines all components:
- Telemetry aggregation (Context)
- Protocol specifications (Spec-Driven)  
- Test harness (Harness)
- Autonomous intent control (Intent)

Usage:
    python netvelocity.py --mode sender --intent balanced
    python netvelocity.py --mode receiver
    python netvelocity.py --mode test --scenario transatlantic
"""

import argparse
import sys
import time
import signal
from typing import Optional

# Import all engineering modules
from context_engineering import (
    TelemetryAggregator,
    ContextPipeline,
    StateManager
)

from intent_engineering import (
    IntentController,
    IntentTemplates,
    IntentSpec,
    IntentType
)

from harness_engineering import (
    TestHarness,
    NetworkScenario
)


class NetVelocityApp:
    """
    Main NetVelocity application integrating all components.
    """
    
    def __init__(self, 
                 mode: str = "sender",
                 intent_type: str = "balanced",
                 redis_host: str = "localhost",
                 redis_port: int = 6379):
        """
        Initialize NetVelocity application.
        
        Args:
            mode: Operating mode (sender, receiver, test)
            intent_type: Intent type for rate control
            redis_host: Redis server host
            redis_port: Redis server port
        """
        self.mode = mode
        self.running = False
        
        # Initialize telemetry
        self.telemetry = TelemetryAggregator(window_size_seconds=60)
        
        # Initialize state manager
        self.state_manager = StateManager(
            redis_host=redis_host,
            redis_port=redis_port,
            use_redis=False  # Use in-memory store by default
        )
        
        # Initialize context pipeline
        self.context_pipeline = ContextPipeline(
            aggregator=self.telemetry,
            redis_client=None
        )
        
        # Initialize intent controller
        self.intent = self._create_intent(intent_type)
        self.controller = IntentController(current_intent=self.intent)
        
        # Initialize test harness (for testing mode)
        self.harness: Optional[TestHarness] = None
        
        print(f"NetVelocity initialized in {mode} mode")
        print(f"Intent: {intent_type}")
    
    def _create_intent(self, intent_type: str) -> IntentSpec:
        """Create intent specification based on type."""
        templates = {
            "max_throughput": IntentTemplates.max_throughput(),
            "low_latency": IntentTemplates.low_latency(),
            "balanced": IntentTemplates.balanced(),
            "reliable": IntentTemplates.reliable(),
        }
        return templates.get(intent_type, IntentTemplates.balanced())
    
    def start(self) -> None:
        """Start the application."""
        self.running = True
        
        if self.mode == "test":
            self._run_test_mode()
        else:
            self._run_control_loop()
    
    def stop(self) -> None:
        """Stop the application."""
        self.running = False
        self.controller.stop()
        self.state_manager.close()
        print("NetVelocity stopped")
    
    def _run_control_loop(self) -> None:
        """Run main control loop."""
        print("Starting control loop...")
        
        # Start intent controller
        self.controller.start()
        
        # Set up signal handler
        def signal_handler(sig, frame):
            self.stop()
            sys.exit(0)
        
        signal.signal(signal.SIGINT, signal_handler)
        
        try:
            while self.running:
                # Record telemetry sample
                self.telemetry.record_sample(
                    latency_ms=50.0,
                    bandwidth_mbps=self.controller.current_rate_mbps,
                    packets_sent_delta=10,
                    packets_received_delta=9,
                    packets_lost_delta=1
                )
                
                # Get ML context
                context = self.context_pipeline.build_inference_context()
                
                # Get current action
                action = self.controller.get_current_action()
                
                # Print status
                print(f"Rate: {action.rate_mbps:.1f} Mbps | "
                      f"Window: {action.window_size} | "
                      f"Loss: {self.telemetry.get_aggregated_telemetry().packet_loss_rate:.2f}%")
                
                time.sleep(1.0)
                
        except Exception as e:
            print(f"Error in control loop: {e}")
            self.stop()
    
    def _run_test_mode(self) -> None:
        """Run in test mode with harness."""
        print("Running test mode...")
        
        self.harness = TestHarness()
        
        # Test each scenario
        scenarios = [
            NetworkScenario.LOCAL,
            NetworkScenario.TRANSATLANTIC,
            NetworkScenario.HIGH_LOSS
        ]
        
        for scenario in scenarios:
            print(f"\n=== Testing {scenario.value} ===")
            with self.harness.scenario_context(scenario):
                time.sleep(5)  # Run for 5 seconds per scenario
        
        # Save results
        self.harness.save_metrics()
        print("\nTest complete!")
    
    def update_intent(self, intent_type: str) -> None:
        """Update the current intent."""
        self.intent = self._create_intent(intent_type)
        self.controller.set_intent(self.intent)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="NetVelocity AI UDP Accelerator"
    )
    
    parser.add_argument(
        '--mode',
        type=str,
        choices=['sender', 'receiver', 'test'],
        default='sender',
        help='Operating mode'
    )
    
    parser.add_argument(
        '--intent',
        type=str,
        choices=['max_throughput', 'low_latency', 'balanced', 'reliable'],
        default='balanced',
        help='Intent type for rate control'
    )
    
    parser.add_argument(
        '--redis-host',
        type=str,
        default='localhost',
        help='Redis host'
    )
    
    parser.add_argument(
        '--redis-port',
        type=int,
        default=6379,
        help='Redis port'
    )
    
    parser.add_argument(
        '--scenario',
        type=str,
        help='Test scenario (for test mode)'
    )
    
    args = parser.parse_args()
    
    # Create and start application
    app = NetVelocityApp(
        mode=args.mode,
        intent_type=args.intent,
        redis_host=args.redis_host,
        redis_port=args.redis_port
    )
    
    app.start()


if __name__ == "__main__":
    main()
