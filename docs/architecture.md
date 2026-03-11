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

```mermaid
graph TD
    classDef ext fill:#f9f9f9,stroke:#333,stroke-width:2px,stroke-dasharray: 5 5;
    classDef ussop fill:#e1f5fe,stroke:#0288d1,stroke-width:2px;
    classDef core fill:#b3e5fc,stroke:#0277bd,stroke-width:1px;

    subgraph External Systems
        PLC[PLC (Modbus)]:::ext
        MES[MES (API)]:::ext
        QMS[QMS (API)]:::ext
        Cloud[Cloud (Optional)]:::ext
    end

    subgraph Ussop Platform
        Gateway[API Gateway Nginx/FastAPI]:::ussop
        
        subgraph Core Services
            Ingest[Ingest Service]:::core
            Inspect[Inspect Service]:::core
            Analyze[Analyze Service]:::core
            Integrate[Integrate Service]:::core
        end

        MQ[(Message Bus Redis/RabbitMQ)]:::core
        
        subgraph Data Stores
            Engine[Model Engine ONNX RT]:::core
            DB[(Data Store PostgreSQL)]:::core
            Cache[(Config Store Redis)]:::core
            Metrics[(Metrics Store Prometheus)]:::core
        end
    end

    subgraph Hardware Layer
        Cam[Camera USB/GigE]:::ext
        Light[Lighting 24V]:::ext
        IO[Digital I/O]:::ext
    end

    PLC <--> Gateway
    MES <--> Gateway
    QMS <--> Gateway
    Cloud <--> Gateway

    Gateway <--> Ingest
    Gateway <--> Inspect
    Gateway <--> Analyze
    Gateway <--> Integrate

    Ingest --> MQ
    Inspect --> MQ
    Analyze --> MQ
    Integrate --> MQ

    MQ --> Engine
    MQ --> DB
    MQ --> Cache
    MQ --> Metrics

    Cam --> Ingest
    Light --> PLC
    IO --> PLC
```

---

## 2. Core Services

### 2.1 Ingest Service

**Purpose:** Capture and preprocess images from cameras

```mermaid
graph TD
    Trigger((Trigger)) --> Handler[Trigger Handler]
    Handler --> |Hardware/Software| CamMan[Camera Manager]
    CamMan --> Pre[Preprocessor]
    Pre --> |Denoising, Color, Format| Out((Processed Image))
```

### 2.2 Inspection Service

**Purpose:** Run detection and segmentation models

```mermaid
sequenceDiagram
    participant Image as Input Image (RGB)
    participant Det as Stage 1: Faster R-CNN
    participant Enc as Stage 2: NanoSAM Encoder
    participant Dec as Stage 2: NanoSAM Decoder
    participant Post as Stage 3: Post-Processing
    
    Image->>Det: Send Tensor
    Det-->>Det: MobileNet V3 Large FPN
    Det->>Enc: Send Image Embedding Request
    Enc-->>Enc: ResNet18 Encoder
    Enc->>Dec: Send Embedding + Bounding Boxes
    Dec-->>Dec: MobileSAM Decoder (per detection)
    Dec->>Post: Send Masks and Scores
    Post-->>Post: Refine Masks, Extract Measurements
    Post-->>Image: InspectionResult (Pass/Fail)
```

**Optimization Profile:**

| Technique | Benefit | Implementation |
|-----------|---------|----------------|
| INT8 Quantization | 2x speedup, 75% size | ONNX Runtime quantization |
| Dynamic Axes | Variable batch/input size | ONNX dynamic shapes |
| Thread Tuning | Maximize CPU utilization | `intra_op_num_threads=0` |

---

### 2.3 Analysis Service

**Purpose:** Analytics, trending, and reporting

```mermaid
erDiagram
    INSPECTIONS ||--o{ DETECTIONS : contains
    DETECTIONS ||--o{ MEASUREMENTS : has
    INSPECTIONS {
        uuid id PK
        string station_id
        timestamp timestamp
        string decision
        float confidence
    }
    DETECTIONS {
        uuid id PK
        uuid inspection_id FK
        string class_name
        float confidence
    }
    MEASUREMENTS {
        uuid id PK
        uuid detection_id FK
        string name
        float value
    }
```

---

### 2.4 Integration Service

**Purpose:** Connect to external systems (PLCs, MES, APIs)

```mermaid
graph LR
    API[Integration Service] --> Modbus[Modbus TCP Server]
    API --> MQTT[MQTT Publisher]
    API --> REST[REST API]
    API --> OPC[OPC-UA Server]
    API --> Web[Webhook Callback]
```

---

## 3. Data Flow Diagrams

### 3.1 Typical Inspection Flow

```mermaid
graph LR
    Cam[Camera] --> Ing[Ingest]
    Ing --> Ins[Inspect]
    Ins --> Ana[Analyze]
    Ins --> Int[Integrate]
    Int --> PLC[PLC]
    API[API] --> Dash[Dashboard]
```

### 3.2 Active Learning Flow

```mermaid
graph LR
    Ins[Inspect Low Confidence] --> Queue[Queue Review]
    Queue --> Op[Operator Labels]
    Op --> Train[Auto Train]
    Train --> Deploy[Deploy Model]
```

### 3.3 Multi-Station Deployment

```mermaid
graph TD
    subgraph Cloud [Cloud (Optional)]
        Model[(Model Repo)]
        Ana[Analytics Dashboard]
    end

    subgraph Factory [Factory Network]
        GW[Edge Gateway]
        
        S1[Station 1]
        S2[Station 2]
        S3[Station 3]
        
        GW --> S1
        GW --> S2
        GW --> S3
    end

    Cloud <-->|VPN / Internet| Factory
```

---

## 4. Security Architecture

### Defense in Depth

```mermaid
graph TD
    subgraph Layer 1: Physical
        L1[Locked Enclosures, Isolated Nets]
    end
    subgraph Layer 2: Network
        L1 --> L2[VLAN, Firewalls]
    end
    subgraph Layer 3: Application
        L2 --> L3[TLS, RBAC, JWT Auth]
    end
    subgraph Layer 4: Data
        L3 --> L4[TDE Encryption, Audit Logs]
    end
```

---

**Document Version:** 1.0  
**Last Updated:** March 2026  
**Owner:** Ussop Engineering Team
