# Customer Onboarding Guide

## What is Ussop?

Ussop is a **CPU-only AI visual inspection system** for manufacturing lines. It detects and precisely segments defects in real time using computer vision — no GPU, no cloud dependency, no ongoing license fees.

**Key benefits vs. traditional systems (e.g., Cognex):**
- 1/3 the cost
- Deploys in hours, not months
- Runs on any industrial PC (Intel i5+, 8 GB RAM)
- Fully customizable via active learning

---

## Step 1 — Hardware Requirements

| Component | Minimum | Recommended |
|-----------|---------|-------------|
| CPU       | Intel i5 4-core | Intel i7/i9 8-core |
| RAM       | 8 GB    | 16 GB       |
| Storage   | 50 GB SSD | 500 GB SSD |
| Camera    | USB 720p | GigE 5MP |
| Network   | 100 Mbps | 1 Gbps |
| OS        | Ubuntu 22.04 / Windows 11 | Ubuntu 22.04 LTS |

---

## Step 2 — Install

**Option A — Python (dev/single machine):**
```bash
pip install -e .
python scripts/download_models.py
python ussop/run.py
```

**Option B — Docker (production):**
```bash
cp .env.example .env   # set SECRET_KEY and POSTGRES_PASSWORD
docker compose -f docker/docker-compose.yml up -d
```

See [deployment.md](deployment.md) for full production setup including TLS and PostgreSQL.

---

## Step 3 — Connect Your Camera

Edit `.env` (or Settings → Configuration in the UI):

| Camera type | Setting |
|-------------|---------|
| USB webcam  | `CAMERA_TYPE=usb`, `CAMERA_INDEX=0` |
| GigE industrial | `CAMERA_TYPE=gige` |
| Image folder | `CAMERA_TYPE=file` |
| Demo/test   | `CAMERA_TYPE=mock` |

Test the connection at **Inspect → Camera tab → Live Capture**.

---

## Step 4 — First Inspection

1. Go to **Inspect**
2. Upload a sample image (JPEG/PNG, max 20 MB)
3. Review the results:
   - **Decision**: Pass / Fail / Uncertain
   - **Detections**: bounding boxes + confidence scores
   - **Segmentation masks**: precise defect boundaries
   - **Measurements**: area in mm² (requires calibration)

---

## Step 5 — Teach Your Defects (Active Learning)

The default model is trained on generic defect categories. To train it on **your specific parts**:

1. Run **≥ 50 inspections** to populate the active learning queue
2. Go to **Annotate** — review images flagged as uncertain
3. Draw bounding boxes and label defect types
4. Once ≥ 100 images are labeled, go to **Settings → Model Training**
5. Click **Start Training** — the model retrains in the background (30–60 min on i7)
6. When complete, click **Deploy** to activate the new model

Repeat every 2–4 weeks as new defect types emerge.

---

## Step 6 — Integrate with Your PLC / SCADA

### Modbus TCP (most PLCs)
```env
MODBUS_ENABLED=true
MODBUS_HOST=192.168.1.100   # your PLC IP
MODBUS_PORT=502
```
Results are written to coil registers after each inspection.

### MQTT (IoT / SCADA)
```env
MQTT_ENABLED=true
MQTT_BROKER=192.168.1.50
MQTT_PORT=1883
```
Topic: `ussop/inspections/{station_id}` — JSON payload per inspection.

### REST API
Any system that can make HTTP calls can use the API directly.
See [api.md](api.md) for full reference.

---

## Step 7 — Set Up Alerts

Go to **Settings → Notifications**:
- Email alerts when pass rate drops below threshold
- Webhook (POST to any URL) for custom integrations
- Configure severity thresholds for automatic alerts

View active alerts on the **Alerts** page.

---

## Step 8 — Monitoring & Reports

- **Analytics** — trend charts, pass/fail over time, defect breakdown
- **History** — full searchable inspection log with CSV export
- **Grafana** (optional) — `http://your-server:3001` for advanced dashboards

---

## Roles & Permissions

| Role      | Can inspect | Configure | Manage users | Train models |
|-----------|-------------|-----------|-------------|--------------|
| Viewer    | Read-only   | No        | No          | No           |
| Operator  | Yes         | No        | No          | No           |
| Engineer  | Yes         | Yes       | No          | Yes          |
| Admin     | Yes         | Yes       | Yes         | Yes          |

Create users at **Settings → User Management**.

---

## Troubleshooting

**"Model files not found"**
```bash
python scripts/download_models.py
```

**Camera shows black frame**
- Check `CAMERA_INDEX` (try 0, 1, 2)
- For GigE: verify camera IP is on the same subnet

**Low pass rate on first deployment**
- The base model has not seen your parts yet
- Complete Step 5 (active learning) with at least 100 labeled images

**High cycle time (> 1 s)**
- Reduce `ONNX_THREADS` to match physical core count
- Use `DETECTOR_BACKBONE=mobilenet` instead of `resnet50`

**Need help?**
- Check logs: `docker compose logs -f api`
- File an issue: https://github.com/ussop/ussop/issues
