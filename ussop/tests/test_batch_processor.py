"""
Tests for BatchProcessor service — execution, file discovery, cancellation,
result export, callbacks, and statistics.
"""
import asyncio
import json
import pytest
import tempfile
import shutil
from pathlib import Path
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch, call


# ── fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def tmp_image_dir(tmp_path):
    """Create a temp dir with a few fake images."""
    for name in ("img1.jpg", "img2.jpg", "img3.png", "readme.txt"):
        (tmp_path / name).write_bytes(b"\xff\xd8\xff" + b"\x00" * 50)
    return tmp_path


@pytest.fixture
def processor():
    """BatchProcessor with mocked InspectionService so no torch needed."""
    with patch("services.batch_processor.InspectionService") as MockSvc:
        MockSvc.return_value = MagicMock()
        from services.batch_processor import BatchProcessor
        bp = BatchProcessor()
        yield bp


@pytest.fixture
def mock_db():
    return MagicMock()


# ══════════════════════════════════════════════════════════════════════════════
# 1. BatchJob dataclass
# ══════════════════════════════════════════════════════════════════════════════

class TestBatchJobDataclass:
    def _make_job(self, **kwargs):
        from services.batch_processor import BatchJob, BatchJobStatus
        defaults = dict(
            id="job-test-1",
            name="Test Job",
            status=BatchJobStatus.PENDING,
            created_at=datetime.now(timezone.utc).replace(tzinfo=None),
            total_files=3,
            input_directory="/tmp/imgs",
        )
        defaults.update(kwargs)
        return BatchJob(**defaults)

    def test_create_job(self):
        job = self._make_job()
        assert job.total_files == 3
        assert job.name == "Test Job"

    def test_job_to_dict(self):
        job = self._make_job()
        d = job.to_dict()
        assert d["id"] == "job-test-1"
        assert d["name"] == "Test Job"
        assert d["total_files"] == 3
        assert "status" in d

    def test_to_dict_has_progress_percent(self):
        job = self._make_job(total_files=10, processed_files=5)
        d = job.to_dict()
        assert "progress_percent" in d
        assert d["progress_percent"] == 50.0

    def test_initial_status_pending(self):
        from services.batch_processor import BatchJobStatus
        job = self._make_job()
        assert job.status == BatchJobStatus.PENDING

    def test_results_initialized_empty(self):
        job = self._make_job()
        assert job.results == []

    def test_to_dict_timestamps_none_when_not_started(self):
        job = self._make_job()
        d = job.to_dict()
        assert d["started_at"] is None
        assert d["completed_at"] is None

    def test_to_dict_timestamps_iso_when_set(self):
        from services.batch_processor import BatchJobStatus
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        job = self._make_job(started_at=now)
        d = job.to_dict()
        assert d["started_at"] is not None
        assert "T" in d["started_at"]  # ISO format check


# ══════════════════════════════════════════════════════════════════════════════
# 2. BatchJobStatus enum
# ══════════════════════════════════════════════════════════════════════════════

class TestBatchJobStatus:
    def test_status_values(self):
        from services.batch_processor import BatchJobStatus
        assert BatchJobStatus.PENDING.value == "pending"
        assert BatchJobStatus.RUNNING.value == "running"
        assert BatchJobStatus.COMPLETED.value == "completed"
        assert BatchJobStatus.FAILED.value == "failed"
        assert BatchJobStatus.CANCELLED.value == "cancelled"

    def test_all_five_statuses_exist(self):
        from services.batch_processor import BatchJobStatus
        assert len(BatchJobStatus) == 5


# ══════════════════════════════════════════════════════════════════════════════
# 3. Progress calculation
# ══════════════════════════════════════════════════════════════════════════════

class TestBatchJobProgress:
    def _make_job(self, total=10, processed=5, failed=0):
        from services.batch_processor import BatchJob, BatchJobStatus
        return BatchJob(
            id="job-prog",
            name="Progress Job",
            status=BatchJobStatus.RUNNING,
            created_at=datetime.now(timezone.utc).replace(tzinfo=None),
            total_files=total,
            processed_files=processed,
            failed_files=failed,
        )

    def test_50_percent_progress(self):
        job = self._make_job(total=10, processed=5)
        assert job.get_progress() == 50.0

    def test_100_percent_progress(self):
        job = self._make_job(total=10, processed=10)
        assert job.get_progress() == 100.0

    def test_zero_total_no_division_error(self):
        from services.batch_processor import BatchJob, BatchJobStatus
        job = BatchJob(
            id="job-zero",
            name="Zero Job",
            status=BatchJobStatus.PENDING,
            created_at=datetime.now(timezone.utc).replace(tzinfo=None),
            total_files=0,
        )
        assert job.get_progress() == 0.0

    def test_progress_never_exceeds_100(self):
        job = self._make_job(total=10, processed=10)
        assert job.get_progress() <= 100.0

    def test_failed_files_counted_in_processed(self):
        job = self._make_job(total=10, processed=10, failed=3)
        assert job.failed_files == 3


# ══════════════════════════════════════════════════════════════════════════════
# 4. Job creation — file discovery
# ══════════════════════════════════════════════════════════════════════════════

class TestBatchProcessorCreateJob:
    def test_create_job_nonexistent_dir_raises(self, processor):
        with pytest.raises(ValueError, match="does not exist"):
            processor.create_job("test", "/nonexistent/path/xyz")

    def test_create_job_discovers_jpg_files(self, processor, tmp_image_dir):
        job = processor.create_job("test", str(tmp_image_dir), pattern="*.jpg")
        # img1.jpg and img2.jpg should be found
        assert job.total_files >= 2

    def test_create_job_discovers_png_files(self, processor, tmp_image_dir):
        job = processor.create_job("test", str(tmp_image_dir), pattern="*.png")
        assert job.total_files >= 1

    def test_create_job_ignores_non_image_files(self, processor, tmp_image_dir):
        job = processor.create_job("test", str(tmp_image_dir), pattern="*.jpg")
        # readme.txt must not be in results
        files_in_results = [r["file"] for r in job.results]
        assert not any("readme.txt" in f for f in files_in_results)

    def test_create_job_results_status_pending(self, processor, tmp_image_dir):
        job = processor.create_job("test", str(tmp_image_dir))
        for item in job.results:
            assert item["status"] == "pending"

    def test_create_job_is_stored_in_processor(self, processor, tmp_image_dir):
        job = processor.create_job("test", str(tmp_image_dir))
        assert job.id in processor.jobs

    def test_create_job_generates_output_directory(self, processor, tmp_image_dir):
        job = processor.create_job("test", str(tmp_image_dir))
        assert job.output_directory != ""
        assert Path(job.output_directory).exists()

    def test_create_job_custom_output_directory(self, processor, tmp_image_dir, tmp_path):
        out_dir = tmp_path / "custom_out"
        job = processor.create_job("test", str(tmp_image_dir), output_directory=str(out_dir))
        assert Path(job.output_directory).exists()

    def test_create_job_unique_ids(self, processor, tmp_image_dir):
        j1 = processor.create_job("job1", str(tmp_image_dir))
        j2 = processor.create_job("job2", str(tmp_image_dir))
        assert j1.id != j2.id


# ══════════════════════════════════════════════════════════════════════════════
# 5. Job lifecycle — get, list, delete
# ══════════════════════════════════════════════════════════════════════════════

class TestBatchProcessorJobLifecycle:
    def test_get_job_returns_job(self, processor, tmp_image_dir):
        job = processor.create_job("test", str(tmp_image_dir))
        retrieved = processor.get_job(job.id)
        assert retrieved is job

    def test_get_job_unknown_returns_none(self, processor):
        assert processor.get_job("nonexistent") is None

    def test_list_jobs_empty(self, processor):
        assert processor.list_jobs() == []

    def test_list_jobs_returns_all(self, processor, tmp_image_dir):
        processor.create_job("j1", str(tmp_image_dir))
        processor.create_job("j2", str(tmp_image_dir))
        assert len(processor.list_jobs()) == 2

    def test_list_jobs_filter_by_status(self, processor, tmp_image_dir):
        from services.batch_processor import BatchJobStatus
        j1 = processor.create_job("j1", str(tmp_image_dir))
        j2 = processor.create_job("j2", str(tmp_image_dir))
        j2.status = BatchJobStatus.COMPLETED
        pending = processor.list_jobs(status=BatchJobStatus.PENDING)
        assert all(j.status == BatchJobStatus.PENDING for j in pending)

    def test_list_jobs_sorted_newest_first(self, processor, tmp_image_dir):
        from services.batch_processor import BatchJobStatus
        import time
        j1 = processor.create_job("j1", str(tmp_image_dir))
        time.sleep(0.01)
        j2 = processor.create_job("j2", str(tmp_image_dir))
        jobs = processor.list_jobs()
        assert jobs[0].created_at >= jobs[-1].created_at

    def test_delete_job(self, processor, tmp_image_dir):
        job = processor.create_job("test", str(tmp_image_dir))
        result = processor.delete_job(job.id)
        assert result is True
        assert processor.get_job(job.id) is None

    def test_delete_nonexistent_job_returns_false(self, processor):
        assert processor.delete_job("nonexistent") is False


# ══════════════════════════════════════════════════════════════════════════════
# 6. Cancellation
# ══════════════════════════════════════════════════════════════════════════════

class TestBatchProcessorCancellation:
    def test_cancel_pending_job_returns_false(self, processor, tmp_image_dir):
        """Can only cancel RUNNING jobs."""
        job = processor.create_job("test", str(tmp_image_dir))
        result = processor.cancel_job(job.id)
        assert result is False

    def test_cancel_nonexistent_job_returns_false(self, processor):
        assert processor.cancel_job("nonexistent") is False

    def test_cancel_running_job(self, processor, tmp_image_dir):
        from services.batch_processor import BatchJobStatus
        job = processor.create_job("test", str(tmp_image_dir))
        job.status = BatchJobStatus.RUNNING
        result = processor.cancel_job(job.id)
        assert result is True
        assert job.status == BatchJobStatus.CANCELLED

    def test_cancel_sets_status_cancelled(self, processor, tmp_image_dir):
        from services.batch_processor import BatchJobStatus
        job = processor.create_job("test", str(tmp_image_dir))
        job.status = BatchJobStatus.RUNNING
        processor.cancel_job(job.id)
        assert job.status == BatchJobStatus.CANCELLED


# ══════════════════════════════════════════════════════════════════════════════
# 7. Statistics
# ══════════════════════════════════════════════════════════════════════════════

class TestBatchProcessorStatistics:
    def test_statistics_empty(self, processor):
        stats = processor.get_statistics()
        assert stats["total_jobs"] == 0
        assert stats["completed_jobs"] == 0
        assert stats["running_jobs"] == 0

    def test_statistics_counts_jobs(self, processor, tmp_image_dir):
        from services.batch_processor import BatchJobStatus
        j1 = processor.create_job("j1", str(tmp_image_dir))
        j2 = processor.create_job("j2", str(tmp_image_dir))
        j2.status = BatchJobStatus.COMPLETED
        stats = processor.get_statistics()
        assert stats["total_jobs"] == 2
        assert stats["completed_jobs"] == 1

    def test_statistics_sums_files(self, processor, tmp_image_dir):
        j1 = processor.create_job("j1", str(tmp_image_dir))
        j2 = processor.create_job("j2", str(tmp_image_dir))
        stats = processor.get_statistics()
        assert stats["total_files"] == j1.total_files + j2.total_files

    def test_statistics_has_required_keys(self, processor):
        stats = processor.get_statistics()
        for key in ("total_jobs", "completed_jobs", "running_jobs", "failed_jobs",
                    "total_files", "processed_files"):
            assert key in stats, f"Missing key: {key}"


# ══════════════════════════════════════════════════════════════════════════════
# 8. Progress callbacks
# ══════════════════════════════════════════════════════════════════════════════

class TestBatchProcessorCallbacks:
    def test_register_callback(self, processor):
        cb = MagicMock()
        processor.on_progress(cb)
        assert cb in processor._callbacks

    def test_multiple_callbacks_registered(self, processor):
        cb1, cb2 = MagicMock(), MagicMock()
        processor.on_progress(cb1)
        processor.on_progress(cb2)
        assert len(processor._callbacks) >= 2

    def test_callback_survives_exception(self, processor, tmp_image_dir):
        """A crashing callback must not affect other callbacks."""
        bad_cb = MagicMock(side_effect=RuntimeError("oops"))
        good_cb = MagicMock()
        processor.on_progress(bad_cb)
        processor.on_progress(good_cb)

        from services.batch_processor import BatchJob, BatchJobStatus
        job = BatchJob(
            id="cb-test",
            name="cb",
            status=BatchJobStatus.RUNNING,
            created_at=datetime.now(timezone.utc).replace(tzinfo=None),
            total_files=1,
        )
        # Simulate the callback loop used in _process_job
        for cb in processor._callbacks:
            try:
                cb(job)
            except Exception:
                pass
        good_cb.assert_called_once_with(job)


# ══════════════════════════════════════════════════════════════════════════════
# 9. Async job execution (end-to-end with mocked inspection)
# ══════════════════════════════════════════════════════════════════════════════

class TestBatchProcessorExecution:
    def _mock_inspect_result(self, file_path):
        return {
            "id": "insp-001",
            "decision": "pass",
            "confidence": 0.95,
            "objects_found": 0,
            "total_time_ms": 200.0,
        }

    @pytest.mark.asyncio
    async def test_start_job_runs_inspection_for_each_file(self, tmp_image_dir, mock_db):
        with patch("services.batch_processor.InspectionService") as MockSvc:
            mock_inspector = MagicMock()
            mock_inspector.inspect_image.side_effect = self._mock_inspect_result
            MockSvc.return_value = mock_inspector

            from services.batch_processor import BatchProcessor
            bp = BatchProcessor()
            job = bp.create_job("exec-test", str(tmp_image_dir), pattern="*.jpg")
            n_files = job.total_files

            await bp.start_job(job.id, mock_db)
            # Allow the async task to complete
            await asyncio.sleep(0.1)

            assert mock_inspector.inspect_image.call_count == n_files

    @pytest.mark.asyncio
    async def test_completed_files_counted(self, tmp_image_dir, mock_db):
        with patch("services.batch_processor.InspectionService") as MockSvc:
            mock_inspector = MagicMock()
            mock_inspector.inspect_image.return_value = {"decision": "pass", "confidence": 0.9}
            MockSvc.return_value = mock_inspector

            from services.batch_processor import BatchProcessor
            bp = BatchProcessor()
            job = bp.create_job("count-test", str(tmp_image_dir), pattern="*.jpg")

            await bp.start_job(job.id, mock_db)
            await asyncio.sleep(0.2)

            assert job.processed_files == job.total_files

    @pytest.mark.asyncio
    async def test_failed_inspection_increments_failed_count(self, tmp_image_dir, mock_db):
        with patch("services.batch_processor.InspectionService") as MockSvc:
            mock_inspector = MagicMock()
            mock_inspector.inspect_image.side_effect = RuntimeError("pipeline error")
            MockSvc.return_value = mock_inspector

            from services.batch_processor import BatchProcessor
            bp = BatchProcessor()
            job = bp.create_job("fail-test", str(tmp_image_dir), pattern="*.jpg")

            await bp.start_job(job.id, mock_db)
            await asyncio.sleep(0.2)

            assert job.failed_files > 0

    @pytest.mark.asyncio
    async def test_start_already_running_raises(self, tmp_image_dir, mock_db):
        with patch("services.batch_processor.InspectionService"):
            from services.batch_processor import BatchProcessor, BatchJobStatus
            bp = BatchProcessor()
            job = bp.create_job("dbl-start", str(tmp_image_dir))
            job.status = BatchJobStatus.RUNNING

            with pytest.raises(ValueError, match="already running"):
                await bp.start_job(job.id, mock_db)

    @pytest.mark.asyncio
    async def test_start_unknown_job_raises(self, mock_db):
        with patch("services.batch_processor.InspectionService"):
            from services.batch_processor import BatchProcessor
            bp = BatchProcessor()
            with pytest.raises(ValueError, match="not found"):
                await bp.start_job("nonexistent-id", mock_db)


# ══════════════════════════════════════════════════════════════════════════════
# 10. Result file export (JSON + CSV)
# ══════════════════════════════════════════════════════════════════════════════

class TestBatchResultExport:
    @pytest.mark.asyncio
    async def test_results_json_written(self, tmp_image_dir, mock_db):
        with patch("services.batch_processor.InspectionService") as MockSvc:
            mock_inspector = MagicMock()
            mock_inspector.inspect_image.return_value = {
                "decision": "pass", "confidence": 0.9,
                "objects_found": 0, "total_time_ms": 100.0,
            }
            MockSvc.return_value = mock_inspector

            from services.batch_processor import BatchProcessor
            bp = BatchProcessor()
            job = bp.create_job("json-test", str(tmp_image_dir), pattern="*.jpg")

            await bp.start_job(job.id, mock_db)
            await asyncio.sleep(0.3)

            results_file = Path(job.output_directory) / "results.json"
            assert results_file.exists()
            data = json.loads(results_file.read_text())
            assert "job" in data
            assert "results" in data

    @pytest.mark.asyncio
    async def test_summary_csv_written(self, tmp_image_dir, mock_db):
        with patch("services.batch_processor.InspectionService") as MockSvc:
            mock_inspector = MagicMock()
            mock_inspector.inspect_image.return_value = {
                "decision": "pass", "confidence": 0.9,
                "objects_found": 0, "total_time_ms": 100.0,
            }
            MockSvc.return_value = mock_inspector

            from services.batch_processor import BatchProcessor
            bp = BatchProcessor()
            job = bp.create_job("csv-test", str(tmp_image_dir), pattern="*.jpg")

            await bp.start_job(job.id, mock_db)
            await asyncio.sleep(0.3)

            csv_file = Path(job.output_directory) / "summary.csv"
            assert csv_file.exists()
            lines = csv_file.read_text().splitlines()
            assert lines[0].startswith("File,")  # header row
            assert len(lines) > 1  # at least one data row
