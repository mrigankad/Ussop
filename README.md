<div align="center">
  <img src="ussop/frontend/src/assets/logo.png" alt="Ussop Logo" width="180" style="margin-bottom: 20px;" />
  <h1 align="center">Ussop Visual Inspection Engine</h1>
  <p align="center">
    <strong>"I am the Sniper King!" — Ussop's precision, now for your production line.</strong>
  </p>
  
  <p align="center">
    <img src="https://img.shields.io/badge/Status-Active-success.svg" alt="Status" />
    <img src="https://img.shields.io/badge/Python-3.10+-blue.svg" alt="Python" />
    <img src="https://img.shields.io/badge/FastAPI-0.100+-green.svg" alt="FastAPI" />
    <img src="https://img.shields.io/badge/React-18+-61DAFB.svg" alt="React" />
    <img src="https://img.shields.io/badge/License-MIT-purple.svg" alt="License" />
  </p>
</div>

Ussop is a premium, production-ready AI visual inspection system that combines high-speed object detection (Faster R-CNN) with precise edge segmentation (NanoSAM) to automate quality control in industrial manufacturing environments—all engineered to run exceptionally fast on standard CPUs.

## 🌟 Key Features

✅ **CPU-Only** — No GPU required, runs on standard industrial PCs
✅ **Fast Deployment** — Hours to deploy, not months
✅ **Precise Segmentation** — SAM masks enable accurate measurements
✅ **Cost-Effective** — 1/3 the price of competitors like Cognex
✅ **Industrial Grade** — Modbus TCP, MQTT, OPC-UA, REST API
✅ **Production Ready** — 70+ API endpoints, JWT auth, audit logging
✅ **Premium UI/UX** — Modern 'OS-in-Browser' TypeScript dashboard with fluid light & dark modes
✅ **Real-Time Telemetry** — Live WebSockets rendering advanced Chart.js KPI analytics
✅ **Multi-Station Fleet** — Centralized panoramic overview across all connected production lines
✅ **AI Query** — Natural language questions about your inspection data
✅ **On-Device Retraining** — Fine-tune models from active-learning annotations

---

## 💻 Modern Tech Stack

<details>
<summary><strong>Frontend (OS-in-Browser UI)</strong></summary>

*   **React 18** (Vite + TypeScript)
*   **Tailwind CSS** (Custom Olive Brand Tokens, Fluid Typography, 12px Radii System)
*   **Radix UI** & **Phosphor Icons** (Accessible, Premium Aesthetics)
*   **Chart.js** (Real-time Analytics, Scatter Plots & Pareto Visualizations)
</details>

<details>
<summary><strong>Backend (Performant Web Engine)</strong></summary>

*   **FastAPI** (Async, high-throughput REST + WebSockets)
*   **SQLAlchemy** & **Alembic** (Robust ORM & Database Migrations)
*   **PyJWT** (Secure RBAC Authentication & Session Management)
*   **Redis & Prometheus** (Caching and Real-time Telemetry)
</details>

<details>
<summary><strong>AI & Computer Vision Core</strong></summary>

*   **PyTorch** & **OpenVINO** (CPU-Optimized Inference Engine)
*   **Faster R-CNN** (Real-time Defect Object Detection)
*   **NanoSAM** (Sub-millisecond Instance Segmentation)
*   **Transformers/VLM** (Natural Language Scene Understanding)
</details>

---

## 🏗️ Technical Architecture

```mermaid
graph TD
    classDef frontend fill:#4EA5D9,stroke:#333,stroke-width:2px,color:#fff;
    classDef core fill:#2A4494,stroke:#333,stroke-width:2px,color:#fff;
    classDef ml fill:#F05D5E,stroke:#333,stroke-width:2px,color:#fff;
    classDef storage fill:#2892D7,stroke:#333,stroke-width:2px,color:#fff;
    classDef ext fill:#44CFCB,stroke:#333,stroke-width:2px,color:#fff;

    UI(React SPA Dashboard):::frontend
    API(FastAPI Backend):::core
    
    subgraph Inspection Engine
        Det(Faster-RCNN Detection):::ml
        Seg(NanoSAM Segmentation):::ml
        OV(OpenVINO Optimizer):::ml
    end
    
    subgraph Services
        AL(Active Learning):::core
        VLM(Vision Language Model):::core
        Wkr(Background Workers):::core
    end
    
    subgraph Storage layer
        DB[(PostgreSQL / SQLite)]:::storage
        Cach[(Redis Cache)]:::storage
        FS[(Local Image Storage)]:::storage
    end

    subgraph Hardware & Integrations
        Cam[Cameras / CCTV]:::ext
        PLC[Modbus / OPC-UA / MQTT]:::ext
    end

    UI <-->|REST & WebSockets| API
    Cam -->|Image Streams| API
    API <--> Det
    Det --> Seg
    Seg --> OV
    API <--> AL
    API <--> VLM
    
    API <--> Cach
    API <--> DB
    API <--> FS
    
    Wkr <--> DB
    Wkr <--> Cach
    
    API -->|Hardware Signals| PLC
```

## 🔄 Inspection Workflow

```mermaid
sequenceDiagram
    participant Cam as Camera
    participant API as Server (FastAPI)
    participant ML as Inspector (CV)
    participant DB as Database
    participant UI as Dashboard (WebSockets)
    participant EXT as PLC / OPC-UA

    Cam->>API: 1. Send Frame (Trigger)
    API->>ML: 2. Process Image
    Note over ML: Detect Objects (Faster R-CNN)
    Note over ML: Generate Masks (NanoSAM)
    Note over ML: AI Query Description (VLM)
    ML-->>API: 3. Inspection Results
    API->>DB: 4. Save Record & Images
    API->>EXT: 5. Signal Modbus/OPC-UA/MQTT
    API->>UI: 6. Push Live Update (WS)
```

---

## 🚀 Quick Start

### Option 1: Docker Compose (Recommended)

```bash
cp .env.example .env        # fill in secrets
docker compose -f docker/docker-compose.yml up -d
# API:     http://localhost:8080
# UI:      http://localhost:8080
# Grafana: http://localhost:3001  (admin / admin)
```

### Option 2: Python (Development)

```bash
# 1. Download models
python scripts/download_models.py

# 2. Install dependencies
pip install -e ".[full]"

# 3. Setup database
python scripts/migrate.py upgrade

# 4. Start API
cd ussop && python run.py

# 5. Start frontend dev server (separate terminal)
cd ussop/frontend && npm install && npm run dev

# Access at http://localhost:8080
```

---

## 📁 Project Structure

```text
ussop-project/
├── ussop/                      # Production application package
│   ├── api/                    # FastAPI app + 70+ endpoints
│   ├── services/               # Core domain services (inspector, models, etc.)
│   ├── integrations/           # Modbus TCP, MQTT, Webhooks, OPC-UA server
│   ├── models/                 # SQLAlchemy ORM (9 tables)
│   ├── config/                 # Pydantic settings loading
│   ├── frontend/               # React 18 + TypeScript + Vite SPA
│   ├── tests/                  # 437 tests across 13 files — all passing
│   ├── worker.py               # Background workers (batch, training, alerts)
│   └── run.py                  # Application entry point
├── alembic/                    # Database migrations
├── docs/                       # Comprehensive documentation
├── examples/                   # Reference implementations (legacy ML code)
├── scripts/                    # Utility scripts (download_models.py, migrate.py)
├── docker/                     # Docker configuration (Nginx, Prometheus, Grafana)
├── pyproject.toml              # Dependencies (PEP 517)
├── .env.example                # Configuration template
└── README.md                   # This file
```

---

## 📚 Documentation

| Document | Description |
|---|---|
| [API Reference](docs/api.md) | All REST + WebSocket endpoints |
| [Deployment Guide](docs/deployment.md) | Docker + bare-metal setup |
| [Customer Onboarding](docs/onboarding.md) | 8-step go-live guide |
| [Architecture](docs/architecture.md) | Technical design |
| [Roadmap](docs/plan.md) | Product roadmap |

---

## ⚙️ System Requirements

- **Minimum**: Intel Core i5-10400 (6+ cores), 16GB RAM, 256GB SSD, Win10/Ubuntu 20.04
- **Recommended**: Intel Core i7-12700 (12 cores), 32GB RAM, 512GB NVMe SSD, Ubuntu 22.04 LTS

---

## 🔌 Core API Endpoints

Interactive Swagger docs available at `http://localhost:8080/docs`

| Method | Path | Description |
|---|---|---|
| `POST` | `/api/v1/inspect` | Upload and inspect image |
| `GET` | `/api/v1/inspections` | List inspection history |
| `GET` | `/api/v1/statistics` | Dashboard statistics (cached 30s) |
| `POST` | `/api/v1/query` | Natural language query |
| `POST` | `/api/v1/models/deploy` | Hot-swap inference model |
| `GET` | `/api/v1/opcua/status` | OPC-UA server status |
| `WS` | `/ws/dashboard` | Real-time dashboard push |

---

## 🛠️ Testing & Performance

- **Inference**: < 1s on Intel i5 (MobileNet + NanoSAM)
- **Throughput**: 30+ inspections/minute
- **Accuracy**: > 85% mAP (Detection), > 80% IoU (Segmentation)

```bash
# Run all tests (437 passing tests)
cd ussop
pytest tests/ -v
```

---

## 🤝 Contributing

1. Create a branch: `git checkout -b feature/name`
2. Make changes and test: `pytest tests/ -v`
3. Commit: `git commit -am "Add feature"`
4. Push and open a Pull Request

---

## 📄 License

- **License**: MIT License — See [LICENSE](LICENSE) file for details.

> **Ussop v2.0** — Sniper precision. Enterprise ready.
> *"Every defect is a target, and we never miss."*
