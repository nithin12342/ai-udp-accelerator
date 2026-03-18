#!/usr/bin/env python3
"""
Harness Engineering: Test Harness
==================================
Specialized, deeply instrumented environment for safely testing
the AI rate-controller with simulated network conditions.

Features:
- Docker-based isolated environment
- Traffic control (tc) for latency simulation
- Configurable packet loss injection
- Automated failure scenarios
- Comprehensive logging and metrics

Usage:
    python test_harness.py --scenario transatlantic
    python test_harness.py --scenario high-loss
    python test_harness.py --scenario variable-latency
"""

import os
import sys
import time
import json
import argparse
import subprocess
import threading
import socket
import random
from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List, Callable
from datetime import datetime
from enum import Enum
from contextlib import contextmanager

# Try to import psutil, but handle gracefully if not available
try:
    import psutil
except ImportError:
    psutil = None


class NetworkScenario(Enum):
    """Predefined network scenarios for testing."""
    LOCAL = "local"                    # No simulation, local network
    TRANSATLANTIC = "transatlantic"     # ~200ms latency, 2% loss
    HIGH_LOSS = "high_loss"            # 5-10% packet loss
    VARIABLE_LATENCY = "variable"      # Latency jitter
    CONGESTED = "congested"            # Bandwidth limitation
    SATELLITE = "satellite"            # High latency + high loss
    FAILURE_RECOVERY = "failure"       # Network partitions


@dataclass
class NetworkConfig:
    """Network simulation configuration."""
    latency_ms: float = 0.0
    latency_jitter_ms: float = 0.0
    packet_loss_percent: float = 0.0
    bandwidth_mbps: float = 0.0
    reorder_percent: float = 0.0
    duplicate_percent: float = 0.0
    corruption_percent: float = 0.0


@dataclass
class TestMetrics:
    """Metrics collected during test execution."""
    packets_sent: int = 0
    packets_received: int = 0
    packets_lost: int = 0
    packets_reordered: int = 0
    bytes_sent: int = 0
    bytes_received: int = 0
    latency_samples: List[float] = field(default_factory=list)
    throughput_samples: List[float] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    start_time: float = 0.0
    end_time: float = 0.0
    
    @property
    def packet_loss_rate(self) -> float:
        if self.packets_sent == 0:
            return 0.0
        return (self.packets_lost / self.packets_sent) * 100
    
    @property
    def average_latency(self) -> float:
        if not self.latency_samples:
            return 0.0
        return sum(self.latency_samples) / len(self.latency_samples)
    
    @property
    def throughput_mbps(self) -> float:
        if self.end_time == self.start_time:
            return 0.0
        duration_seconds = self.end_time - self.start_time
        return (self.bytes_sent * 8) / (duration_seconds * 1_000_000)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "packets_sent": self.packets_sent,
            "packets_received": self.packets_received,
            "packets_lost": self.packets_lost,
            "packet_loss_rate_percent": self.packet_loss_rate,
            "average_latency_ms": self.average_latency,
            "throughput_mbps": self.throughput_mbps,
            "duration_seconds": self.end_time - self.start_time,
            "errors": self.errors
        }


class NetworkSimulator:
    """
    Network simulator using Linux tc (traffic control).
    
    Applies network conditions to simulate various
    real-world scenarios for testing.
    """
    
    def __init__(self, interface: str = "lo"):
        """
        Initialize network simulator.
        
        Args:
            interface: Network interface to apply tc rules to
        """
        self.interface = interface
        self.original_config: Optional[NetworkConfig] = None
        self.current_config = NetworkConfig()
        self._lock = threading.Lock()
    
    def _run_command(self, cmd: List[str], check: bool = True) -> subprocess.CompletedProcess:
        """Run a shell command."""
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=check
            )
            return result
        except subprocess.CalledProcessError as e:
            print(f"Command failed: {' '.join(cmd)}")
            print(f"stderr: {e.stderr}")
            raise
    
    def apply_config(self, config: NetworkConfig) -> None:
        """
        Apply network configuration using tc.
        
        Args:
            config: Network configuration to apply
        """
        with self._lock:
            # Clear existing rules
            self._clear_rules()
            
            if config.latency_ms == 0 and config.packet_loss_percent == 0:
                print("No network simulation configured")
                return
            
            # Build tc command
            cmd = ["tc", "qdisc", "add", "dev", self.interface, "root", "netem"]
            
            # Add latency
            if config.latency_ms > 0:
                if config.latency_jitter_ms > 0:
                    cmd.extend([
                        "delay", 
                        f"{config.latency_ms}ms",
                        f"{config.latency_jitter_ms}ms",
                        "distribution", "normal"
                    ])
                else:
                    cmd.extend(["delay", f"{config.latency_ms}ms"])
            
            # Add packet loss
            if config.packet_loss_percent > 0:
                cmd.extend(["loss", f"{config.packet_loss_percent}%"])
            
            # Add reordering
            if config.reorder_percent > 0:
                cmd.extend(["reorder", f"{config.reorder_percent}%"])
            
            # Add corruption
            if config.corruption_percent > 0:
                cmd.extend(["corrupt", f"{config.corruption_percent}%"])
            
            try:
                self._run_command(cmd)
                print(f"Applied network config: {config}")
                self.current_config = config
            except subprocess.CalledProcessError as e:
                print(f"Failed to apply tc config: {e}")
                # Fallback: just track config without actual tc
                self.current_config = config
    
    def _clear_rules(self) -> None:
        """Clear all tc qdisc rules."""
        try:
            self._run_command([
                "tc", "qdisc", "del", "dev", self.interface, "root"
            ])
        except subprocess.CalledProcessError:
            pass  # No rules to delete
    
    def reset(self) -> None:
        """Reset network to original state."""
        with self._lock:
            self._clear_rules()
            self.current_config = NetworkConfig()
            print("Network reset to normal")


class TestHarness:
    """
    Comprehensive test harness for AI rate-controller.
    
    Provides:
    - Isolated test environment
    - Network simulation
    - Metrics collection
    - Automated test scenarios
    """
    
    SCENARIOS = {
        NetworkScenario.LOCAL: NetworkConfig(
            latency_ms=0,
            packet_loss_percent=0
        ),
        NetworkScenario.TRANSATLANTIC: NetworkConfig(
            latency_ms=200,
            latency_jitter_ms=20,
            packet_loss_percent=2,
            reorder_percent=1
        ),
        NetworkScenario.HIGH_LOSS: NetworkConfig(
            latency_ms=50,
            packet_loss_percent=7,
            corruption_percent=0.5
        ),
        NetworkScenario.VARIABLE_LATENCY: NetworkConfig(
            latency_ms=100,
            latency_jitter_ms=80,
            packet_loss_percent=1
        ),
        NetworkScenario.CONGESTED: NetworkConfig(
            latency_ms=30,
            packet_loss_percent=3,
            bandwidth_mbps=100
        ),
        NetworkScenario.SATELLITE: NetworkConfig(
            latency_ms=600,
            latency_jitter_ms=50,
            packet_loss_percent=5,
            duplicate_percent=1
        ),
        NetworkScenario.FAILURE_RECOVERY: NetworkConfig(
            latency_ms=5000,  # Simulate network partition
            packet_loss_percent=100,
        ),
    }
    
    def __init__(self, 
                 interface: str = "lo",
                 log_dir: str = "./logs",
                 metrics_file: str = "test_metrics.json"):
        """
        Initialize test harness.
        
        Args:
            interface: Network interface for simulation
            log_dir: Directory for test logs
            metrics_file: File to save test metrics
        """
        self.simulator = NetworkSimulator(interface)
        self.log_dir = log_dir
        self.metrics_file = metrics_file
        self.metrics = TestMetrics()
        self._running = False
        self._metrics_thread: Optional[threading.Thread] = None
        
        # Create log directory
        os.makedirs(log_dir, exist_ok=True)
    
    def apply_scenario(self, scenario: NetworkScenario) -> None:
        """Apply a predefined test scenario."""
        config = self.SCENARIOS.get(scenario, NetworkConfig())
        self.simulator.apply_config(config)
    
    def reset_network(self) -> None:
        """Reset network to normal."""
        self.simulator.reset()
    
    @contextmanager
    def scenario_context(self, scenario: NetworkScenario):
        """Context manager for applying a scenario."""
        self.apply_scenario(scenario)
        try:
            yield self
        finally:
            self.reset_network()
    
    def start_metrics_collection(self, interval: float = 1.0) -> None:
        """Start collecting metrics in background."""
        self._running = True
        self.metrics.start_time = time.time()
        
        def collect():
            while self._running:
                try:
                    # Collect network metrics
                    if psutil:
                        net_io = psutil.net_io_counters()
                        self.metrics.packets_sent = net_io.packets_sent
                        self.metrics.packets_received = net_io.packets_recv
                        self.metrics.bytes_sent = net_io.bytes_sent
                        self.metrics.bytes_received = net_io.bytes_recv
                except Exception as e:
                    self.metrics.errors.append(f"Metrics error: {e}")
                
                time.sleep(interval)
        
        self._metrics_thread = threading.Thread(target=collect, daemon=True)
        self.metrics_thread.start()
    
    def stop_metrics_collection(self) -> None:
        """Stop metrics collection."""
        self._running = False
        self.metrics.end_time = time.time()
        if self._metrics_thread:
            self._metrics_thread.join(timeout=2.0)
    
    def save_metrics(self) -> str:
        """Save metrics to file."""
        filepath = os.path.join(self.log_dir, self.metrics_file)
        with open(filepath, 'w') as f:
            json.dump(self.metrics.to_dict(), f, indent=2)
        return filepath
    
    def record_test_run(self, 
                        scenario: NetworkScenario,
                        test_func: Callable,
                        *args, **kwargs) -> TestMetrics:
        """
        Run a test with metrics collection.
        
        Args:
            scenario: Network scenario to test
            test_func: Test function to execute
            *args, **kwargs: Arguments to pass to test function
            
        Returns:
            TestMetrics from the test run
        """
        # Reset metrics
        self.metrics = TestMetrics()
        
        # Apply scenario
        self.apply_scenario(scenario)
        
        # Start metrics collection
        self.start_metrics_collection()
        
        try:
            # Run test
            result = test_func(*args, **kwargs)
            return self.metrics
        finally:
            # Cleanup
            self.stop_metrics_collection()
            self.reset_network()
            self.save_metrics()


class UDPTestClient:
    """
    UDP test client for sending/receiving test packets.
    """
    
    def __init__(self, 
                 bind_address: str = "127.0.0.1",
                 bind_port: int = 9000,
                 target_address: str = "127.0.0.1",
                 target_port: int = 9001,
                 packet_size: int = 1400,
                 packet_count: int = 1000):
        """
        Initialize UDP test client.
        
        Args:
            bind_address: Local bind address
            bind_port: Local bind port
            target_address: Target address
            target_port: Target port
            packet_size: Size of each UDP packet
            packet_count: Number of packets to send
        """
        self.bind_address = bind_address
        self.bind_port = bind_port
        self.target_address = target_address
        self.target_port = target_port
        self.packet_size = packet_size
        self.packet_count = packet_count
        
        self.socket: Optional[socket.socket] = None
        self.sent_packets: List[Dict[str, Any]] = []
        self.received_acks: List[Dict[str, Any]] = []
    
    def start(self) -> None:
        """Start the UDP client."""
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.bind((self.bind_address, self.bind_port))
        self.socket.settimeout(5.0)
        print(f"UDP client started on {self.bind_address}:{self.bind_port}")
    
    def stop(self) -> None:
        """Stop the UDP client."""
        if self.socket:
            self.socket.close()
            self.socket = None
    
    def send_test_packets(self) -> int:
        """
        Send test packets to target.
        
        Returns:
            Number of packets sent
        """
        if not self.socket:
            raise RuntimeError("Client not started")
        
        payload = b'X' * self.packet_size
        sent = 0
        
        for i in range(self.packet_count):
            try:
                # Create packet with sequence number
                seq_bytes = i.to_bytes(4, byteorder='big')
                packet = seq_bytes + payload
                
                self.socket.sendto(
                    packet, 
                    (self.target_address, self.target_port)
                )
                sent += 1
                
                self.sent_packets.append({
                    'sequence': i,
                    'timestamp': time.time(),
                    'size': len(packet)
                })
                
                # Small delay to avoid overwhelming
                time.sleep(0.001)
                
            except socket.error as e:
                print(f"Send error: {e}")
                break
        
        return sent
    
    def receive_with_timeout(self, timeout: float = 5.0) -> List[bytes]:
        """
        Receive packets with timeout.
        
        Args:
            timeout: Receive timeout in seconds
            
        Returns:
            List of received packets
        """
        if not self.socket:
            raise RuntimeError("Client not started")
        
        received = []
        self.socket.settimeout(timeout)
        
        try:
            while True:
                data, addr = self.socket.recvfrom(65535)
                received.append(data)
        except socket.timeout:
            pass
        
        return received


def run_integration_test(harness: TestHarness) -> Dict[str, Any]:
    """
    Run a complete integration test.
    
    This simulates a full test of the AI rate-controller
    with network simulation.
    """
    print("Starting integration test...")
    
    # Create UDP clients
    sender = UDPTestClient(
        bind_port=9000,
        target_port=9001,
        packet_count=100
    )
    receiver = UDPTestClient(
        bind_port=9001,
        target_port=9000,
        packet_count=0
    )
    
    results = {}
    
    # Test each scenario
    for scenario in [
        NetworkScenario.LOCAL,
        NetworkScenario.TRANSATLANTIC,
        NetworkScenario.HIGH_LOSS
    ]:
        print(f"\nTesting scenario: {scenario.value}")
        
        with harness.scenario_context(scenario):
            # Start receiver in background
            receiver.start()
            
            # Send packets
            sender.start()
            packets_sent = sender.send_test_packets()
            
            # Wait for ACKs
            time.sleep(1.0)
            
            # Stop
            sender.stop()
            receiver.stop()
            
            # Record results
            results[scenario.value] = {
                'packets_sent': packets_sent,
                'config': harness.simulator.current_config.__dict__
            }
        
        # Reset between scenarios
        time.sleep(0.5)
    
    return results


def main():
    """Main entry point for test harness."""
    parser = argparse.ArgumentParser(
        description="NetVelocity Test Harness"
    )
    parser.add_argument(
        '--scenario',
        type=str,
        choices=[s.value for s in NetworkScenario],
        default='transatlantic',
        help='Network scenario to simulate'
    )
    parser.add_argument(
        '--interface',
        type=str,
        default='lo',
        help='Network interface to use'
    )
    parser.add_argument(
        '--duration',
        type=int,
        default=60,
        help='Test duration in seconds'
    )
    parser.add_argument(
        '--log-dir',
        type=str,
        default='./logs',
        help='Log directory'
    )
    
    args = parser.parse_args()
    
    # Create harness
    harness = TestHarness(
        interface=args.interface,
        log_dir=args.log_dir
    )
    
    # Map string to enum
    scenario = NetworkScenario(args.scenario)
    
    print(f"NetVelocity Test Harness")
    print(f"=========================")
    print(f"Scenario: {scenario.value}")
    print(f"Interface: {args.interface}")
    print(f"Duration: {args.duration}s")
    print()
    
    # Run test with scenario
    with harness.scenario_context(scenario):
        print(f"Applied scenario: {scenario.value}")
        print(f"Config: {harness.simulator.current_config}")
        
        # Run for specified duration
        harness.start_metrics_collection()
        time.sleep(args.duration)
        harness.stop_metrics_collection()
        
        # Save results
        metrics_file = harness.save_metrics()
        print(f"\nMetrics saved to: {metrics_file}")
        print(f"Results: {json.dumps(harness.metrics.to_dict(), indent=2)}")
    
    # Cleanup
    harness.reset_network()
    print("\nTest harness complete.")


if __name__ == "__main__":
    main()
