# API Reference

Base URL: `http://localhost:8080`
Interactive docs: `http://localhost:8080/docs` (Swagger) · `http://localhost:8080/redoc`

All endpoints (except `/api/v1/health` and `/api/v1/auth/login`) require a Bearer token:
```
Authorization: Bearer <access_token>
```

---

## Authentication

### POST /api/v1/auth/login
```json
// Request
{ "username": "admin", "password": "admin" }

// Response 200
{
  "access_token": "eyJ...",
  "refresh_token": "eyJ...",
  "token_type": "bearer",
  "user": { "id": "...", "username": "admin", "roles": ["admin"] }
}
```

### POST /api/v1/auth/refresh
```json
// Request
{ "refresh_token": "eyJ..." }
// Response 200 — new access_token
```

### POST /api/v1/auth/logout
Invalidates the refresh token.

### GET /api/v1/auth/me
Returns the current user profile.

---

## Inspection

### POST /api/v1/inspect
Upload an image for inspection.

```
Content-Type: multipart/form-data
Fields:
  file        image/jpeg|png|bmp|tiff|webp  (max 20 MB)
  station_id  string  (default: "default")
  part_id     string  (optional)
```

Response:
```json
{
  "id": "uuid",
  "decision": "pass|fail|uncertain",
  "confidence": 0.94,
  "objects_found": 2,
  "total_time_ms": 340,
  "detections": [
    {
      "class_name": "scratch",
      "confidence": 0.94,
      "bbox": [120, 80, 240, 160],
      "area_mm2": 12.4
    }
  ],
  "image_url": "/static/images/..."
}
```

### POST /api/v1/inspect/camera
Capture from the configured camera and inspect. Same response shape.

Query params: `station_id`, `part_id`

### GET /api/v1/inspect/{id}
Returns a stored inspection record by ID.

### GET /api/v1/inspections
List inspections with filtering and pagination.

Query params:
| Param      | Type   | Default | Description              |
|------------|--------|---------|--------------------------|
| station_id | string | —       | Filter by station        |
| decision   | string | —       | pass / fail / uncertain  |
| limit      | int    | 50      | Max results (≤ 500)      |
| offset     | int    | 0       | Pagination offset        |

### DELETE /api/v1/inspect/{id}
Delete an inspection record (admin/engineer only).

---

## Statistics & Trends

### GET /api/v1/statistics
Returns aggregated stats for the last N hours. **Cached 30 s.**

Query: `hours` (1–168, default 24), `station_id`

```json
{
  "total_inspections": 1420,
  "passed": 1380,
  "failed": 32,
  "uncertain": 8,
  "pass_rate": 0.972,
  "avg_inspection_time_ms": 312,
  "defect_breakdown": { "scratch": 18, "dent": 14 }
}
```

### GET /api/v1/trends
Time-series data for charting. **Cached 60 s.**

Query: `hours`, `interval` (hour|day), `station_id`

```json
{
  "labels": ["2024-01-15 08:00:00", "..."],
  "total":  [45, 52, 38],
  "passed": [44, 50, 38],
  "failed": [1, 2, 0]
}
```

### GET /api/v1/export/csv
Download all inspection history as CSV.

---

## Batch Processing

### GET /api/v1/batch/jobs
List all batch jobs.

### POST /api/v1/batch/jobs
Create a new batch job.
```json
{ "name": "Shift A", "input_dir": "/data/shift_a", "file_pattern": "*.jpg" }
```

### POST /api/v1/batch/jobs/{id}/start
Start a pending job.

### POST /api/v1/batch/jobs/{id}/cancel
Cancel a running job.

### GET /api/v1/batch/jobs/{id}
Get job status and progress.

---

## Active Learning

### GET /api/v1/active-learning/stats
Returns queue counts: pending / labeled / trained.

### GET /api/v1/active-learning/queue?limit=1
Returns the next N images requiring annotation.

### POST /api/v1/active-learning/annotate/{id}
Submit annotations for a queued image.
```json
{
  "annotations": [
    { "class_name": "scratch", "bbox": [10, 20, 100, 80] }
  ],
  "reviewed_by": "operator1"
}
```

---

## Model Training & Deployment

### POST /api/v1/training/start
Start a fine-tuning job using labeled images.
```json
{
  "epochs": 20,
  "batch_size": 8,
  "learning_rate": 0.001,
  "model_name": "v1.1-scratch"
}
```

### GET /api/v1/training/status
Returns current training job status and metrics.

### POST /api/v1/training/stop
Abort the running training job.

### GET /api/v1/models
List all available model versions.

### POST /api/v1/models/{id}/deploy
Hot-swap the active model (zero downtime).

### POST /api/v1/models/{id}/rollback
Revert to a previous model version.

---

## Alerts

### GET /api/v1/alerts
Query params: `severity` (info|warning|error|critical), `acknowledged` (bool)

```json
{
  "alerts": [
    {
      "id": "uuid",
      "severity": "warning",
      "title": "Pass rate below threshold",
      "message": "Pass rate 87% is below the 90% target",
      "timestamp": "2024-01-15T09:32:00",
      "acknowledged": false
    }
  ]
}
```

### POST /api/v1/alerts/{id}/acknowledge
Mark an alert as acknowledged.

---

## System

### GET /api/v1/health
No auth required.
```json
{ "status": "healthy", "version": "1.0.0" }
```

### GET /api/v1/config
Returns current application configuration.

### POST /api/v1/config
Update configuration (admin/engineer only).

### GET /api/v1/storage/usage
Returns disk usage breakdown.

### POST /api/v1/storage/cleanup
Delete images older than retention policy.

### GET /metrics
Prometheus metrics endpoint.

---

## Natural Language Query (VLM)

Requires `VLM_ENABLED=true` in settings.

### POST /api/v1/query
```json
// Request
{ "question": "How many scratches were found at Station 3 this week?" }

// Response
{
  "question": "How many scratches...",
  "answer": "17 scratches were detected at Station 3 over the last 7 days...",
  "backend": "anthropic"
}
```

---

## OPC-UA

### GET /api/v1/opcua/status

Returns the current state of the OPC-UA server.

**Response**
```json
{
  "enabled": true,
  "running": true,
  "endpoint": "opc.tcp://0.0.0.0:4840/ussop",
  "station_count": 3,
  "nodes": ["station/line-1", "station/line-2", "station/line-3", "SystemStatus"]
}
```

The OPC-UA server exposes the following nodes per station:

| Node | Type | Description |
|---|---|---|
| `LastDecision` | String | `"pass"` / `"fail"` / `"uncertain"` |
| `LastConfidence` | Float | Confidence score 0–1 |
| `ObjectsFound` | Int | Number of detections in last inspection |
| `CycleTimeMs` | Float | Inference time in milliseconds |
| `PassCount` | Int | Cumulative pass count |
| `FailCount` | Int | Cumulative fail count |
| `UncertainCount` | Int | Cumulative uncertain count |
| `PassRate1h` | Float | Pass rate over last hour (0–100) |
| `LastInspectionTime` | DateTime | UTC timestamp of last inspection |

Enable the server by setting `OPCUA_ENABLED=true` and `OPCUA_PORT=4840` in `.env`.

---

## OpenVINO

### GET /api/v1/openvino/status

Returns whether the OpenVINO optimizer is available and which device is configured.

**Response**
```json
{
  "available": true,
  "enabled": true,
  "device": "AUTO",
  "loaded_models": ["encoder", "decoder"],
  "ort_fallback": false
}
```

---

### POST /api/v1/openvino/load

Load an ONNX model into the OpenVINO runtime.

**Request body**
```json
{
  "model_key": "encoder",
  "model_path": "/app/models/resnet18_image_encoder.onnx",
  "device": "CPU"
}
```

**Response** — `200 OK`
```json
{ "status": "loaded", "model_key": "encoder", "device": "CPU" }
```

---

### POST /api/v1/openvino/benchmark

Run a side-by-side latency comparison between ONNX Runtime and OpenVINO.

**Request body**
```json
{
  "model_key": "encoder",
  "iterations": 50
}
```

**Response**
```json
{
  "model_key": "encoder",
  "ort_mean_ms": 42.1,
  "ov_mean_ms": 18.7,
  "speedup": 2.25
}
```

---

## WebSocket

### WS /ws/dashboard?token={access_token}

Real-time push updates for the dashboard. Messages:

```json
// Heartbeat (every 5 s)
{ "type": "ping", "data": { ... current stats ... } }

// New inspection completed
{ "type": "inspection", "data": { ... inspection record ... } }

// Stats refresh
{ "type": "stats", "data": { ... statistics ... } }
```

Falls back to polling if WebSocket is unavailable.

---

## User Management (Admin only)

| Method | Path | Description |
|--------|------|-------------|
| GET    | /api/v1/users | List all users |
| POST   | /api/v1/users | Create user |
| PUT    | /api/v1/users/{id} | Update user |
| DELETE | /api/v1/users/{id} | Delete user |
| PUT    | /api/v1/users/me | Update own email |
| PUT    | /api/v1/users/me/password | Change own password |

---

## Rate Limits

| Endpoint       | Limit        |
|----------------|--------------|
| POST /auth/login | 10 / minute |
| All others     | 200 / minute |

Exceeding limits returns `429 Too Many Requests`.

---

## Error Responses

All errors follow:
```json
{ "detail": "Human-readable error message" }
```

| Code | Meaning |
|------|---------|
| 400  | Bad request / validation error |
| 401  | Missing or invalid token |
| 403  | Insufficient permissions |
| 404  | Resource not found |
| 413  | File too large (> 20 MB) |
| 415  | Unsupported media type |
| 422  | Unprocessable entity |
| 429  | Rate limit exceeded |
| 503  | Service unavailable (VLM disabled, etc.) |
