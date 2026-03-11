"""
Tests for model deployment and hot-swap service
"""
import pytest
from unittest.mock import MagicMock, patch
from pathlib import Path
import json
import tempfile


class TestModelVersion:
    """Tests for ModelVersion dataclass."""

    def test_to_dict(self):
        from ussop.services.model_deployer import ModelVersion
        v = ModelVersion(
            version_id="v1",
            created_at="2026-03-09T00:00:00",
            model_path="/tmp/model.pt",
            base_model="mobilenet",
            map_score=0.87,
            val_loss=0.23,
            training_job_id="job-1",
        )
        d = v.to_dict()
        assert d["version_id"] == "v1"
        assert d["map_score"] == 0.87
        assert d["is_active"] is False


class TestModelDeployer:
    """Tests for ModelDeployer service."""

    @pytest.fixture
    def deployer(self, tmp_path):
        with patch('ussop.services.model_deployer.settings') as mock_settings:
            mock_settings.MODELS_DIR = tmp_path
            from ussop.services.model_deployer import ModelDeployer
            return ModelDeployer()

    def test_initial_state(self, deployer):
        assert deployer.list_versions() == []
        assert deployer.get_active_version() is None

    def test_deploy_from_job(self, deployer, tmp_path):
        """Test deploying a model from a training job."""
        # Create a fake model checkpoint
        model_path = tmp_path / "best_model.pt"
        import torch
        torch.save({}, str(model_path))  # empty state_dict

        version = deployer.deploy_from_job(
            job_id="job-abc",
            model_path=str(model_path),
            map_score=0.85,
            val_loss=0.20,
            auto_activate=True,
        )
        assert version.map_score == 0.85
        assert version.is_active is True

    def test_deploy_better_model_replaces_active(self, deployer, tmp_path):
        """Better mAP should replace the current active version."""
        import torch

        model_path_1 = tmp_path / "model1.pt"
        model_path_2 = tmp_path / "model2.pt"
        torch.save({}, str(model_path_1))
        torch.save({}, str(model_path_2))

        v1 = deployer.deploy_from_job("job-1", str(model_path_1), map_score=0.70, val_loss=0.30)
        v2 = deployer.deploy_from_job("job-2", str(model_path_2), map_score=0.85, val_loss=0.20)

        versions = deployer.list_versions()
        active = deployer.get_active_version()
        assert active["version_id"] == v2.version_id

    def test_worse_model_not_auto_activated(self, deployer, tmp_path):
        """Worse mAP should NOT replace the current active version."""
        import torch

        model_path_1 = tmp_path / "model1b.pt"
        model_path_2 = tmp_path / "model2b.pt"
        torch.save({}, str(model_path_1))
        torch.save({}, str(model_path_2))

        v1 = deployer.deploy_from_job("job-1", str(model_path_1), map_score=0.90, val_loss=0.10)
        v2 = deployer.deploy_from_job("job-2", str(model_path_2), map_score=0.70, val_loss=0.30)

        active = deployer.get_active_version()
        assert active["version_id"] == v1.version_id

    def test_activate_version(self, deployer, tmp_path):
        """Manually activating a version should hot-swap."""
        import torch

        p1 = tmp_path / "m1.pt"
        p2 = tmp_path / "m2.pt"
        torch.save({}, str(p1))
        torch.save({}, str(p2))

        v1 = deployer.deploy_from_job("j1", str(p1), 0.80, 0.25, auto_activate=False)
        v2 = deployer.deploy_from_job("j2", str(p2), 0.75, 0.28, auto_activate=False)

        deployer.activate_version(v2.version_id)
        active = deployer.get_active_version()
        assert active["version_id"] == v2.version_id

    def test_rollback(self, deployer, tmp_path):
        """Rollback should go to the previous active version."""
        import torch

        p1 = tmp_path / "rb1.pt"
        p2 = tmp_path / "rb2.pt"
        torch.save({}, str(p1))
        torch.save({}, str(p2))

        v1 = deployer.deploy_from_job("j-rb1", str(p1), 0.80, 0.25, auto_activate=True)
        v2 = deployer.deploy_from_job("j-rb2", str(p2), 0.85, 0.20, auto_activate=True)

        prev_id = deployer.rollback()
        assert prev_id == v1.version_id
        active = deployer.get_active_version()
        assert active["version_id"] == v1.version_id

    def test_rollback_no_previous(self, deployer, tmp_path):
        """Rollback with only one version should return None."""
        import torch

        p = tmp_path / "single.pt"
        torch.save({}, str(p))
        deployer.deploy_from_job("j-single", str(p), 0.80, 0.25, auto_activate=True)

        result = deployer.rollback()
        assert result is None

    def test_delete_inactive_version(self, deployer, tmp_path):
        """Deleting a non-active version should succeed."""
        import torch

        p1 = tmp_path / "del1.pt"
        p2 = tmp_path / "del2.pt"
        torch.save({}, str(p1))
        torch.save({}, str(p2))

        v1 = deployer.deploy_from_job("j-del1", str(p1), 0.80, 0.25, auto_activate=True)
        v2 = deployer.deploy_from_job("j-del2", str(p2), 0.85, 0.20, auto_activate=True)

        result = deployer.delete_version(v1.version_id)
        assert result is True
        versions = deployer.list_versions()
        ids = [v["version_id"] for v in versions]
        assert v1.version_id not in ids

    def test_delete_active_version_blocked(self, deployer, tmp_path):
        """Deleting the active version should fail."""
        import torch

        p = tmp_path / "active_del.pt"
        torch.save({}, str(p))
        v = deployer.deploy_from_job("j-active-del", str(p), 0.80, 0.25, auto_activate=True)

        result = deployer.delete_version(v.version_id)
        assert result is False

    def test_hot_swap_calls_inspector(self, deployer, tmp_path):
        """Activating should call inspector.reload_finetuned_weights."""
        import torch

        mock_inspector = MagicMock()
        deployer.register_inspector(mock_inspector)

        p = tmp_path / "swap.pt"
        torch.save({}, str(p))
        v = deployer.deploy_from_job("j-swap", str(p), 0.80, 0.25, auto_activate=False)
        deployer.activate_version(v.version_id)

        mock_inspector.reload_finetuned_weights.assert_called_once()

    def test_deploy_missing_file_raises(self, deployer):
        with pytest.raises(FileNotFoundError):
            deployer.deploy_from_job("j-missing", "/nonexistent/model.pt", 0.80, 0.25)

    def test_registry_persistence(self, tmp_path):
        """Registry should be saved and reloaded across instances."""
        import torch
        from unittest.mock import patch

        with patch('ussop.services.model_deployer.settings') as mock_settings:
            mock_settings.MODELS_DIR = tmp_path
            from ussop.services.model_deployer import ModelDeployer

            d1 = ModelDeployer()
            p = tmp_path / "persist.pt"
            torch.save({}, str(p))
            v = d1.deploy_from_job("j-persist", str(p), 0.80, 0.25, auto_activate=True)
            v_id = v.version_id

            # Create a new instance (simulating restart)
            d2 = ModelDeployer()
            assert d2.get_active_version() is not None
            assert d2.get_active_version()["version_id"] == v_id
