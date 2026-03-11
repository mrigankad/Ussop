# Ussop — Technical Architecture

> **Sniper-precision defect detection, engineered for production**

---

## 1. Architecture Overview

### 1.1 Design Principles

| Principle | Implementation |
|-----------|----------------|
| **Edge-First** | All inference on local CPU, no cloud dependency |
| **Modular** | Swappable components (detectors, models, integrations) |
| **Scalable** | Single station to enterprise multi-site |
| **Observable** | Comprehensive logging, metrics, tracing |
| **Secure** | Defense in depth, encryption, audit trails |

### 1.2 System Context

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           EXTERNAL SYSTEMS                                   │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │    PLC       │  │    MES       │  │    QMS       │  │   Cloud      │     │
│  │  (Modbus)    │  │   (API)      │  │   (API)      │  │  (Optional)  │     │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘     │
└─────────┼─────────────────┼─────────────────┼─────────────────┼─────────────┘
          │                 │                 │                 │
          └─────────────────┴─────────────────┴─────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                              USSOP PLATFORM                                  │
│                                                                              │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │                      API GATEWAY (Nginx/FastAPI)                      │   │
│  │         Auth, Rate Limiting, Routing, Load Balancing                 │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                    │                                         │
│  ┌─────────────────────────────────┼─────────────────────────────────────┐   │
│  │                                 ▼                                     │   │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐   │   │
│  │  │   INGEST    │  │  INSPECT    │  │   ANALYZE   │  │   INTEGRATE │   │   │
│  │  │   SERVICE   │  │   SERVICE   │  │   SERVICE   │  │   SERVICE   │   │   │
│  │  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘   │   │
│  │          │               │               │               │            │   │
│  │          ▼               ▼               ▼               ▼            │   │
│  │  ┌─────────────────────────────────────────────────────────────────┐  │   │
│  │  │              MESSAGE BUS (Redis/RabbitMQ)                        │  │   │
│  │  │     Async processing, job queues, event streaming                │  │   │
│  │  └─────────────────────────────────────────────────────────────────┘  │   │
│  └────────────────────────────────────────────────────────────────────────┘   │
│                                    │                                          │
│  ┌─────────────────────────────────┼─────────────────────────────────────┐   │
│  │                                 ▼                                     │   │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐   │   │
│  │  │    MODEL    │  │    DATA     │  │    CONFIG   │  │    METRICS  │   │   │
│  │  │   ENGINE    │  │    STORE    │  │    STORE    │  │    STORE    │   │   │
│  │  │  (ONNX RT)  │  │  (PostgreSQL│  │    (Redis)  │  │ (Prometheus)│   │   │
│  │  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘   │   │
│  └────────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
          │
          ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           HARDWARE LAYER                                     │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐         │
│  │   Camera    │  │   Lighting  │  │     PLC     │  │    I/O      │         │
│  │  (USB/GigE) │  │   (24V)     │  │  (Modbus)   │  │  (Digital)  │         │
│  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘         │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Core Services

### 2.1 Ingest Service

**Purpose:** Capture and preprocess images from cameras

```python
# Simplified architecture diagram
class IngestService:
    """
    Handles multiple trigger types:
    - Software trigger (HTTP request)
    - Hardware trigger (digital input)
    - Free-run mode (continuous capture)
    - Scheduled capture (time-based)
    """
    
    Components:
    ├── Camera Manager (USB3/GigE/LineScan)
    │   ├── Device discovery
    │   ├── Parameter configuration
    │   └── Image acquisition
    ├── Preprocessor
    │   ├── Denoising
    │   ├── Color correction
    │   └── Format conversion
    └── Trigger Handler
        ├── Hardware interrupt
        ├── Software event
        └── Timing synchronization
```

**Key Technologies:**
- OpenCV (video I/O)
- GenICam (camera abstraction)
- Python GStreamer (streaming)

**Performance Targets:**
- Trigger latency: < 10ms
- Throughput: 30 FPS @ 2MP
- Support 4 concurrent cameras

---

### 2.2 Inspection Service

**Purpose:** Run detection and segmentation models

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         INSPECTION PIPELINE                              │
│                                                                          │
│  Input: PIL Image (RGB)                                                  │
│       │                                                                  │
│       ▼                                                                  │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │  STAGE 1: OBJECT DETECTION (Faster R-CNN)                        │    │
│  │  ┌───────────────────────────────────────────────────────────┐   │    │
│  │  │  Model: fasterrcnn_mobilenet_v3_large_fpn                 │   │    │
│  │  │  Input: (3, H, W) tensor                                  │   │    │
│  │  │  Output: List[Detection]                                  │   │    │
│  │  │  • box: [x1, y1, x2, y2]                                  │   │    │
│  │  │  • label: class_id                                        │   │    │
│  │  │  • score: confidence [0-1]                                │   │    │
│  │  └───────────────────────────────────────────────────────────┘   │    │
│  │       │                                                          │    │
│  │       ▼                                                          │    │
│  │  [Detection A, Detection B, ...]                                  │    │
│  │       │                                                          │    │
│  └───────┼──────────────────────────────────────────────────────────┘    │
│          │                                                               │
│          ▼                                                               │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │  STAGE 2: SEGMENTATION (NanoSAM)                                │    │
│  │  ┌───────────────────────────────────────────────────────────┐   │    │
│  │  │  Encoder: resnet18_image_encoder.onnx                     │   │    │
│  │  │  • Input: (1, 3, 1024, 1024)                              │   │    │
│  │  │  • Output: (1, 256, 64, 64) image embedding               │   │    │
│  │  │  • Runs once per image                                    │   │    │
│  │  └───────────────────────────────────────────────────────────┘   │    │
│  │       │                                                          │    │
│  │       ▼                                                          │    │
│  │  ┌───────────────────────────────────────────────────────────┐   │    │
│  │  │  Decoder: mobile_sam_mask_decoder.onnx (per detection)    │   │    │
│  │  │  • Input: embedding + box prompt                          │   │    │
│  │  │  • Output: (3, H, W) masks + (3,) scores                  │   │    │
│  │  │  • Pick best mask by IoU score                            │   │    │
│  │  └───────────────────────────────────────────────────────────┘   │    │
│  │       │                                                          │    │
│  └───────┼──────────────────────────────────────────────────────────┘    │
│          │                                                               │
│          ▼                                                               │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │  STAGE 3: POST-PROCESSING                                        │    │
│  │  • Mask refinement (morphological ops)                          │    │
│  │  • Measurement extraction (area, dimensions)                    │    │
│  │  • Defect classification                                        │    │
│  │  • Pass/fail decision                                           │    │
│  └─────────────────────────────────────────────────────────────────┘    │
│          │                                                               │
│          ▼                                                               │
│  Output: InspectionResult                                                │
│       • original_image                                                   │
│       • detections: List[SegmentedObject]                                │
│       • measurements: Dict[str, float]                                   │
│       • decision: PASS / FAIL / UNCERTAIN                                │
│       • timing: {detection_ms, segmentation_ms, total_ms}                │
└─────────────────────────────────────────────────────────────────────────┘
```

**Model Optimization:**

| Technique | Benefit | Implementation |
|-----------|---------|----------------|
| INT8 Quantization | 2x speedup, 75% size | ONNX Runtime quantization |
| Dynamic Axes | Variable batch/input size | ONNX dynamic shapes |
| Thread Tuning | Maximize CPU utilization | `intra_op_num_threads=0` |
| Memory Pooling | Reduce allocation overhead | Pre-allocated buffers |

**Performance Profile (Intel i5-12400):**
```
Detection (MobileNet):     ~400ms
Encoder (ResNet18):        ~300ms (runs once)
Decoder (per object):      ~150ms
───────────────────────────────────
Total (5 objects):         ~1.4s
Optimized (async):         ~0.8s
```

---

### 2.3 Analysis Service

**Purpose:** Analytics, trending, and reporting

```python
class AnalysisService:
    """
    Real-time and batch analytics for quality data
    """
    
    Components:
    ├── Real-time Aggregator
    │   ├── Parts per hour
    │   ├── Pass/fail rates
    │   └── Defect distribution
    ├── Trend Analyzer
    │   ├── SPC control charts
    │   ├── Pareto analysis
    │   └── Shift comparisons
    ├── Measurement Analytics
    │   ├── CPK calculations
    │   ├── Distribution fitting
    │   └── Outlier detection
    └── Report Generator
        ├── PDF reports
        ├── Excel exports
        └── Email scheduling
```

**Database Schema:**

```sql
-- Core tables
inspections (
    id UUID PRIMARY KEY,
    station_id TEXT,
    timestamp TIMESTAMPTZ,
    part_id TEXT,
    image_path TEXT,
    decision TEXT CHECK (decision IN ('PASS', 'FAIL', 'UNCERTAIN')),
    confidence FLOAT,
    metadata JSONB
);

detections (
    id UUID PRIMARY KEY,
    inspection_id UUID REFERENCES inspections,
    class_name TEXT,
    confidence FLOAT,
    box BOX,  -- PostgreSQL geometric type
    mask_path TEXT,  -- Path to PNG mask
    area_pixels INT,
    area_mm2 FLOAT
);

measurements (
    id UUID PRIMARY KEY,
    detection_id UUID REFERENCES detections,
    name TEXT,
    value FLOAT,
    unit TEXT,
    tolerance_min FLOAT,
    tolerance_max FLOAT
);

-- Time-series aggregates (continuous aggregates)
daily_stats (
    station_id TEXT,
    date DATE,
    total_inspections INT,
    pass_count INT,
    fail_count INT,
    defect_counts JSONB,  -- {"scratch": 45, "dent": 12}
    avg_cycle_time_ms INT
);
```

---

### 2.4 Integration Service

**Purpose:** Connect to external systems (PLCs, MES, APIs)

```
┌─────────────────────────────────────────────────────────────────────────┐
│                      INTEGRATION ADAPTERS                                │
│                                                                          │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐      │
│  │  MODBUS TCP      │  │  MQTT CLIENT     │  │  REST API        │      │
│  │  ━━━━━━━━━━━━━━  │  │  ━━━━━━━━━━━━━━  │  │  ━━━━━━━━━━━━━━  │      │
│  │  Server/Slave    │  │  Publisher/Sub   │  │  FastAPI Server  │      │
│  │  • Coils         │  │  • Topics:       │  │  • /inspect      │      │
│  │  • Registers     │  │    ussop/results │  │  • /results      │      │
│  │  • Discrete I/O  │  │    ussop/status  │  │  • /models       │      │
│  └──────────────────┘  └──────────────────┘  └──────────────────┘      │
│                                                                          │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐      │
│  │  OPC-UA          │  │  DATABASE        │  │  WEBHOOK         │      │
│  │  ━━━━━━━━━━━━━━  │  │  ━━━━━━━━━━━━━━  │  │  ━━━━━━━━━━━━━━  │      │
│  │  Client/Server   │  │  Sync            │  │  Outbound        │      │
│  │  • Nodes         │  │  • PostgreSQL    │  │  • HTTPS POST    │      │
│  │  • Subscriptions │  │  • MySQL         │  │  • Retry logic   │      │
│  │  • Method calls  │  │  • SQL Server    │  │  • Auth headers  │      │
│  └──────────────────┘  └──────────────────┘  └──────────────────┘      │
└─────────────────────────────────────────────────────────────────────────┘
```

**Modbus Register Map Example:**

| Address | Type | Description | Values |
|---------|------|-------------|--------|
| 1 | Coil | Trigger Inspection | 0→1 pulse |
| 2 | Coil | Pass Signal | 0/1 |
| 3 | Coil | Fail Signal | 0/1 |
| 4 | Coil | System Ready | 0/1 |
| 100 | Input Reg | Result Code | 0=Pass, 1=Fail, 2=Error |
| 101 | Input Reg | Defect Count | 0-255 |
| 102-105 | Input Reg | Defect Codes | Class IDs |

---

## 3. Data Flow Diagrams

### 3.1 Typical Inspection Flow

```
┌──────────┐     ┌──────────┐     ┌──────────┐     ┌──────────┐
│  Camera  │────▶│  Ingest  │────▶│ Inspect  │────▶│  Analyze │
└──────────┘     └──────────┘     └──────────┘     └────┬─────┘
                                                        │
                     ┌──────────┐     ┌──────────┐     │
                     │    PLC   │◀────│ Integrate│◀────┘
                     └──────────┘     └──────────┘
                     
                     ┌──────────┐     ┌──────────┐
                     │ Dashboard│◀────│   API    │
                     └──────────┘     └──────────┘
```

### 3.2 Active Learning Flow

```
┌──────────┐     ┌──────────┐     ┌──────────┐     ┌──────────┐
│  Inspect │────▶│ Confidence│────▶│  Queue   │────▶│ Operator │
│  (Low)   │     │  0.3-0.7  │     │  Review  │     │  Labels  │
└──────────┘     └──────────┘     └──────────┘     └────┬─────┘
                                                        │
                     ┌──────────┐     ┌──────────┐     │
                     │  Deploy  │◀────│  Train   │◀────┘
                     │  Model   │     │  (Auto)  │
                     └──────────┘     └──────────┘
```

### 3.3 Multi-Station Deployment

```
┌─────────────────────────────────────────────────────────────────┐
│                      CLOUD (Optional)                            │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │ Model Repo   │  │ Analytics    │  │ Remote       │          │
│  │ (S3)         │  │ Dashboard    │  │ Support      │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
└──────────┬──────────────────────────────────────────────────────┘
           │
           │ Internet/VPN
           │
┌──────────┼──────────────────────────────────────────────────────┐
│          │              FACTORY NETWORK                          │
│  ┌───────┴────┐                                                 │
│  │  Gateway   │                                                 │
│  │  (Edge)    │                                                 │
│  └─────┬──────┘                                                 │
│        │                                                        │
│  ┌─────┼─────┬─────────┬─────────┐                             │
│  │     │     │         │         │                             │
│  ▼     ▼     ▼         ▼         ▼                             │
│ ┌───┐ ┌───┐ ┌───┐   ┌───┐   ┌───┐                             │
│ │S1 │ │S2 │ │S3 │   │S4 │   │S5 │   Stations (Ussop)          │
│ └───┘ └───┘ └───┘   └───┘   └───┘                             │
└─────────────────────────────────────────────────────────────────┘
```

---

## 4. Deployment Architecture

### 4.1 Docker Compose (Single Station)

```yaml
# docker-compose.yml
version: '3.8'

services:
  # Core API
  ussop-api:
    image: ussop/api:latest
    ports:
      - "8080:8080"
    environment:
      - DATABASE_URL=postgresql://ussop:pass@postgres:5432/ussop
      - REDIS_URL=redis://redis:6379
      - MODEL_PATH=/models
    volumes:
      - ./models:/models:ro
      - ussop-data:/data
    depends_on:
      - postgres
      - redis
    restart: unless-stopped

  # ML Inference (separate for resource management)
  ussop-inference:
    image: ussop/inference:latest
    environment:
      - ONNX_THREADS=6
      - MAX_BATCH_SIZE=4
    volumes:
      - ./models:/models:ro
    deploy:
      resources:
        limits:
          cpus: '6.0'
          memory: 4G
    restart: unless-stopped

  # Background workers
  ussop-worker:
    image: ussop/worker:latest
    environment:
      - DATABASE_URL=postgresql://ussop:pass@postgres:5432/ussop
      - REDIS_URL=redis://redis:6379
    depends_on:
      - postgres
      - redis
    restart: unless-stopped

  # Web UI
  ussop-ui:
    image: ussop/ui:latest
    ports:
      - "80:80"
    depends_on:
      - ussop-api
    restart: unless-stopped

  # Databases
  postgres:
    image: postgres:15-alpine
    environment:
      - POSTGRES_USER=ussop
      - POSTGRES_PASSWORD=pass
      - POSTGRES_DB=ussop
    volumes:
      - postgres-data:/var/lib/postgresql/data
    restart: unless-stopped

  redis:
    image: redis:7-alpine
    volumes:
      - redis-data:/data
    restart: unless-stopped

  # Monitoring
  prometheus:
    image: prom/prometheus:latest
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml
      - prometheus-data:/prometheus
    restart: unless-stopped

  grafana:
    image: grafana/grafana:latest
    ports:
      - "3000:3000"
    volumes:
      - grafana-data:/var/lib/grafana
    restart: unless-stopped

volumes:
  ussop-data:
  postgres-data:
  redis-data:
  prometheus-data:
  grafana-data:
```

### 4.2 Kubernetes (Enterprise)

```yaml
# Deployment excerpt for inference service
apiVersion: apps/v1
kind: Deployment
metadata:
  name: ussop-inference
spec:
  replicas: 2  # HA for inference
  selector:
    matchLabels:
      app: ussop-inference
  template:
    spec:
      containers:
      - name: inference
        image: ussop/inference:latest
        resources:
          requests:
            memory: "2Gi"
            cpu: "2000m"
          limits:
            memory: "4Gi"
            cpu: "4000m"
        env:
        - name: OMP_NUM_THREADS
          value: "4"
        volumeMounts:
        - name: models
          mountPath: /models
      volumes:
      - name: models
        persistentVolumeClaim:
          claimName: ussop-models
```

---

## 5. Security Architecture

### 5.1 Defense in Depth

```
┌─────────────────────────────────────────────────────────────────┐
│ LAYER 1: PHYSICAL                                               │
│ • Industrial PC in locked enclosure                             │
│ • Camera network isolated from corporate network                │
│ • USB ports disabled (except authorized devices)                │
├─────────────────────────────────────────────────────────────────┤
│ LAYER 2: NETWORK                                                │
│ • VLAN segmentation                                             │
│ • Firewall rules (deny all, allow specific)                     │
│ • No inbound internet access required                           │
├─────────────────────────────────────────────────────────────────┤
│ LAYER 3: APPLICATION                                            │
│ • TLS 1.3 for all communications                                │
│ • API authentication (JWT with short expiry)                    │
│ • Role-based access control (RBAC)                              │
│ • Input validation and sanitization                             │
├─────────────────────────────────────────────────────────────────┤
│ LAYER 4: DATA                                                   │
│ • Encryption at rest (PostgreSQL TDE)                           │
│ • Encrypted backups                                             │
│ • Audit logging (tamper-proof)                                  │
│ • Data retention policies                                       │
├─────────────────────────────────────────────────────────────────┤
│ LAYER 5: MODELS                                                 │
│ • Signed model artifacts                                        │
│ • Model provenance tracking                                     │
│ • Access control to model repository                            │
└─────────────────────────────────────────────────────────────────┘
```

### 5.2 Authentication Flow

```
User ──▶ Login Page ──▶ Auth Service ──▶ LDAP/AD (optional)
                          │
                          ▼
                    JWT Token Issued
                    (access: 15min, refresh: 7days)
                          │
User ──▶ API Call ──▶ JWT Validation ──▶ RBAC Check ──▶ Resource
```

### 5.3 Compliance Features

| Regulation | Feature | Implementation |
|------------|---------|----------------|
| **FDA 21 CFR Part 11** | Electronic signatures | PKI signatures on inspection records |
| | Audit trails | Immutable logs with hashing |
| | Access controls | Role-based with expiration |
| **ISO 9001** | Document control | Version-controlled SOPs |
| | Corrective actions | CAPA workflow integration |
| **GDPR** | Data deletion | Right to be forgotten API |
| | Data portability | Export in standard formats |

---

## 6. Performance Optimization

### 6.1 Inference Optimization

```python
# ONNX Runtime optimization settings
session_options = ort.SessionOptions()

# Enable all graph optimizations
session_options.graph_optimization_level = (
    ort.GraphOptimizationLevel.ORT_ENABLE_ALL
)

# Threading (let ORT decide based on CPU)
session_options.intra_op_num_threads = 0
session_options.inter_op_num_threads = 0

# Memory optimization
session_options.enable_cpu_mem_arena = True
session_options.enable_mem_pattern = True

# Quantization (INT8)
# Applied during model export:
#   onnxruntime.quantization.quantize_dynamic(
#       model_input,
#       model_output,
#       weight_type=QuantType.QInt8
#   )
```

### 6.2 Caching Strategy

```
┌─────────────────────────────────────────────────────────────┐
│ CACHE LAYERS                                                │
│                                                             │
│ L1: In-Memory (Redis)                                       │
│   • Image embeddings (TTL: 5 min)                          │
│   • Station configuration (TTL: 1 hour)                    │
│   • Model metadata (TTL: 24 hours)                         │
│                                                             │
│ L2: Disk (SSD)                                              │
│   • Preprocessed images (LRU cache: 10GB)                  │
│   • Mask cache for recent inspections                       │
│                                                             │
│ L3: Object Storage (Optional)                               │
│   • Long-term image storage (S3-compatible)                │
│   • Model artifacts                                        │
└─────────────────────────────────────────────────────────────┘
```

### 6.3 Profiling & Benchmarks

| Operation | Baseline | Optimized | Improvement |
|-----------|----------|-----------|-------------|
| Image load + preprocess | 120ms | 45ms | 2.7x |
| Detection (MobileNet) | 450ms | 280ms | 1.6x |
| Encoder (ResNet18) | 350ms | 180ms | 1.9x |
| Decoder (per object) | 180ms | 95ms | 1.9x |
| **Total (5 objects)** | 1750ms | 850ms | **2.1x** |

---

## 7. Monitoring & Observability

### 7.1 Metrics

```python
# Key metrics collected
METRICS = {
    # Business metrics
    "inspections_total": Counter,
    "inspections_failed": Counter,
    "inspection_duration": Histogram,
    
    # Technical metrics  
    "inference_latency": Histogram,
    "queue_depth": Gauge,
    "camera_fps": Gauge,
    
    # Quality metrics
    "defect_rate": Gauge,
    "false_positive_rate": Gauge,
    "model_confidence": Histogram,
}
```

### 7.2 Alerting Rules

```yaml
# Example Prometheus alerting rules
groups:
  - name: ussop-alerts
    rules:
      - alert: HighDefectRate
        expr: defect_rate > 0.1
        for: 5m
        annotations:
          summary: "Defect rate elevated on {{ $labels.station }}"
          
      - alert: CameraDisconnected
        expr: camera_connected == 0
        for: 1m
        annotations:
          summary: "Camera disconnected on {{ $labels.station }}"
          
      - alert: HighLatency
        expr: inference_latency_p99 > 2000
        for: 5m
        annotations:
          summary: "Inference latency > 2s"
```

### 7.3 Logging Structure

```json
{
  "timestamp": "2026-03-15T14:32:01Z",
  "level": "INFO",
  "service": "inspection-service",
  "trace_id": "abc123",
  "event": "inspection_completed",
  "station_id": "line3_station2",
  "part_id": "PCB-28472",
  "decision": "FAIL",
  "defects_detected": 2,
  "timing_ms": {
    "detection": 280,
    "segmentation": 420,
    "total": 850
  }
}
```

---

## 8. Development & Testing

### 8.1 Development Environment

```
ussop/
├── services/
│   ├── api/                 # FastAPI application
│   ├── inference/           # Model serving
│   ├── worker/              # Background jobs
│   └── integration/         # Protocol adapters
├── models/
│   ├── detector/            # Faster R-CNN wrapper
│   └── segmenter/           # NanoSAM wrapper
├── sdk/
│   └── python/              # Client SDK
├── tests/
│   ├── unit/                # Pytest
│   ├── integration/         # Docker-compose test env
│   └── e2e/                 # Selenium/Playwright
├── infra/
│   ├── docker/              # Dockerfiles
│   ├── k8s/                 # Kubernetes manifests
│   └── terraform/           # Cloud provisioning
└── docs/
    └── api/                 # OpenAPI specs
```

### 8.2 Testing Strategy

| Type | Scope | Tools | Frequency |
|------|-------|-------|-----------|
| Unit | Functions, classes | Pytest | Every commit |
| Integration | Service boundaries | Docker Compose | PR merge |
| Performance | Latency, throughput | Locust, k6 | Nightly |
| Accuracy | Model mAP, IoU | Custom eval | Weekly |
| E2E | Full workflows | Playwright | Release |
| Security | Vulnerabilities | Bandit, Trivy | Weekly |

---

## 9. Future Architecture Evolution

### 9.1 Phase 2: Distributed Processing

```
┌─────────────────────────────────────────────────────────────┐
│                    PHASE 2 ARCHITECTURE                      │
│                                                              │
│  ┌─────────────┐     ┌─────────────┐     ┌─────────────┐   │
│  │   Camera    │────▶│  Edge Node  │────▶│   Cloud     │   │
│  │   Node 1    │     │  (Ussop)    │     │  Analytics  │   │
│  └─────────────┘     └─────────────┘     └─────────────┘   │
│                                                              │
│  ┌─────────────┐     ┌─────────────┐                        │
│  │   Camera    │────▶│  Edge Node  │                        │
│  │   Node 2    │     │  (Ussop)    │                        │
│  └─────────────┘     └─────────────┘                        │
│                                                              │
│  Benefits:                                                   │
│  • Centralized model management                              │
│  • Aggregated analytics                                      │
│  • Remote diagnostics                                        │
└─────────────────────────────────────────────────────────────┘
```

### 9.2 Phase 3: Edge AI Optimizations

- **NPU Support**: Intel OpenVINO for integrated graphics
- **ARM Edge**: Raspberry Pi 5, NVIDIA Jetson (optional GPU)
- **Model Distillation**: Smaller student models for speed
- **Federated Learning**: Train across sites without data sharing

---

## 10. Appendix

### A. Hardware Specifications

#### Minimum (Development/Pilot)
| Component | Spec |
|-----------|------|
| CPU | Intel i5-10400 (6 cores) |
| RAM | 16 GB DDR4 |
| Storage | 256 GB SSD |
| Network | Gigabit Ethernet |
| OS | Ubuntu 22.04 LTS |

#### Recommended (Production)
| Component | Spec |
|-----------|------|
| CPU | Intel i7-12700 (12 cores) |
| RAM | 32 GB DDR4 |
| Storage | 512 GB NVMe SSD |
| Network | Gigabit Ethernet |
| OS | Ubuntu 22.04 LTS or Windows 11 IoT |

#### Industrial PC (Harsh Environments)
| Component | Spec |
|-----------|------|
| CPU | Intel i7-1185G7E (embedded) |
| RAM | 32 GB DDR4 |
| Storage | 256 GB industrial SSD |
| Rating | IP65, -20°C to 60°C |
| Power | 24V DC industrial |

### B. API Reference (Excerpt)

```yaml
openapi: 3.0.0
paths:
  /api/v1/inspect:
    post:
      summary: Run inspection on image
      requestBody:
        content:
          multipart/form-data:
            schema:
              type: object
              properties:
                image:
                  type: string
                  format: binary
                station_id:
                  type: string
      responses:
        200:
          description: Inspection result
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/InspectionResult'
```

### C. Glossary

| Term | Definition |
|------|------------|
| **SAM** | Segment Anything Model — generates masks for any object |
| **ONNX** | Open Neural Network Exchange — model format |
| **mAP** | mean Average Precision — detection accuracy metric |
| **IoU** | Intersection over Union — mask quality metric |
| **CPK** | Process Capability Index — statistical quality metric |
| **MES** | Manufacturing Execution System |
| **PLC** | Programmable Logic Controller |

---

**Document Version:** 1.0  
**Last Updated:** March 2026  
**Owner:** Ussop Engineering Team
