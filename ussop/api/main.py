"""
Ussop FastAPI Application
"""
import asyncio
import logging
import os
from pathlib import Path
from typing import List, Optional
from datetime import datetime, timedelta, timezone
import json
import io

logger = logging.getLogger(__name__)

from contextlib import asynccontextmanager
from fastapi import FastAPI, File, UploadFile, Depends, HTTPException, Query, BackgroundTasks, Request
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response as StarletteResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from sqlalchemy.orm import Session

# ─── Rate limiter ────────────────────────────────────────────────────────────
limiter = Limiter(key_func=get_remote_address, default_limits=["200/minute"])

# Allowed MIME types and max size for image uploads
_ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/bmp", "image/tiff", "image/webp"}
_MAX_UPLOAD_BYTES = 20 * 1024 * 1024  # 20 MB


async def _validate_image_upload(file: UploadFile) -> bytes:
    """Read and validate an uploaded image. Returns raw bytes."""
    content = await file.read()
    if len(content) == 0:
        raise HTTPException(status_code=422, detail="Uploaded file is empty.")
    if len(content) > _MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail=f"File too large (max {_MAX_UPLOAD_BYTES // 1024 // 1024} MB).")
    ct = (file.content_type or "").lower().split(";")[0].strip()
    if ct and ct not in _ALLOWED_IMAGE_TYPES:
        raise HTTPException(status_code=415, detail=f"Unsupported media type '{ct}'. Upload a JPEG, PNG, BMP, TIFF or WebP image.")
    return content

# Add paths: ussop/ for bare imports, project root for ussop package, examples/ for pipeline
import sys
_api_dir = Path(__file__).parent
_ussop_dir = _api_dir.parent
_project_root = _ussop_dir.parent
_examples_dir = _project_root / "examples"
for _p in (_examples_dir, _ussop_dir, _project_root):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

from config.settings import settings, ensure_directories
from models.database import init_database, get_db, Inspection, Decision
from models.auth import User, Role, UserSession, init_default_roles, create_default_admin
from services.inspector import InspectionService, InspectionConfig
from services.camera import CameraService
from services.active_learning import get_active_learning, get_retrainer
from services.monitoring import get_metrics_collector, get_alert_manager, get_audit_logger
from services.auth_service import (
    get_auth_service, get_current_user_dependency, get_current_active_user,
    require_permission, require_inspect, require_configure, require_manage_users
)
from services.batch_processor import get_batch_processor, BatchJobStatus, InspectionConfig
from services.model_trainer import get_model_trainer, TrainingConfig
from services.model_deployer import get_model_deployer
from services.cache import cache

# Optional integrations
mqtt_client = None
try:
    from integrations.mqtt_client import get_mqtt_client
    mqtt_client = get_mqtt_client()
except:
    pass

# Auth enabled flag (can be disabled for development)
AUTH_ENABLED = True  # Set to False to disable authentication

# Initialize
ensure_directories()
init_database()

# Initialize auth tables and default admin
try:
    from sqlalchemy.orm import sessionmaker
    from models.database import engine
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()
    init_default_roles(db)
    create_default_admin(db, password="admin")
    db.close()
    print("[Auth] Authentication system initialized")
except Exception as e:
    print(f"[Auth] Initialization error: {e}")

def _run_migrations() -> None:
    """Apply any pending Alembic migrations at startup."""
    try:
        from pathlib import Path as _Path
        from alembic.config import Config as _AlembicConfig
        from alembic import command as _alembic_cmd

        ini = _Path(__file__).parent.parent.parent / "alembic.ini"
        if ini.exists():
            cfg = _AlembicConfig(str(ini))
            _alembic_cmd.upgrade(cfg, "head")
            logger.info("[Startup] Alembic migrations applied")
        else:
            logger.debug("[Startup] alembic.ini not found — skipping migrations")
    except Exception as exc:
        logger.warning("[Startup] Alembic migration warning: %s", exc)


@asynccontextmanager
async def _lifespan(app: FastAPI):
    _run_migrations()
    await cache.connect(settings.REDIS_URL)
    logger.info("[Startup] Cache backend: %s", cache.backend)

    # OPC-UA server (optional)
    _opcua = None
    if settings.OPCUA_ENABLED:
        try:
            from integrations.opcua_server import get_opcua_server
            _opcua = get_opcua_server()
            await _opcua.start()
        except Exception as _e:
            logger.warning("[Startup] OPC-UA start failed: %s", _e)

    yield

    if _opcua:
        await _opcua.stop()
    await cache.close()
    logger.info("[Shutdown] Complete")


app = FastAPI(
    title="Ussop API",
    description="AI Visual Inspection for Manufacturing",
    version=settings.APP_VERSION,
    lifespan=_lifespan,
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Security headers middleware
class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        # Only add HSTS in production (when served over HTTPS)
        # response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        return response

app.add_middleware(SecurityHeadersMiddleware)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static files
app.mount("/static", StaticFiles(directory=str(Path(__file__).parent.parent / "static")), name="static")

# Services
inspector_service = InspectionService()

# Wire deployer → inspector for hot-swap
try:
    get_model_deployer().register_inspector(inspector_service)
except Exception as _e:
    print(f"[API] Deployer wiring warning: {_e}")


# =============================================================================
# SPA catch-all — serves the React frontend for all UI routes
# =============================================================================

_SPA_INDEX = Path(__file__).parent.parent / "static" / "dist" / "index.html"

def _serve_spa() -> HTMLResponse:
    """Serve the React SPA. Falls back to a plain error page if not built yet."""
    if _SPA_INDEX.exists():
        return HTMLResponse(content=_SPA_INDEX.read_text(encoding="utf-8"))
    return HTMLResponse(
        content=(
            "<html><body style='font-family:sans-serif;padding:2rem'>"
            "<h2>Ussop UI not built</h2>"
            "<p>Run <code>cd ussop/frontend && npm run build</code> then restart.</p>"
            "<p>API docs: <a href='/docs'>/docs</a></p>"
            "</body></html>"
        ),
        status_code=503,
    )

@app.get("/", response_class=HTMLResponse)
async def root(): return _serve_spa()

@app.get("/inspect",   response_class=HTMLResponse)
async def inspect_page(): return _serve_spa()

@app.get("/history",   response_class=HTMLResponse)
async def history_page(): return _serve_spa()

@app.get("/analytics", response_class=HTMLResponse)
async def analytics_page(): return _serve_spa()


# =============================================================================
# API Routes - Inspection
# =============================================================================

@app.post("/api/v1/inspect")
async def inspect_image(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    part_id: Optional[str] = None,
    station_id: str = "default",
    db: Session = Depends(get_db),
    current_user: User = Depends(require_inspect),
):
    """
    Upload and inspect an image (JPEG, PNG, BMP, TIFF, WebP — max 20 MB).
    """
    try:
        # Validate before touching disk
        content = await _validate_image_upload(file)

        # Save uploaded file temporarily
        safe_name = Path(file.filename or "upload.jpg").name  # strip any path traversal
        temp_path = settings.IMAGES_DIR / "temp" / safe_name
        temp_path.parent.mkdir(parents=True, exist_ok=True)

        with open(temp_path, "wb") as f:
            f.write(content)

        # Run CPU-bound inference in a thread pool so the event loop stays free
        config = InspectionConfig()
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None,
            lambda: inspector_service.inspect_image(
                image_path=str(temp_path),
                part_id=part_id,
                station_id=station_id,
                db=db,
                config=config,
            ),
        )

        # Clean up temp file
        background_tasks.add_task(lambda: temp_path.unlink() if temp_path.exists() else None)

        # Push to live dashboard clients + record Prometheus metrics (non-blocking)
        background_tasks.add_task(broadcast_inspection, result)
        background_tasks.add_task(_record_prometheus, result)
        background_tasks.add_task(lambda: asyncio.run(cache.clear_prefix("stats:")))
        background_tasks.add_task(lambda: asyncio.run(cache.clear_prefix("trends:")))

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Inspection failed")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/inspect/camera")
async def inspect_from_camera(
    station_id: str = "default",
    part_id: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_inspect),
):
    """
    Capture from camera and inspect.
    """
    try:
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None,
            lambda: inspector_service.inspect_from_camera(
                station_id=station_id,
                part_id=part_id,
                db=db,
            ),
        )
        background_tasks.add_task(lambda: asyncio.run(cache.clear_prefix("stats:")))
        background_tasks.add_task(lambda: asyncio.run(cache.clear_prefix("trends:")))
        return result
    except Exception as e:
        logger.exception("Camera inspection failed")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/inspect/{inspection_id}")
async def get_inspection(
    inspection_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_inspect),
):
    """
    Get inspection details by ID.
    """
    from ussop.models.database import Inspection
    
    inspection = db.query(Inspection).filter(Inspection.id == inspection_id).first()
    if not inspection:
        raise HTTPException(status_code=404, detail="Inspection not found")
    
    from ussop.models.database import Detection
    detections = db.query(Detection).filter(Detection.inspection_id == inspection_id).all()

    return {
        "id": inspection.id,
        "station_id": inspection.station_id,
        "part_id": inspection.part_id,
        "timestamp": inspection.timestamp.isoformat(),
        "decision": inspection.decision.value if inspection.decision else None,
        "confidence": inspection.confidence,
        "objects_found": len(detections),
        "detection_time_ms": inspection.detection_time_ms,
        "segmentation_time_ms": inspection.segmentation_time_ms,
        "total_time_ms": inspection.total_time_ms,
        "original_image": inspection.original_image_path,
        "annotated_image": inspection.annotated_image_path,
        "vlm_description": (inspection.metadata_json or {}).get("vlm_description"),
        "detections": [
            {
                "class_name": d.class_name,
                "confidence": d.confidence,
                "box": {"x1": d.box_x1, "y1": d.box_y1, "x2": d.box_x2, "y2": d.box_y2}
                    if all(v is not None for v in [d.box_x1, d.box_y1, d.box_x2, d.box_y2]) else None,
            }
            for d in detections
        ],
    }


# =============================================================================
# API Routes - History & Analytics
# =============================================================================

@app.get("/api/v1/inspections")
async def list_inspections(
    station_id: Optional[str] = None,
    decision: Optional[str] = None,
    limit: int = Query(50, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_inspect),
):
    """
    List inspections with filtering.
    """
    from ussop.models.database import Inspection
    
    query = db.query(Inspection)
    
    if station_id:
        query = query.filter(Inspection.station_id == station_id)
    if decision:
        query = query.filter(Inspection.decision == decision)
    
    total = query.count()
    inspections = query.order_by(Inspection.timestamp.desc()).offset(offset).limit(limit).all()
    
    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "items": [
            {
                "id": i.id,
                "station_id": i.station_id,
                "part_id": i.part_id,
                "timestamp": i.timestamp.isoformat(),
                "decision": i.decision.value if i.decision else None,
                "confidence": i.confidence,
                "objects_found": len(i.detections),
                "thumbnail": i.annotated_image_path or i.original_image_path
            }
            for i in inspections
        ]
    }


@app.get("/api/v1/statistics")
async def get_statistics(
    station_id: Optional[str] = None,
    hours: int = Query(24, ge=1, le=168),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_inspect),
):
    """
    Get inspection statistics (cached 30 s).
    """
    cache_key = f"stats:{station_id or ''}:{hours}"
    cached = await cache.get(cache_key)
    if cached is not None:
        return cached
    result = inspector_service.get_statistics(db, station_id, hours)
    await cache.set(cache_key, result, ttl=30)
    return result


@app.get("/api/v1/trends")
async def get_trends(
    station_id: Optional[str] = None,
    hours: int = Query(24, ge=1, le=168),
    interval: str = Query("hour", pattern="^(hour|day)$"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_inspect),
):
    """
    Get trend data for charts (cached 60 s).
    """
    cache_key = f"trends:{station_id or ''}:{hours}:{interval}"
    cached = await cache.get(cache_key)
    if cached is not None:
        return cached

    from sqlalchemy import func
    from datetime import timedelta
    from ussop.models.database import Inspection, Decision

    since = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(hours=hours)

    # Group by time interval
    if interval == "hour":
        time_trunc = func.strftime('%Y-%m-%d %H:00:00', Inspection.timestamp)
    else:
        time_trunc = func.strftime('%Y-%m-%d', Inspection.timestamp)

    query = db.query(
        time_trunc.label('time_bucket'),
        func.count(Inspection.id).label('count'),
        func.sum((Inspection.decision == Decision.PASS).cast(Integer)).label('pass_count'),
        func.sum((Inspection.decision == Decision.FAIL).cast(Integer)).label('fail_count')
    ).filter(
        Inspection.timestamp >= since
    )

    if station_id:
        query = query.filter(Inspection.station_id == station_id)

    results = query.group_by('time_bucket').order_by('time_bucket').all()

    result = {
        "labels": [r.time_bucket for r in results],
        "total": [r.count for r in results],
        "passed": [r.pass_count or 0 for r in results],
        "failed": [r.fail_count or 0 for r in results]
    }
    await cache.set(cache_key, result, ttl=60)
    return result


# =============================================================================
# API Routes - Images
# =============================================================================

@app.get("/api/v1/images/{path:path}")
async def get_image(path: str):
    """
    Serve an image file.
    """
    image_path = settings.DATA_DIR / path
    if not image_path.exists():
        raise HTTPException(status_code=404, detail="Image not found")
    
    return FileResponse(str(image_path))


# =============================================================================
# API Routes - System
# =============================================================================

@app.get("/api/v1/health")
async def health_check():
    """
    Health check endpoint.
    """
    return {
        "status": "healthy",
        "version": settings.APP_VERSION,
        "timestamp": datetime.now(timezone.utc).replace(tzinfo=None).isoformat()
    }


@app.get("/api/v1/config")
async def get_config():
    """
    Get current configuration (safe values only).
    """
    return {
        "app_name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "detector_backbone": settings.DETECTOR_BACKBONE,
        "confidence_threshold": settings.CONFIDENCE_THRESHOLD,
        "max_detections": settings.MAX_DETECTIONS,
        "camera_type": settings.CAMERA_TYPE,
    }


# =============================================================================
# API Routes - Active Learning
# =============================================================================

@app.get("/api/v1/active-learning/queue")
async def get_review_queue(
    status: str = "pending",
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_inspect),
):
    """
    Get images in the active learning review queue.
    """
    al_service = get_active_learning()
    return al_service.get_review_queue(db, status, limit)


@app.post("/api/v1/active-learning/annotate/{training_image_id}")
async def submit_annotation(
    training_image_id: str,
    request: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_inspect),
):
    """
    Submit human annotations for a training image.
    """
    al_service = get_active_learning()
    success = al_service.submit_annotation(
        db, 
        training_image_id, 
        request.get('annotations', []),
        request.get('reviewed_by', 'unknown')
    )
    
    if not success:
        raise HTTPException(status_code=404, detail="Training image not found")
    
    return {"status": "success", "message": "Annotation submitted"}


@app.get("/api/v1/active-learning/stats")
async def get_active_learning_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_inspect),
):
    """
    Get active learning queue statistics.
    """
    al_service = get_active_learning()
    return al_service.get_statistics(db)


@app.get("/api/v1/active-learning/dataset")
async def get_training_dataset(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_inspect),
):
    """
    Get dataset ready for training.
    """
    al_service = get_active_learning()
    return al_service.get_training_dataset(db)


@app.post("/api/v1/active-learning/check-retrain")
async def check_retraining_needed(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_inspect),
):
    """
    Check if model retraining is recommended.
    """
    retrainer = get_retrainer()
    needed, reason = retrainer.check_retraining_needed(db)
    
    return {
        "retraining_needed": needed,
        "reason": reason
    }


# =============================================================================
# API Routes - Monitoring & Alerts
# =============================================================================

@app.get("/api/v1/health")
async def health_check(db: Session = Depends(get_db)):
    """
    Health check endpoint with system status.
    """
    metrics = get_metrics_collector()
    health = metrics.get_system_health(db)
    
    return {
        "status": health['status'],
        "version": settings.APP_VERSION,
        "timestamp": datetime.now(timezone.utc).replace(tzinfo=None).isoformat(),
        "details": health
    }


@app.get("/api/v1/metrics/performance")
async def get_performance_metrics(
    hours: int = Query(24, ge=1, le=168),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_inspect),
):
    """
    Get performance metrics.
    """
    metrics = get_metrics_collector()
    return metrics.get_performance_metrics(db, hours)


@app.get("/api/v1/alerts")
async def get_alerts(
    severity: Optional[str] = None,
    acknowledged: Optional[bool] = None,
    current_user: User = Depends(require_inspect),
):
    """
    Get system alerts.
    """
    alert_mgr = get_alert_manager()
    alerts = alert_mgr.get_alerts(severity, acknowledged)
    
    return {
        "alerts": [
            {
                "id": a.id,
                "severity": a.severity,
                "title": a.title,
                "message": a.message,
                "timestamp": a.timestamp.isoformat(),
                "acknowledged": a.acknowledged
            }
            for a in alerts
        ]
    }


@app.post("/api/v1/alerts/{alert_id}/acknowledge")
async def acknowledge_alert(
    alert_id: str,
    current_user: User = Depends(require_inspect),
):
    """
    Acknowledge an alert.
    """
    alert_mgr = get_alert_manager()
    success = alert_mgr.acknowledge_alert(alert_id)
    
    if not success:
        raise HTTPException(status_code=404, detail="Alert not found")
    
    return {"status": "success"}


# =============================================================================
# API Routes - Export
# =============================================================================

@app.get("/api/v1/export/csv")
async def export_csv(
    station_id: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_inspect),
):
    """
    Export inspections to CSV.
    """
    import csv
    import io
    from fastapi.responses import StreamingResponse
    
    # Query inspections
    query = db.query(Inspection)
    if station_id:
        query = query.filter(Inspection.station_id == station_id)
    
    inspections = query.order_by(Inspection.timestamp.desc()).limit(10000).all()
    
    # Create CSV
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['ID', 'Timestamp', 'Station', 'Part ID', 'Decision', 'Confidence', 
                     'Objects Found', 'Total Time (ms)'])
    
    for i in inspections:
        writer.writerow([
            i.id, i.timestamp.isoformat(), i.station_id, i.part_id,
            i.decision.value if i.decision else 'unknown',
            i.confidence, len(i.detections), i.total_time_ms
        ])
    
    output.seek(0)
    
    return StreamingResponse(
        io.BytesIO(output.getvalue().encode()),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=inspections.csv"}
    )


# =============================================================================
# API Routes - Config
# =============================================================================

@app.get("/api/v1/config")
async def get_config():
    """
    Get current configuration (safe values only).
    """
    vlm_loaded = False
    if settings.VLM_ENABLED:
        try:
            from services.vlm_service import get_vlm_service
            vlm = get_vlm_service()
            vlm_loaded = bool(vlm and getattr(getattr(vlm, "_backend", None), "_loaded", False))
        except Exception:
            pass
    return {
        "app_name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "station_id": "default",
        "detector_backbone": settings.DETECTOR_BACKBONE,
        "confidence_threshold": settings.CONFIDENCE_THRESHOLD,
        "max_detections": settings.MAX_DETECTIONS,
        "camera_type": settings.CAMERA_TYPE,
        "active_learning_enabled": settings.ACTIVE_LEARNING_ENABLED,
        "modbus_enabled": settings.MODBUS_ENABLED,
        "mqtt_enabled": settings.MQTT_ENABLED,
        # VLM
        "vlm_enabled": settings.VLM_ENABLED,
        "vlm_backend": settings.VLM_BACKEND,
        "vlm_local_model": settings.VLM_LOCAL_MODEL,
        "vlm_loaded": vlm_loaded,
        "nvidia_nim_model": settings.NVIDIA_NIM_MODEL,
        "nvidia_nim_base_url": settings.NVIDIA_NIM_BASE_URL,
    }


@app.post("/api/v1/config")
async def update_config(
    config: dict,
    current_user: User = Depends(require_configure),
):
    """
    Update configuration (requires restart for some changes).
    """
    # In production, this would update the config file or database
    # For now, we just return success - changes need restart
    return {
        "status": "success",
        "message": "Configuration updated. Some changes may require restart.",
        "updated_fields": list(config.keys())
    }


@app.get("/api/v1/config/export")
async def export_config(current_user: User = Depends(require_configure)):
    """
    Export full configuration as JSON.
    """
    import json
    from fastapi.responses import StreamingResponse
    
    config = {
        "app_name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "detector_backbone": settings.DETECTOR_BACKBONE,
        "confidence_threshold": settings.CONFIDENCE_THRESHOLD,
        "max_detections": settings.MAX_DETECTIONS,
        "camera_type": settings.CAMERA_TYPE,
        "camera_index": settings.CAMERA_INDEX,
        "camera_resolution": f"{settings.CAMERA_WIDTH}x{settings.CAMERA_HEIGHT}",
        "active_learning_enabled": settings.ACTIVE_LEARNING_ENABLED,
        "modbus_enabled": settings.MODBUS_ENABLED,
        "mqtt_enabled": settings.MQTT_ENABLED,
    }
    
    output = json.dumps(config, indent=2)
    
    return StreamingResponse(
        io.BytesIO(output.encode()),
        media_type="application/json",
        headers={"Content-Disposition": "attachment; filename=ussop-config.json"}
    )


# =============================================================================
# API Routes - Storage & Backup
# =============================================================================

@app.get("/api/v1/storage/usage")
async def get_storage_usage(current_user: User = Depends(require_configure)):
    """
    Get storage usage statistics.
    """
    import os
    
    def get_dir_size(path):
        total = 0
        try:
            for entry in os.scandir(path):
                if entry.is_file():
                    total += entry.stat().st_size
                elif entry.is_dir():
                    total += get_dir_size(entry.path)
        except:
            pass
        return total
    
    images_size = get_dir_size(settings.IMAGES_DIR)
    masks_size = get_dir_size(settings.MASKS_DIR)
    db_size = os.path.getsize(settings.DATA_DIR / 'db' / 'ussop.db') if (settings.DATA_DIR / 'db' / 'ussop.db').exists() else 0
    
    return {
        "images_gb": images_size / (1024**3),
        "masks_gb": masks_size / (1024**3),
        "database_mb": db_size / (1024**2),
        "total_gb": (images_size + masks_size + db_size) / (1024**3),
        "max_gb": settings.MAX_STORAGE_GB
    }


@app.post("/api/v1/storage/cleanup")
async def cleanup_storage(
    days: int = Query(90, ge=1),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_configure),
):
    """
    Clean up old inspection data.
    """
    from datetime import timedelta
    import os
    
    cutoff = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=days)
    
    # Find old inspections
    old_inspections = db.query(Inspection).filter(Inspection.timestamp < cutoff).all()
    
    deleted_count = 0
    for inspection in old_inspections:
        # Delete associated images
        if inspection.original_image_path:
            path = settings.DATA_DIR / inspection.original_image_path
            if path.exists():
                os.remove(path)
                deleted_count += 1
        
        if inspection.annotated_image_path:
            path = settings.DATA_DIR / inspection.annotated_image_path
            if path.exists():
                os.remove(path)
                deleted_count += 1
        
        # Delete from database
        db.delete(inspection)
    
    db.commit()
    
    return {
        "deleted_count": deleted_count,
        "inspections_removed": len(old_inspections),
        "cutoff_date": cutoff.isoformat()
    }


@app.post("/api/v1/backup")
async def create_backup(current_user: User = Depends(require_configure)):
    """
    Create a backup of all data.
    """
    import zipfile
    import tempfile
    
    # Create temporary zip file
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.zip')
    
    with zipfile.ZipFile(temp_file.name, 'w', zipfile.ZIP_DEFLATED) as zf:
        # Add database
        db_path = settings.DATA_DIR / 'db' / 'ussop.db'
        if db_path.exists():
            zf.write(db_path, 'database/ussop.db')
        
        # Add config
        zf.writestr('config/settings.json', json.dumps({
            'version': settings.APP_VERSION,
            'exported_at': datetime.now(timezone.utc).replace(tzinfo=None).isoformat()
        }))
        
        # Add recent images (last 7 days)
        cutoff = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=7)
        # This would iterate through images and add recent ones
        # For now, just add a manifest
        zf.writestr('manifest.json', json.dumps({
            'backup_date': datetime.now(timezone.utc).replace(tzinfo=None).isoformat(),
            'version': settings.APP_VERSION,
            'note': 'Recent images not included in backup, use full export for complete backup'
        }))
    
    return FileResponse(
        temp_file.name,
        media_type="application/zip",
        headers={"Content-Disposition": f"attachment; filename=ussop-backup-{datetime.now().strftime('%Y%m%d')}.zip"}
    )


# =============================================================================
# API Routes - Reports
# =============================================================================

@app.get("/api/v1/reports/pdf/{inspection_id}")
async def generate_inspection_report(
    inspection_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_inspect),
):
    """
    Generate PDF report for a specific inspection.
    """
    try:
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import letter
        from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
        from reportlab.lib.styles import getSampleStyleSheet
        import tempfile
    except ImportError:
        return JSONResponse(
            status_code=501,
            content={"error": "PDF generation not available. Install reportlab: pip install reportlab"}
        )
    
    # Get inspection
    inspection = db.query(Inspection).filter(Inspection.id == inspection_id).first()
    if not inspection:
        raise HTTPException(status_code=404, detail="Inspection not found")
    
    # Create PDF
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.pdf')
    doc = SimpleDocTemplate(temp_file.name, pagesize=letter)
    styles = getSampleStyleSheet()
    story = []
    
    # Title
    story.append(Paragraph(f"Inspection Report - {inspection_id[:8]}", styles['Title']))
    story.append(Spacer(1, 20))
    
    # Info table
    data = [
        ['Timestamp:', inspection.timestamp.strftime('%Y-%m-%d %H:%M:%S')],
        ['Station:', inspection.station_id],
        ['Part ID:', inspection.part_id or 'N/A'],
        ['Decision:', inspection.decision.value.upper() if inspection.decision else 'UNKNOWN'],
        ['Confidence:', f"{inspection.confidence:.1%}" if inspection.confidence else 'N/A'],
        ['Processing Time:', f"{inspection.total_time_ms:.0f} ms"],
    ]
    
    t = Table(data, colWidths=[150, 300])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.lightgrey),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    story.append(t)
    story.append(Spacer(1, 20))
    
    # Detections
    story.append(Paragraph("Detected Objects", styles['Heading2']))
    story.append(Spacer(1, 10))
    
    if inspection.detections:
        det_data = [['Class', 'Confidence', 'Bounding Box', 'IoU']]
        for det in inspection.detections:
            det_data.append([
                det.class_name,
                f"{det.confidence:.1%}",
                f"[{det.box_x1:.0f}, {det.box_y1:.0f}, {det.box_x2:.0f}, {det.box_y2:.0f}]",
                f"{det.mask_iou:.2f}" if det.mask_iou else 'N/A'
            ])
        
        det_table = Table(det_data)
        det_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ]))
        story.append(det_table)
    else:
        story.append(Paragraph("No objects detected", styles['Normal']))
    
    # Add image if available
    if inspection.annotated_image_path:
        img_path = settings.DATA_DIR / inspection.annotated_image_path
        if img_path.exists():
            story.append(Spacer(1, 20))
            story.append(Paragraph("Annotated Image", styles['Heading2']))
            story.append(Spacer(1, 10))
            img = Image(str(img_path), width=400, height=300)
            story.append(img)
    
    # Footer
    story.append(Spacer(1, 30))
    story.append(Paragraph(
        f"Generated by Ussop v{settings.APP_VERSION} | {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        styles['Normal']
    ))
    
    doc.build(story)
    
    return FileResponse(
        temp_file.name,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=inspection-{inspection_id[:8]}.pdf"}
    )


# =============================================================================
# API Routes - Authentication
# =============================================================================

@app.post("/api/v1/auth/login")
@limiter.limit("10/minute")
async def login(
    request: Request,
    db: Session = Depends(get_db),
):
    """
    Login and get access token. Rate limited to 10 attempts per minute per IP.
    Body: {"username": "...", "password": "..."}
    """
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=422, detail="Request body must be JSON with 'username' and 'password'.")
    auth_service = get_auth_service()

    result = auth_service.authenticate_user(
        db,
        username=body.get("username"),
        password=body.get("password"),
    )

    if not result:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    return result


@app.post("/api/v1/auth/refresh")
async def refresh_token(
    request: dict,
    db: Session = Depends(get_db)
):
    """
    Refresh access token using refresh token.
    """
    auth_service = get_auth_service()
    
    result = auth_service.refresh_access_token(
        db,
        refresh_token=request.get("refresh_token")
    )
    
    if not result:
        raise HTTPException(status_code=401, detail="Invalid refresh token")
    
    return result


@app.post("/api/v1/auth/logout")
async def logout(
    request: dict,
    db: Session = Depends(get_db)
):
    """
    Logout and revoke token.
    """
    auth_service = get_auth_service()
    
    success = auth_service.logout(db, request.get("token"))
    
    return {"status": "success" if success else "error"}


@app.get("/api/v1/auth/me")
async def get_current_user_info(
    current_user: User = Depends(get_current_active_user)
):
    """
    Get current user information.
    """
    return current_user.to_dict()


@app.put("/api/v1/users/me")
async def update_my_profile(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Update the current user's own profile (email)."""
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=422, detail="Invalid JSON body")
    if "email" in body:
        current_user.email = body["email"]
    db.commit()
    return current_user.to_dict()


@app.put("/api/v1/users/me/password")
async def change_my_password(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Change the current user's own password."""
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=422, detail="Invalid JSON body")
    current_password = body.get("current_password", "")
    new_password = body.get("new_password", "")
    if not current_user.verify_password(current_password):
        raise HTTPException(status_code=400, detail="Current password is incorrect")
    if len(new_password) < 6:
        raise HTTPException(status_code=422, detail="New password must be at least 6 characters")
    current_user.set_password(new_password)
    db.commit()
    return {"message": "Password updated successfully"}


# =============================================================================
# API Routes - User Management (Admin only)
# =============================================================================

@app.get("/api/v1/users")
async def list_users(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_manage_users)
):
    """
    List all users (admin only).
    """
    users = db.query(User).all()
    return [user.to_dict() for user in users]


@app.post("/api/v1/users")
async def create_user(
    request: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_manage_users)
):
    """
    Create new user (admin only).
    """
    # Check if username exists
    existing = db.query(User).filter(User.username == request["username"]).first()
    if existing:
        raise HTTPException(status_code=400, detail="Username already exists")
    
    # Create user
    user = User(
        username=request["username"],
        email=request.get("email"),
        is_active=request.get("is_active", True),
        is_superuser=request.get("is_superuser", False)
    )
    user.set_password(request["password"])
    
    # Assign roles
    if "roles" in request:
        for role_name in request["roles"]:
            role = db.query(Role).filter(Role.name == role_name).first()
            if role:
                user.roles.append(role)
    
    db.add(user)
    db.commit()
    
    # Audit log
    audit = get_audit_logger()
    audit.log(
        action="user_created",
        user=current_user.username,
        resource_type="user",
        resource_id=user.id
    )
    
    return user.to_dict()


@app.put("/api/v1/users/{user_id}")
async def update_user(
    user_id: str,
    request: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_manage_users)
):
    """
    Update user (admin only).
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Update fields
    if "email" in request:
        user.email = request["email"]
    if "is_active" in request:
        user.is_active = request["is_active"]
    if "password" in request:
        user.set_password(request["password"])
    
    db.commit()
    
    return user.to_dict()


@app.delete("/api/v1/users/{user_id}")
async def delete_user(
    user_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_manage_users)
):
    """
    Delete user (admin only).
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if user.id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot delete yourself")
    
    db.delete(user)
    db.commit()
    
    return {"status": "success"}


# =============================================================================
# API Routes - Roles
# =============================================================================

@app.get("/api/v1/roles")
async def list_roles(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_manage_users)
):
    """
    List all roles.
    """
    roles = db.query(Role).all()
    return [
        {
            "id": role.id,
            "name": role.name,
            "description": role.description,
            "permissions": role.get_permissions_list()
        }
        for role in roles
    ]


# =============================================================================
# API Routes - Batch Processing
# =============================================================================

@app.get("/api/v1/batch/stats")
async def get_batch_stats(
    current_user: User = Depends(require_inspect)
):
    """
    Get batch processing statistics.
    """
    processor = get_batch_processor()
    return processor.get_statistics()


@app.get("/api/v1/batch/jobs")
async def list_batch_jobs(
    status: Optional[str] = None,
    current_user: User = Depends(require_inspect)
):
    """
    List batch jobs.
    """
    processor = get_batch_processor()
    
    if status:
        job_status = BatchJobStatus(status)
        jobs = processor.list_jobs(job_status)
    else:
        jobs = processor.list_jobs()
    
    return [job.to_dict() for job in jobs]


@app.post("/api/v1/batch/jobs")
async def create_batch_job(
    request: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_inspect)
):
    """
    Create a new batch processing job.
    """
    try:
        processor = get_batch_processor()
        job = processor.create_job(
            name=request.get("name", "Unnamed Job"),
            input_directory=request.get("input_directory"),
            pattern=request.get("pattern", "*.jpg")
        )
        
        # Auto-start the job
        await processor.start_job(job.id, db)
        
        return job.to_dict()
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/v1/batch/jobs/{job_id}/start")
async def start_batch_job(
    job_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_inspect)
):
    """
    Start a batch job.
    """
    processor = get_batch_processor()
    job = processor.get_job(job_id)
    
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    await processor.start_job(job_id, db)
    return {"status": "started"}


@app.post("/api/v1/batch/jobs/{job_id}/cancel")
async def cancel_batch_job(
    job_id: str,
    current_user: User = Depends(require_inspect)
):
    """
    Cancel a batch job.
    """
    processor = get_batch_processor()
    success = processor.cancel_job(job_id)
    
    if not success:
        raise HTTPException(status_code=400, detail="Cannot cancel job")
    
    return {"status": "cancelled"}


@app.get("/api/v1/batch/jobs/{job_id}")
async def get_batch_job(
    job_id: str,
    current_user: User = Depends(require_inspect)
):
    """
    Get batch job details.
    """
    processor = get_batch_processor()
    job = processor.get_job(job_id)
    
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    return job.to_dict()


@app.get("/api/v1/batch/jobs/{job_id}/download")
async def download_batch_results(
    job_id: str,
    current_user: User = Depends(require_inspect)
):
    """
    Download batch job results.
    """
    processor = get_batch_processor()
    job = processor.get_job(job_id)
    
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    import zipfile
    import tempfile
    
    # Create zip of results
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.zip')
    
    with zipfile.ZipFile(temp_file.name, 'w', zipfile.ZIP_DEFLATED) as zf:
        output_path = Path(job.output_directory)
        if output_path.exists():
            for file in output_path.glob('*'):
                zf.write(file, file.name)
    
    return FileResponse(
        temp_file.name,
        media_type="application/zip",
        headers={"Content-Disposition": f"attachment; filename=batch-{job_id}-results.zip"}
    )


# =============================================================================
# HTML Routes - Authentication
# =============================================================================

@app.get("/login",    response_class=HTMLResponse)
async def login_page(): return _serve_spa()

@app.get("/batch",    response_class=HTMLResponse)
async def batch_page(): return _serve_spa()

@app.get("/annotate", response_class=HTMLResponse)
async def annotate_page(): return _serve_spa()

@app.get("/config",   response_class=HTMLResponse)
async def config_page(): return _serve_spa()


# Import Integer for trends endpoint
from sqlalchemy import Integer


# =============================================================================
# API Routes - Model Training
# =============================================================================

@app.post("/api/v1/training/jobs")
async def start_training_job(
    request: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_configure),
):
    """
    Start an on-device model fine-tuning job using annotated data.
    Body: { "epochs": 10, "batch_size": 2, "learning_rate": 1e-4 }
    """
    al_service = get_active_learning()
    dataset = al_service.get_training_dataset(db, min_annotations=1)

    if not dataset.get("ready"):
        raise HTTPException(
            status_code=422,
            detail=dataset.get("message", "Not enough annotated images"),
        )

    cfg_data = {k: request[k] for k in ("epochs", "batch_size", "learning_rate",
                                          "momentum", "weight_decay",
                                          "early_stopping_patience") if k in request}
    config = TrainingConfig(**cfg_data)

    trainer = get_model_trainer()
    job = trainer.submit_job(dataset, config)

    return job.to_dict()


@app.get("/api/v1/training/jobs")
async def list_training_jobs(
    current_user: User = Depends(require_configure),
):
    """List all training jobs."""
    return get_model_trainer().list_jobs()


@app.get("/api/v1/training/jobs/{job_id}")
async def get_training_job(
    job_id: str,
    current_user: User = Depends(require_configure),
):
    """Get training job details and progress."""
    job = get_model_trainer().get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Training job not found")
    return job.to_dict()


@app.post("/api/v1/training/jobs/{job_id}/cancel")
async def cancel_training_job(
    job_id: str,
    current_user: User = Depends(require_configure),
):
    """Cancel a queued training job."""
    success = get_model_trainer().cancel_job(job_id)
    if not success:
        raise HTTPException(status_code=400, detail="Job not found or already running")
    return {"status": "cancelled"}


@app.post("/api/v1/training/jobs/{job_id}/deploy")
async def deploy_training_job(
    job_id: str,
    request: dict,
    current_user: User = Depends(require_configure),
):
    """
    Deploy a completed training job as the active model.
    Automatically rolled out if mAP improves; can be forced via { "force": true }.
    """
    trainer = get_model_trainer()
    job = trainer.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Training job not found")
    if job.status.value != "completed":
        raise HTTPException(status_code=422, detail="Job not completed yet")
    if not job.output_model_path:
        raise HTTPException(status_code=422, detail="No model output available")

    deployer = get_model_deployer()
    version = deployer.deploy_from_job(
        job_id=job_id,
        model_path=job.output_model_path,
        map_score=job.best_map,
        val_loss=job.val_loss,
        auto_activate=not request.get("force", False),
        description=request.get("description", ""),
    )

    if request.get("force", False):
        deployer.activate_version(version.version_id)

    return version.to_dict()


# =============================================================================
# API Routes - Model Deployment
# =============================================================================

@app.get("/api/v1/models/versions")
async def list_model_versions(
    current_user: User = Depends(require_configure),
):
    """List all deployed model versions."""
    return get_model_deployer().list_versions()


@app.get("/api/v1/models/active")
async def get_active_model(
    current_user: User = Depends(require_configure),
):
    """Get the currently active model version."""
    version = get_model_deployer().get_active_version()
    if not version:
        return {"message": "No fine-tuned model deployed; using base COCO weights"}
    return version


@app.post("/api/v1/models/versions/{version_id}/activate")
async def activate_model_version(
    version_id: str,
    current_user: User = Depends(require_configure),
):
    """Activate a specific model version (hot-swap)."""
    success = get_model_deployer().activate_version(version_id)
    if not success:
        raise HTTPException(status_code=404, detail="Model version not found")
    return {"status": "activated", "version_id": version_id}


@app.post("/api/v1/models/rollback")
async def rollback_model(
    current_user: User = Depends(require_configure),
):
    """Roll back to the previous model version."""
    prev = get_model_deployer().rollback()
    if not prev:
        raise HTTPException(status_code=400, detail="No previous version to roll back to")
    return {"status": "rolled_back", "version_id": prev}


@app.delete("/api/v1/models/versions/{version_id}")
async def delete_model_version(
    version_id: str,
    current_user: User = Depends(require_configure),
):
    """Delete a non-active model version to free disk space."""
    success = get_model_deployer().delete_version(version_id)
    if not success:
        raise HTTPException(status_code=400, detail="Version not found or is currently active")
    return {"status": "deleted"}


# =============================================================================
# API Routes - VLM (Vision Language Model)
# =============================================================================

@app.post("/api/v1/vlm/download")
async def vlm_download_model(
    request: Request,
    current_user: User = Depends(require_configure),
):
    """
    Download a local VLM model from HuggingFace in the background.
    Body: {"model": "moondream2"}
    """
    body = await request.json()
    model_name = body.get("model", "moondream2")

    _LOCAL_MODELS = {
        "moondream2":  "vikhyatk/moondream2",
        "internvl2":   "OpenGVLab/InternVL2-2B",
        "qwen2vl":     "Qwen/Qwen2-VL-2B-Instruct",
        "phi35vision": "microsoft/Phi-3.5-vision-instruct",
        "llava":       "llava-hf/llava-1.5-7b-hf",
        "paligemma":   "google/paligemma-3b-pt-224",
    }
    if model_name not in _LOCAL_MODELS:
        raise HTTPException(status_code=400, detail=f"Unknown model '{model_name}'. Valid: {list(_LOCAL_MODELS.keys())}")

    def _do_download():
        try:
            import torch
            from transformers import AutoModelForCausalLM, AutoTokenizer, AutoProcessor
            hf_id = _LOCAL_MODELS[model_name]
            cache_dir = str(settings.MODELS_DIR / "vlm" / model_name)
            logger.info(f"[VLM] Downloading {hf_id} to {cache_dir} …")
            if model_name == "moondream2":
                AutoModelForCausalLM.from_pretrained(hf_id, trust_remote_code=True, torch_dtype=torch.float32, cache_dir=cache_dir)
                AutoTokenizer.from_pretrained(hf_id, trust_remote_code=True, cache_dir=cache_dir)
            else:
                AutoProcessor.from_pretrained(hf_id, trust_remote_code=True, cache_dir=cache_dir)
                AutoModelForCausalLM.from_pretrained(hf_id, trust_remote_code=True, torch_dtype=torch.float32, low_cpu_mem_usage=True, cache_dir=cache_dir)
            logger.info(f"[VLM] Download complete: {model_name}")
        except Exception as e:
            logger.error(f"[VLM] Download failed: {e}")

    import asyncio
    loop = asyncio.get_event_loop()
    loop.run_in_executor(None, _do_download)
    return {"status": "downloading", "model": model_name, "hf_id": _LOCAL_MODELS[model_name]}


@app.get("/api/v1/vlm/status")
async def vlm_status(current_user: User = Depends(require_inspect)):
    """
    Return current VLM configuration and readiness.
    """
    from services.vlm_service import get_vlm_service
    if not settings.VLM_ENABLED:
        return {"enabled": False, "message": "VLM is disabled. Set VLM_ENABLED=true in .env"}
    vlm = get_vlm_service()
    return vlm.status() if vlm else {"enabled": False}


@app.post("/api/v1/vlm/describe")
async def vlm_describe_image(
    file: UploadFile = File(...),
    current_user: User = Depends(require_inspect),
):
    """
    Describe defects in an uploaded image using the configured VLM.
    Returns a natural language description.
    """
    if not settings.VLM_ENABLED:
        raise HTTPException(status_code=503, detail="VLM is disabled.")

    import tempfile, shutil
    from services.vlm_service import get_vlm_service

    vlm = get_vlm_service()
    if not vlm:
        raise HTTPException(status_code=503, detail="VLM service unavailable.")

    suffix = Path(file.filename).suffix if file.filename else ".jpg"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        shutil.copyfileobj(file.file, tmp)
        tmp_path = tmp.name

    try:
        description = vlm.describe_defect(tmp_path)
        return {"description": description, "backend": settings.VLM_BACKEND}
    finally:
        Path(tmp_path).unlink(missing_ok=True)


@app.get("/api/v1/inspect/{inspection_id}/description")
async def get_inspection_vlm_description(
    inspection_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_inspect),
):
    """
    Get or generate a VLM description for an existing inspection.
    If already generated, returns cached value from the result.
    If not, runs VLM on the stored original image.
    """
    if not settings.VLM_ENABLED:
        raise HTTPException(status_code=503, detail="VLM is disabled.")

    from services.vlm_service import get_vlm_service
    from ussop.models.database import Inspection

    inspection = db.query(Inspection).filter(Inspection.id == inspection_id).first()
    if not inspection:
        raise HTTPException(status_code=404, detail="Inspection not found")

    vlm = get_vlm_service()
    if not vlm:
        raise HTTPException(status_code=503, detail="VLM service unavailable.")

    image_path = settings.DATA_DIR / inspection.original_image_path if inspection.original_image_path else None
    if not image_path or not image_path.exists():
        raise HTTPException(status_code=404, detail="Original image not found on disk")

    description = vlm.describe_defect(str(image_path))
    return {
        "inspection_id": inspection_id,
        "description": description,
        "backend": settings.VLM_BACKEND,
    }


@app.post("/api/v1/query")
async def natural_language_query(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_inspect),
):
    """
    Answer a natural language question about inspection data.
    Body: {"question": "How many scratches at Station 3 this week?"}
    """
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=422, detail="Invalid JSON body")

    if not settings.VLM_ENABLED:
        raise HTTPException(status_code=503, detail="VLM is disabled.")

    question = body.get("question", "").strip()
    if not question:
        raise HTTPException(status_code=422, detail="'question' field is required.")

    from services.vlm_service import get_vlm_service

    vlm = get_vlm_service()
    if not vlm:
        raise HTTPException(status_code=503, detail="VLM service unavailable.")

    # Build lightweight context from recent statistics
    try:
        stats = inspector_service.get_statistics(db, hours=168)
        context = (
            f"Last 7 days: {stats['total_inspections']} inspections, "
            f"pass rate {stats['pass_rate']:.1%}, "
            f"defects: {stats['defect_breakdown']}."
        )
    except Exception:
        context = ""

    answer = vlm.answer_query(question, context)
    return {"question": question, "answer": answer, "backend": settings.VLM_BACKEND}


# =============================================================================
# OpenVINO / NPU optimization endpoints
# =============================================================================

@app.get("/api/v1/openvino/status")
async def openvino_status(current_user: User = Depends(require_configure)):
    """Get OpenVINO runtime status and loaded model info."""
    from services.openvino_optimizer import get_openvino_runner
    runner = get_openvino_runner()
    return runner.get_status()


@app.post("/api/v1/openvino/benchmark")
async def openvino_benchmark(
    request: Request,
    current_user: User = Depends(require_configure),
):
    """
    Benchmark OpenVINO vs ONNX Runtime for a given model.
    Body: {"model": "encoder" | "decoder"}
    """
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=422, detail="Invalid JSON body")

    model_key = body.get("model", "encoder")
    if model_key == "encoder":
        onnx_path = settings.ENCODER_PATH
    elif model_key == "decoder":
        onnx_path = settings.DECODER_PATH
    else:
        raise HTTPException(status_code=422, detail="model must be 'encoder' or 'decoder'")

    from services.openvino_optimizer import get_openvino_runner
    runner = get_openvino_runner()
    result = await asyncio.get_event_loop().run_in_executor(
        None, lambda: runner.benchmark(model_key, onnx_path)
    )
    return result


@app.post("/api/v1/openvino/load")
async def openvino_load_models(current_user: User = Depends(require_configure)):
    """
    Pre-compile encoder + decoder models into OpenVINO IR.
    This makes the first inference fast (no JIT compile delay).
    """
    from services.openvino_optimizer import get_openvino_runner
    runner = get_openvino_runner()
    if not runner.available:
        raise HTTPException(status_code=503, detail="OpenVINO not installed.")

    results = {
        "encoder": runner.load_model("encoder", settings.ENCODER_PATH),
        "decoder": runner.load_model("decoder", settings.DECODER_PATH),
    }
    return {"loaded": results, "status": runner.get_status()}


# =============================================================================
# OPC-UA endpoints
# =============================================================================

@app.get("/api/v1/opcua/status")
async def opcua_status(current_user: User = Depends(require_configure)):
    """Get OPC-UA server status."""
    from integrations.opcua_server import get_opcua_server
    return get_opcua_server().get_status()


# =============================================================================
# Prometheus metrics endpoint
# =============================================================================

try:
    from prometheus_client import (
        Counter, Histogram, Gauge,
        generate_latest, CONTENT_TYPE_LATEST,
        REGISTRY as _PROM_REGISTRY,
    )
    from fastapi.responses import Response as _Response

    def _get_or_create(cls, name, doc, **kwargs):
        """Return an existing collector or create a new one (safe for test reloads)."""
        try:
            return cls(name, doc, **kwargs)
        except ValueError:
            return _PROM_REGISTRY._names_to_collectors.get(name)  # type: ignore[attr-defined]

    _insp_total   = _get_or_create(Counter,   "ussop_inspections_total", "Total inspections",       labelnames=["decision"])
    _insp_latency = _get_or_create(Histogram, "ussop_inspection_ms",     "Inspection latency (ms)", buckets=[50,100,200,500,1000,2000,5000])
    _ws_clients   = _get_or_create(Gauge,     "ussop_ws_clients",        "Active WebSocket clients")

    def _record_prometheus(result: dict):
        decision = result.get("decision", "unknown")
        _insp_total.labels(decision=decision).inc()
        ms = result.get("total_time_ms")
        if ms:
            _insp_latency.observe(ms)

    @app.get("/metrics", include_in_schema=False)
    async def prometheus_metrics():
        """Prometheus scrape endpoint — no auth required (protect via network policy)."""
        return _Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)

    _PROMETHEUS_ENABLED = True

except ImportError:
    _PROMETHEUS_ENABLED = False
    def _record_prometheus(_result: dict): pass
    logger.warning("prometheus_client not installed — /metrics endpoint disabled")


# =============================================================================
# WebSocket — Live dashboard push
# =============================================================================

from fastapi import WebSocket, WebSocketDisconnect
from fastapi.websockets import WebSocketState


class _ConnectionManager:
    """Broadcast inspection events to all connected dashboard clients."""

    def __init__(self):
        self._active: list[WebSocket] = []

    async def connect(self, ws: WebSocket):
        await ws.accept()
        self._active.append(ws)

    def disconnect(self, ws: WebSocket):
        self._active = [c for c in self._active if c is not ws]

    async def broadcast(self, data: dict):
        dead = []
        for ws in self._active:
            try:
                if ws.client_state == WebSocketState.CONNECTED:
                    await ws.send_json(data)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect(ws)


ws_manager = _ConnectionManager()


@app.websocket("/ws/dashboard")
async def dashboard_ws(websocket: WebSocket):
    """
    WebSocket endpoint for real-time dashboard updates.
    Clients receive a JSON ping every 5 s with the latest statistics,
    plus an immediate push whenever a new inspection completes.

    Connect: ws://<host>/ws/dashboard?token=<access_token>
    """
    token = websocket.query_params.get("token", "")
    # Validate token before accepting
    auth_svc = get_auth_service()
    from models.database import get_db as _get_db
    db_gen = _get_db()
    db = next(db_gen)
    try:
        user = auth_svc.get_current_user(db, token)
    finally:
        try:
            next(db_gen)
        except StopIteration:
            pass

    if not user:
        await websocket.close(code=4401)
        return

    await ws_manager.connect(websocket)
    logger.info("WS dashboard connected: %s", user.username)
    try:
        while True:
            # Send a stats heartbeat every 5 seconds
            await asyncio.sleep(5)
            if websocket.client_state != WebSocketState.CONNECTED:
                break
            try:
                db_gen2 = _get_db()
                db2 = next(db_gen2)
                try:
                    stats = inspector_service.get_statistics(db2)
                    await websocket.send_json({"type": "stats", "data": stats})
                finally:
                    try:
                        next(db_gen2)
                    except StopIteration:
                        pass
            except Exception as e:
                logger.debug("WS heartbeat error: %s", e)
    except WebSocketDisconnect:
        pass
    finally:
        ws_manager.disconnect(websocket)
        logger.info("WS dashboard disconnected: %s", user.username)


async def broadcast_inspection(result: dict):
    """Call this after every inspection to push the result to dashboard clients."""
    await ws_manager.broadcast({"type": "inspection", "data": result})
    # OPC-UA publish (if enabled)
    if settings.OPCUA_ENABLED:
        try:
            from integrations.opcua_server import get_opcua_server
            await get_opcua_server().publish_inspection(result)
        except Exception as _e:
            logger.debug("[OPC-UA] Publish error: %s", _e)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "api.main:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=settings.DEBUG
    )
