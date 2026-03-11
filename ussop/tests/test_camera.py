"""
Tests for CameraService — mock/file modes, USB (mocked cv2),
capture return value, test image generation, preview, release.
"""
import sys
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch, PropertyMock

_ussop_dir = Path(__file__).parent.parent
_project_root = _ussop_dir.parent
for _p in (_ussop_dir, _project_root):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))


def _mock_settings(camera_type="mock", tmp_path=None):
    ms = MagicMock()
    ms.CAMERA_TYPE   = camera_type
    ms.CAMERA_INDEX  = 0
    ms.CAMERA_WIDTH  = 640
    ms.CAMERA_HEIGHT = 480
    ms.CAMERA_FPS    = 30
    ms.IMAGES_DIR    = tmp_path or Path("/tmp/ussop_test_images")
    return ms


# ══════════════════════════════════════════════════════════════════════════════
# 1. Mock / file mode
# ══════════════════════════════════════════════════════════════════════════════

class TestMockMode:
    def test_mock_capture_returns_string_path(self, tmp_path):
        with patch("services.camera.settings", _mock_settings("mock", tmp_path)):
            from services.camera import CameraService
            svc = CameraService()
            result = svc.capture()
        assert isinstance(result, str)
        assert len(result) > 0

    def test_mock_capture_file_exists(self, tmp_path):
        with patch("services.camera.settings", _mock_settings("mock", tmp_path)):
            from services.camera import CameraService
            svc = CameraService()
            result = svc.capture()
        assert Path(result).exists()

    def test_mock_capture_is_jpg(self, tmp_path):
        with patch("services.camera.settings", _mock_settings("mock", tmp_path)):
            from services.camera import CameraService
            svc = CameraService()
            result = svc.capture()
        assert result.endswith(".jpg")

    def test_file_mode_capture_returns_path(self, tmp_path):
        with patch("services.camera.settings", _mock_settings("file", tmp_path)):
            from services.camera import CameraService
            svc = CameraService()
            result = svc.capture()
        assert result is not None

    def test_consecutive_captures_have_unique_names(self, tmp_path):
        import time
        with patch("services.camera.settings", _mock_settings("mock", tmp_path)):
            from services.camera import CameraService
            svc = CameraService()
            r1 = svc.capture()
            time.sleep(0.01)
            r2 = svc.capture()
        assert r1 != r2

    def test_custom_save_dir_used(self, tmp_path):
        custom_dir = tmp_path / "custom_captures"
        with patch("services.camera.settings", _mock_settings("mock", tmp_path)):
            from services.camera import CameraService
            svc = CameraService()
            result = svc.capture(save_dir=custom_dir)
        assert custom_dir.exists()
        assert str(custom_dir) in result

    def test_default_save_dir_created_if_missing(self, tmp_path):
        captures_dir = tmp_path / "captures"
        assert not captures_dir.exists()
        with patch("services.camera.settings", _mock_settings("mock", tmp_path)):
            from services.camera import CameraService
            svc = CameraService()
            svc.capture()
        assert captures_dir.exists()


# ══════════════════════════════════════════════════════════════════════════════
# 2. Generated test image content
# ══════════════════════════════════════════════════════════════════════════════

class TestGeneratedImage:
    def test_generated_image_is_valid_jpeg(self, tmp_path):
        from PIL import Image
        with patch("services.camera.settings", _mock_settings("mock", tmp_path)):
            from services.camera import CameraService
            svc = CameraService()
            path = svc.capture()
        img = Image.open(path)
        assert img.format == "JPEG"

    def test_generated_image_is_rgb(self, tmp_path):
        from PIL import Image
        with patch("services.camera.settings", _mock_settings("mock", tmp_path)):
            from services.camera import CameraService
            svc = CameraService()
            path = svc.capture()
        img = Image.open(path)
        assert img.mode == "RGB"

    def test_generated_image_has_reasonable_size(self, tmp_path):
        from PIL import Image
        with patch("services.camera.settings", _mock_settings("mock", tmp_path)):
            from services.camera import CameraService
            svc = CameraService()
            path = svc.capture()
        img = Image.open(path)
        w, h = img.size
        assert w > 0 and h > 0

    def test_generate_test_image_directly(self, tmp_path):
        with patch("services.camera.settings", _mock_settings("mock", tmp_path)):
            from services.camera import CameraService
            svc = CameraService()
            path = svc._generate_test_image(save_dir=tmp_path)
        assert Path(path).exists()


# ══════════════════════════════════════════════════════════════════════════════
# 3. USB mode (cv2 mocked)
# ══════════════════════════════════════════════════════════════════════════════

class TestUSBMode:
    def _usb_svc(self, tmp_path, cap_mock=None):
        ms = _mock_settings("usb", tmp_path)
        import numpy as np
        frame = np.zeros((480, 640, 3), dtype="uint8")
        if cap_mock is None:
            cap_mock = MagicMock()
            cap_mock.read.return_value = (True, frame)
        with patch("services.camera.settings", ms), \
             patch("services.camera.cv2") as mock_cv2:
            mock_cv2.VideoCapture.return_value = cap_mock
            mock_cv2.CAP_PROP_FRAME_WIDTH  = 3
            mock_cv2.CAP_PROP_FRAME_HEIGHT = 4
            mock_cv2.CAP_PROP_FPS          = 5
            mock_cv2.imwrite.return_value  = True
            from services.camera import CameraService
            svc = CameraService()
            svc.cap = cap_mock
            return svc, mock_cv2

    def test_usb_capture_returns_path(self, tmp_path):
        svc, mock_cv2 = self._usb_svc(tmp_path)
        with patch("services.camera.settings", _mock_settings("usb", tmp_path)):
            result = svc.capture()
        assert result is not None

    def test_usb_capture_calls_imwrite(self, tmp_path):
        import numpy as np
        ms = _mock_settings("usb", tmp_path)
        frame = np.zeros((480, 640, 3), dtype="uint8")
        cap_mock = MagicMock()
        cap_mock.read.return_value = (True, frame)
        with patch("services.camera.settings", ms), \
             patch("services.camera.cv2") as mock_cv2:
            mock_cv2.VideoCapture.return_value = cap_mock
            mock_cv2.CAP_PROP_FRAME_WIDTH  = 3
            mock_cv2.CAP_PROP_FRAME_HEIGHT = 4
            mock_cv2.CAP_PROP_FPS          = 5
            mock_cv2.imwrite.return_value  = True
            from services.camera import CameraService
            svc = CameraService()
            svc.cap = cap_mock
            svc.capture()
        mock_cv2.imwrite.assert_called_once()

    def test_usb_capture_fails_gracefully_when_read_fails(self, tmp_path):
        import numpy as np
        cap_mock = MagicMock()
        cap_mock.read.return_value = (False, None)
        ms = _mock_settings("usb", tmp_path)
        with patch("services.camera.settings", ms), \
             patch("services.camera.cv2") as mock_cv2:
            mock_cv2.VideoCapture.return_value = cap_mock
            mock_cv2.CAP_PROP_FRAME_WIDTH  = 3
            mock_cv2.CAP_PROP_FRAME_HEIGHT = 4
            mock_cv2.CAP_PROP_FPS          = 5
            from services.camera import CameraService
            svc = CameraService()
            svc.cap = cap_mock
            result = svc.capture()
        assert result is None

    def test_usb_init_opens_video_capture(self, tmp_path):
        ms = _mock_settings("usb", tmp_path)
        with patch("services.camera.settings", ms), \
             patch("services.camera.cv2") as mock_cv2:
            cap = MagicMock()
            mock_cv2.VideoCapture.return_value = cap
            mock_cv2.CAP_PROP_FRAME_WIDTH  = 3
            mock_cv2.CAP_PROP_FRAME_HEIGHT = 4
            mock_cv2.CAP_PROP_FPS          = 5
            from services.camera import CameraService
            svc = CameraService()
        mock_cv2.VideoCapture.assert_called_once_with(0)


# ══════════════════════════════════════════════════════════════════════════════
# 4. Unknown camera type
# ══════════════════════════════════════════════════════════════════════════════

class TestUnknownMode:
    def test_unknown_type_returns_none(self, tmp_path):
        with patch("services.camera.settings", _mock_settings("gige", tmp_path)):
            from services.camera import CameraService
            svc = CameraService()
            result = svc.capture()
        assert result is None


# ══════════════════════════════════════════════════════════════════════════════
# 5. Preview & release
# ══════════════════════════════════════════════════════════════════════════════

class TestPreviewAndRelease:
    def test_preview_returns_none_when_no_cap(self, tmp_path):
        with patch("services.camera.settings", _mock_settings("mock", tmp_path)):
            from services.camera import CameraService
            svc = CameraService()
            svc.cap = None
            assert svc.preview() is None

    def test_preview_returns_frame_from_usb(self, tmp_path):
        import numpy as np
        frame = np.zeros((480, 640, 3), dtype="uint8")
        cap = MagicMock()
        cap.read.return_value = (True, frame)
        with patch("services.camera.settings", _mock_settings("usb", tmp_path)), \
             patch("services.camera.cv2") as mock_cv2:
            mock_cv2.VideoCapture.return_value = cap
            mock_cv2.CAP_PROP_FRAME_WIDTH  = 3
            mock_cv2.CAP_PROP_FRAME_HEIGHT = 4
            mock_cv2.CAP_PROP_FPS          = 5
            from services.camera import CameraService
            svc = CameraService()
            svc.camera_type = "usb"
            svc.cap = cap
            result = svc.preview()
        assert result is not None

    def test_release_clears_cap(self, tmp_path):
        with patch("services.camera.settings", _mock_settings("mock", tmp_path)):
            from services.camera import CameraService
            svc = CameraService()
            svc.cap = MagicMock()
            svc.release()
        assert svc.cap is None

    def test_release_calls_cap_release(self, tmp_path):
        with patch("services.camera.settings", _mock_settings("mock", tmp_path)):
            from services.camera import CameraService
            svc = CameraService()
            cap_mock = MagicMock()
            svc.cap = cap_mock
            svc.release()
        cap_mock.release.assert_called_once()

    def test_release_safe_when_cap_is_none(self, tmp_path):
        with patch("services.camera.settings", _mock_settings("mock", tmp_path)):
            from services.camera import CameraService
            svc = CameraService()
            svc.cap = None
            svc.release()  # must not raise
