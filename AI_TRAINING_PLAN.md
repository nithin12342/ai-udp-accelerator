# NetVelocity AI Training Simulation Plan for Lightning AI Platform

## Overview

This document outlines a comprehensive plan to simulate UDP data transfer and train an AI model for the NetVelocity intelligent rate control system using the Lightning AI platform.

---

## 1. Data Simulation Architecture

### 1.1 Simulation Components

```
┌─────────────────────────────────────────────────────────────────────────┐
│                     Lightning AI Training Pipeline                     │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐             │
│  │   Network    │    │    Data      │    │    Model     │             │
│  │  Simulator   │───▶│  Generator   │───▶│   Training   │             │
│  │   (tc/netem) │    │  (Synthetic) │    │  (Lightning)│             │
│  └──────────────┘    └──────────────┘    └──────────────┘             │
│         │                   │                   │                     │
│         ▼                   ▼                   ▼                     │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐             │
│  │  Real/Proxy  │    │   Dataset    │    │   Checkpoint │             │
│  │   Metrics    │    │   Storage    │    │   Storage    │             │
│  └──────────────┘    └──────────────┘    └──────────────┘             │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### 1.2 Network Scenarios to Simulate

| Scenario | Latency (ms) | Loss (%) | Jitter (ms) | Bandwidth (Mbps) |
|----------|-------------|----------|-------------|------------------|
| Ideal    | 0           | 0        | 0           | ∞                |
| LAN      | 1           | 0        | 1           | 1000             |
| Transatlantic | 200   | 2        | 20          | 100              |
| High Loss | 50         | 7        | 10          | 50               |
| Satellite | 600        | 5        | 50          | 20               |
| Variable  | 100±80     | 3        | 80          | 100              |
| Congested | 150        | 5        | 30          | 10               |

---

## 2. Data Generation Strategy

### 2.1 Synthetic Dataset Fields

```python
@dataclass
class TransferSample:
    # Input Features (Network Conditions)
    latency_ms: float
    latency_jitter_ms: float
    packet_loss_rate: float
    bandwidth_mbps: float
    cpu_usage_percent: float
    memory_usage_percent: float
    queue_depth: int
    routing_changes: int
    
    # Current Configuration
    current_rate_mbps: float
    current_window_size: int
    
    # Output Labels (What the model should predict)
    optimal_rate_mbps: float
    optimal_window_size: int
    expected_throughput_mbps: float
    expected_latency_ms: float
    expected_loss_rate: float
```

### 2.2 Data Generation Approach

1. **Rule-Based Simulation**: Use known network formulas to generate ground truth
2. **Perturbation**: Add noise to simulate real-world variations
3. **Intent-Aware**: Generate different optimal rates based on intent (throughput vs latency)

### 2.3 Dataset Size Recommendations

| Dataset Type | Samples | Use Case |
|--------------|---------|----------|
| Small | 10,000 | Quick iteration |
| Medium | 100,000 | Standard training |
| Large | 1,000,000+ | Production model |

---

## 3. Lightning AI Integration

### 3.1 Project Structure

```
lightning-project/
├── app.py                 # Lightning app entry point
├── src/
│   ├── data/
│   │   ├── dataset.py     # PyTorch Dataset
│   │   └── datamodule.py  # Lightning DataModule
│   ├── models/
│   │   ├── module.py      # Lightning Module
│   │   └── architecture.py # Neural network definition
│   └── utils/
│       ├── metrics.py     # Training metrics
│       └── config.py      # Configuration
├── configs/
│   └── config.yaml        # Training configurations
└── requirements.txt       # Dependencies
```

### 3.2 DataModule Implementation

```python
# src/data/datamodule.py
from lightning import LightningDataModule
from torch.utils.data import DataLoader

class NetVelocityDataModule(LightningDataModule):
    def __init__(self, data_dir: str, batch_size: int = 32):
        super().__init__()
        self.data_dir = data_dir
        self.batch_size = batch_size
    
    def train_dataloader(self):
        return DataLoader(
            NetVelocityDataset(self.data_dir, split='train'),
            batch_size=self.batch_size,
            shuffle=True,
            num_workers=4
        )
    
    def val_dataloader(self):
        return DataLoader(
            NetVelocityDataset(self.data_dir, split='val'),
            batch_size=self.batch_size,
            num_workers=4
        )
```

### 3.3 Model Module Implementation

```python
# src/models/module.py
import lightning as L
import torch
import torch.nn as nn

class RatePredictionModule(L.LightningModule):
    def __init__(self, input_dim: int = 11, learning_rate: float = 1e-3):
        super().__init__()
        self.save_hyperparameters()
        
        self.network = nn.Sequential(
            nn.Linear(input_dim, 128),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(128, 256),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(256, 128),
            nn.ReLU(),
            nn.Linear(128, 4)  # [rate, window, throughput, loss]
        )
        
        self.mse = nn.MSELoss()
        self.lr = learning_rate
    
    def forward(self, x):
        return self.network(x)
    
    def training_step(self, batch, batch_idx):
        x, y = batch
        pred = self.forward(x)
        loss = self.mse(pred, y)
        self.log('train_loss', loss)
        return loss
    
    def configure_optimizers(self):
        return torch.optim.Adam(self.parameters(), lr=self.lr)
```

---

## 4. Training Pipeline

### 4.1 Phase 1: Baseline Model

1. Generate synthetic dataset with rule-based labels
2. Train simple MLP model
3. Validate on held-out scenarios

### 4.2 Phase 2: Curriculum Learning

1. Start with simple scenarios (LAN, Ideal)
2. Progressively add complex scenarios
3. Increase perturbation variance

### 4.3 Phase 3: RL Fine-Tuning

1. Deploy model in simulation environment
2. Use real network feedback for online learning
3. Apply PPO or SAC algorithms

---

## 5. Lightning AI Platform Commands

### 5.1 Setup

```bash
# Install Lightning CLI
pip install lightning

# Login to Lightning AI
lightning login
```

### 5.2 Training Commands

```bash
# Local training
lightning train model.py

# Cloud training
lightning train model.py --cloud

# With custom config
lightning train model.py --config configs/config.yaml
```

### 5.3 Configuration (configs/config.yaml)

```yaml
model:
  class_path: src.models.module.RatePredictionModule
  init_args:
    input_dim: 11
    learning_rate: 1e-3

data:
  class_path: src.data.datamodule.NetVelocityDataModule
  init_args:
    data_dir: /data/netvelocity
    batch_size: 64

trainer:
  max_epochs: 100
  accelerator: auto
  devices: auto
  precision: 32
```

---

## 6. Integration with NetVelocity

### 6.1 Export Trained Model

```python
# Export for inference
model = RatePredictionModule.load_from_checkpoint("checkpoints/epoch=10.ckpt")
model.eval()

# Convert to ONNX for portability
torch.onnx.export(
    model,
    torch.randn(1, 11),
    "rate_predictor.onnx",
    input_names=['network_state'],
    output_names=['rate_prediction']
)
```

### 6.2 Inference Integration

The trained model can be integrated into the NetVelocity intent controller:

```python
# In intent_controller.py
class AIRateController:
    def __init__(self, model_path: str):
        self.model = load_onnx_model(model_path)
    
    def predict(self, telemetry_context: dict) -> RateAction:
        input_tensor = self._prepare_input(telemetry_context)
        prediction = self.model.run(input_tensor)
        return self._parse_prediction(prediction)
```

---

## 7. Success Metrics

| Metric | Target |
|--------|--------|
| Rate Prediction Error | < 10% |
| Latency Prediction Error | < 15% |
| Training Time (100K samples) | < 1 hour |
| Model Size | < 50 MB |
| Inference Latency | < 5 ms |

---

## 8. Next Steps

1. [ ] Create Lightning AI project structure
2. [ ] Implement synthetic data generator
3. [ ] Build Lightning DataModule
4. [ ] Design neural network architecture
5. [ ] Configure training pipeline
6. [ ] Run initial training experiments
7. [ ] Integrate with NetVelocity intent controller
8. [ ] Deploy to production

---

*Document Version: 1.0*
*Last Updated: 2026-03-19*
