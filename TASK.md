# NetVelocity AI UDP Accelerator - Project Documentation

## Project Overview

**Project Name:** NetVelocity  
**Type:** AI-powered UDP acceleration system with intelligent rate control  
**Purpose:** Intelligent network throughput optimization using AI/ML with autonomous intent-driven control  

---

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Module Descriptions](#module-descriptions)
3. [Implementation Details](#implementation-details)
4. [Usage Guide](#usage-guide)
5. [API Specifications](#api-specifications)
6. [Testing](#testing)
7. [Configuration](#configuration)

---

## Architecture Overview

The NetVelocity system is built on six core engineering principles:

### 1. Global Earth-to-Earth Connectivity
- **Maximum Distance:** 40,000 km (equator-to-antipode)
- **Distance-Based Latency:** ~133ms minimum (speed of light in fiber)
- **Geo-Routing:** Intelligent multi-path routing across continents
- **Edge Points of Presence:** Global PoP network for optimal path selection

### 2. Multi-Speed Connection Support
- **1 Gbps Tier:** Standard enterprise connections
- **10 Gbps Tier:** High-performance data centers
- **100 Gbps Tier:** Ultra-high-speed backbone transfers
- **Auto-Bandwidth Detection:** Automatic speed negotiation and adaptation

### 3. Strong Encryption
- **TLS 1.3:** Latest transport layer security
- **AES-256-GCM:** Military-grade packet encryption
- **Post-Quantum Ready:** Lattice-based key exchange preparation
- **Hardware Security Module (HSM) Integration:** Secure key management
- **End-to-End Encryption:** All data encrypted in transit

### 4. Telemetry & State Management
- **Sliding Window:** 60-second rolling telemetry window
- **Metrics:** CPU, memory, packet loss, latency, throughput, routing changes, encryption overhead
- **Storage:** Redis-backed with in-memory fallback

### 5. Protocol Specifications  
- **Serialization:** Protocol Buffers for cross-language compatibility
- **NACK Packet:** Exactly 16 bytes fixed size (plus 32 bytes encrypted wrapper)
- **ACK Packet:** Exactly 12 bytes fixed size (plus 32 bytes encrypted wrapper)
- **Control Channel:** TCP REST API (OpenAPI 3.0) with TLS

### 6. Test Environment
- **Containerization:** Docker Compose
- **Network Simulation:** Linux tc (traffic control)
- **Scenarios:** Local, Transcontinental (40000km), Continental (10000km), Regional (1000km), High Loss (7%), Variable, Congested, Satellite, Failure Recovery

### 7. Autonomous Control
- **Intent Types:** MAXIMIZE_THROUGHPUT, MINIMIZE_LATENCY, BALANCED, RELIABLE, ENCRYPTED_MAX_SPEED
- **Constraints:** Hard limits (e.g., packet_loss < 1%, latency < 200ms)
- **Optimization:** RL-based autonomous parameter tuning with speed tier awareness

---

## Module Descriptions

### context_engineering/

#### telemetry_aggregator.py

**Purpose:** Manages sliding window of network telemetry for ML inference

**Key Classes:**
- `TelemetryPoint`: Single telemetry measurement
- `TelemetryAggregator`: Rolling window manager
- `ContextPipeline`: Formats data for ML model

**Features:**
- 60-second sliding window (configurable)
- 10 samples/second maximum
- CPU/memory monitoring via psutil
- Packet loss rate calculation
- Latency averaging and max tracking
- Throughput calculation

**Usage:**
```python
from context_engineering import TelemetryAggregator

aggregator = TelemetryAggregator(window_size_seconds=60)
aggregator.record_sample(
    latency_ms=50.0,
    bandwidth_mbps=1000.0,
    packets_sent_delta=10,
    packets_received_delta=9,
    packets_lost_delta=1
)
context = aggregator.get_ml_context()
```

---

#### state_manager.py

**Purpose:** Redis-backed rapid state retrieval

**Key Classes:**
- `StateManager`: Redis state storage
- `ConnectionState`: Network connection state
- `RateControllerState`: AI controller state

**Features:**
- Connection pooling
- Automatic JSON serialization/deserialization
- State history tracking (1000 entries)
- Thread-safe operations
- In-memory fallback when Redis unavailable

**Usage:**
```python
from context_engineering import StateManager, StateKey

manager = StateManager(use_redis=False)
manager.set("netvelocity:test", {"value": 123})
result = manager.get("netvelocity:test")
```

---

### spec_engineering/

#### protobuf_spec.proto

**Purpose:** Machine-readable contract for UDP packet structures

**Packet Definitions:**
```
UDPDataPacket    - Variable size (up to 1472 bytes)
NACKPacket       - 16 bytes fixed
ACKPacket        - 12 bytes fixed
RateControlCommand - 20 bytes fixed
TelemetryReport - Variable size
SessionInitRequest  - Variable size
InferenceRequest    - Variable size
InferenceResponse   - Variable size
```

**Field Mappings (NACK - 16 bytes):**
| Field | Bytes | Description |
|-------|-------|-------------|
| sequence_number | 4 | Missing sequence ID |
| detection_timestamp | 4 | When gap detected |
| missing_count | 4 | How many packets missing |
| priority | 4 | Urgency (1=low, 5=critical) |

**Field Mappings (ACK - 12 bytes):**
| Field | Bytes | Description |
|-------|-------|-------------|
| sequence_number | 4 | Highest received sequence |
| timestamp | 4 | ACK timestamp |
| cumulative_ack | 4 | Cumulative ACK flag |

**Generate Code:**
```bash
# Python
protoc --python_out=. protobuf_spec.proto

# Java
protoc --java_out=. protobuf_spec.proto
```

---

#### openapi_spec.yaml

**Purpose:** OpenAPI 3.0 specification for TCP control channel

**Base URL:** `tcp://localhost:8080`

**Endpoints:**

| Method | Path | Description |
|--------|------|-------------|
| POST | /api/v1/sessions | Create transfer session |
| GET | /api/v1/sessions | List active sessions |
| GET | /api/v1/sessions/{id} | Get session details |
| DELETE | /api/v1/sessions/{id} | Close session |
| GET | /api/v1/sessions/{id}/telemetry | Get current telemetry |
| GET | /api/v1/sessions/{id}/telemetry/history | Get telemetry history |
| PUT | /api/v1/sessions/{id}/intent | Update rate control intent |
| GET | /api/v1/sessions/{id}/rate | Get current rate settings |
| POST | /api/v1/inference | Request AI inference |

**Security:**
- Bearer Auth (JWT)
- API Key (X-Session-Token)

---

#### contract_validator.py

**Purpose:** Runtime validation of protocol contracts

**Validates:**
- Packet size constraints (NACK=16, ACK=12)
- Field range validation
- Protocol version compatibility
- Session state transitions

---

### harness_engineering/

#### docker-compose.yml

**Purpose:** Full Docker test environment with network simulation

**Services:**
- `netem-simulator` - Network emulator (tc)
- `udp-sender` - Python UDP sender
- `udp-receiver` - Java UDP receiver  
- `control-channel` - TCP REST API
- `ai-controller` - ML rate controller
- `redis` - State storage
- `kafka` - Event streaming
- `prometheus` - Metrics collection
- `grafana` - Dashboards
- `chaos-mesh` - Chaos engineering

**Network Profiles:**
```yaml
profiles:
  - network-sim  # Network emulation
  - sender       # UDP sender
  - receiver     # UDP receiver
  - control      # REST API
  - ai           # ML controller
  - storage      # Redis
  - streaming    # Kafka
  - monitoring   # Prometheus/Grafana
  - chaos        # Chaos engineering
```

**Usage:**
```bash
# Full stack
docker-compose up -d

# Just sender + receiver
docker-compose --profile sender --profile receiver up -d

# With monitoring
docker-compose --profile monitoring up -d
```

---

#### test_harness.py

**Purpose:** Python test harness with configurable network simulation

**Network Scenarios:**
```python
class NetworkScenario(Enum):
    LOCAL              # No simulation
    TRANSATLANTIC      # 200ms latency, 2% loss
    HIGH_LOSS         # 7% packet loss  
    VARIABLE_LATENCY  # 100ms ± 80ms jitter
    CONGESTED         # Bandwidth limited
    SATELLITE         # 600ms latency, 5% loss
    FAILURE_RECOVERY  # Network partition
```

**Configuration:**
```python
@dataclass
class NetworkConfig:
    latency_ms: float = 0.0
    latency_jitter_ms: float = 0.0
    packet_loss_percent: float = 0.0
    bandwidth_mbps: float = 0.0
    reorder_percent: float = 0.0
    duplicate_percent: float = 0.0
    corruption_percent: float = 0.0
```

**Usage:**
```python
from harness_engineering import TestHarness, NetworkScenario

harness = TestHarness(interface='lo')
with harness.scenario_context(NetworkScenario.TRANSATLANTIC):
    # Run tests with 200ms latency, 2% packet loss
    time.sleep(60)
```

---

### intent_engineering/

#### intent_spec.py

**Purpose:** Declarative intent definitions

**Intent Types:**
```python
class IntentType(Enum):
    MAXIMIZE_THROUGHPUT  # Maximize bandwidth
    MINIMIZE_LATENCY     # Minimize delay
    BALANCED            # Balance throughput/latency
    CUSTOM              # User-defined
    MAINTAIN_CURRENT    # Keep current rate
    ENERGY_EFFICIENT    # Minimize power
```

**Key Classes:**
- `Constraint`: Hard limit (e.g., packet_loss < 1%)
- `Objective`: Optimization target with weight
- `IntentSpec`: Complete intent definition
- `IntentTemplates`: Predefined intent patterns

**Usage:**
```python
from intent_engineering import IntentTemplates, IntentSpec, Constraint, Objective

# Use predefined
intent = IntentTemplates.max_throughput()

# Or create custom
intent = IntentSpec(
    intent_type=IntentType.BALANCED,
    constraints=[
        Constraint("packet_loss_percent", "<", 1.0),
        Constraint("latency_ms", "<", 200.0)
    ],
    objectives=[
        Objective("throughput_mbps", weight=1.0),
        Objective("latency_ms", weight=0.5, minimize=True)
    ],
    target_packet_loss_percent=0.5,
    target_latency_ms=50.0,
    target_throughput_mbps=500.0
)
```

---

#### intent_controller.py

**Purpose:** Autonomous RL-based rate controller

**Key Classes:**
- `IntentController`: Main controller
- `RateControllerConfig`: Configuration
- `RateAction`: Rate control action

**Configuration:**
```python
@dataclass
class RateControllerConfig:
    min_rate_mbps: float = 1.0
    max_rate_mbps: float = 10000.0
    min_window_size: int = 1
    max_window_size: int = 1000
    
    # RL parameters
    learning_rate: float = 0.1
    discount_factor: float = 0.95
    exploration_rate: float = 0.1
    
    # Adaptation
    adaptation_interval_seconds: float = 1.0
    max_rate_change_mbps: float = 500.0
```

**Usage:**
```python
from intent_engineering import IntentController, IntentTemplates

controller = IntentController(
    current_intent=IntentTemplates.balanced()
)

# Get recommended action
action = controller.get_current_action()
print(f"Rate: {action.rate_mbps} Mbps, Window: {action.window_size}")

# Start autonomous control
controller.start()
```

---

## Usage Guide

### Running the Application

```bash
# Sender mode with balanced intent
python netvelocity.py --mode sender --intent balanced

# Receiver mode  
python netvelocity.py --mode receiver

# Test mode
python netvelocity.py --mode test --scenario transatlantic
```

### Running Tests

```bash
# Run test harness
python harness_engineering/test_harness.py --scenario transatlantic

# Run with Docker
docker-compose -f harness_engineering/docker-compose.yml up -d
```

### Configuration

Environment variables:
- `REDIS_HOST` - Redis server (default: localhost)
- `REDIS_PORT` - Redis port (default: 6379)
- `LOG_LEVEL` - Logging level (default: INFO)

---

## API Specifications

### Rate Control Intent

```json
{
  "intent_type": "BALANCED",
  "constraints": [
    {"metric": "packet_loss_percent", "operator": "<=", "value": 1.0}
  ],
  "objectives": [
    {"metric": "throughput_mbps", "weight": 0.5},
    {"metric": "latency_ms", "weight": 0.5, "minimize": true}
  ],
  "target_packet_loss_percent": 0.5,
  "target_latency_ms": 50.0,
  "target_throughput_mbps": 500.0,
  "adaptation_rate": 0.1,
  "exploration_rate": 0.1
}
```

### Inference Request

```json
{
  "request_id": "uuid",
  "timestamp": "2026-03-18T00:00:00Z",
  "context": {
    "window_size_seconds": 60,
    "cpu_avg": 45.2,
    "cpu_max": 78.0,
    "memory_avg": 62.1,
    "packet_loss_rate": 0.5,
    "latency_avg_ms": 45.0,
    "latency_max_ms": 120.0,
    "throughput_avg_mbps": 850.0,
    "packets_lost_total": 150,
    "packets_sent_total": 30000,
    "routing_change_count": 2
  },
  "intent": {
    "intent_type": "BALANCED",
    "target_packet_loss_percent": 0.5
  }
}
```

### Inference Response

```json
{
  "request_id": "uuid",
  "timestamp": "2026-03-18T00:00:01Z",
  "recommended_rate_mbps": 920.0,
  "recommended_window_size": 150,
  "confidence_score": 0.87,
  "alternatives": [
    {
      "rate_mbps": 850.0,
      "window_size": 120,
      "expected_loss_rate": 0.3,
      "expected_latency_ms": 42.0,
      "utility_score": 0.82
    }
  ],
  "model_version": "1.0.0",
  "inference_time_ms": 15
}
```

---

## Testing

### Unit Tests

Test each module independently:
```bash
# Test telemetry
python -m pytest context_engineering/tests/

# Test intent controller
python -m pytest intent_engineering/tests/
```

### Integration Tests

Run with test harness:
```bash
python harness_engineering/test_harness.py --scenario transatlantic
```

### Docker Tests

```bash
# Build and test with Docker
docker-compose build
docker-compose up -d
docker-compose logs -f
```

---

## Configuration Examples

### Maximum Throughput Intent
```python
IntentSpec(
    intent_type=IntentType.MAXIMIZE_THROUGHPUT,
    constraints=[
        Constraint("packet_loss_percent", "<", 1.0),
        Constraint("latency_ms", "<", 200.0)
    ],
    target_packet_loss_percent=0.5
)
```

### Low Latency Intent
```python
IntentSpec(
    intent_type=IntentType.MINIMIZE_LATENCY,
    constraints=[
        Constraint("packet_loss_percent", "<", 2.0),
        Constraint("throughput_mbps", ">", 10.0)
    ],
    target_latency_ms=20.0
)
```

### High Reliability Intent
```python
IntentSpec(
    intent_type=IntentType.BALANCED,
    constraints=[
        Constraint("packet_loss_percent", "<", 0.1),
        Constraint("latency_ms", "<", 500.0)
    ],
    target_packet_loss_percent=0.01
)
```

---

## Git Commits

All files committed individually:

1. `819072e` - context_engineering package init
2. `a7bf4b9` - telemetry_aggregator
3. `5b0a21c` - state_manager
4. `7e5101c` - spec_engineering package init
5. `aa3d0da` - protobuf_spec.proto
6. `f5693f9` - openapi_spec.yaml
7. `2bcdd92` - contract_validator.py
8. `99bbd28` - harness_engineering package init
9. `9d2ef6c` - docker-compose.yml
10. `e6bd633` - test_harness.py
11. `4ef8400` - intent_engineering package init
12. `f4c4f75` - intent_spec.py
13. `bb13193` - intent_controller.py
14. `ffa2c36` - TASK.md
15. `d25fb07` - netvelocity.py
16. `1b60391` - .gitignore

---

*Last Updated: 2026-03-18*
*Project: NetVelocity AI UDP Accelerator*
*Version: 1.0.0*
