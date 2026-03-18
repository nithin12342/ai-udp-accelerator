"""
Spec-Driven Engineering: Contract Validator
=============================================
Validates that implementations conform to the protobuf and OpenAPI specs.
Ensures perfect cross-language compatibility between Python and Java.

Key Features:
- Protobuf message validation
- OpenAPI schema validation
- Message size enforcement
- Field boundary checking
"""

import struct
import json
from typing import Any, Dict, Optional, List, Tuple
from dataclasses import dataclass
from enum import Enum
from abc import ABC, abstractmethod


class ValidationResult:
    """Result of a validation check."""
    
    def __init__(self, valid: bool, message: str = "", field: str = ""):
        self.valid = valid
        self.message = message
        self.field = field
    
    def __bool__(self) -> bool:
        return self.valid
    
    def __str__(self) -> str:
        return f"{'✓' if self.valid else '✗'} {self.field}: {self.message}"


class ContractType(Enum):
    """Contract types for validation."""
    UDP_DATA_PACKET = "udp_data_packet"
    NACK_PACKET = "nack_packet"
    ACK_PACKET = "ack_packet"
    RATE_CONTROL_COMMAND = "rate_control_command"
    TELEMETRY_REPORT = "telemetry_report"
    SESSION_INIT_REQUEST = "session_init_request"
    INFERENCE_REQUEST = "inference_request"


# Fixed sizes from protobuf spec
FIXED_SIZES = {
    ContractType.NACK_PACKET: 16,
    ContractType.ACK_PACKET: 12,
    ContractType.RATE_CONTROL_COMMAND: 20,
}

# Field boundaries
FIELD_BOUNDS = {
    "sequence_number": (0, 0xFFFFFFFF),
    "timestamp": (0, 0xFFFFFFFF),
    "target_rate_mbps": (0, 100000),  # 100 Gbps max
    "window_size": (1, 100000),
    "priority": (1, 5),
    "cpu_usage_percent": (0.0, 100.0),
    "memory_usage_percent": (0.0, 100.0),
    "packet_loss_rate": (0.0, 100.0),
    "latency_ms": (0.0, 100000.0),  # 100 seconds max
    "bandwidth_mbps": (0.0, 100000.0),
}


class ContractValidator(ABC):
    """Abstract base class for contract validators."""
    
    @abstractmethod
    def validate(self, data: Any) -> List[ValidationResult]:
        """Validate data against contract."""
        pass
    
    @abstractmethod
    def get_contract_type(self) -> ContractType:
        """Get the contract type."""
        pass


class NACKPacketValidator(ContractValidator):
    """
    Validates NACK (Negative Acknowledgment) packets.
    Must be exactly 16 bytes with specific field layout.
    
    Layout:
    - Bytes 0-3: sequence_number (uint32)
    - Bytes 4-7: detection_timestamp (uint32)
    - Bytes 8-11: missing_count (uint32)
    - Bytes 12-15: priority (uint32)
    """
    
    FIXED_SIZE = 16
    
    def get_contract_type(self) -> ContractType:
        return ContractType.NACK_PACKET
    
    def validate(self, data: Any) -> List[ValidationResult]:
        results = []
        
        # Check if data is bytes
        if isinstance(data, bytes):
            results.extend(self._validate_bytes(data))
        elif isinstance(data, dict):
            results.extend(self._validate_dict(data))
        else:
            results.append(ValidationResult(
                False, 
                f"Expected bytes or dict, got {type(data).__name__}",
                "input_type"
            ))
        
        return results
    
    def _validate_bytes(self, data: bytes) -> List[ValidationResult]:
        """Validate raw bytes."""
        results = []
        
        # Size check
        if len(data) != self.FIXED_SIZE:
            results.append(ValidationResult(
                False,
                f"Expected {self.FIXED_SIZE} bytes, got {len(data)}",
                "packet_size"
            ))
            return results
        
        # Parse fields
        try:
            sequence_number = struct.unpack('>I', data[0:4])[0]
            detection_timestamp = struct.unpack('>I', data[4:8])[0]
            missing_count = struct.unpack('>I', data[8:12])[0]
            priority = struct.unpack('>I', data[12:16])[0]
            
            # Validate bounds
            results.append(self._validate_field("sequence_number", sequence_number))
            results.append(self._validate_field("priority", priority))
            
        except struct.error as e:
            results.append(ValidationResult(False, str(e), "unpack"))
        
        return results
    
    def _validate_dict(self, data: dict) -> List[ValidationResult]:
        """Validate dictionary representation."""
        results = []
        
        required_fields = ["sequence_number", "detection_timestamp", "missing_count", "priority"]
        
        for field in required_fields:
            if field not in data:
                results.append(ValidationResult(False, f"Missing required field", field))
        
        if not results:
            # Validate field bounds
            for field, value in data.items():
                if field in FIELD_BOUNDS:
                    results.append(self._validate_field(field, value))
        
        return results
    
    def _validate_field(self, field_name: str, value: Any) -> ValidationResult:
        """Validate a single field against bounds."""
        if field_name not in FIELD_BOUNDS:
            return ValidationResult(True, "", field_name)
        
        min_val, max_val = FIELD_BOUNDS[field_name]
        
        if isinstance(value, (int, float)):
            if not (min_val <= value <= max_val):
                return ValidationResult(
                    False,
                    f"Value {value} outside bounds [{min_val}, {max_val}]",
                    field_name
                )
        
        return ValidationResult(True, "", field_name)


class ACKPacketValidator(ContractValidator):
    """
    Validates ACK (Acknowledgment) packets.
    Must be exactly 12 bytes.
    """
    
    FIXED_SIZE = 12
    
    def get_contract_type(self) -> ContractType:
        return ContractType.ACK_PACKET
    
    def validate(self, data: Any) -> List[ValidationResult]:
        results = []
        
        if isinstance(data, bytes):
            if len(data) != self.FIXED_SIZE:
                results.append(ValidationResult(
                    False,
                    f"Expected {self.FIXED_SIZE} bytes, got {len(data)}",
                    "packet_size"
                ))
            else:
                results.append(ValidationResult(True, "", "packet_size"))
        
        elif isinstance(data, dict):
            required = ["sequence_number", "timestamp", "cumulative_ack"]
            for field in required:
                if field not in data:
                    results.append(ValidationResult(False, f"Missing field", field))
        
        return results


class RateControlCommandValidator(ContractValidator):
    """
    Validates Rate Control Command packets.
    Must be exactly 20 bytes.
    """
    
    FIXED_SIZE = 20
    
    def get_contract_type(self) -> ContractType:
        return ContractType.RATE_CONTROL_COMMAND
    
    def validate(self, data: Any) -> List[ValidationResult]:
        results = []
        
        if isinstance(data, bytes):
            if len(data) != self.FIXED_SIZE:
                results.append(ValidationResult(
                    False,
                    f"Expected {self.FIXED_SIZE} bytes, got {len(data)}",
                    "packet_size"
                ))
        
        elif isinstance(data, dict):
            required = ["command_id", "target_rate_mbps", "window_size", "timestamp", "flags"]
            for field in required:
                if field not in data:
                    results.append(ValidationResult(False, f"Missing field", field))
            
            # Validate bounds
            if "target_rate_mbps" in data:
                results.append(self._validate_bound("target_rate_mbps", data["target_rate_mbps"]))
            if "window_size" in data:
                results.append(self._validate_bound("window_size", data["window_size"]))
        
        return results
    
    def _validate_bound(self, field: str, value: Any) -> ValidationResult:
        if field not in FIELD_BOUNDS:
            return ValidationResult(True, "", field)
        
        min_val, max_val = FIELD_BOUNDS[field]
        if not (min_val <= value <= max_val):
            return ValidationResult(False, f"Out of bounds", field)
        
        return ValidationResult(True, "", field)


class UDPDataPacketValidator(ContractValidator):
    """
    Validates UDP Data packets.
    Max size: 1472 bytes (with IP/UDP headers)
    """
    
    MAX_SIZE = 1472
    MIN_PAYLOAD_SIZE = 1
    
    def get_contract_type(self) -> ContractType:
        return ContractType.UDP_DATA_PACKET
    
    def validate(self, data: Any) -> List[ValidationResult]:
        results = []
        
        if isinstance(data, bytes):
