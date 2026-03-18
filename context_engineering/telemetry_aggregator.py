"""
Context Engineering: Telemetry Aggregator
===========================================
Implements a sliding window of network telemetry for the AI rate-controller.
Aggregates CPU load, historical packet loss, and routing table changes.

Key Features:
- Sliding window telemetry (60-second history)
- CPU load monitoring
- Packet loss tracking
- Routing change detection
- Real-time stream processing
"""

import time
import threading
from collections import deque
from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List
from datetime import datetime
import psutil
import json


@dataclass
class TelemetryPoint:
    """Single telemetry measurement point."""
    timestamp: float
    cpu_usage_percent: float
    memory_usage_percent: float
    packets_sent: int
    packets_received: int
    packets_lost: int
    latency_ms: float
    bandwidth_mbps: float
    routing_changes: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "cpu_usage_percent": self.cpu_usage_percent,
            "memory_usage_percent": self.memory_usage_percent,
            "packets_sent": self.packets_sent,
            "packets_received": self.packets_received,
            "packets_lost": self.packets_lost,
            "latency_ms": self.latency_ms,
            "bandwidth_mbps": self.bandwidth_mbps,
            "routing_changes": self.routing_changes
        }


@dataclass 
class AggregatedTelemetry:
    """Aggregated telemetry for ML model inference."""
    window_duration_seconds: int = 60
    current: Optional[TelemetryPoint] = None
    cpu_avg: float = 0.0
    cpu_max: float = 0.0
    cpu_min: float = 0.0
    memory_avg: float = 0.0
    packet_loss_rate: float = 0.0
    latency_avg_ms: float = 0.0
    latency_max_ms: float = 0.0
    throughput_avg_mbps: float = 0.0
    total_packets_sent: int = 0
    total_packets_lost: int = 0
    routing_change_count: int = 0
    window_start: float = 0.0
    window_end: float = 0.0
    
    def to_ml_context(self) -> Dict[str, Any]:
        """Format for ML model inference engine."""
        return {
            "context_window": {
                "duration_seconds": self.window_duration_seconds,
                "start": self.window_start,
                "end": self.window_end
            },
            "cpu_metrics": {
                "avg": self.cpu_avg,
                "max": self.cpu_max,
                "min": self.cpu_min
            },
            "memory_metrics": {
                "avg": self.memory_avg
            },
            "network_metrics": {
                "packet_loss_rate": self.packet_loss_rate,
                "latency_avg_ms": self.latency_avg_ms,
                "latency_max_ms": self.latency_max_ms,
                "throughput_avg_mbps": self.throughput_avg_mbps,
                "total_sent": self.total_packets_sent,
                "total_lost": self.total_packets_lost
            },
            "routing": {
                "change_count": self.routing_change_count
            }
        }


class TelemetryAggregator:
    """
    Sliding window telemetry aggregator for AI rate-controller.
    
    Maintains a rolling window of network and system metrics,
    computing aggregated statistics for ML inference.
    """
    
    def __init__(self, window_size_seconds: int = 60):
        """
        Initialize the telemetry aggregator.
        
        Args:
            window_size_seconds: Size of sliding window (default 60s)
        """
        self.window_size_seconds = window_size_seconds
        self.window: deque = deque(maxlen=window_size_seconds * 10)  # 10 samples/sec max
        self._lock = threading.RLock()
        self._last_routing_hash: Optional[str] = None
        self._sample_interval = 0.1  # 100ms
        
        # Network counters
        self._packets_sent = 0
        self._packets_received = 0
        self._packets_lost = 0
        
    def record_sample(self, 
                      latency_ms: float = 0.0, 
                      bandwidth_mbps: float = 0.0,
                      packets_sent_delta: int = 0,
                      packets_received_delta: int = 0,
                      packets_lost_delta: int = 0) -> None:
        """
        Record a single telemetry sample.
        
        Args:
            latency_ms: Current latency in milliseconds
            bandwidth_mbps: Current bandwidth in Mbps
            packets_sent_delta: New packets sent since last sample
            packets_received_delta: New packets received
            packets_lost_delta: New packets lost
        """
        # Update counters
        self._packets_sent += packets_sent_delta
        self._packets_received += packets_received_delta
        self._packets_lost += packets_lost_delta
        
        # Get system metrics
        cpu_percent = psutil.cpu_percent(interval=0.01)
        memory = psutil.virtual_memory()
        
        # Check for routing changes
        routing_changes = self._detect_routing_changes()
        
        # Create telemetry point
        point = TelemetryPoint(
            timestamp=time.time(),
            cpu_usage_percent=cpu_percent,
            memory_usage_percent=memory.percent,
            packets_sent=self._packets_sent,
            packets_received=self._packets_received,
            packets_lost=self._packets_lost,
            latency_ms=latency_ms,
            bandwidth_mbps=bandwidth_mbps,
            routing_changes=routing_changes
        )
        
        with self._lock:
            self.window.append(point)
            self._prune_old_samples()
    
    def _detect_routing_changes(self) -> int:
        """Detect routing table changes (simplified)."""
        # In production, this would parse routing table
        # For now, return 0 as placeholder
        return 0
    
    def _prune_old_samples(self) -> None:
        """Remove samples outside the sliding window."""
        cutoff_time = time.time() - self.window_size_seconds
        while self.window and self.window[0].timestamp < cutoff_time:
            self.window.popleft()
    
    def get_aggregated_telemetry(self) -> AggregatedTelemetry:
        """
        Compute aggregated telemetry for the current window.
        
        Returns:
            AggregatedTelemetry ready for ML model inference
        """
        with self._lock:
            if not self.window:
                return AggregatedTelemetry()
            
            # Get current point
            current = self.window[-1]
            
            # Calculate aggregations
            cpu_values = [p.cpu_usage_percent for p in self.window]
            memory_values = [p.memory_usage_percent for p in self.window]
            latency_values = [p.latency_ms for p in self.window if p.latency_ms > 0]
            bandwidth_values = [p.bandwidth_mbps for p in self.window if p.bandwidth_mbps > 0]
            
            total_sent = current.packets_sent - self.window[0].packets_sent
            total_lost = current.packets_lost - self.window[0].packets_lost
            
            packet_loss_rate = (total_lost / total_sent * 100) if total_sent > 0 else 0.0
            
            routing_changes = sum(p.routing_changes for p in self.window)
            
            return AggregatedTelemetry(
                window_duration_seconds=self.window_size_seconds,
                current=current,
                cpu_avg=sum(cpu_values) / len(cpu_values) if cpu_values else 0.0,
                cpu_max=max(cpu_values) if cpu_values else 0.0,
                cpu_min=min(cpu_values) if cpu_values else 0.0,
                memory_avg=sum(memory_values) / len(memory_values) if memory_values else 0.0,
                packet_loss_rate=packet_loss_rate,
                latency_avg_ms=sum(latency_values) / len(latency_values) if latency_values else 0.0,
                latency_max_ms=max(latency_values) if latency_values else 0.0,
                throughput_avg_mbps=sum(bandwidth_values) / len(bandwidth_values) if bandwidth_values else 0.0,
                total_packets_sent=total_sent,
                total_packets_lost=total_lost,
                routing_change_count=routing_changes,
                window_start=self.window[0].timestamp,
                window_end=current.timestamp
            )
    
    def get_ml_context(self) -> Dict[str, Any]:
        """
        Get formatted context for ML model inference.
        
        Returns:
            Dictionary formatted for injection into ML inference engine
        """
        aggregated = self.get_aggregated_telemetry()
        return aggregated.to_ml_context()
    
    def reset(self) -> None:
        """Reset all telemetry data."""
        with self._lock:
            self.window.clear()
            self._packets_sent = 0
            self._packets_received = 0
            self._packets_lost = 0


class ContextPipeline:
    """
    Context Engineering Pipeline that formats telemetry for ML inference.
    
    Integrates with Redis for state retrieval and formats data
    for the rate-controller AI model.
    """
    
    def __init__(self, 
                 aggregator: TelemetryAggregator,
                 redis_client: Optional[Any] = None):
        """
        Initialize the context pipeline.
        
        Args:
            aggregator: Telemetry aggregator instance
            redis_client: Optional Redis client for state retrieval
        """
        self.aggregator = aggregator
        self.redis_client = redis_client
        
    def build_inference_context(self) -> Dict[str, Any]:
        """
        Build complete context for ML inference.
        
        Combines:
        - Real-time telemetry from aggregator
        - Historical patterns from Redis
        - System state information
        
        Returns:
            Complete context dictionary for ML model
        """
        # Get current telemetry
        telemetry_context = self.aggregator.get_ml_context()
        
        # Build complete context
        context = {
            "generated_at": datetime.utcnow().isoformat() + "Z",
            "telemetry": telemetry_context,
            "system_state": self._get_system_state(),
            "inference_ready": True
        }
        
        return context
    
    def _get_system_state(self) -> Dict[str, Any]:
        """Get current system state from Redis if available."""
        if not self.redis_client:
            return {"status": "standalone", "redis_connected": False}
        
        try:
            # Get recent states from Redis
            # This would be implemented with actual Redis queries
            return {
                "status": "connected",
                "redis_connected": True,
                "state_retrieved": True
            }
        except Exception as e:
            return {
                "status": "error",
                "redis_connected": False,
                "error": str(e)
            }
    
    def inject_into_model(self, model: Any) -> Dict[str, Any]:
        """
        Inject formatted context into ML model.
        
        Args:
            model: ML model instance for inference
            
        Returns:
            Model prediction/inference result
        """
        context = self.build_inference_context()
        
        # In production, this would call model.predict(context)
        # For now, return the context structure
        return {
            "context": context,
            "model_input_ready": True
        }


# Module exports
__all__ = [
    'TelemetryPoint',
    'AggregatedTelemetry', 
    'TelemetryAggregator',
    'ContextPipeline'
]
