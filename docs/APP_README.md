# 🎯 Ussop - AI Visual Inspector

> **"Sniper precision. Slingshot simple."**

Ussop is a CPU-based visual inspection system for manufacturing, combining Faster R-CNN object detection with NanoSAM segmentation for precise defect detection.

Named after the legendary sniper of the Straw Hat Pirates — every defect is a target, and we never miss.

## ✨ Features

### Core Inspection
- 🔍 **Object Detection** - Detect defects with Faster R-CNN (MobileNet/ResNet)
- 🎯 **Precise Segmentation** - Pixel-perfect masks with NanoSAM
- 📊 **Measurements** - Area, dimensions from segmentation masks
- 📷 **Multi-Camera** - USB, GigE, or file-based input
- ⚡ **CPU-Only** - No GPU required, runs on standard industrial PCs

### Web Interface
- 🌐 **Dashboard** - Real-time monitoring and statistics
- 🔧 **Inspect** - Upload images or capture from camera
- 📋 **History** - Browse, filter, and search inspections
- 📈 **Analytics** - Charts, trends, and quality metrics
- ✏️ **Annotation** - Active learning with human-in-the-loop

### Integrations
- 🔌 **Modbus TCP** - PLC integration for factory automation
- 📡 **MQTT** - IoT platform connectivity
- 🔗 **REST API** - Full programmatic access
- 📤 **Export** - CSV export for external analysis

### Advanced Features
- 🧠 **Active Learning** - Automatic flagging of uncertain predictions
- 📊 **Monitoring** - Performance metrics and alerting
- 🔒 **Audit Logging** - Tamper-proof compliance logs
- 🐳 **Docker Ready** - One-command deployment

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- NanoSAM ONNX models (downloaded automatically)

### 1. Clone and Setup

```bash
# From project root
git clone <repo>
cd ussop
```

### 2. Download Models

```bash
# From project root
python download_models.py
```

This downloads:
- `resnet18_image_encoder.onnx` (~60 MB)
- `mobile_sam_mask_decoder.onnx` (~17 MB)

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Run Ussop

```bash
python run.py
```

Access the dashboard at **http://localhost:8080**

### Docker Deployment

```bash
docker-compose up -d
```

## 📁 Project Structure

```
ussop/
├── api/
│   └── main.py              # FastAPI backend (40+ endpoints)
├── services/
│   ├── inspector.py         # Inspection pipeline
│   ├── camera.py            # Camera service
│   ├── active_learning.py   # Active learning & retraining
│   └── monitoring.py        # Metrics, alerts, audit logs
├── models/
│   └── database.py          # SQLAlchemy ORM models
├── integrations/
│   ├── modbus_server.py     # PLC/Modbus TCP interface
│   └── mqtt_client.py       # MQTT IoT integration
├── config/
│   └── settings.py          # Environment configuration
├── static/css/
│   └── style.css            # Modern UI styling
├── templates/
│   ├── index.html           # Dashboard
│   ├── inspect.html         # Inspection interface
│   ├── history.html         # History view
│   ├── analytics.html       # Charts & trends
│   └── annotate.html        # Active learning annotation
├── data/                    # Runtime data storage
│   ├── images/              # Stored inspection images
│   ├── masks/               # Segmentation masks
│   ├── db/                  # SQLite database
│   ├── logs/                # Application logs
│   └── audit/               # Audit logs
├── tests/                   # Unit and integration tests
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── run.py                   # Quick start script
└── README.md
```

## 🖥️ Web Interface

| Page | URL | Description |
|------|-----|-------------|
| Dashboard | `/` | Overview stats, recent inspections, defect breakdown |
| Inspect | `/inspect` | Upload images, use camera, view results |
| History | `/history` | Browse all inspections, filter, export CSV |
| Analytics | `/analytics` | Charts (volume, quality, defects, timing) |
| Annotate | `/annotate` | Active learning - review uncertain predictions |
| API Docs | `/docs` | Swagger/OpenAPI documentation |

## 🔌 API Endpoints

### Inspection
```bash
# Upload image for inspection
curl -X POST -F "file=@image.jpg" \
  -F "part_id=ABC123" \
  http://localhost:8080/api/v1/inspect

# Capture from camera
curl -X POST http://localhost:8080/api/v1/inspect/camera

# Get inspection by ID
curl http://localhost:8080/api/v1/inspect/{id}
```

### History & Analytics
```bash
# List inspections with filters
curl "http://localhost:8080/api/v1/inspections?decision=fail&limit=50"

# Get statistics
curl http://localhost:8080/api/v1/statistics?hours=24

# Get trends for charts
curl http://localhost:8080/api/v1/trends?hours=72&interval=hour

# Export to CSV
curl http://localhost:8080/api/v1/export/csv > inspections.csv
```

### Active Learning
```bash
# Get review queue
curl http://localhost:8080/api/v1/active-learning/queue

# Submit annotation
curl -X POST http://localhost:8080/api/v1/active-learning/annotate/{id} \
  -H "Content-Type: application/json" \
  -d '{"annotations": [...], "reviewed_by": "operator"}'

# Get training dataset status
curl http://localhost:8080/api/v1/active-learning/dataset

# Check if retraining is needed
curl -X POST http://localhost:8080/api/v1/active-learning/check-retrain
```

### Monitoring
```bash
# Health check
curl http://localhost:8080/api/v1/health

# Performance metrics
curl http://localhost:8080/api/v1/metrics/performance?hours=24

# Get alerts
curl http://localhost:8080/api/v1/alerts

# Acknowledge alert
curl -X POST http://localhost:8080/api/v1/alerts/{id}/acknowledge
```

## 🔧 Configuration

Set via environment variables or `.env` file:

```env
# App
DEBUG=false
API_PORT=8080
SECRET_KEY=your-secret-key

# Models
ENCODER_PATH=models/resnet18_image_encoder.onnx
DECODER_PATH=models/mobile_sam_mask_decoder.onnx
DETECTOR_BACKBONE=mobilenet  # or resnet50
CONFIDENCE_THRESHOLD=0.5
MAX_DETECTIONS=20

# Camera
CAMERA_TYPE=mock  # mock, file, usb, gige
CAMERA_INDEX=0
CAMERA_WIDTH=1920
CAMERA_HEIGHT=1080

# Active Learning
ACTIVE_LEARNING_ENABLED=true
UNCERTAINTY_THRESHOLD_LOW=0.3
UNCERTAINTY_THRESHOLD_HIGH=0.7

# Modbus (PLC Integration)
MODBUS_ENABLED=false
MODBUS_HOST=0.0.0.0
MODBUS_PORT=502

# MQTT (IoT Integration)
MQTT_ENABLED=false
MQTT_BROKER=localhost
MQTT_PORT=1883

# Storage
IMAGE_RETENTION_DAYS=90
MAX_STORAGE_GB=100
```

## 🏭 PLC Integration (Modbus TCP)

Ussop exposes a Modbus TCP server for PLC communication:

### Register Map

| Address | Type | Access | Description |
|---------|------|--------|-------------|
| 1 | Coil | RW | Trigger inspection (write 1 to trigger) |
| 2 | Coil | R | Pass signal |
| 3 | Coil | R | Fail signal |
| 4 | Coil | R | System ready |
| 3001 | Input Reg | R | Result code (0=none, 1=pass, 2=fail, 3=error) |
| 3002 | Input Reg | R | Defect count |
| 3003-3006 | Input Reg | R | Defect class IDs (up to 4) |
| 3007-3008 | Input Reg | R | Processing time (ms) |

### Example PLC Logic

```python
# Trigger inspection
write_coil(1, True)

# Wait for result
wait_for_coil(4, True)  # System ready

# Read result
result_code = read_input_register(3001)
if result_code == 1:
    print("Part PASSED")
elif result_code == 2:
    print("Part FAILED")
    defect_count = read_input_register(3002)
```

## 📡 MQTT Topics

Ussop publishes to the following MQTT topics:

| Topic | Description |
|-------|-------------|
| `ussop/{station_id}/status` | System status (online/offline) - retained |
| `ussop/{station_id}/inspection` | Inspection results |
| `ussop/{station_id}/alert` | Alerts and warnings |
| `ussop/{station_id}/command` | Incoming commands (subscribe) |

### Message Format

```json
{
  "timestamp": "2026-03-15T10:30:00Z",
  "station_id": "line1_station2",
  "type": "inspection",
  "data": {
    "inspection_id": "uuid",
    "decision": "pass",
    "confidence": 0.95,
    "objects_found": 2,
    "total_time_ms": 850
  }
}
```

## 🧠 Active Learning

Ussop includes an active learning pipeline for continuous improvement:

### How It Works

1. **Uncertainty Detection**: Inspections with confidence 0.3-0.7 are flagged
2. **Review Queue**: Flagged images appear in the Annotation UI
3. **Human Annotation**: Operator draws bounding boxes and labels
4. **Training Dataset**: Accumulate labeled images for retraining
5. **Model Update**: Retrain when enough data is collected

### Uncertainty Metrics

- **Confidence**: Average detection confidence
- **Entropy**: Prediction uncertainty
- **Margin**: Difference between top 2 predictions

### Workflow

```
Inspection → Calculate Uncertainty → Flag if Low Confidence
                                      ↓
                    Review Queue ←────┘
                         ↓
              Operator Annotates
                         ↓
              Training Dataset
                         ↓
              Retrain Model → Deploy
```

## 📊 Monitoring & Alerting

### Health Checks

- System status (healthy/warning/critical)
- Error rate monitoring
- Performance metrics (latency, throughput)

### Alert Rules

| Rule | Condition | Severity |
|------|-----------|----------|
| High Defect Rate | > 20% defects | Warning |
| High Latency | > 2s per inspection | Warning |
| System Errors | > 10% error rate | Critical |

### Audit Logging

Tamper-proof logs for compliance:
- Immutable entries with chain hashing
- Export for FDA/ISO audits
- Integrity verification

## 🐳 Docker Deployment

### Quick Start

```bash
cd ussop
docker-compose up -d
```

### Production

```bash
# Build image
docker build -t ussop:latest .

# Run with volume mounts
docker run -d \
  -p 8080:8080 \
  -v $(pwd)/data:/app/data \
  -v $(pwd)/../models:/app/models:ro \
  -e CAMERA_TYPE=mock \
  ussop:latest
```

## 🛠️ Development

### Run in Debug Mode

```bash
DEBUG=true python run.py
```

### Database Migrations

```bash
# Create migration
alembic revision --autogenerate -m "description"

# Apply migration
alembic upgrade head
```

### Running Tests

```bash
pytest tests/ -v
```

### Code Structure

```
services/       # Business logic
├── inspector.py        # Main inspection pipeline
├── camera.py           # Image acquisition
├── active_learning.py  # Active learning & retraining
└── monitoring.py       # Metrics & alerting

integrations/   # External system connectors
├── modbus_server.py    # PLC integration
└── mqtt_client.py      # IoT integration

api/            # HTTP API
└── main.py             # FastAPI routes
```

## 📊 Performance

Benchmarks on Intel i5-12400:

| Operation | Time |
|-----------|------|
| Detection (MobileNet) | ~280ms |
| Encoder (ResNet18) | ~180ms |
| Decoder (per object) | ~95ms |
| **Total (5 objects)** | **~850ms** |

Throughput: ~30 inspections/minute (async processing)

## 🗺️ Roadmap

### Phase 1 (Current)
- [x] Core detection & segmentation
- [x] Web dashboard
- [x] REST API
- [x] Modbus TCP
- [x] Active learning pipeline
- [x] Monitoring & alerts

### Phase 2 (Planned)
- [ ] Multi-camera support
- [ ] Model versioning
- [ ] OPC-UA support
- [ ] Cloud backup/sync
- [ ] Mobile app

### Phase 3 (Future)
- [ ] NPU optimization (Intel OpenVINO)
- [ ] Federated learning
- [ ] Predictive quality
- [ ] Multi-tenant SaaS

## 📜 License

MIT License - See LICENSE file

## 🤝 Contributing

Contributions welcome! Please read CONTRIBUTING.md for guidelines.

## 📞 Support

- Documentation: https://ussop.ai/docs
- Issues: https://github.com/ussop/ussop/issues
- Email: support@ussop.ai

---

<p align="center">
  <i>"8000 Shooters, Fire!"</i> — Ussop
</p>

<p align="center">
  <sub>Built with ❤️ for manufacturers everywhere</sub>
</p>
