# Ussop — AI Visual Inspection for Manufacturing

> **"I am the Sniper King!"** — Ussop's precision, now for your production line.

Ussop is a production-ready, CPU-based AI visual inspection system that combines object detection (Faster R-CNN) with precise segmentation (NanoSAM) to automate quality control in manufacturing environments.

## Key Features

✅ **CPU-Only** — No GPU required, runs on standard industrial PCs
✅ **Fast Deployment** — Hours to deploy, not months
✅ **Precise Segmentation** — SAM masks enable accurate measurements
✅ **Cost-Effective** — 1/3 the price of competitors like Cognex
✅ **Industrial Grade** — Modbus TCP, MQTT, OPC-UA, REST API
✅ **Production Ready** — 70+ API endpoints, JWT auth, audit logging
✅ **React SPA Frontend** — 10-page TypeScript UI, real-time WebSocket dashboard
✅ **Multi-Station** — Centralized overview across all inspection stations
✅ **AI Query** — Natural language questions about your inspection data
✅ **On-Device Retraining** — Fine-tune models from active-learning annotations

## Quick Start

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

## Project Structure

```
ussop-project/
├── ussop/                      # Production application package
│   ├── api/                    # FastAPI app + 70+ endpoints
│   ├── services/               # Inspector, camera, cache, trainer, deployer,
│   │                           #   active learning, monitoring, notifications,
│   │                           #   model_trainer, model_deployer, openvino_optimizer
│   ├── integrations/           # Modbus TCP, MQTT, Webhooks, OPC-UA server
│   ├── models/                 # SQLAlchemy ORM (9 tables)
│   ├── config/                 # Pydantic settings
│   ├── frontend/               # React 18 + TypeScript + Vite SPA
│   │   └── src/
│   │       ├── pages/          # Dashboard, Inspect, History, Analytics,
│   │       │                   #   Annotate, Batch, Query, Alerts, Stations, Config
│   │       ├── components/     # AppShell, Header, Sidebar, Toast, charts
│   │       └── lib/            # api.ts (typed client), cn.ts
│   ├── tests/                  # 437 tests across 13 files — all passing
│   ├── worker.py               # Background workers (batch, training, alerts, cleanup)
│   ├── run.py                  # Application entry point
│   └── setup.py                # Setup wizard
│
├── alembic/                    # Database migrations
│   ├── env.py
│   └── versions/
│
├── docs/                       # Documentation
│   ├── deployment.md           # Docker + bare-metal deployment guide
│   ├── api.md                  # REST + WebSocket API reference
│   ├── onboarding.md           # 8-step customer onboarding
│   ├── architecture.md         # Technical architecture
│   └── plan.md                 # Product roadmap
│
├── examples/                   # Reference implementations (legacy ML code)
│   ├── pipeline.py             # Detection + segmentation pipeline
│   ├── detector.py             # Faster R-CNN wrapper
│   └── predictor.py            # NanoSAM wrapper
│
├── scripts/                    # Utility scripts
│   ├── download_models.py      # Model download
│   └── migrate.py              # Alembic CLI wrapper
│
├── docker/                     # Docker configuration
│   ├── Dockerfile
│   ├── docker-compose.yml      # 7-service production stack
│   ├── nginx/nginx.conf        # TLS, gzip, rate limiting, WS proxy
│   ├── prometheus/             # Metrics scraping config
│   └── grafana/                # Dashboard provisioning
│
├── pyproject.toml              # Dependencies (PEP 517)
├── .env.example                # Configuration template
└── README.md                   # This file
```

## Documentation

| Document | Description |
|---|---|
| [API Reference](docs/api.md) | All REST + WebSocket endpoints |
| [Deployment Guide](docs/deployment.md) | Docker + bare-metal setup |
| [Customer Onboarding](docs/onboarding.md) | 8-step go-live guide |
| [Architecture](docs/architecture.md) | Technical design |
| [Roadmap](docs/plan.md) | Product roadmap |

## System Requirements

### Minimum
- **CPU**: Intel Core i5-10400 (6+ cores)
- **RAM**: 16 GB
- **Storage**: 256 GB SSD
- **OS**: Windows 10+ or Ubuntu 20.04+

### Recommended
- **CPU**: Intel Core i7-12700 (12 cores)
- **RAM**: 32 GB
- **Storage**: 512 GB NVMe SSD
- **OS**: Ubuntu 22.04 LTS

## API

Interactive Swagger docs at `http://localhost:8080/docs`

### Key Endpoints

| Method | Path | Description |
|---|---|---|
| `POST` | `/api/v1/inspect` | Upload and inspect image |
| `GET` | `/api/v1/inspections` | List inspection history |
| `GET` | `/api/v1/statistics` | Dashboard statistics (cached 30 s) |
| `GET` | `/api/v1/trends` | Trend data (cached 60 s) |
| `POST` | `/api/v1/query` | Natural language query |
| `GET` | `/api/v1/alerts` | Alert list with filters |
| `POST` | `/api/v1/batch/jobs` | Create batch job |
| `POST` | `/api/v1/training/start` | Start model fine-tuning |
| `POST` | `/api/v1/models/deploy` | Hot-swap inference model |
| `GET` | `/api/v1/opcua/status` | OPC-UA server status |
| `GET` | `/api/v1/openvino/status` | OpenVINO optimizer status |
| `GET` | `/api/v1/health` | Health check |
| `WS` | `/ws/dashboard` | Real-time dashboard push |

## Testing

```bash
# Run all tests
cd ussop
pytest tests/ -v

# Run with coverage
pytest tests/ -v --cov=. --cov-report=html

# Run a specific module
pytest tests/test_inspector.py -v
```

437 tests across 13 files — all passing.

## Configuration

Copy `.env.example` to `.env` and customize:

```env
# Core
DEBUG=false
SECRET_KEY=change-this-in-production

# Camera
CAMERA_TYPE=mock          # mock | usb | file | gige

# ML
DETECTOR_BACKBONE=mobilenet   # mobilenet | resnet50

# Integrations
MODBUS_ENABLED=false
MQTT_ENABLED=false
OPCUA_ENABLED=false           # expose OPC-UA server on port 4840
OPENVINO_ENABLED=false        # use Intel OpenVINO acceleration

# Redis (optional — in-process cache used when not set)
# REDIS_URL=redis://localhost:6379/0
```

See `.env.example` for the full list.

## Performance

- **Inference**: < 1 s on Intel i5 (MobileNet + NanoSAM)
- **Throughput**: 30+ inspections/minute
- **Memory**: < 4 GB RAM
- **Detection Accuracy**: > 85% mAP (COCO)
- **Segmentation Accuracy**: > 80% IoU

## Integrations

| Protocol | Purpose |
|---|---|
| **Modbus TCP** | PLC register write on each inspection result |
| **MQTT** | Publish inspection events to IoT broker |
| **OPC-UA** | Industry-standard machine connectivity (port 4840) |
| **Webhooks** | HTTP callbacks to external systems |
| **REST API** | Full programmatic access |
| **Email** | Alert notifications |

## Technology Stack

- **Backend**: Python 3.11, FastAPI, SQLAlchemy, Alembic
- **ML/CV**: PyTorch, TorchVision, ONNX Runtime, OpenCV, OpenVINO (optional)
- **Frontend**: React 18, TypeScript, Vite, Tailwind CSS, Chart.js, Radix UI
- **Database**: SQLite (dev) / PostgreSQL (production)
- **Cache**: Redis (optional) / in-process LRU fallback
- **Testing**: pytest (437 tests)
- **Deployment**: Docker Compose (7 services), nginx, Prometheus, Grafana

## Development

### Running in Development Mode

```bash
# Backend (hot-reload)
cd ussop
DEBUG=true python run.py

# Frontend (hot-reload, proxies /api to :8080)
cd ussop/frontend
npm run dev
```

### Contributing

1. Create a branch: `git checkout -b feature/name`
2. Make changes and test: `pytest tests/ -v`
3. Commit: `git commit -am "Add feature"`
4. Push and open a Pull Request

## License

MIT License — See LICENSE file for details.

## Support

- **Email**: founders@ussop.ai
- **Docs**: `/docs` directory
- **API**: `http://localhost:8080/docs`

---

**Ussop v2.0** — Sniper precision. Enterprise ready.

*"Every defect is a target, and we never miss."*
