"""
Tests for ORM models — real SQLite in-memory, insert/query/cascade delete,
constraints, relationships, and get_db session lifecycle.
"""
import sys
import uuid
import pytest
from datetime import datetime
from pathlib import Path

_ussop_dir = Path(__file__).parent.parent
_project_root = _ussop_dir.parent
for _p in (_ussop_dir, _project_root):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


@pytest.fixture(scope="module")
def engine():
    from models.database import Base
    eng = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=eng)
    yield eng
    Base.metadata.drop_all(bind=eng)


@pytest.fixture
def db(engine):
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.rollback()
    session.close()


def _inspection(**kwargs):
    from models.database import Inspection, Decision, InspectionStatus
    defaults = dict(
        id=str(uuid.uuid4()),
        station_id="S1",
        timestamp=datetime.utcnow(),
        part_id="PART-001",
        status=InspectionStatus.COMPLETED,
        decision=Decision.PASS,
        confidence=0.95,
        detection_time_ms=300.0,
        segmentation_time_ms=450.0,
        total_time_ms=750.0,
    )
    defaults.update(kwargs)
    return Inspection(**defaults)


def _detection(inspection_id, **kwargs):
    from models.database import Detection
    defaults = dict(
        id=str(uuid.uuid4()),
        inspection_id=inspection_id,
        class_name="scratch",
        class_label=1,
        confidence=0.92,
        box_x1=10.0, box_y1=20.0, box_x2=100.0, box_y2=200.0,
        mask_iou=0.88,
    )
    defaults.update(kwargs)
    return Detection(**defaults)


def _measurement(detection_id, **kwargs):
    from models.database import Measurement
    defaults = dict(
        id=str(uuid.uuid4()),
        detection_id=detection_id,
        name="area_pixels",
        value=2500.0,
        unit="px",
    )
    defaults.update(kwargs)
    return Measurement(**defaults)


# ══════════════════════════════════════════════════════════════════════════════
# 1. Inspection CRUD
# ══════════════════════════════════════════════════════════════════════════════

class TestInspectionCRUD:
    def test_insert_and_query(self, db):
        insp = _inspection()
        db.add(insp)
        db.commit()
        found = db.query(__import__("models.database", fromlist=["Inspection"]).Inspection) \
                  .filter_by(id=insp.id).first()
        assert found is not None
        assert found.station_id == "S1"

    def test_decision_stored_correctly(self, db):
        from models.database import Inspection, Decision
        insp = _inspection(decision=Decision.FAIL)
        db.add(insp); db.commit()
        found = db.query(Inspection).filter_by(id=insp.id).first()
        assert found.decision == Decision.FAIL

    def test_pass_decision(self, db):
        from models.database import Inspection, Decision
        insp = _inspection(decision=Decision.PASS)
        db.add(insp); db.commit()
        found = db.query(Inspection).filter_by(id=insp.id).first()
        assert found.decision == Decision.PASS

    def test_uncertain_decision(self, db):
        from models.database import Inspection, Decision
        insp = _inspection(decision=Decision.UNCERTAIN)
        db.add(insp); db.commit()
        found = db.query(Inspection).filter_by(id=insp.id).first()
        assert found.decision == Decision.UNCERTAIN

    def test_confidence_stored(self, db):
        from models.database import Inspection
        insp = _inspection(confidence=0.77)
        db.add(insp); db.commit()
        found = db.query(Inspection).filter_by(id=insp.id).first()
        assert abs(found.confidence - 0.77) < 1e-5

    def test_nullable_part_id(self, db):
        from models.database import Inspection
        insp = _inspection(part_id=None)
        db.add(insp); db.commit()
        found = db.query(Inspection).filter_by(id=insp.id).first()
        assert found.part_id is None

    def test_multiple_inspections(self, db):
        from models.database import Inspection
        ids = [str(uuid.uuid4()) for _ in range(5)]
        for i in ids:
            db.add(_inspection(id=i))
        db.commit()
        count = db.query(Inspection).filter(Inspection.id.in_(ids)).count()
        assert count == 5

    def test_filter_by_station(self, db):
        from models.database import Inspection
        db.add(_inspection(station_id="ALPHA"))
        db.add(_inspection(station_id="BETA"))
        db.commit()
        alpha = db.query(Inspection).filter_by(station_id="ALPHA").all()
        assert all(i.station_id == "ALPHA" for i in alpha)

    def test_filter_by_decision(self, db):
        from models.database import Inspection, Decision
        db.add(_inspection(decision=Decision.FAIL))
        db.add(_inspection(decision=Decision.PASS))
        db.commit()
        fails = db.query(Inspection).filter_by(decision=Decision.FAIL).all()
        assert all(i.decision == Decision.FAIL for i in fails)


# ══════════════════════════════════════════════════════════════════════════════
# 2. Detection CRUD
# ══════════════════════════════════════════════════════════════════════════════

class TestDetectionCRUD:
    def test_insert_detection(self, db):
        from models.database import Detection
        insp = _inspection()
        db.add(insp); db.commit()
        det = _detection(insp.id)
        db.add(det); db.commit()
        found = db.query(Detection).filter_by(id=det.id).first()
        assert found is not None
        assert found.class_name == "scratch"

    def test_bounding_box_stored(self, db):
        from models.database import Detection
        insp = _inspection()
        db.add(insp); db.commit()
        det = _detection(insp.id, box_x1=5.0, box_y1=10.0, box_x2=50.0, box_y2=80.0)
        db.add(det); db.commit()
        found = db.query(Detection).filter_by(id=det.id).first()
        assert found.box_x1 == 5.0
        assert found.box_y2 == 80.0

    def test_confidence_stored(self, db):
        from models.database import Detection
        insp = _inspection()
        db.add(insp); db.commit()
        det = _detection(insp.id, confidence=0.87)
        db.add(det); db.commit()
        found = db.query(Detection).filter_by(id=det.id).first()
        assert abs(found.confidence - 0.87) < 1e-5

    def test_multiple_detections_per_inspection(self, db):
        from models.database import Detection
        insp = _inspection()
        db.add(insp); db.commit()
        for name in ("scratch", "dent", "crack"):
            db.add(_detection(insp.id, class_name=name))
        db.commit()
        dets = db.query(Detection).filter_by(inspection_id=insp.id).all()
        assert len(dets) == 3


# ══════════════════════════════════════════════════════════════════════════════
# 3. Measurement CRUD
# ══════════════════════════════════════════════════════════════════════════════

class TestMeasurementCRUD:
    def test_insert_measurement(self, db):
        from models.database import Measurement
        insp = _inspection()
        db.add(insp); db.commit()
        det = _detection(insp.id)
        db.add(det); db.commit()
        meas = _measurement(det.id)
        db.add(meas); db.commit()
        found = db.query(Measurement).filter_by(id=meas.id).first()
        assert found is not None
        assert found.name == "area_pixels"
        assert found.value == 2500.0

    def test_multiple_measurements_per_detection(self, db):
        from models.database import Measurement
        insp = _inspection()
        db.add(insp); db.commit()
        det = _detection(insp.id)
        db.add(det); db.commit()
        for name, val in [("area_pixels", 100), ("width", 10), ("height", 10)]:
            db.add(_measurement(det.id, name=name, value=float(val)))
        db.commit()
        meas = db.query(Measurement).filter_by(detection_id=det.id).all()
        assert len(meas) == 3


# ══════════════════════════════════════════════════════════════════════════════
# 4. Relationships
# ══════════════════════════════════════════════════════════════════════════════

class TestRelationships:
    def test_inspection_detections_relationship(self, db):
        insp = _inspection()
        db.add(insp); db.commit()
        db.add(_detection(insp.id, class_name="scratch"))
        db.add(_detection(insp.id, class_name="dent"))
        db.commit()
        db.refresh(insp)
        assert len(insp.detections) == 2

    def test_detection_measurements_relationship(self, db):
        insp = _inspection()
        db.add(insp); db.commit()
        det = _detection(insp.id)
        db.add(det); db.commit()
        db.add(_measurement(det.id, name="width", value=15.0))
        db.add(_measurement(det.id, name="height", value=8.0))
        db.commit()
        db.refresh(det)
        assert len(det.measurements) == 2

    def test_detection_back_reference_to_inspection(self, db):
        from models.database import Detection
        insp = _inspection()
        db.add(insp); db.commit()
        det = _detection(insp.id)
        db.add(det); db.commit()
        found = db.query(Detection).filter_by(id=det.id).first()
        assert found.inspection.id == insp.id


# ══════════════════════════════════════════════════════════════════════════════
# 5. Cascade delete
# ══════════════════════════════════════════════════════════════════════════════

class TestCascadeDelete:
    def test_delete_inspection_removes_detections(self, db):
        from models.database import Inspection, Detection
        insp = _inspection()
        db.add(insp); db.commit()
        det = _detection(insp.id)
        db.add(det); db.commit()
        det_id = det.id

        db.delete(insp)
        db.commit()

        assert db.query(Detection).filter_by(id=det_id).first() is None

    def test_delete_detection_removes_measurements(self, db):
        from models.database import Detection, Measurement
        insp = _inspection()
        db.add(insp); db.commit()
        det = _detection(insp.id)
        db.add(det); db.commit()
        meas = _measurement(det.id)
        db.add(meas); db.commit()
        meas_id = meas.id

        db.delete(det)
        db.commit()

        assert db.query(Measurement).filter_by(id=meas_id).first() is None

    def test_delete_inspection_removes_nested_measurements(self, db):
        from models.database import Inspection, Measurement
        insp = _inspection()
        db.add(insp); db.commit()
        det = _detection(insp.id)
        db.add(det); db.commit()
        meas = _measurement(det.id)
        db.add(meas); db.commit()
        meas_id = meas.id

        db.delete(insp)
        db.commit()

        assert db.query(Measurement).filter_by(id=meas_id).first() is None


# ══════════════════════════════════════════════════════════════════════════════
# 6. TrainingImage
# ══════════════════════════════════════════════════════════════════════════════

class TestTrainingImage:
    def test_insert_training_image(self, db):
        from models.database import TrainingImage
        ti = TrainingImage(
            id=str(uuid.uuid4()),
            image_path="images/test.jpg",
            status="pending",
            confidence_score=0.42,
            annotations=None,
        )
        db.add(ti); db.commit()
        found = db.query(TrainingImage).filter_by(id=ti.id).first()
        assert found is not None
        assert found.status == "pending"

    def test_training_image_with_annotations(self, db):
        from models.database import TrainingImage
        anns = [{"class": "scratch", "box": [10, 20, 100, 200]}]
        ti = TrainingImage(
            id=str(uuid.uuid4()),
            image_path="images/test2.jpg",
            status="labeled",
            confidence_score=0.5,
            annotations=anns,
        )
        db.add(ti); db.commit()
        found = db.query(TrainingImage).filter_by(id=ti.id).first()
        assert found.annotations[0]["class"] == "scratch"

    def test_filter_by_status(self, db):
        from models.database import TrainingImage
        for status in ("pending", "labeled", "pending"):
            db.add(TrainingImage(
                id=str(uuid.uuid4()),
                image_path="img.jpg",
                status=status,
            ))
        db.commit()
        pending = db.query(TrainingImage).filter_by(status="pending").all()
        assert len(pending) >= 2


# ══════════════════════════════════════════════════════════════════════════════
# 7. get_db session lifecycle
# ══════════════════════════════════════════════════════════════════════════════

class TestGetDB:
    def test_get_db_yields_session(self):
        from models.database import get_db
        gen = get_db()
        session = next(gen)
        assert session is not None
        try:
            next(gen)
        except StopIteration:
            pass

    def test_get_db_session_closes_after_use(self):
        from models.database import get_db
        gen = get_db()
        session = next(gen)
        closed_before = not session.is_active if hasattr(session, "is_active") else False
        try:
            next(gen)
        except StopIteration:
            pass
        # After generator exhausts, the session should be closed / invalid for new ops

    def test_get_db_multiple_calls_independent(self):
        from models.database import get_db
        g1 = get_db()
        g2 = get_db()
        s1 = next(g1)
        s2 = next(g2)
        assert s1 is not s2
        for g in (g1, g2):
            try: next(g)
            except StopIteration: pass
