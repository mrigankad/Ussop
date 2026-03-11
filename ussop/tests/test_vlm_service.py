"""
Tests for VLMService — all backends, describe_defect, suggest_annotations,
answer_query, fallback behaviour, and inspector/active_learning integration.
"""
import json
import sys
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch, PropertyMock

_ussop_dir = Path(__file__).parent.parent
_project_root = _ussop_dir.parent
for _p in (_ussop_dir, _project_root):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))


# ── helpers ───────────────────────────────────────────────────────────────────

def _write_fake_image(path: Path):
    from PIL import Image
    Image.new("RGB", (64, 64), (128, 64, 32)).save(path)


def _make_settings(**kwargs):
    """Build a MagicMock that looks like a settings object."""
    defaults = dict(
        VLM_ENABLED=True,
        VLM_BACKEND="local",
        VLM_LOCAL_MODEL="moondream2",
        VLM_LOCAL_MODEL_PATH="",
        VLM_MAX_TOKENS=200,
        VLM_TIMEOUT_S=10.0,
        VLM_FALLBACK_ON_ERROR=True,
        ANTHROPIC_API_KEY="",
        OPENAI_API_KEY="",
        GOOGLE_API_KEY="",
        GROQ_API_KEY="",
        NVIDIA_NIM_API_KEY="",
        NVIDIA_NIM_BASE_URL="https://integrate.api.nvidia.com/v1",
        NVIDIA_NIM_MODEL="microsoft/phi-3-vision-128k-instruct",
        MODELS_DIR=Path("/tmp/models"),
        DATA_DIR=Path("/tmp/data"),
    )
    defaults.update(kwargs)
    mock = MagicMock()
    for k, v in defaults.items():
        setattr(mock, k, v)
    return mock


def _patch_settings(**kwargs):
    """Return a context manager that patches settings in vlm_service."""
    return patch("services.vlm_service.settings", new=_make_settings(**kwargs))


# ══════════════════════════════════════════════════════════════════════════════
# 1. VLMService initialisation
# ══════════════════════════════════════════════════════════════════════════════

class TestVLMServiceInit:
    def test_invalid_backend_raises(self):
        with _patch_settings(VLM_BACKEND="invalid_backend"):
            from services.vlm_service import VLMService
            with pytest.raises(ValueError, match="Unknown VLM_BACKEND"):
                VLMService()

    def test_valid_backends_instantiate(self):
        from services.vlm_service import (
            _AnthropicBackend, _OpenAIBackend, _GoogleBackend,
            _GroqBackend, _NIMBackend, _LocalBackend,
        )
        for backend_name, cls in [
            ("local", _LocalBackend),
            ("anthropic", _AnthropicBackend),
            ("openai", _OpenAIBackend),
            ("google", _GoogleBackend),
            ("groq", _GroqBackend),
            ("nim", _NIMBackend),
        ]:
            with _patch_settings(VLM_BACKEND=backend_name):
                from services.vlm_service import VLMService
                svc = VLMService()
                assert isinstance(svc._backend, cls)

    def test_get_vlm_service_returns_none_when_disabled(self):
        with _patch_settings(VLM_ENABLED=False):
            import importlib
            import services.vlm_service as mod
            importlib.reload(mod)
            result = mod.get_vlm_service()
            assert result is None

    def test_get_vlm_service_returns_instance_when_enabled(self, tmp_path):
        import services.vlm_service as mod
        original = mod._vlm_service
        mod._vlm_service = None
        try:
            with _patch_settings(VLM_ENABLED=True, VLM_BACKEND="local",
                                 MODELS_DIR=tmp_path, DATA_DIR=tmp_path):
                svc = mod.get_vlm_service()
                assert svc is not None
        finally:
            mod._vlm_service = original


# ══════════════════════════════════════════════════════════════════════════════
# 2. describe_defect
# ══════════════════════════════════════════════════════════════════════════════

class TestDescribeDefect:
    @pytest.fixture
    def svc_with_mock_backend(self, tmp_path):
        with _patch_settings(VLM_BACKEND="local", DATA_DIR=tmp_path):
            from services.vlm_service import VLMService
            svc = VLMService()
            svc._backend = MagicMock()
            svc._backend.query.return_value = "Linear crack, ~5 mm, thermal origin."
            return svc, tmp_path

    def test_describe_returns_string(self, svc_with_mock_backend, tmp_path):
        svc, _ = svc_with_mock_backend
        img = tmp_path / "test.jpg"
        _write_fake_image(img)
        result = svc.describe_defect(str(img))
        assert isinstance(result, str)
        assert len(result) > 0

    def test_describe_calls_backend_query(self, svc_with_mock_backend, tmp_path):
        svc, _ = svc_with_mock_backend
        img = tmp_path / "test.jpg"
        _write_fake_image(img)
        svc.describe_defect(str(img))
        svc._backend.query.assert_called_once()

    def test_describe_includes_detection_context_in_prompt(self, svc_with_mock_backend, tmp_path):
        svc, _ = svc_with_mock_backend
        img = tmp_path / "test.jpg"
        _write_fake_image(img)
        detections = [{"class_name": "scratch", "confidence": 0.92}]
        svc.describe_defect(str(img), detections=detections)
        call_args = svc._backend.query.call_args
        prompt = call_args[0][1]
        assert "scratch" in prompt

    def test_describe_fallback_on_backend_error(self, tmp_path):
        with _patch_settings(VLM_BACKEND="local", VLM_FALLBACK_ON_ERROR=True,
                             DATA_DIR=tmp_path):
            from services.vlm_service import VLMService
            svc = VLMService()
            svc._backend = MagicMock()
            svc._backend.query.side_effect = RuntimeError("model crash")
            img = tmp_path / "test.jpg"
            _write_fake_image(img)
            result = svc.describe_defect(str(img))
            assert result == "Description unavailable."

    def test_describe_raises_when_fallback_disabled(self, tmp_path):
        with _patch_settings(VLM_BACKEND="local", VLM_FALLBACK_ON_ERROR=False,
                             DATA_DIR=tmp_path):
            from services.vlm_service import VLMService
            svc = VLMService()
            svc._backend = MagicMock()
            svc._backend.query.side_effect = RuntimeError("model crash")
            img = tmp_path / "test.jpg"
            _write_fake_image(img)
            with pytest.raises(RuntimeError):
                svc.describe_defect(str(img))


# ══════════════════════════════════════════════════════════════════════════════
# 3. suggest_annotations
# ══════════════════════════════════════════════════════════════════════════════

class TestSuggestAnnotations:
    @pytest.fixture
    def svc(self, tmp_path):
        with _patch_settings(VLM_BACKEND="local", DATA_DIR=tmp_path):
            from services.vlm_service import VLMService
            s = VLMService()
            s._backend = MagicMock()
            return s, tmp_path

    def test_returns_list(self, svc, tmp_path):
        s, _ = svc
        s._backend.query.return_value = '[{"class":"scratch","box":[10,20,100,200],"confidence":0.9}]'
        img = tmp_path / "test.jpg"; _write_fake_image(img)
        result = s.suggest_annotations(str(img))
        assert isinstance(result, list)

    def test_parses_valid_json(self, svc, tmp_path):
        s, _ = svc
        payload = '[{"class":"dent","box":[5,5,50,50],"confidence":0.85}]'
        s._backend.query.return_value = payload
        img = tmp_path / "test.jpg"; _write_fake_image(img)
        result = s.suggest_annotations(str(img))
        assert len(result) == 1
        assert result[0]["class"] == "dent"

    def test_parses_json_with_markdown_fence(self, svc, tmp_path):
        s, _ = svc
        s._backend.query.return_value = '```json\n[{"class":"crack","box":[1,2,3,4],"confidence":0.7}]\n```'
        img = tmp_path / "test.jpg"; _write_fake_image(img)
        result = s.suggest_annotations(str(img))
        assert len(result) == 1

    def test_returns_empty_on_invalid_json(self, svc, tmp_path):
        s, _ = svc
        s._backend.query.return_value = "Sorry, I cannot identify defects."
        img = tmp_path / "test.jpg"; _write_fake_image(img)
        result = s.suggest_annotations(str(img))
        assert result == []

    def test_returns_empty_on_backend_error_with_fallback(self, tmp_path):
        with _patch_settings(VLM_BACKEND="local", VLM_FALLBACK_ON_ERROR=True,
                             DATA_DIR=tmp_path):
            from services.vlm_service import VLMService
            s = VLMService()
            s._backend = MagicMock()
            s._backend.query.side_effect = RuntimeError("timeout")
            img = tmp_path / "test.jpg"; _write_fake_image(img)
            result = s.suggest_annotations(str(img))
            assert result == []

    def test_multiple_annotations_parsed(self, svc, tmp_path):
        s, _ = svc
        payload = json.dumps([
            {"class": "scratch", "box": [10, 20, 100, 200], "confidence": 0.9},
            {"class": "dent",    "box": [50, 60, 120, 160], "confidence": 0.75},
        ])
        s._backend.query.return_value = payload
        img = tmp_path / "test.jpg"; _write_fake_image(img)
        result = s.suggest_annotations(str(img))
        assert len(result) == 2


# ══════════════════════════════════════════════════════════════════════════════
# 4. answer_query
# ══════════════════════════════════════════════════════════════════════════════

class TestAnswerQuery:
    @pytest.fixture
    def svc(self, tmp_path):
        with _patch_settings(VLM_BACKEND="local", DATA_DIR=tmp_path):
            from services.vlm_service import VLMService
            s = VLMService()
            s._backend = MagicMock()
            s._backend.query.return_value = "3 scratches found at Station 3 this week."
            return s, tmp_path

    def test_returns_string(self, svc):
        s, _ = svc
        result = s.answer_query("How many scratches at Station 3?")
        assert isinstance(result, str)
        assert len(result) > 0

    def test_question_in_prompt(self, svc):
        s, _ = svc
        s.answer_query("How many scratches at Station 3?", context="5 inspections.")
        call_args = s._backend.query.call_args
        prompt = call_args[0][1]
        assert "scratches" in prompt.lower()

    def test_context_in_prompt(self, svc):
        s, _ = svc
        s.answer_query("Any dents?", context="Last 7 days: 100 inspections, pass rate 95%.")
        prompt = s._backend.query.call_args[0][1]
        assert "100 inspections" in prompt

    def test_fallback_on_error(self, tmp_path):
        with _patch_settings(VLM_BACKEND="local", VLM_FALLBACK_ON_ERROR=True,
                             DATA_DIR=tmp_path):
            from services.vlm_service import VLMService
            s = VLMService()
            s._backend = MagicMock()
            s._backend.query.side_effect = RuntimeError("API down")
            result = s.answer_query("Any defects?")
            assert result == "Unable to answer query."


# ══════════════════════════════════════════════════════════════════════════════
# 5. status()
# ══════════════════════════════════════════════════════════════════════════════

class TestVLMStatus:
    def test_status_local_backend(self, tmp_path):
        with _patch_settings(VLM_ENABLED=True, VLM_BACKEND="local",
                             VLM_LOCAL_MODEL="moondream2", DATA_DIR=tmp_path):
            from services.vlm_service import VLMService
            svc = VLMService()
            st = svc.status()
            assert st["enabled"] is True
            assert st["backend"] == "local"
            assert st["model"] == "moondream2"
            assert "loaded" in st

    def test_status_nim_backend(self, tmp_path):
        with _patch_settings(VLM_BACKEND="nim", DATA_DIR=tmp_path,
                             NVIDIA_NIM_MODEL="microsoft/phi-3-vision-128k-instruct",
                             NVIDIA_NIM_BASE_URL="https://integrate.api.nvidia.com/v1"):
            from services.vlm_service import VLMService
            svc = VLMService()
            st = svc.status()
            assert st["backend"] == "nim"
            assert "nim_model" in st


# ══════════════════════════════════════════════════════════════════════════════
# 6. API key validation
# ══════════════════════════════════════════════════════════════════════════════

class TestAPIKeyValidation:
    def test_anthropic_raises_without_key(self, tmp_path):
        with _patch_settings(VLM_BACKEND="anthropic", ANTHROPIC_API_KEY="",
                             DATA_DIR=tmp_path):
            from services.vlm_service import _AnthropicBackend
            backend = _AnthropicBackend()
            img = tmp_path / "test.jpg"; _write_fake_image(img)
            # anthropic package may not be installed in test env
            with pytest.raises((ValueError, ImportError)):
                backend.query(str(img), "describe")

    def test_openai_raises_without_key(self, tmp_path):
        with _patch_settings(VLM_BACKEND="openai", OPENAI_API_KEY="",
                             DATA_DIR=tmp_path):
            from services.vlm_service import _OpenAIBackend
            backend = _OpenAIBackend()
            img = tmp_path / "test.jpg"; _write_fake_image(img)
            with pytest.raises((ValueError, ImportError)):
                backend.query(str(img), "describe")

    def test_nim_raises_without_key(self, tmp_path):
        with _patch_settings(VLM_BACKEND="nim", NVIDIA_NIM_API_KEY="",
                             DATA_DIR=tmp_path):
            from services.vlm_service import _NIMBackend
            backend = _NIMBackend()
            img = tmp_path / "test.jpg"; _write_fake_image(img)
            with pytest.raises((ValueError, ImportError)):
                backend.query(str(img), "describe")


# ══════════════════════════════════════════════════════════════════════════════
# 7. Inspector integration — vlm_description in result
# ══════════════════════════════════════════════════════════════════════════════

class TestInspectorVLMIntegration:
    def test_vlm_description_in_result_when_enabled(self, tmp_path):
        from PIL import Image as PILImage
        img_path = tmp_path / "part.jpg"
        PILImage.new("RGB", (64, 64)).save(img_path)

        with patch("services.inspector.NanoSAMPipeline"):
            from services.inspector import InspectionService, InspectionConfig
            svc = InspectionService()
            svc.pipeline = MagicMock()

            mock_obj = MagicMock()
            mock_obj.detection.box = [10.0, 20.0, 80.0, 90.0]
            mock_obj.detection.label = 1
            mock_obj.detection.score = 0.9
            mock_obj.detection.class_name = "scratch"
            import numpy as np
            mock_obj.mask = np.zeros((64, 64), dtype=bool)
            mock_obj.iou_score = 0.8

            pipeline_result = MagicMock()
            pipeline_result.objects = [mock_obj]
            pipeline_result.detection_time_s = 0.3
            pipeline_result.segmentation_time_s = 0.5
            pipeline_result.total_time_s = 0.8
            svc.pipeline.run.return_value = pipeline_result
            svc.pipeline.visualize = MagicMock()

            mock_vlm = MagicMock()
            mock_vlm.describe_defect.return_value = "Surface scratch, ~8 mm."

            with patch("services.inspector.settings") as ms:
                ms.IMAGES_DIR = tmp_path / "images"
                ms.MASKS_DIR  = tmp_path / "masks"
                ms.DATA_DIR   = tmp_path
                ms.ACTIVE_LEARNING_ENABLED = False
                ms.VLM_ENABLED = True
                (tmp_path / "images").mkdir(parents=True, exist_ok=True)
                (tmp_path / "masks").mkdir(parents=True, exist_ok=True)

                with patch("services.vlm_service.get_vlm_service", return_value=mock_vlm):
                    result = svc.inspect_image(
                        str(img_path), db=None,
                        config=InspectionConfig(save_images=False, generate_annotated=False)
                    )

            assert result.get("vlm_description") == "Surface scratch, ~8 mm."

    def test_vlm_description_none_when_no_defects(self, tmp_path):
        from PIL import Image as PILImage
        img_path = tmp_path / "clean.jpg"
        PILImage.new("RGB", (64, 64)).save(img_path)

        with patch("services.inspector.NanoSAMPipeline"):
            from services.inspector import InspectionService, InspectionConfig
            svc = InspectionService()
            svc.pipeline = MagicMock()

            pipeline_result = MagicMock()
            pipeline_result.objects = []
            pipeline_result.detection_time_s = 0.2
            pipeline_result.segmentation_time_s = 0.3
            pipeline_result.total_time_s = 0.5
            svc.pipeline.run.return_value = pipeline_result
            svc.pipeline.visualize = MagicMock()

            with patch("services.inspector.settings") as ms:
                ms.IMAGES_DIR = tmp_path / "images"
                ms.MASKS_DIR  = tmp_path / "masks"
                ms.DATA_DIR   = tmp_path
                ms.ACTIVE_LEARNING_ENABLED = False
                ms.VLM_ENABLED = True
                (tmp_path / "images").mkdir(parents=True, exist_ok=True)
                (tmp_path / "masks").mkdir(parents=True, exist_ok=True)

                result = svc.inspect_image(
                    str(img_path), db=None,
                    config=InspectionConfig(save_images=False, generate_annotated=False)
                )

            # VLM only runs when objects are found
            assert result.get("vlm_description") is None

    def test_vlm_failure_does_not_break_inspection(self, tmp_path):
        from PIL import Image as PILImage
        img_path = tmp_path / "part2.jpg"
        PILImage.new("RGB", (64, 64)).save(img_path)

        with patch("services.inspector.NanoSAMPipeline"):
            from services.inspector import InspectionService, InspectionConfig
            svc = InspectionService()
            svc.pipeline = MagicMock()

            mock_obj = MagicMock()
            mock_obj.detection.box = [10.0, 20.0, 80.0, 90.0]
            mock_obj.detection.label = 1
            mock_obj.detection.score = 0.9
            mock_obj.detection.class_name = "dent"
            import numpy as np
            mock_obj.mask = np.zeros((64, 64), dtype=bool)
            mock_obj.iou_score = 0.7

            pipeline_result = MagicMock()
            pipeline_result.objects = [mock_obj]
            pipeline_result.detection_time_s = 0.3
            pipeline_result.segmentation_time_s = 0.5
            pipeline_result.total_time_s = 0.8
            svc.pipeline.run.return_value = pipeline_result
            svc.pipeline.visualize = MagicMock()

            with patch("services.inspector.settings") as ms:
                ms.IMAGES_DIR = tmp_path / "images"
                ms.MASKS_DIR  = tmp_path / "masks"
                ms.DATA_DIR   = tmp_path
                ms.ACTIVE_LEARNING_ENABLED = False
                ms.VLM_ENABLED = True
                (tmp_path / "images").mkdir(parents=True, exist_ok=True)
                (tmp_path / "masks").mkdir(parents=True, exist_ok=True)

                # VLM crashes
                with patch("services.vlm_service.get_vlm_service", side_effect=RuntimeError("GPU OOM")):
                    result = svc.inspect_image(
                        str(img_path), db=None,
                        config=InspectionConfig(save_images=False, generate_annotated=False)
                    )

            # Inspection must still return a valid result
            assert "decision" in result
            assert result.get("objects_found", 0) >= 0


# ══════════════════════════════════════════════════════════════════════════════
# 8. Active learning VLM pre-labelling
# ══════════════════════════════════════════════════════════════════════════════

class TestActiveLearningVLMIntegration:
    def test_vlm_suggestions_stored_when_enabled(self):
        with patch("services.active_learning.settings") as ms:
            ms.VLM_ENABLED = True
            ms.UNCERTAINTY_THRESHOLD_LOW = 0.3
            ms.UNCERTAINTY_THRESHOLD_HIGH = 0.7

            suggestions = [{"class": "scratch", "box": [10, 20, 100, 200], "confidence": 0.9}]
            mock_vlm = MagicMock()
            mock_vlm.suggest_annotations.return_value = suggestions

            with patch("services.vlm_service.get_vlm_service", return_value=mock_vlm):
                from services.active_learning import ActiveLearningService, UncertaintyScore

                al = ActiveLearningService()
                db = MagicMock()
                db.add = MagicMock()
                db.commit = MagicMock()

                inspection = {
                    "id": "insp-001",
                    "original_image": "/tmp/img.jpg",
                    "detections": [{"class_name": "scratch", "confidence": 0.45}],
                }
                uncertainty = UncertaintyScore(
                    inspection_id="insp-001",
                    confidence=0.45,
                    entropy=0.5,
                    margin=0.1,
                    suggested_action="review",
                )
                al.add_to_review_queue(db, inspection, uncertainty)

                # The TrainingImage added to DB must have VLM suggestions
                added_obj = db.add.call_args[0][0]
                assert added_obj.annotations == suggestions

    def test_vlm_failure_in_al_does_not_raise(self):
        with patch("services.active_learning.settings") as ms:
            ms.VLM_ENABLED = True
            ms.UNCERTAINTY_THRESHOLD_LOW = 0.3
            ms.UNCERTAINTY_THRESHOLD_HIGH = 0.7

            with patch("services.vlm_service.get_vlm_service", side_effect=RuntimeError("crash")):
                from services.active_learning import ActiveLearningService, UncertaintyScore

                al = ActiveLearningService()
                db = MagicMock()

                inspection = {"id": "insp-002", "original_image": "/tmp/img2.jpg", "detections": []}
                uncertainty = UncertaintyScore("insp-002", 0.4, 0.5, 0.1, "review")

                # Must not raise
                al.add_to_review_queue(db, inspection, uncertainty)
                db.commit.assert_called_once()
