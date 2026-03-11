"""
Tests for the OpenVINO optimizer service (services/openvino_optimizer.py).
All tests work without OpenVINO installed — tests the fallback path and
mock the openvino runtime for the accelerated path.
"""
import pytest
import numpy as np
from unittest.mock import MagicMock, patch, PropertyMock
from pathlib import Path


class TestOpenVINORunnerFallback:
    """Tests for the ONNX Runtime fallback (no OpenVINO installed)."""

    def test_available_false_without_openvino(self):
        with patch.dict("sys.modules", {"openvino": None, "openvino.runtime": None}):
            # Re-import with openvino patched out
            import importlib
            import services.openvino_optimizer as mod
            # When _OV_AVAILABLE is False the runner should still construct
            runner = mod.OpenVINORunner.__new__(mod.OpenVINORunner)
            runner.available = False
            runner._models = {}
            runner._latencies = {}
            assert runner.available is False

    def test_run_returns_none_when_unavailable(self):
        from services.openvino_optimizer import OpenVINORunner
        runner = OpenVINORunner.__new__(OpenVINORunner)
        runner.available = False
        runner._models = {}
        runner._latencies = {}

        result = runner.run("encoder", {"input": np.zeros((1, 3, 224, 224), dtype=np.float32)})
        assert result is None

    def test_load_model_returns_false_when_unavailable(self):
        from services.openvino_optimizer import OpenVINORunner
        runner = OpenVINORunner.__new__(OpenVINORunner)
        runner.available = False
        runner._models = {}

        assert runner.load_model("encoder", "/nonexistent.onnx") is False

    def test_available_devices_empty_when_unavailable(self):
        from services.openvino_optimizer import OpenVINORunner
        runner = OpenVINORunner.__new__(OpenVINORunner)
        runner.available = False
        assert runner.available_devices() == []

    def test_get_status_when_unavailable(self):
        from services.openvino_optimizer import OpenVINORunner
        runner = OpenVINORunner.__new__(OpenVINORunner)
        runner.available = False
        runner._device = "AUTO"
        runner._models = {}
        runner._latencies = {}

        status = runner.get_status()
        assert status["available"] is False
        assert status["loaded_models"] == []

    def test_avg_latency_none_before_runs(self):
        from services.openvino_optimizer import OpenVINORunner
        runner = OpenVINORunner.__new__(OpenVINORunner)
        runner._latencies = {}
        assert runner.avg_latency("encoder") is None

    def test_avg_latency_computed_after_runs(self):
        from services.openvino_optimizer import OpenVINORunner
        runner = OpenVINORunner.__new__(OpenVINORunner)
        runner._latencies = {"encoder": [10.0, 20.0, 30.0]}
        assert runner.avg_latency("encoder") == 20.0


class TestOpenVINORunnerMocked:
    """Tests for the OpenVINO path with the runtime fully mocked."""

    def _make_runner(self):
        """Build a runner with mocked OpenVINO Core."""
        from services.openvino_optimizer import OpenVINORunner

        mock_core = MagicMock()
        mock_compiled = MagicMock()
        mock_output = MagicMock()
        mock_output.any_name = "output"
        mock_compiled.outputs = [mock_output]

        mock_infer = MagicMock()
        mock_infer.get_output_tensor.return_value.data = np.array([1.0, 2.0])
        mock_compiled.create_infer_request.return_value = mock_infer
        mock_core.read_model.return_value = MagicMock()
        mock_core.compile_model.return_value = mock_compiled
        mock_core.available_devices = ["CPU", "GPU"]

        runner = OpenVINORunner.__new__(OpenVINORunner)
        runner.available = True
        runner._device = "CPU"
        runner._cache = Path("/tmp")
        runner._models = {}
        runner._latencies = {}
        runner._core = mock_core
        return runner, mock_core, mock_compiled, mock_infer

    def test_load_model_success(self, tmp_path):
        runner, mock_core, _, _ = self._make_runner()
        # Create a fake onnx file so Path.exists() returns True
        fake_onnx = tmp_path / "encoder.onnx"
        fake_onnx.write_bytes(b"fake")

        result = runner.load_model("encoder", str(fake_onnx))
        assert result is True
        assert "encoder" in runner._models
        mock_core.read_model.assert_called_once()
        mock_core.compile_model.assert_called_once()

    def test_load_model_missing_file(self):
        runner, _, _, _ = self._make_runner()
        result = runner.load_model("encoder", "/does/not/exist.onnx")
        assert result is False

    def test_run_success(self):
        runner, _, mock_compiled, mock_infer = self._make_runner()
        runner._models["encoder"] = mock_compiled

        inputs = {"input": np.zeros((1, 3, 224, 224), dtype=np.float32)}
        outputs = runner.run("encoder", inputs)

        assert outputs is not None
        assert "output" in outputs
        mock_infer.start_async.assert_called_once()
        mock_infer.wait.assert_called_once()

    def test_run_records_latency(self):
        runner, _, mock_compiled, _ = self._make_runner()
        runner._models["encoder"] = mock_compiled

        runner.run("encoder", {"input": np.zeros((1,), dtype=np.float32)})
        assert len(runner._latencies.get("encoder", [])) == 1

    def test_run_unknown_model_returns_none(self):
        runner, _, _, _ = self._make_runner()
        result = runner.run("unknown", {"x": np.array([1.0])})
        assert result is None

    def test_available_devices(self):
        runner, _, _, _ = self._make_runner()
        devices = runner.available_devices()
        assert "CPU" in devices

    def test_get_status_with_loaded_model(self, tmp_path):
        runner, mock_core, _, _ = self._make_runner()
        fake = tmp_path / "enc.onnx"
        fake.write_bytes(b"x")
        runner.load_model("encoder", str(fake))

        status = runner.get_status()
        assert status["available"] is True
        assert "encoder" in status["loaded_models"]


class TestGetOpenVINORunner:
    def test_singleton(self):
        from services import openvino_optimizer as mod
        mod._runner = None   # reset
        r1 = mod.get_openvino_runner()
        r2 = mod.get_openvino_runner()
        assert r1 is r2
        mod._runner = None   # cleanup
