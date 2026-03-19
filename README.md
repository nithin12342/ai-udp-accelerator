# NetVelocity AI UDP Accelerator

**Enterprise-grade AI-driven UDP acceleration and CDC pipeline for high-speed, fault-tolerant global data migration.**

---

## Key Features

### 🌐 Global Earth-to-Earth Connectivity
- Supports transfers up to **40,000 km** (antipodes)
- Intelligent geo-routing across continents
- Distance-aware latency optimization (~133ms minimum via fiber)

### ⚡ Multi-Speed Tier Support
- **1 Gbps** - Standard enterprise connections
- **10 Gbps** - High-performance data centers
- **100 Gbps** - Ultra-high-speed backbone transfers
- Auto-bandwidth detection and adaptation

### 🔒 Strong Encryption
- **TLS 1.3** - Latest transport layer security
- **AES-256-GCM** - Military-grade packet encryption
- **Post-Quantum Ready** - Lattice-based key exchange preparation
- Hardware Security Module (HSM) integration

### 🤖 AI-Powered Rate Control
- Reinforcement learning-based autonomous optimization
- Real-time adaptation to network conditions
- Intent-driven (MAXIMIZE_THROUGHPUT, MINIMIZE_LATENCY, BALANCED, ENCRYPTED_MAX_SPEED)

### 🛡️ Low Latency, Low Loss
- Intelligent packet loss recovery
- Adaptive congestion control
- Sub-150ms latency optimization

---

## Quick Start

```bash
# Sender mode with balanced intent
python netvelocity.py --mode sender --intent balanced

# Receiver mode  
python netvelocity.py --mode receiver

# Test mode with global scenario
python netvelocity.py --mode test --scenario global_antipodes
```

---

## Architecture

- **Telemetry & State Management**: Redis-backed with 60-second sliding window
- **Protocol**: Protocol Buffers for cross-language compatibility
- **Control Channel**: TCP REST API (OpenAPI 3.0) with TLS
- **Autonomous Control**: RL-based intent fulfillment

---

## Documentation

See [TASK.md](TASK.md) for detailed documentation.

See [AI_TRAINING_PLAN.md](AI_TRAINING_PLAN.md) for AI model training on Lightning AI platform.

---

## License

Proprietary - NetVelocity Engineering
