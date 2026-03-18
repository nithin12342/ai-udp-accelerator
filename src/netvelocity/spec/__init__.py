"""
Spec-Driven Engineering Package
================================
Machine-readable contract definitions for NetVelocity.

This package implements Spec-Driven Engineering principles,
ensuring perfect cross-language compatibility between 
Python sender and Java receiver through rigorous specs.

Modules:
- protobuf_spec: Protocol Buffer definitions for UDP packets
- openapi_spec: OpenAPI specification for TCP control channel
- contract_validator: Runtime contract validation

Key Concepts:
- NACK packet: Exactly 16 bytes fixed size
- ACK packet: Exactly 12 bytes fixed size
- RateControlCommand: Exactly 20 bytes fixed size
- All data structures generated from single source of truth
"""

__version__ = '1.0.0'
__author__ = 'NetVelocity Engineering'

# Package metadata
SPEC_VERSION = "1.0.0"
PROTOCOL_VERSION = 1

# Known packet sizes (from protobuf spec)
PACKET_SIZES = {
    'NACK': 16,
    'ACK': 12,
    'RateControlCommand': 20,
    'UDPDataPacket': None,  # Variable
    'SessionInitRequest': None,  # Variable
    'SessionInitResponse': None,  # Variable
}
