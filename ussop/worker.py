"""
Ussop Background Worker
=======================
Runs as a separate process alongside the API server, handling:
  - Batch inspection jobs (polling the batch processor queue)
  - Model training jobs (polling the trainer queue)
  - Periodic storage cleanup
  - Alert evaluation

Start via:
    python -m ussop.worker          # normal mode
    WORKER_MODE=1 python -m ussop   # env-flag mode (Docker)

Docker Compose starts this automatically as the 'worker' service.
"""
import asyncio
import logging
import signal
import sys
import time
from pathlib import Path

# ── Make ussop package importable when run as __main__ ───────────────────────
_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(_ROOT))
sys.path.insert(0, str(Path(__file__).parent))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [WORKER] %(levelname)s %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("ussop.worker")


# ── Graceful shutdown ─────────────────────────────────────────────────────────
_stop = asyncio.Event()


def _handle_signal(*_):
    logger.info("Shutdown signal received")
    _stop.set()


# ── Helpers ───────────────────────────────────────────────────────────────────

def _get_db():
    from models.database import SessionLocal
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ── Workers ───────────────────────────────────────────────────────────────────

async def batch_worker(interval: float = 5.0):
    """Poll for pending batch jobs and advance them."""
    from services.batch_processor import get_batch_processor, BatchJobStatus
    from models.database import SessionLocal

    processor = get_batch_processor()
    logger.info("Batch worker started (poll interval %.0fs)", interval)

    while not _stop.is_set():
        try:
            jobs = [j for j in processor.jobs.values() if j.status == BatchJobStatus.PENDING]
            for job in jobs:
                db = SessionLocal()
                try:
                    logger.info("Starting batch job %s (%s)", job.id, job.name)
                    await processor.start_job(job.id, db)
                except Exception as exc:
                    logger.error("Batch job %s failed: %s", job.id, exc)
                finally:
                    db.close()
        except Exception as exc:
            logger.error("Batch worker error: %s", exc)

        try:
            await asyncio.wait_for(_stop.wait(), timeout=interval)
        except asyncio.TimeoutError:
            pass


async def training_worker(interval: float = 30.0):
    """Log training job progress (training threads are self-managed)."""
    from services.model_trainer import get_model_trainer

    trainer = get_model_trainer()
    logger.info("Training monitor started (poll interval %.0fs)", interval)

    while not _stop.is_set():
        try:
            jobs = trainer.list_jobs()
            running = [j for j in jobs if j.get("status") == "running"]
            if running:
                for j in running:
                    pct = j.get("progress_pct", 0)
                    logger.info("Training job %s: %.0f%% complete", j["job_id"][:8], pct)
        except Exception as exc:
            logger.error("Training monitor error: %s", exc)

        try:
            await asyncio.wait_for(_stop.wait(), timeout=interval)
        except asyncio.TimeoutError:
            pass


async def cleanup_worker(interval: float = 3600.0):
    """Run periodic storage cleanup (default every hour)."""
    import os
    from datetime import timedelta
    from models.database import SessionLocal, Inspection
    from config.settings import settings as _settings

    logger.info("Cleanup worker started (interval %.0fs)", interval)

    while not _stop.is_set():
        try:
            db = SessionLocal()
            try:
                cutoff = __import__('datetime').datetime.now() - timedelta(days=_settings.IMAGE_RETENTION_DAYS)
                old = db.query(Inspection).filter(Inspection.timestamp < cutoff).all()
                deleted = 0
                for insp in old:
                    for attr in ("original_image_path", "annotated_image_path"):
                        p = getattr(insp, attr, None)
                        if p:
                            full = _settings.DATA_DIR / p
                            if full.exists():
                                os.remove(full)
                                deleted += 1
                    db.delete(insp)
                db.commit()
                if deleted:
                    logger.info("Cleanup removed %d files / %d records", deleted, len(old))
            finally:
                db.close()
        except Exception as exc:
            logger.error("Cleanup worker error: %s", exc)

        try:
            await asyncio.wait_for(_stop.wait(), timeout=interval)
        except asyncio.TimeoutError:
            pass


async def alert_worker(interval: float = 60.0):
    """Evaluate alert rules and emit alerts (uses AlertManager.check_alerts)."""
    from services.monitoring import get_alert_manager
    from models.database import SessionLocal

    alert_mgr = get_alert_manager()
    logger.info("Alert worker started (poll interval %.0fs)", interval)

    while not _stop.is_set():
        try:
            db = SessionLocal()
            try:
                new_alerts = alert_mgr.check_alerts(db)
                if new_alerts:
                    logger.info("Triggered %d new alert(s)", len(new_alerts))
                alert_mgr.clear_old_alerts(hours=24)
            finally:
                db.close()
        except Exception as exc:
            logger.error("Alert worker error: %s", exc)

        try:
            await asyncio.wait_for(_stop.wait(), timeout=interval)
        except asyncio.TimeoutError:
            pass


# ── Main ──────────────────────────────────────────────────────────────────────

async def main():
    from config.settings import settings
    from services.cache import cache

    logger.info("Ussop Worker v%s starting", settings.APP_VERSION)

    # Connect cache (Redis if configured, otherwise local)
    await cache.connect(settings.REDIS_URL)
    logger.info("Cache backend: %s", cache.backend)

    # Register OS signal handlers
    loop = asyncio.get_event_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, _handle_signal)
        except NotImplementedError:
            # Windows doesn't support add_signal_handler for all signals
            signal.signal(sig, _handle_signal)

    # Run all workers concurrently
    tasks = [
        asyncio.create_task(batch_worker(),    name="batch"),
        asyncio.create_task(training_worker(), name="training"),
        asyncio.create_task(cleanup_worker(),  name="cleanup"),
        asyncio.create_task(alert_worker(),    name="alerts"),
    ]

    logger.info("All workers running. Press Ctrl+C to stop.")

    try:
        await _stop.wait()
    finally:
        logger.info("Stopping workers…")
        for t in tasks:
            t.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
        await cache.close()
        logger.info("Worker stopped cleanly.")


if __name__ == "__main__":
    asyncio.run(main())
