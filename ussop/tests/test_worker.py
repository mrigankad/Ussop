"""
Tests for the background worker (ussop/worker.py).
Tests individual worker coroutines with mocked dependencies.
"""
import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


def _stop_after_one():
    """Return an asyncio.wait_for side-effect that stops the worker loop after one poll."""
    from ussop.worker import _stop
    _stop.clear()
    call_count = 0

    async def mock_wait(coro, timeout):
        nonlocal call_count
        call_count += 1
        _stop.set()
        raise asyncio.TimeoutError()

    return mock_wait


class TestBatchWorker:
    @pytest.mark.asyncio
    async def test_starts_pending_job(self):
        from ussop.worker import _stop, batch_worker
        _stop.clear()

        from services.batch_processor import BatchJobStatus
        mock_job = MagicMock()
        mock_job.id = "job-1"
        mock_job.name = "Test"
        mock_job.status = BatchJobStatus.PENDING

        mock_processor = MagicMock()
        mock_processor.start_job = AsyncMock()
        mock_processor.jobs = {"job-1": mock_job}

        mock_db = MagicMock()

        with patch("services.batch_processor.get_batch_processor", return_value=mock_processor), \
             patch("models.database.SessionLocal", return_value=mock_db), \
             patch("asyncio.wait_for", side_effect=_stop_after_one()):
            await batch_worker(interval=0.01)

        mock_processor.start_job.assert_called_once_with("job-1", mock_db)
        _stop.clear()

    @pytest.mark.asyncio
    async def test_skips_non_pending_jobs(self):
        from ussop.worker import _stop, batch_worker
        _stop.clear()

        from services.batch_processor import BatchJobStatus
        mock_job = MagicMock()
        mock_job.id = "job-2"
        mock_job.status = BatchJobStatus.RUNNING

        mock_processor = MagicMock()
        mock_processor.start_job = AsyncMock()
        mock_processor.jobs = {"job-2": mock_job}

        with patch("services.batch_processor.get_batch_processor", return_value=mock_processor), \
             patch("models.database.SessionLocal", return_value=MagicMock()), \
             patch("asyncio.wait_for", side_effect=_stop_after_one()):
            await batch_worker(interval=0.01)

        mock_processor.start_job.assert_not_called()
        _stop.clear()


class TestTrainingWorker:
    @pytest.mark.asyncio
    async def test_logs_running_jobs(self):
        from ussop.worker import _stop, training_worker
        _stop.clear()

        mock_trainer = MagicMock()
        mock_trainer.list_jobs.return_value = [
            {"job_id": "abc123def", "status": "running", "progress_pct": 45.0}
        ]

        with patch("services.model_trainer.get_model_trainer", return_value=mock_trainer), \
             patch("asyncio.wait_for", side_effect=_stop_after_one()):
            await training_worker(interval=0.01)

        mock_trainer.list_jobs.assert_called_once()
        _stop.clear()

    @pytest.mark.asyncio
    async def test_no_running_jobs_no_log(self):
        from ussop.worker import _stop, training_worker
        _stop.clear()

        mock_trainer = MagicMock()
        mock_trainer.list_jobs.return_value = []

        with patch("services.model_trainer.get_model_trainer", return_value=mock_trainer), \
             patch("asyncio.wait_for", side_effect=_stop_after_one()):
            await training_worker(interval=0.01)

        mock_trainer.list_jobs.assert_called_once()
        _stop.clear()


class TestAlertWorker:
    @pytest.mark.asyncio
    async def test_calls_check_alerts(self):
        from ussop.worker import _stop, alert_worker
        _stop.clear()

        mock_alert_mgr = MagicMock()
        mock_alert_mgr.check_alerts.return_value = []
        mock_db = MagicMock()

        with patch("services.monitoring.get_alert_manager", return_value=mock_alert_mgr), \
             patch("models.database.SessionLocal", return_value=mock_db), \
             patch("asyncio.wait_for", side_effect=_stop_after_one()):
            await alert_worker(interval=0.01)

        mock_alert_mgr.check_alerts.assert_called_once_with(mock_db)
        mock_alert_mgr.clear_old_alerts.assert_called_once_with(hours=24)
        _stop.clear()

    @pytest.mark.asyncio
    async def test_handles_error_gracefully(self):
        from ussop.worker import _stop, alert_worker
        _stop.clear()

        mock_alert_mgr = MagicMock()
        mock_alert_mgr.check_alerts.side_effect = RuntimeError("db gone")

        with patch("services.monitoring.get_alert_manager", return_value=mock_alert_mgr), \
             patch("models.database.SessionLocal", return_value=MagicMock()), \
             patch("asyncio.wait_for", side_effect=_stop_after_one()):
            await alert_worker(interval=0.01)   # must not raise

        _stop.clear()


class TestCleanupWorker:
    @pytest.mark.asyncio
    async def test_runs_without_crash_empty_db(self):
        from ussop.worker import _stop, cleanup_worker
        _stop.clear()

        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.all.return_value = []
        mock_db.commit = MagicMock()
        mock_db.__enter__ = lambda s: s
        mock_db.__exit__ = MagicMock(return_value=False)

        with patch("models.database.SessionLocal", return_value=mock_db), \
             patch("asyncio.wait_for", side_effect=_stop_after_one()):
            await cleanup_worker(interval=0.01)

        mock_db.commit.assert_called_once()
        _stop.clear()
