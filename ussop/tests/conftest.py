"""
Pytest configuration and fixtures
"""
import sys
from pathlib import Path

# Allow `from services.x import ...` imports used in test files
_ussop_dir = Path(__file__).parent.parent
_project_root = _ussop_dir.parent
_examples_dir = _project_root / "examples"  # pipeline.py, detector.py live here

# Only add project root (not ussop/) to avoid duplicate module registrations.
# Tests must use 'from ussop.services.x import ...' OR 'from services.x import ...'
# consistently. We add ussop/ as well so legacy test files using 'from services.x'
# still work, but we ensure the canonical ussop package is loaded first via project root.
for _p in (_ussop_dir, _project_root, _examples_dir):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

# Ensure log directory exists (monitoring.py opens it at import time)
(_ussop_dir / "data" / "logs").mkdir(parents=True, exist_ok=True)

import pytest
import tempfile
import shutil


@pytest.fixture(scope="session")
def test_data_dir():
    """Create temporary test data directory."""
    temp_dir = tempfile.mkdtemp()
    yield Path(temp_dir)
    shutil.rmtree(temp_dir)


@pytest.fixture
def sample_inspection_result():
    """Sample inspection result for testing."""
    return {
        "id": "test-inspection-123",
        "station_id": "test-station",
        "part_id": "PART-001",
        "timestamp": "2026-03-15T10:30:00",
        "decision": "pass",
        "confidence": 0.95,
        "detection_time_ms": 280.5,
        "segmentation_time_ms": 450.2,
        "total_time_ms": 850.7,
        "objects_found": 0,
        "original_image": "images/2026/03/15/test.jpg",
        "annotated_image": "images/2026/03/15/test_annotated.jpg",
        "detections": []
    }


@pytest.fixture
def sample_detection_result():
    """Sample detection result with defects."""
    return {
        "id": "test-inspection-456",
        "station_id": "test-station",
        "part_id": "PART-002",
        "timestamp": "2026-03-15T10:35:00",
        "decision": "fail",
        "confidence": 0.87,
        "detection_time_ms": 320.0,
        "segmentation_time_ms": 480.0,
        "total_time_ms": 920.0,
        "objects_found": 2,
        "original_image": "images/2026/03/15/test2.jpg",
        "annotated_image": "images/2026/03/15/test2_annotated.jpg",
        "detections": [
            {
                "id": "det-1",
                "class_name": "scratch",
                "class_label": 1,
                "confidence": 0.92,
                "box": {"x1": 100, "y1": 200, "x2": 150, "y2": 250},
                "mask_path": "masks/2026/03/15/test_mask_0.png",
                "mask_iou": 0.88,
                "measurements": [
                    {"name": "area_pixels", "value": 2500, "unit": "px"}
                ]
            },
            {
                "id": "det-2",
                "class_name": "dent",
                "class_label": 2,
                "confidence": 0.85,
                "box": {"x1": 300, "y1": 400, "x2": 380, "y2": 480},
                "mask_path": "masks/2026/03/15/test_mask_1.png",
                "mask_iou": 0.82,
                "measurements": [
                    {"name": "area_pixels", "value": 6400, "unit": "px"}
                ]
            }
        ]
    }


@pytest.fixture
def mock_db_session():
    """Mock database session."""
    from unittest.mock import MagicMock
    
    session = MagicMock()
    session.add = MagicMock()
    session.commit = MagicMock()
    session.query = MagicMock(return_value=session)
    session.filter = MagicMock(return_value=session)
    session.all = MagicMock(return_value=[])
    session.first = MagicMock(return_value=None)
    session.count = MagicMock(return_value=0)
    
    return session
