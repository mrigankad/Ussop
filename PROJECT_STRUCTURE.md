# Project Structure Guide

## Overview
Ussop now follows industry-standard Python project layout making it easier to maintain, test, and deploy.

## Directory Structure

```
ussop-project/
├── .github/                    # GitHub workflows (CI/CD)
│   └── workflows/              # Future: GitHub Actions
│       ├── tests.yml
│       └── deploy.yml
│
├── docs/                        # Project documentation
│   ├── README.md               # Getting started
│   ├── architecture.md         # Technical design
│   ├── plan.md                 # Product roadmap
│   ├── FEATURES.md             # Feature checklist
│   ├── APP_README.md           # Application docs
│   ├── PROJECT_SUMMARY.md      # Project overview
│   ├── STATUS_REPORT.md        # Current status
│   ├── pitch_deck.md           # Investor pitch
│   └── user_stories.md         # User requirements
│
├── examples/                    # Demo code and examples
│   ├── pipeline.py             # Detection + segmentation pipeline
│   ├── detector.py             # Faster R-CNN wrapper
│   ├── predictor.py            # NanoSAM segmentation
│   ├── demo.py                 # Interactive demo
│   └── safety_checker.py        # Safety feature examples
│
├── scripts/                     # Utility scripts
│   └── download_models.py       # Model download script
│
├── docker/                      # Docker configuration
│   ├── Dockerfile              # Container image
│   └── docker-compose.yml       # Multi-service orchestration
│
├── ussop/                       # Main application package
│   ├── api/                     # FastAPI REST endpoints (50+)
│   │   └── main.py              # API routes and handlers
│   │
│   ├── services/                # Business logic
│   │   ├── inspector.py         # Core inspection pipeline
│   │   ├── camera.py            # Camera integration
│   │   ├── camera_manager.py    # Multi-camera support
│   │   ├── active_learning.py   # Uncertainty sampling
│   │   ├── monitoring.py        # Metrics & alerts
│   │   └── notifications.py     # Email, Slack, webhooks
│   │
│   ├── models/                  # Database models
│   │   └── database.py          # SQLAlchemy ORM
│   │
│   ├── integrations/            # Protocol adapters
│   │   ├── modbus_server.py     # PLC (Modbus TCP)
│   │   └── mqtt_client.py       # IoT (MQTT)
│   │
│   ├── config/                  # Configuration management
│   │   └── settings.py          # Environment settings
│   │
│   ├── core/                    # Core utilities
│   │   └── __init__.py
│   │
│   ├── templates/               # HTML templates (Jinja2)
│   │   ├── index.html           # Dashboard
│   │   ├── inspect.html         # Inspection interface
│   │   ├── history.html         # History & export
│   │   ├── analytics.html       # Charts
│   │   ├── annotate.html        # Active learning
│   │   └── config.html          # Settings
│   │
│   ├── static/                  # Frontend assets
│   │   ├── css/                 # Stylesheets
│   │   │   └── style.css        # Main styles
│   │   └── js/                  # JavaScript
│   │
│   ├── ui/                      # UI components (future)
│   │
│   ├── data/                    # Runtime data (auto-created)
│   │   ├── db/                  # SQLite database files
│   │   ├── images/              # Inspection images
│   │   ├── masks/               # Segmentation masks
│   │   ├── logs/                # Application logs
│   │   └── audit/               # Audit logs
│   │
│   ├── tests/                   # Test suite
│   │   ├── conftest.py          # Pytest fixtures
│   │   ├── unit/                # Unit tests
│   │   ├── integration/         # Integration tests
│   │   └── test_*.py            # Test modules
│   │
│   ├── __init__.py              # Package initialization
│   ├── run.py                   # Application entry point
│   ├── run_tests.py             # Test runner
│   └── setup.py                 # Setup wizard
│
├── .env.example                 # Configuration template
├── .gitignore                   # Git ignore rules
├── .git/                        # Git repository
│
├── README.md                    # Project README (START HERE)
├── LICENSE                      # MIT License
├── CHANGELOG.md                 # Version history
├── pyproject.toml               # Modern Python project config
├── requirements.txt             # Python dependencies
│
└── .github/                     # GitHub config
    └── workflows/               # CI/CD (future)
```

## Key Conventions

### Code Organization
- **`ussop/api/`** — All REST endpoints live here (API layer)
- **`ussop/services/`** — Business logic independent of HTTP (service layer)
- **`ussop/models/`** — Database schema and ORM models (data layer)
- **`ussop/integrations/`** — External system connectors (adapter pattern)

### Configuration
- Use `.env` files for environment-specific settings (never commit `.env`)
- Template file: `.env.example` (commit this, don't commit `.env`)
- Settings class: `ussop/config/settings.py` (validates all configs)

### Testing
- Place tests in `ussop/tests/` with structure mirroring `ussop/`
- Use pytest fixtures from `conftest.py`
- Run tests: `cd ussop && python run_tests.py`

### Documentation
- User-facing docs in `docs/`
- API docs auto-generated from FastAPI docstrings
- Architecture and design decisions in `docs/architecture.md`

### Examples
- Legacy/demo code in `examples/` (reference only)
- Keep real code in `ussop/` package
- Examples for customers in `examples/` with clear comments

### Scripts
- One-off utility scripts in `scripts/`
- Production code lives in `ussop/` package

## Development Workflow

### Setup
```bash
# 1. Clone and install
git clone <repo>
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 2. Configure
cp .env.example .env
# Edit .env with your settings

# 3. Run
cd ussop
python run.py
```

### Adding Features
```bash
# 1. Create feature branch
git checkout -b feature/my-feature

# 2. Add code in ussop/ package
# ussop/api/main.py for endpoints
# ussop/services/ for logic
# ussop/models/ for database

# 3. Add tests
# ussop/tests/unit/ for unit tests
# ussop/tests/integration/ for integration tests

# 4. Run tests
cd ussop && python run_tests.py

# 5. Commit with message following Conventional Commits
git commit -m "feat(api): add new inspection endpoint"
```

### Deployment
```bash
# Option 1: Docker Compose (recommended)
docker-compose -f docker/docker-compose.yml up -d

# Option 2: Manual
cd ussop && python setup.py && python run.py
```

## Files to Know

### Must Read
- **`README.md`** — Start here
- **`docs/STATUS_REPORT.md`** — Current project status
- **`docs/architecture.md`** — Technical design

### Important References
- **`docs/plan.md`** — Product roadmap
- **`docs/FEATURES.md`** — Feature checklist
- **`requirements.txt`** — Dependencies

### Configuration
- **`.env.example`** — Configuration template
- **`pyproject.toml`** — Project metadata
- **`docker-compose.yml`** — Deployment config

## What Was Removed (Cleanup)

### Removed Directories
- ✅ `ref/` — Reference material (moved to docs if needed)
- ✅ `__pycache__/` — Python cache files
- ✅ `assets/` — Consolidated where needed

### Consolidated Files
- ✅ `ussop/README.md` → `docs/APP_README.md`
- ✅ `ussop/FEATURES.md` → `docs/FEATURES.md`
- ✅ `ussop/PROJECT_SUMMARY.md` → `docs/PROJECT_SUMMARY.md`
- ✅ `ussop/requirements.txt` → `requirements.txt` (root)
- ✅ `ussop/.env.example` → `.env.example` (root)
- ✅ `ussop/Dockerfile` → `docker/Dockerfile`
- ✅ `ussop/docker-compose.yml` → `docker/docker-compose.yml`

### Moved Demo Code
- ✅ `pipeline.py` → `examples/pipeline.py`
- ✅ `detector.py` → `examples/detector.py`
- ✅ `predictor.py` → `examples/predictor.py`
- ✅ `demo.py` → `examples/demo.py`
- ✅ `safety_checker.py` → `examples/safety_checker.py`
- ✅ `download_models.py` → `scripts/download_models.py`

### Moved Documentation
- ✅ `architecture.md` → `docs/architecture.md`
- ✅ `plan.md` → `docs/plan.md`
- ✅ `pitch_deck.md` → `docs/pitch_deck.md`
- ✅ `user_stories.md` → `docs/user_stories.md`
- ✅ `STATUS_REPORT.md` → `docs/STATUS_REPORT.md`

## Next Steps

1. **Update imports** — Adjust any imports in code to point to new locations
2. **Update CI/CD** — Add GitHub Actions workflows in `.github/workflows/`
3. **Update documentation links** — Ensure all links point to new doc locations
4. **Commit cleanup** — `git commit -am "chore: reorganize to industry-standard structure"`

## Benefits of New Structure

| Benefit | Why It Matters |
|---------|----------------|
| **Standard Layout** | New developers recognize the structure immediately |
| **Separation of Concerns** | Code, tests, docs, examples, scripts all separate |
| **Scalability** | Easy to add new services, models, integrations |
| **Maintainability** | Clear file organization reduces cognitive load |
| **Deployment Ready** | `docker/` and `scripts/` make ops tasks clear |
| **Documentation First** | `/docs` is central, easier to find information |
| **Example Driven** | `/examples` shows how to use the system |

---

For questions about file locations, see the structure above.
