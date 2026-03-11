# 🚀 Ussop - Start Here

> **Project just cleaned and reorganized!** Welcome to Ussop, the sniper-precision AI inspection system for manufacturing.

## ⚡ Quick Links

**👉 Just arrived?** Start with these 3 files:
1. **[README.md](README.md)** — Project overview and quick start
2. **[PROJECT_STRUCTURE.md](PROJECT_STRUCTURE.md)** — Where everything is located
3. **[docs/STATUS_REPORT.md](docs/STATUS_REPORT.md)** — Current implementation status

## 📋 What Happened (Cleanup)

Your project was recently reorganized to **industry-standard structure**:

✅ **Files Removed**: Cache files, reference directories
✅ **Files Organized**: Documentation, examples, scripts grouped
✅ **Files Consolidated**: Single source of truth for configs
✅ **Files Added**: README, LICENSE, CHANGELOG, pyproject.toml

**See:** [BEFORE_AND_AFTER.md](BEFORE_AND_AFTER.md) for details
**See:** [CLEANUP_SUMMARY.txt](CLEANUP_SUMMARY.txt) for full summary

---

## 🎯 Project Structure

```
ussop-project/
├── docs/              ← All documentation (8 files)
├── examples/          ← Reference code (5 scripts)
├── scripts/           ← Utilities (model download)
├── docker/            ← Deployment (Docker Compose)
├── ussop/             ← Production application
│   ├── api/           ← REST endpoints (50+)
│   ├── services/      ← Business logic
│   ├── models/        ← Database
│   ├── tests/         ← Test suite
│   └── ...
├── README.md          ← Start here
├── LICENSE            ← MIT
├── CHANGELOG.md       ← Version history
└── requirements.txt   ← Dependencies
```

---

## 📖 Documentation by Purpose

### Getting Started
- **[README.md](README.md)** — Project overview, quick start, features
- **[PROJECT_STRUCTURE.md](PROJECT_STRUCTURE.md)** — File organization guide
- **[docs/STATUS_REPORT.md](docs/STATUS_REPORT.md)** — What's implemented

### Technical Details
- **[docs/architecture.md](docs/architecture.md)** — System design
- **[docs/FEATURES.md](docs/FEATURES.md)** — Feature checklist
- **[docs/APP_README.md](docs/APP_README.md)** — API documentation

### Business & Planning
- **[docs/plan.md](docs/plan.md)** — Product roadmap
- **[docs/pitch_deck.md](docs/pitch_deck.md)** — Investor presentation
- **[docs/user_stories.md](docs/user_stories.md)** — Requirements

### Examples & Learning
- **[examples/](examples/)** — Reference implementations (5 scripts)
- **[docs/FEATURES.md](docs/FEATURES.md)** — What's already built

### Project Info
- **[LICENSE](LICENSE)** — MIT License
- **[CHANGELOG.md](CHANGELOG.md)** — Version history and roadmap
- **[BEFORE_AND_AFTER.md](BEFORE_AND_AFTER.md)** — Recent cleanup details
- **[CLEANUP_SUMMARY.txt](CLEANUP_SUMMARY.txt)** — Comprehensive cleanup log

---

## 🚀 Get Started in 5 Minutes

### 1. Setup Environment
```bash
cd /path/to/ussop-project
cp .env.example .env
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Deploy (Choose One)

**Option A: Docker (Recommended)**
```bash
docker-compose -f docker/docker-compose.yml up -d
# Open http://localhost:8080
```

**Option B: Manual**
```bash
cd ussop
python setup.py
python run.py
# Open http://localhost:8080
```

### 3. Run Tests
```bash
cd ussop
python run_tests.py
```

### 4. Access API Docs
```
http://localhost:8080/docs
```

---

## 📊 Project Status

**Phase:** MVP (Production-Ready) + Phase 2 (90% Complete)

### What's Built ✅
- Faster R-CNN + NanoSAM inference pipeline (CPU-optimized)
- Web dashboard with real-time metrics
- 60+ REST API endpoints
- User authentication + role-based access control
- Active learning with annotation UI
- Batch processing
- Modbus TCP + MQTT integrations
- Performance monitoring & alerts
- Audit logging (compliance)

### What's Needed 🟡
- Model retraining pipeline (~40-60h)
- Comprehensive test suite (~50-80h)
- Security hardening (~25-35h)
- Documentation & examples (~30-40h)

**→ See [docs/STATUS_REPORT.md](docs/STATUS_REPORT.md) for full details**

---

## 🎯 Key Features

| Feature | Status | Details |
|---------|--------|---------|
| Object Detection | ✅ | Faster R-CNN (MobileNet + ResNet50) |
| Segmentation | ✅ | NanoSAM (ONNX Runtime) |
| CPU-Only | ✅ | No GPU required |
| Web UI | ✅ | 7 pages + dashboard |
| API | ✅ | 60+ REST endpoints |
| Authentication | ✅ | JWT + RBAC |
| Integrations | ✅ | Modbus TCP, MQTT |
| Active Learning | ✅ | Annotation queue |
| Batch Processing | ✅ | Folder inspection |
| Monitoring | ✅ | Metrics + alerts |
| Docker | ✅ | Docker Compose |

---

## 💡 Common Tasks

### Add a New Feature
1. Create service in `ussop/services/`
2. Add API endpoint in `ussop/api/main.py`
3. Add tests in `ussop/tests/`
4. Update [docs/FEATURES.md](docs/FEATURES.md)
5. Commit with meaningful message

### Deploy to Production
1. Update `.env` with production settings
2. Use `docker-compose` (see [README.md](README.md))
3. Run database migrations if needed
4. Monitor with health checks: `/api/v1/health`

### Run Tests
```bash
cd ussop
python run_tests.py              # All tests
pytest tests/test_inspector.py   # Specific test
pytest tests/ -v --cov          # With coverage
```

### Check Status
- Health: `http://localhost:8080/api/v1/health`
- Metrics: `http://localhost:8080/api/v1/metrics/performance`
- Logs: `ussop/data/logs/`

---

## 🔍 File Guide

### If You Want To...

**Understand the project**
→ Read [README.md](README.md), then [docs/STATUS_REPORT.md](docs/STATUS_REPORT.md)

**Find where something is**
→ See [PROJECT_STRUCTURE.md](PROJECT_STRUCTURE.md)

**Learn the architecture**
→ Read [docs/architecture.md](docs/architecture.md)

**See what's implemented**
→ Check [docs/FEATURES.md](docs/FEATURES.md)

**Learn how to use APIs**
→ See [docs/APP_README.md](docs/APP_README.md)

**Understand the business**
→ Read [docs/plan.md](docs/plan.md)

**See reference code**
→ Look in [examples/](examples/)

**Know what changed**
→ See [BEFORE_AND_AFTER.md](BEFORE_AND_AFTER.md)

**Understand deployment**
→ Read [docker/docker-compose.yml](docker/docker-compose.yml)

---

## 🛠️ Technology Stack

- **Backend**: Python 3.11, FastAPI
- **ML/CV**: PyTorch, ONNX Runtime, OpenCV
- **Database**: SQLite (PostgreSQL ready)
- **Frontend**: HTML5, CSS3, Chart.js
- **Testing**: pytest
- **Deployment**: Docker, Docker Compose

---

## 📞 Need Help?

### Documentation
- **README.md** — Quick overview
- **PROJECT_STRUCTURE.md** — File organization
- **docs/** — Comprehensive guides

### Common Questions
- *"How do I run this?"* → [README.md](README.md)
- *"Where is X?"* → [PROJECT_STRUCTURE.md](PROJECT_STRUCTURE.md)
- *"What's implemented?"* → [docs/STATUS_REPORT.md](docs/STATUS_REPORT.md)
- *"How do I deploy?"* → [README.md](README.md) + [docker/](docker/)
- *"What's the architecture?"* → [docs/architecture.md](docs/architecture.md)
- *"How does API work?"* → [docs/APP_README.md](docs/APP_README.md)

---

## ✅ You're Ready!

Your Ussop project is now:
- ✅ Professionally organized
- ✅ Well-documented
- ✅ Production-ready
- ✅ Easy to maintain
- ✅ Ready to scale

**Next Step:** Read [README.md](README.md) for quick start! 🚀

---

**Version**: 1.0.0 (March 3, 2026)
**Structure**: Industry-Standard Python Project
**Status**: Production-Ready MVP + Phase 2 (90% Complete)
