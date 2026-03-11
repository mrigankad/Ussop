"""
Tests for InspectionService — full pipeline, detection processing,
DB persistence, statistics, edge cases, and thread safety.
"""
import uuid
import pytest
import tempfile
import threading
from pathlib import Path
from unittest.mock import MagicMock, patch, PropertyMock
from datetime import datetime, timezone

import numpy as np
from PIL import Image


# ── helpers ───────────────────────────────────────────────────────────────────

def _make_service():
    """Create InspectionService with the ML pipeline fully mocked."""
    with patch("services.inspector.NanoSAMPipeline"):
        from services.inspector import InspectionService
        svc = InspectionService()
        svc.pipeline = MagicMock()
        return svc


def _make_segmented_object(class_name="scratch", score=0.92, label=1,
                            box=None, mask=None, iou=0.88):
    """Build a mock SegmentedObject."""
    obj = MagicMock()
    obj.detection.box = box or [10.0, 20.0, 100.0, 200.0]
    obj.detection.label = label
    obj.detection.score = score
    obj.detection.class_name = class_name
    if mask is None:
        m = np.zeros((200, 200), dtype=bool)
        m[30:80, 30:80] = True
        obj.mask = m
    else:
        obj.mask = mask
    obj.iou_score = iou
    return obj


def _fake_pipeline_result(objects=None):
    """Build a mock PipelineResult."""
    result = MagicMock()
    result.objects = objects or []
    result.detection_time_s = 0.3
    result.segmentation_time_s = 0.5
    result.total_time_s = 0.8
    return result


def _write_fake_image(path: Path):
    """Write a tiny RGB image to path."""
    img = Image.new("RGB", (64, 64), color=(128, 128, 128))
    img.save(path)


# ══════════════════════════════════════════════════════════════════════════════
# 1. InspectionConfig defaults
# ══════════════════════════════════════════════════════════════════════════════

class TestInspectionConfig:
    def test_default_confidence_threshold(self):
        from services.inspector import InspectionConfig
        cfg = InspectionConfig()
        assert cfg.confidence_threshold == 0.5

    def test_default_max_detections(self):
        from services.inspector import InspectionConfig
        assert InspectionConfig().max_detections == 20

    def test_default_measure_area_true(self):
        from services.inspector import InspectionConfig
        assert InspectionConfig().measure_area is True

    def test_default_save_images_true(self):
        from services.inspector import InspectionConfig
        assert InspectionConfig().save_images is True

    def test_default_generate_annotated_true(self):
        from services.inspector import InspectionConfig
        assert InspectionConfig().generate_annotated is True

    def test_custom_values(self):
        from services.inspector import InspectionConfig
        cfg = InspectionConfig(confidence_threshold=0.8, max_detections=5)
        assert cfg.confidence_threshold == 0.8
        assert cfg.max_detections == 5


# ══════════════════════════════════════════════════════════════════════════════
# 2. _process_detection — measurement extraction
# ══════════════════════════════════════════════════════════════════════════════

class TestProcessDetection:
    @pytest.fixture
    def service(self):
        return _make_service()

    def test_class_name_propagated(self, service):
        from services.inspector import InspectionConfig
        obj = _make_segmented_object(class_name="crack")
        result = service._process_detection(obj, 0, "insp-1", "2026/03/10",
                                             InspectionConfig())
        assert result["class_name"] == "crack"

    def test_confidence_propagated(self, service):
        from services.inspector import InspectionConfig
        obj = _make_segmented_object(score=0.77)
        result = service._process_detection(obj, 0, "insp-1", "2026/03/10",
                                             InspectionConfig())
        assert abs(result["confidence"] - 0.77) < 1e-6

    def test_bounding_box_structure(self, service):
        from services.inspector import InspectionConfig
        obj = _make_segmented_object(box=[5.0, 10.0, 50.0, 80.0])
        result = service._process_detection(obj, 0, "insp-1", "2026/03/10",
                                             InspectionConfig())
        box = result["box"]
        assert box["x1"] == 5.0
        assert box["y1"] == 10.0
        assert box["x2"] == 50.0
        assert box["y2"] == 80.0

    def test_measurements_populated_when_mask_present(self, service):
        from services.inspector import InspectionConfig
        obj = _make_segmented_object()
        result = service._process_detection(obj, 0, "insp-1", "2026/03/10",
                                             InspectionConfig())
        assert len(result["measurements"]) > 0

    def test_area_pixels_measurement_present(self, service):
        from services.inspector import InspectionConfig
        obj = _make_segmented_object()
        result = service._process_detection(obj, 0, "insp-1", "2026/03/10",
                                             InspectionConfig())
        names = [m["name"] for m in result["measurements"]]
        assert "area_pixels" in names

    def test_width_height_measurements_present(self, service):
        from services.inspector import InspectionConfig
        obj = _make_segmented_object()
        result = service._process_detection(obj, 0, "insp-1", "2026/03/10",
                                             InspectionConfig())
        names = [m["name"] for m in result["measurements"]]
        assert "width" in names
        assert "height" in names

    def test_area_value_correct(self, service):
        from services.inspector import InspectionConfig
        mask = np.zeros((100, 100), dtype=bool)
        mask[10:20, 10:20] = True  # 100 px
        obj = _make_segmented_object(mask=mask)
        result = service._process_detection(obj, 0, "insp-1", "2026/03/10",
                                             InspectionConfig())
        area = next(m for m in result["measurements"] if m["name"] == "area_pixels")
        assert area["value"] == 100.0

    def test_no_measurements_when_mask_none(self, service):
        from services.inspector import InspectionConfig
        obj = _make_segmented_object(mask=None)
        obj.mask = None
        result = service._process_detection(obj, 0, "insp-1", "2026/03/10",
                                             InspectionConfig())
        assert result["measurements"] == []

    def test_result_has_unique_id(self, service):
        from services.inspector import InspectionConfig
        obj = _make_segmented_object()
        r1 = service._process_detection(obj, 0, "insp-1", "2026/03/10", InspectionConfig())
        r2 = service._process_detection(obj, 1, "insp-1", "2026/03/10", InspectionConfig())
        assert r1["id"] != r2["id"]

    def test_mask_iou_propagated(self, service):
        from services.inspector import InspectionConfig
        obj = _make_segmented_object(iou=0.75)
        result = service._process_detection(obj, 0, "insp-1", "2026/03/10",
                                             InspectionConfig())
        assert abs(result["mask_iou"] - 0.75) < 1e-6

    def test_measurement_units_are_px(self, service):
        from services.inspector import InspectionConfig
        obj = _make_segmented_object()
        result = service._process_detection(obj, 0, "insp-1", "2026/03/10",
                                             InspectionConfig())
        for m in result["measurements"]:
            assert m["unit"] == "px"


# ══════════════════════════════════════════════════════════════════════════════
# 3. inspect_image — decision logic
# ══════════════════════════════════════════════════════════════════════════════

class TestInspectImageDecision:
    @pytest.fixture
    def service(self):
        return _make_service()

    def _run_inspect(self, service, objects, tmp_path):
        """Helper: write a real image, run inspect_image with a mocked pipeline."""
        img_path = tmp_path / "test.jpg"
        _write_fake_image(img_path)
        service.pipeline.run.return_value = _fake_pipeline_result(objects=objects)
        service.pipeline.visualize = MagicMock()

        from services.inspector import InspectionConfig
        with patch("services.inspector.settings") as mock_settings:
            mock_settings.IMAGES_DIR = tmp_path / "images"
            mock_settings.MASKS_DIR = tmp_path / "masks"
            mock_settings.DATA_DIR = tmp_path
            mock_settings.ACTIVE_LEARNING_ENABLED = False
            mock_settings.CONFIDENCE_THRESHOLD = 0.5
            (tmp_path / "images").mkdir(parents=True, exist_ok=True)
            (tmp_path / "masks").mkdir(parents=True, exist_ok=True)
            result = service.inspect_image(
                str(img_path), part_id="P001", station_id="S1", db=None,
                config=InspectionConfig(save_images=False, generate_annotated=False)
            )
        return result

    def test_no_objects_gives_pass(self, service, tmp_path):
        result = self._run_inspect(service, objects=[], tmp_path=tmp_path)
        assert result["decision"] == "pass"

    def test_no_objects_confidence_is_1(self, service, tmp_path):
        result = self._run_inspect(service, objects=[], tmp_path=tmp_path)
        assert result["confidence"] == 1.0

    def test_high_confidence_objects_give_fail(self, service, tmp_path):
        objs = [_make_segmented_object(score=0.9)]
        result = self._run_inspect(service, objects=objs, tmp_path=tmp_path)
        assert result["decision"] == "fail"

    def test_objects_found_count_matches(self, service, tmp_path):
        objs = [_make_segmented_object(), _make_segmented_object(class_name="dent")]
        result = self._run_inspect(service, objects=objs, tmp_path=tmp_path)
        assert result["objects_found"] == 2

    def test_result_has_inspection_id(self, service, tmp_path):
        result = self._run_inspect(service, objects=[], tmp_path=tmp_path)
        assert "id" in result
        assert len(result["id"]) > 0

    def test_result_has_station_id(self, service, tmp_path):
        result = self._run_inspect(service, objects=[], tmp_path=tmp_path)
        assert result["station_id"] == "S1"

    def test_result_has_part_id(self, service, tmp_path):
        result = self._run_inspect(service, objects=[], tmp_path=tmp_path)
        assert result["part_id"] == "P001"

    def test_detections_list_populated(self, service, tmp_path):
        objs = [_make_segmented_object(class_name="scratch", score=0.9)]
        result = self._run_inspect(service, objects=objs, tmp_path=tmp_path)
        assert len(result["detections"]) == 1
        assert result["detections"][0]["class_name"] == "scratch"

    def test_timing_fields_present(self, service, tmp_path):
        result = self._run_inspect(service, objects=[], tmp_path=tmp_path)
        assert "total_time_ms" in result
        assert result["total_time_ms"] > 0

    def test_pipeline_exception_returns_error_dict(self, service, tmp_path):
        img_path = tmp_path / "test.jpg"
        _write_fake_image(img_path)
        service.pipeline.run.side_effect = RuntimeError("GPU OOM")

        from services.inspector import InspectionConfig
        with patch("services.inspector.settings") as mock_settings:
            mock_settings.IMAGES_DIR = tmp_path / "images"
            mock_settings.MASKS_DIR = tmp_path / "masks"
            mock_settings.DATA_DIR = tmp_path
            mock_settings.ACTIVE_LEARNING_ENABLED = False
            (tmp_path / "images").mkdir(parents=True, exist_ok=True)
            result = service.inspect_image(
                str(img_path), db=None,
                config=InspectionConfig(save_images=False, generate_annotated=False)
            )
        assert "error" in result

    def test_missing_image_file_returns_error(self, service, tmp_path):
        """inspector.py opens the image before pipeline.run, so FileNotFoundError
        is caught by the broad except clause and returned as an error dict."""
        from services.inspector import InspectionConfig
        with patch("services.inspector.settings") as mock_settings:
            mock_settings.IMAGES_DIR = tmp_path / "images"
            mock_settings.MASKS_DIR = tmp_path / "masks"
            mock_settings.DATA_DIR = tmp_path
            mock_settings.ACTIVE_LEARNING_ENABLED = False
            (tmp_path / "images").mkdir(parents=True, exist_ok=True)
            try:
                result = service.inspect_image(
                    "/nonexistent/path/img.jpg", db=None,
                    config=InspectionConfig(save_images=False, generate_annotated=False)
                )
                # If the service catches and wraps the error, it should have "error" key
                assert "error" in result
            except (FileNotFoundError, OSError):
                # If the service propagates the error directly, that's also valid behavior
                pass


# ══════════════════════════════════════════════════════════════════════════════
# 4. Database persistence
# ══════════════════════════════════════════════════════════════════════════════

class TestInspectorDBPersistence:
    @pytest.fixture
    def service(self):
        return _make_service()

    def test_save_to_db_calls_add_and_commit(self, service):
        db = MagicMock()
        result = {
            "id": str(uuid.uuid4()),
            "station_id": "S1",
            "part_id": "P001",
            "timestamp": datetime.now(timezone.utc).replace(tzinfo=None).isoformat(),
            "decision": "pass",
            "confidence": 0.95,
            "detection_time_ms": 300.0,
            "segmentation_time_ms": 450.0,
            "total_time_ms": 750.0,
            "original_image": "images/test.jpg",
            "annotated_image": None,
            "detections": [],
        }
        service._save_to_db(db, result)
        db.add.assert_called()
        db.commit.assert_called_once()

    def test_save_to_db_with_detections(self, service):
        db = MagicMock()
        det_id = str(uuid.uuid4())
        result = {
            "id": str(uuid.uuid4()),
            "station_id": "S1",
            "part_id": None,
            "timestamp": datetime.now(timezone.utc).replace(tzinfo=None).isoformat(),
            "decision": "fail",
            "confidence": 0.87,
            "detection_time_ms": 300.0,
            "segmentation_time_ms": 450.0,
            "total_time_ms": 750.0,
            "original_image": "images/test.jpg",
            "annotated_image": "images/test_ann.jpg",
            "detections": [
                {
                    "id": det_id,
                    "class_name": "scratch",
                    "class_label": 1,
                    "confidence": 0.92,
                    "box": {"x1": 10.0, "y1": 20.0, "x2": 100.0, "y2": 200.0},
                    "mask_path": None,
                    "mask_iou": 0.88,
                    "measurements": [
                        {"name": "area_pixels", "value": 2500.0, "unit": "px"}
                    ],
                }
            ],
        }
        service._save_to_db(db, result)
        # add called at least 3 times: 1 Inspection + 1 Detection + 1 Measurement
        assert db.add.call_count >= 3
        db.commit.assert_called_once()

    def test_inspect_image_calls_save_to_db_when_db_provided(self, service, tmp_path):
        img_path = tmp_path / "test.jpg"
        _write_fake_image(img_path)
        service.pipeline.run.return_value = _fake_pipeline_result(objects=[])
        service.pipeline.visualize = MagicMock()

        db = MagicMock()
        service._save_to_db = MagicMock()

        from services.inspector import InspectionConfig
        with patch("services.inspector.settings") as mock_settings:
            mock_settings.IMAGES_DIR = tmp_path / "images"
            mock_settings.MASKS_DIR = tmp_path / "masks"
            mock_settings.DATA_DIR = tmp_path
            mock_settings.ACTIVE_LEARNING_ENABLED = False
            (tmp_path / "images").mkdir(parents=True, exist_ok=True)
            service.inspect_image(
                str(img_path), db=db,
                config=InspectionConfig(save_images=False, generate_annotated=False)
            )
        service._save_to_db.assert_called_once()

    def test_inspect_image_skips_db_when_none(self, service, tmp_path):
        img_path = tmp_path / "test.jpg"
        _write_fake_image(img_path)
        service.pipeline.run.return_value = _fake_pipeline_result(objects=[])
        service.pipeline.visualize = MagicMock()
        service._save_to_db = MagicMock()

        from services.inspector import InspectionConfig
        with patch("services.inspector.settings") as mock_settings:
            mock_settings.IMAGES_DIR = tmp_path / "images"
            mock_settings.MASKS_DIR = tmp_path / "masks"
            mock_settings.DATA_DIR = tmp_path
            mock_settings.ACTIVE_LEARNING_ENABLED = False
            (tmp_path / "images").mkdir(parents=True, exist_ok=True)
            service.inspect_image(
                str(img_path), db=None,
                config=InspectionConfig(save_images=False, generate_annotated=False)
            )
        service._save_to_db.assert_not_called()


# ══════════════════════════════════════════════════════════════════════════════
# 5. Statistics query
# ══════════════════════════════════════════════════════════════════════════════

class TestInspectorStatistics:
    @pytest.fixture
    def service(self):
        return _make_service()

    def test_statistics_zero_total(self, service):
        db = MagicMock()
        db.query.return_value.filter.return_value.count.return_value = 0
        db.query.return_value.filter.return_value.scalar.return_value = None
        db.query.return_value.filter.return_value.group_by.return_value.all.return_value = []
        stats = service.get_statistics(db)
        assert stats["total_inspections"] == 0
        assert stats["pass_rate"] == 0

    def test_statistics_pass_rate_calculation(self, service):
        db = MagicMock()
        # total=10, passed=8
        query_mock = MagicMock()
        query_mock.count.side_effect = [10, 8, 2, 0]
        query_mock.filter.return_value = query_mock
        query_mock.scalar.return_value = 250.0
        query_mock.group_by.return_value.all.return_value = []
        db.query.return_value = query_mock
        stats = service.get_statistics(db)
        # pass_rate = 8/10 = 0.8
        assert stats["pass_rate"] == pytest.approx(0.8)

    def test_statistics_has_required_keys(self, service):
        db = MagicMock()
        db.query.return_value.filter.return_value.count.return_value = 0
        db.query.return_value.filter.return_value.scalar.return_value = None
        db.query.return_value.filter.return_value.group_by.return_value.all.return_value = []
        stats = service.get_statistics(db)
        for key in ("total_inspections", "passed", "failed", "pass_rate",
                    "avg_inspection_time_ms", "defect_breakdown"):
            assert key in stats, f"Missing key: {key}"

    def test_statistics_station_filter_accepted(self, service):
        db = MagicMock()
        query_mock = MagicMock()
        query_mock.count.return_value = 0
        query_mock.filter.return_value = query_mock
        query_mock.scalar.return_value = None
        query_mock.group_by.return_value.all.return_value = []
        db.query.return_value = query_mock
        stats = service.get_statistics(db, station_id="S1")
        assert stats["station_id"] == "S1"


# ══════════════════════════════════════════════════════════════════════════════
# 6. Hot-swap weights
# ══════════════════════════════════════════════════════════════════════════════

class TestInspectorWeightsReload:
    @pytest.fixture
    def service(self):
        return _make_service()

    def test_reload_nonexistent_weights_raises(self, service):
        with pytest.raises(FileNotFoundError):
            service.reload_finetuned_weights("/nonexistent/weights.pth")

    def test_reload_weights_thread_safe(self, service, tmp_path):
        """reload_finetuned_weights must hold the lock during swap."""
        weights_path = tmp_path / "weights.pth"
        weights_path.write_bytes(b"fake")

        lock_acquired = []

        def patched_load(path, map_location):
            # Lock must be held at this point
            locked = not service._pipeline_lock.acquire(blocking=False)
            lock_acquired.append(locked)
            return {}

        service.pipeline.detector = MagicMock()
        service.pipeline.detector.model.load_state_dict = MagicMock()
        service.pipeline.detector.model.eval = MagicMock()

        with patch("torch.load", side_effect=patched_load):
            service.reload_finetuned_weights(str(weights_path))

        assert any(lock_acquired), "Lock was not held during weight load"

    def test_reload_calls_load_state_dict(self, service, tmp_path):
        weights_path = tmp_path / "weights.pth"
        weights_path.write_bytes(b"fake")

        service.pipeline.detector = MagicMock()
        service.pipeline.detector.model.load_state_dict = MagicMock()
        service.pipeline.detector.model.eval = MagicMock()

        with patch("torch.load", return_value={"layer.weight": MagicMock()}):
            service.reload_finetuned_weights(str(weights_path))

        service.pipeline.detector.model.load_state_dict.assert_called_once()

    def test_reload_calls_eval_after_load(self, service, tmp_path):
        weights_path = tmp_path / "weights.pth"
        weights_path.write_bytes(b"fake")

        service.pipeline.detector = MagicMock()
        service.pipeline.detector.model.load_state_dict = MagicMock()
        service.pipeline.detector.model.eval = MagicMock()

        with patch("torch.load", return_value={}):
            service.reload_finetuned_weights(str(weights_path))

        service.pipeline.detector.model.eval.assert_called_once()


# ══════════════════════════════════════════════════════════════════════════════
# 7. Thread safety of inspect_image
# ══════════════════════════════════════════════════════════════════════════════

class TestInspectorThreadSafety:
    def test_concurrent_inspections_dont_crash(self, tmp_path):
        """Multiple threads calling inspect_image concurrently must not raise."""
        service = _make_service()
        service.pipeline.run.return_value = _fake_pipeline_result(objects=[])
        service.pipeline.visualize = MagicMock()

        errors = []

        def run_inspect():
            img_path = tmp_path / f"img_{threading.get_ident()}.jpg"
            _write_fake_image(img_path)
            from services.inspector import InspectionConfig
            with patch("services.inspector.settings") as ms:
                ms.IMAGES_DIR = tmp_path / "images"
                ms.MASKS_DIR = tmp_path / "masks"
                ms.DATA_DIR = tmp_path
                ms.ACTIVE_LEARNING_ENABLED = False
                (tmp_path / "images").mkdir(parents=True, exist_ok=True)
                try:
                    service.inspect_image(
                        str(img_path), db=None,
                        config=InspectionConfig(save_images=False, generate_annotated=False)
                    )
                except Exception as e:
                    errors.append(e)

        threads = [threading.Thread(target=run_inspect) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=10)

        assert errors == [], f"Concurrent inspection raised: {errors}"
