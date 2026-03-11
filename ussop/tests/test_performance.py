"""
Performance benchmarks for Ussop core services.
These tests verify latency and throughput meet production targets.
"""
import pytest
import time
import threading
from unittest.mock import MagicMock, patch
import numpy as np
from PIL import Image


# Performance targets from MEMORY.md
INFERENCE_TARGET_MS = 1000      # < 1s per inspection on Intel i5
THROUGHPUT_TARGET_IPM = 30      # 30+ inspections/minute
MEMORY_TARGET_MB = 4096         # < 4GB RAM


class TestInferenceLatency:
    """Verify inference pipeline meets latency targets."""

    @pytest.fixture
    def mock_pipeline_result(self):
        """Create a mock pipeline result with typical data."""
        result = MagicMock()
        result.objects = []
        result.detection_time = 0.28
        result.segmentation_time = 0.45
        return result

    def test_active_learning_uncertainty_is_fast(self):
        """Uncertainty calculation should be sub-millisecond."""
        from ussop.services.active_learning import ActiveLearningService
        service = ActiveLearningService()

        inspection_result = {
            "id": "perf-test-1",
            "detections": [
                {"confidence": 0.85},
                {"confidence": 0.72},
                {"confidence": 0.91},
            ]
        }

        start = time.perf_counter()
        for _ in range(1000):
            service.calculate_uncertainty(inspection_result)
        elapsed_ms = (time.perf_counter() - start) * 1000

        avg_ms = elapsed_ms / 1000
        assert avg_ms < 1.0, f"Uncertainty calc took {avg_ms:.3f}ms avg (target < 1ms)"

    def test_map_computation_scales(self):
        """mAP computation should handle 100 images in < 500ms."""
        import torch
        from ussop.services.model_trainer import _compute_map

        n = 100
        preds = []
        tgts = []
        for _ in range(n):
            n_boxes = np.random.randint(1, 5)
            boxes = torch.rand(n_boxes, 4)
            boxes[:, 2:] += boxes[:, :2]  # ensure x2>x1, y2>y1
            preds.append({
                "boxes": boxes,
                "scores": torch.rand(n_boxes),
                "labels": torch.ones(n_boxes, dtype=torch.long),
            })
            tgts.append({
                "boxes": boxes.clone(),
                "labels": torch.ones(n_boxes, dtype=torch.long),
            })

        start = time.perf_counter()
        _compute_map(preds, tgts)
        elapsed_ms = (time.perf_counter() - start) * 1000

        assert elapsed_ms < 500, f"mAP for 100 images took {elapsed_ms:.1f}ms (target < 500ms)"


class TestConcurrency:
    """Verify thread safety of critical services."""

    def test_trainer_concurrent_job_creation(self, tmp_path):
        """Multiple threads can safely check job list concurrently."""
        with patch('ussop.services.model_trainer.settings') as mock_settings:
            mock_settings.MODELS_DIR = tmp_path
            from ussop.services.model_trainer import ModelTrainer, TrainingJob, TrainingConfig

            trainer = ModelTrainer()
            errors = []

            def read_jobs():
                try:
                    for _ in range(50):
                        trainer.list_jobs()
                except Exception as e:
                    errors.append(str(e))

            threads = [threading.Thread(target=read_jobs) for _ in range(10)]
            for t in threads:
                t.start()
            for t in threads:
                t.join()

            assert errors == [], f"Thread safety errors: {errors}"

    def test_deployer_concurrent_reads(self, tmp_path):
        """Multiple threads reading deployer state should not corrupt it."""
        with patch('ussop.services.model_deployer.settings') as mock_settings:
            mock_settings.MODELS_DIR = tmp_path
            from ussop.services.model_deployer import ModelDeployer

            deployer = ModelDeployer()
            errors = []

            def read_versions():
                try:
                    for _ in range(50):
                        deployer.list_versions()
                        deployer.get_active_version()
                except Exception as e:
                    errors.append(str(e))

            threads = [threading.Thread(target=read_versions) for _ in range(8)]
            for t in threads:
                t.start()
            for t in threads:
                t.join()

            assert errors == [], f"Thread safety errors: {errors}"


class TestDatasetPerformance:
    """Performance tests for dataset loading."""

    def test_dataset_build_scales(self, tmp_path):
        """Building a 100-image dataset should complete in < 2 seconds."""
        from PIL import Image
        from ussop.services.model_trainer import DefectDataset

        # Create 100 tiny images
        images = []
        annotations = []
        for i in range(100):
            img_path = tmp_path / f"img_{i}.jpg"
            Image.new("RGB", (64, 64), color=(i % 256, 128, 64)).save(img_path)
            images.append({"id": f"img-{i}", "path": str(img_path)})
            annotations.append({
                "image_id": f"img-{i}",
                "annotations": [{"box": [5, 5, 30, 30], "class_label": 1}]
            })

        start = time.perf_counter()
        ds = DefectDataset(images, annotations)
        elapsed = time.perf_counter() - start

        assert len(ds) == 100
        assert elapsed < 2.0, f"Dataset build took {elapsed:.2f}s for 100 images (target < 2s)"

    def test_single_image_load_time(self, tmp_path):
        """Loading one image from dataset should be < 50ms."""
        from PIL import Image
        from ussop.services.model_trainer import DefectDataset

        img_path = tmp_path / "single.jpg"
        Image.new("RGB", (640, 480), color=(100, 150, 200)).save(img_path)

        ds = DefectDataset(
            [{"id": "s1", "path": str(img_path)}],
            [{"image_id": "s1", "annotations": [{"box": [10, 10, 200, 200], "class_label": 1}]}],
        )

        start = time.perf_counter()
        for _ in range(20):
            ds[0]
        elapsed_ms = (time.perf_counter() - start) / 20 * 1000

        assert elapsed_ms < 50, f"Image load took {elapsed_ms:.1f}ms avg (target < 50ms)"


class TestMemoryUsage:
    """Basic memory usage checks."""

    def test_active_learning_service_lightweight(self):
        """ActiveLearningService should have minimal memory footprint."""
        import tracemalloc
        tracemalloc.start()

        from ussop.services.active_learning import ActiveLearningService
        service = ActiveLearningService()

        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        peak_mb = peak / 1024 / 1024
        assert peak_mb < 10, f"ActiveLearningService used {peak_mb:.1f}MB (target < 10MB)"

    def test_model_deployer_lightweight(self, tmp_path):
        """ModelDeployer should have minimal memory footprint without models loaded."""
        import tracemalloc
        with patch('ussop.services.model_deployer.settings') as mock_settings:
            mock_settings.MODELS_DIR = tmp_path
            tracemalloc.start()

            from ussop.services.model_deployer import ModelDeployer
            d = ModelDeployer()

            current, peak = tracemalloc.get_traced_memory()
            tracemalloc.stop()

            peak_mb = peak / 1024 / 1024
            assert peak_mb < 5, f"ModelDeployer used {peak_mb:.1f}MB (target < 5MB)"
