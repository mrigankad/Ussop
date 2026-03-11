"""
Tests for the on-device model training pipeline
"""
import pytest
from unittest.mock import MagicMock, patch
from pathlib import Path
import tempfile
import numpy as np
import torch


class TestTrainingConfig:
    """Tests for TrainingConfig dataclass."""

    def test_default_config(self):
        from ussop.services.model_trainer import TrainingConfig
        cfg = TrainingConfig()
        assert cfg.epochs == 10
        assert cfg.batch_size == 2
        assert cfg.learning_rate == 1e-4
        assert 0 < cfg.validation_split < 1
        assert cfg.early_stopping_patience > 0

    def test_custom_config(self):
        from ussop.services.model_trainer import TrainingConfig
        cfg = TrainingConfig(epochs=5, batch_size=4, learning_rate=5e-5)
        assert cfg.epochs == 5
        assert cfg.batch_size == 4
        assert cfg.learning_rate == 5e-5


class TestTrainingJob:
    """Tests for TrainingJob dataclass."""

    def test_initial_state(self):
        from ussop.services.model_trainer import TrainingJob, TrainingStatus, TrainingConfig
        job = TrainingJob(
            job_id="test-job-1",
            created_at="2026-03-09T00:00:00",
            image_count=20,
            config=TrainingConfig(),
        )
        assert job.status == TrainingStatus.QUEUED
        assert job.current_epoch == 0
        assert job.best_map == 0.0
        assert job.output_model_path is None

    def test_to_dict_structure(self):
        from ussop.services.model_trainer import TrainingJob, TrainingConfig
        job = TrainingJob(
            job_id="test-job-2",
            created_at="2026-03-09T00:00:00",
            image_count=10,
            config=TrainingConfig(),
            total_epochs=10,
        )
        d = job.to_dict()
        assert "job_id" in d
        assert "status" in d
        assert "progress" in d
        assert "metrics" in d
        assert "log" in d
        assert d["progress"]["total_epochs"] == 10

    def test_to_dict_progress_percent(self):
        from ussop.services.model_trainer import TrainingJob, TrainingConfig
        job = TrainingJob(
            job_id="test-job-3",
            created_at="2026-03-09T00:00:00",
            image_count=10,
            config=TrainingConfig(),
            current_epoch=5,
            total_epochs=10,
        )
        d = job.to_dict()
        assert d["progress"]["percent"] == 50


class TestDefectDataset:
    """Tests for the PyTorch Dataset."""

    def test_empty_dataset(self):
        from ussop.services.model_trainer import DefectDataset
        ds = DefectDataset([], [])
        assert len(ds) == 0

    def test_dataset_with_nonexistent_paths(self):
        from ussop.services.model_trainer import DefectDataset
        images = [{"id": "img1", "path": "/nonexistent/image.jpg"}]
        annotations = [{"image_id": "img1", "annotations": []}]
        ds = DefectDataset(images, annotations)
        # Should skip nonexistent files
        assert len(ds) == 0

    def test_dataset_getitem(self, tmp_path):
        """Test loading a real image."""
        from PIL import Image
        from ussop.services.model_trainer import DefectDataset

        # Create a small test image
        img_path = tmp_path / "test.jpg"
        img = Image.new("RGB", (64, 64), color=(128, 64, 32))
        img.save(img_path)

        images = [{"id": "img1", "path": str(img_path)}]
        annotations = [{
            "image_id": "img1",
            "annotations": [{"box": [5, 5, 30, 30], "class_label": 1}]
        }]
        ds = DefectDataset(images, annotations)
        assert len(ds) == 1

        img_tensor, target = ds[0]
        assert img_tensor.shape == (3, 64, 64)
        assert "boxes" in target
        assert "labels" in target
        assert target["boxes"].shape == (1, 4)

    def test_dataset_invalid_box_skipped(self, tmp_path):
        """Test that degenerate boxes (x2<=x1) are skipped."""
        from PIL import Image
        from ussop.services.model_trainer import DefectDataset

        img_path = tmp_path / "test2.jpg"
        Image.new("RGB", (64, 64)).save(img_path)

        images = [{"id": "img2", "path": str(img_path)}]
        annotations = [{
            "image_id": "img2",
            "annotations": [{"box": [30, 30, 10, 10], "class_label": 1}]  # invalid
        }]
        ds = DefectDataset(images, annotations)
        _, target = ds[0]
        assert target["boxes"].shape[0] == 0  # no valid boxes


class TestMapComputation:
    """Tests for simple mAP calculation."""

    def test_perfect_predictions(self):
        from ussop.services.model_trainer import _compute_map
        pred = [{
            "boxes": torch.tensor([[10., 10., 50., 50.]]),
            "scores": torch.tensor([0.9]),
            "labels": torch.tensor([1]),
        }]
        tgt = [{"boxes": torch.tensor([[10., 10., 50., 50.]]), "labels": torch.tensor([1])}]
        map_score = _compute_map(pred, tgt)
        assert map_score > 0.9

    def test_no_predictions_no_targets(self):
        from ussop.services.model_trainer import _compute_map
        pred = [{"boxes": torch.zeros((0, 4)), "scores": torch.zeros(0), "labels": torch.zeros(0)}]
        tgt = [{"boxes": torch.zeros((0, 4)), "labels": torch.zeros(0)}]
        map_score = _compute_map(pred, tgt)
        assert map_score == 1.0

    def test_empty_input(self):
        from ussop.services.model_trainer import _compute_map
        assert _compute_map([], []) == 0.0

    def test_missed_detection(self):
        from ussop.services.model_trainer import _compute_map
        pred = [{"boxes": torch.zeros((0, 4)), "scores": torch.zeros(0), "labels": torch.zeros(0)}]
        tgt = [{"boxes": torch.tensor([[10., 10., 50., 50.]]), "labels": torch.tensor([1])}]
        map_score = _compute_map(pred, tgt)
        assert map_score == 0.0


class TestModelTrainer:
    """Tests for ModelTrainer service."""

    @pytest.fixture
    def trainer(self, tmp_path):
        with patch('ussop.services.model_trainer.settings') as mock_settings:
            mock_settings.MODELS_DIR = tmp_path
            from ussop.services.model_trainer import ModelTrainer
            return ModelTrainer()

    def test_initial_state(self, trainer):
        assert trainer.list_jobs() == []

    def test_submit_job_not_ready(self, trainer):
        dataset = {"ready": False, "message": "Need more data"}
        with pytest.raises(ValueError):
            trainer.submit_job(dataset)

    def test_cancel_queued_job(self, trainer, tmp_path):
        """Test that a queued job can be cancelled."""
        from ussop.services.model_trainer import TrainingJob, TrainingStatus, TrainingConfig

        job = TrainingJob(
            job_id="cancel-test",
            created_at="2026-03-09T00:00:00",
            image_count=5,
            config=TrainingConfig(),
        )
        trainer._jobs[job.job_id] = job

        result = trainer.cancel_job(job.job_id)
        assert result is True
        assert trainer._jobs[job.job_id].status == TrainingStatus.CANCELLED

    def test_cancel_nonexistent_job(self, trainer):
        result = trainer.cancel_job("does-not-exist")
        assert result is False

    def test_get_job(self, trainer):
        from ussop.services.model_trainer import TrainingJob, TrainingConfig

        job = TrainingJob(
            job_id="get-test",
            created_at="2026-03-09T00:00:00",
            image_count=3,
            config=TrainingConfig(),
        )
        trainer._jobs[job.job_id] = job
        result = trainer.get_job(job.job_id)
        assert result is not None
        assert result.job_id == "get-test"

    def test_list_jobs_sorted(self, trainer):
        from ussop.services.model_trainer import TrainingJob, TrainingConfig

        for i, ts in enumerate(["2026-03-09T00:00:00", "2026-03-10T00:00:00"]):
            job = TrainingJob(
                job_id=f"job-{i}",
                created_at=ts,
                image_count=i + 1,
                config=TrainingConfig(),
            )
            trainer._jobs[job.job_id] = job

        jobs = trainer.list_jobs()
        assert len(jobs) == 2
        # Most recent first
        assert jobs[0]["created_at"] > jobs[1]["created_at"]
