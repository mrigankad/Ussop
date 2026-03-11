#!/usr/bin/env python3
"""
Ussop - Quick Start Script
Run: python ussop/run.py
"""
import sys
import os
from pathlib import Path

# Add paths: project root (for ussop package) and ussop dir (for config/models/services)
_project_root = str(Path(__file__).parent.parent)
_ussop_dir = str(Path(__file__).parent)
for _p in (_ussop_dir, _project_root):
    if _p not in sys.path:
        sys.path.insert(0, _p)

# Ensure directories and resolve model paths
from config.settings import settings, ensure_directories
ensure_directories()

encoder_path = Path(settings.ENCODER_PATH)
decoder_path = Path(settings.DECODER_PATH)

if not encoder_path.exists() or not decoder_path.exists():
    print("=" * 60)
    print("NanoSAM models not found!")
    print("=" * 60)
    print("\nPlease download the models first:")
    print("  python scripts/download_models.py")
    print("\nThen copy them to:", settings.MODELS_DIR)
    print("=" * 60)
    sys.exit(1)

# Initialize database
from models.database import init_database
init_database()

print("=" * 60)
print("  USSOP - AI Visual Inspector")
print("  'Sniper precision. Slingshot simple.'")
print("=" * 60)
print()
print("  Dashboard : http://localhost:8080")
print("  Inspect   : http://localhost:8080/inspect")
print("  History   : http://localhost:8080/history")
print("  Analytics : http://localhost:8080/analytics")
print("  API Docs  : http://localhost:8080/docs")
print()

# Run server
import uvicorn

if __name__ == "__main__":
    uvicorn.run(
        "ussop.api.main:app",
        host="0.0.0.0",
        port=8080,
        reload=False,
        log_level="info"
    )
