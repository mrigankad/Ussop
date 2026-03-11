# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.0.0] - 2026-03-10

### Added — Enterprise Features

- **React SPA Frontend**
  - Full TypeScript + Vite + Tailwind CSS rebuild of the web UI
  - 10 pages: Dashboard, Inspect, History, Analytics, Annotate, Batch, AI Query, Stations, Alerts, Config
  - `@radix-ui` component primitives (Dialog, DropdownMenu, Slider, Tabs)
  - `@phosphor-icons/react` icon set
  - Account Settings modal (profile email update + password change)
  - 401 auto-redirect with transparent JWT refresh guard

- **Multi-Station Management**
  - `/stations` page: per-station health, KPIs, defect breakdown, last result
  - Health scoring: green ≥ 95%, amber ≥ 85%, red < 85% pass rate
  - 30 s auto-refresh

- **AI Query (Natural Language)**
  - `/query` chat interface — ask questions about inspection history in plain English
  - Suggestion chips for common queries
  - Shows backend model name on each response

- **Alerts UI**
  - `/alerts` page with severity filter (All / Info / Warning / Error / Critical)
  - Unacknowledged toggle, per-alert acknowledge button, 10 s auto-refresh

- **Redis Caching (`services/cache.py`)**
  - Async `Cache` wrapper with transparent in-process LRU fallback (no Redis required)
  - `_LocalCache`: TTL-based, max-size eviction, prefix-clear
  - Statistics cached 30 s, trends cached 60 s; both invalidated after each inspection

- **Background Worker (`worker.py`)**
  - `batch_worker`: polls and starts PENDING batch jobs
  - `training_worker`: monitors active training job progress
  - `alert_worker`: runs alert checks and clears stale alerts every 60 s
  - `cleanup_worker`: deletes images + DB records beyond retention policy
  - Graceful shutdown via `asyncio.Event` + OS signal handlers

- **Model Retraining (`services/model_trainer.py`)**
  - Fine-tune Faster R-CNN on accumulated active-learning annotations
  - Background training threads, early stopping, progress tracking
  - REST endpoints: `POST /api/v1/training/start`, `GET /api/v1/training/jobs`

- **Model Deployment (`services/model_deployer.py`)**
  - Hot-swap inference model without restart
  - Full version history, rollback to any previous version
  - REST endpoints: `POST /api/v1/models/deploy`, `POST /api/v1/models/rollback`

- **OpenVINO Acceleration (`services/openvino_optimizer.py`)**
  - Load ONNX models via `openvino.runtime.Core`, compile for AUTO/CPU/GPU/NPU
  - Side-by-side ORT vs OpenVINO benchmark
  - Graceful fallback to ONNX Runtime when `openvino` not installed
  - Endpoints: `GET /api/v1/openvino/status`, `POST /api/v1/openvino/benchmark`, `POST /api/v1/openvino/load`

- **OPC-UA Server (`integrations/opcua_server.py`)**
  - Full `asyncua` OPC-UA server at `opc.tcp://<host>:4840/ussop`
  - Per-station nodes: LastDecision, LastConfidence, ObjectsFound, CycleTimeMs, PassCount, FailCount, PassRate1h, LastInspectionTime
  - SystemStatus object: IsRunning, APIVersion, UptimeSeconds
  - Lazy station node creation; auto-started when `OPCUA_ENABLED=true`
  - Endpoint: `GET /api/v1/opcua/status`

- **Database Migrations (Alembic)**
  - `alembic/env.py` reads `DATABASE_URL` from app settings, auto-imports all models
  - Initial migration covers 9 tables; `alembic upgrade head` runs automatically at API startup
  - `scripts/migrate.py` CLI: `upgrade`, `downgrade`, `current`, `history`

- **Production Docker Stack (`docker/docker-compose.yml`)**
  - 7 services: api, worker, postgres, redis, nginx, prometheus, grafana
  - `x-common-env` YAML anchor for shared environment variables
  - Health checks on postgres and redis before dependent services start
  - nginx: HTTP→HTTPS redirect, TLS termination, gzip, rate limiting, WebSocket proxy
  - Prometheus scraping + Grafana dashboards provisioned automatically
  - Port 4840 exposed for OPC-UA clients

- **Security**
  - `SecurityHeadersMiddleware`: X-Content-Type-Options, X-Frame-Options, X-XSS-Protection, Referrer-Policy, Permissions-Policy
  - Self-service profile endpoints: `PUT /api/v1/users/me`, `PUT /api/v1/users/me/password`

- **Testing**
  - 437 tests across 13 test files — all passing
  - `test_cache.py` (19 tests): LocalCache + async Cache, Redis mock path, fallback behaviour
  - `test_openvino.py` (15 tests): runner, benchmark, load endpoint, ORT fallback
  - `test_worker.py` (9 tests): batch, training, alert, cleanup workers
  - `test_performance.py`: inference latency and throughput benchmarks

- **Documentation**
  - `docs/deployment.md` — full Docker + bare-metal deployment guide
  - `docs/api.md` — complete REST + WebSocket API reference (70+ endpoints)
  - `docs/onboarding.md` — 8-step customer onboarding guide

### Changed
- Frontend fully rebuilt from Jinja2 templates to React 18 + TypeScript SPA
- Analytics page: station filter, Refresh + CSV Export, pass-rate-over-time chart, Pareto defect chart
- API lifespan now runs Alembic migrations, connects Redis cache, and starts OPC-UA server

---

## [1.0.0] - 2026-03-03

### Added — Production v1.0

- **Core Inspection Engine**
  - Faster R-CNN object detection (ResNet50 + MobileNet backbones)
  - NanoSAM precise segmentation (ONNX Runtime, CPU-optimized)
  - Measurement extraction (area, dimensions, bounding boxes)
  - Multi-camera support (USB, GigE, file-based, mock)
  - Async processing pipeline

- **Web Application (FastAPI)**
  - 60+ REST API endpoints with Swagger documentation
  - JWT authentication with secure password hashing
  - Role-based access control (Admin, Operator, Engineer, Viewer)
  - User management, session management
  - Real-time WebSocket dashboard
  - Image upload and camera capture
  - Inspection history with filters and CSV export

- **Advanced Features**
  - Active learning with uncertainty sampling and human-in-the-loop annotation
  - Batch processing (folder inspection with parallel workers)
  - PDF report generation
  - Performance monitoring and alerting
  - Audit logging (tamper-proof, chain-hashed, compliance-ready)
  - Data retention and cleanup policies

- **Industrial Integrations**
  - Modbus TCP server (PLC communication)
  - MQTT client (IoT platform publishing)
  - Webhook support (HTTP callbacks)
  - Email notifications

- **Deployment**
  - Docker containerization
  - Environment-based configuration via `.env`
  - Setup wizard (`ussop/setup.py`)
  - Health check endpoints

- **Testing**
  - pytest with fixtures and coverage reporting
  - Unit tests for inspector, active learning, monitoring, batch processor, auth

### Performance
- Inference: < 1 s on Intel i5 (MobileNet + NanoSAM)
- Throughput: 30+ inspections/minute
- Memory: < 4 GB RAM
- Detection Accuracy: > 85% mAP (COCO)
- Segmentation Accuracy: > 80% IoU

---

## [0.9.0] - 2026-02-28

### Added
- Initial project structure and ML pipeline
- Basic web UI templates and database models
- Faster R-CNN + NanoSAM proof of concept
