"""
Ussop Inspection Service - Main business logic
"""
import logging
import os
import time
import uuid

logger = logging.getLogger(__name__)
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime, timezone

import cv2
import numpy as np
from PIL import Image
from sqlalchemy.orm import Session

# Import existing pipeline
import sys
_examples_dir = str(Path(__file__).parent.parent.parent / "examples")
if _examples_dir not in sys.path:
    sys.path.insert(0, _examples_dir)
from pipeline import NanoSAMPipeline, PipelineResult, SegmentedObject
from detector import Detection

from config.settings import settings
from models.database import Inspection, Detection as DBDetection, Measurement, Decision, InspectionStatus


@dataclass
class InspectionConfig:
    """Configuration for an inspection run."""
    confidence_threshold: float = 0.5
    max_detections: int = 20
    measure_area: bool = True
    save_images: bool = True
    generate_annotated: bool = True


class InspectionService:
    """Main service for running inspections."""

    def __init__(self):
        self.pipeline = None
        self._pipeline_lock = __import__('threading').Lock()
        self._init_pipeline()

    def _init_pipeline(self):
        """Initialize the detection/segmentation pipeline."""
        try:
            self.pipeline = NanoSAMPipeline(
                encoder_path=settings.ENCODER_PATH,
                decoder_path=settings.DECODER_PATH,
                detector_backbone=settings.DETECTOR_BACKBONE,
                confidence_threshold=settings.CONFIDENCE_THRESHOLD,
                max_detections=settings.MAX_DETECTIONS,
            )
            logger.info("Pipeline initialized with %s", settings.DETECTOR_BACKBONE)
        except Exception as e:
            logger.error("Failed to initialize pipeline: %s", e)
            logger.error("Run: python download_models.py")
            raise

    def reload_finetuned_weights(self, weights_path: str) -> bool:
        """
        Hot-swap the detector's weights without restarting the service.
        Loads the fine-tuned state_dict into the existing Faster R-CNN backbone.
        Thread-safe: acquires pipeline lock while swapping.
        """
        import torch
        path = Path(weights_path)
        if not path.exists():
            raise FileNotFoundError(f"Weights not found: {weights_path}")

        with self._pipeline_lock:
            if self.pipeline is None or not hasattr(self.pipeline, 'detector'):
                raise RuntimeError("Pipeline or detector not initialized")
            state_dict = torch.load(str(path), map_location="cpu")
            # Load into the underlying Faster R-CNN model (strict=False allows partial loads)
            self.pipeline.detector.model.load_state_dict(state_dict, strict=False)
            self.pipeline.detector.model.eval()
            logger.info("Hot-swapped weights from %s", path.name)
        return True
    
    def inspect_image(
        self,
        image_path: str,
        part_id: Optional[str] = None,
        station_id: str = "default",
        db: Optional[Session] = None,
        config: Optional[InspectionConfig] = None
    ) -> Dict[str, Any]:
        """
        Run full inspection on an image.
        
        Returns inspection result dictionary.
        """
        config = config or InspectionConfig()
        start_time = time.time()
        
        # Generate inspection ID
        inspection_id = str(uuid.uuid4())
        timestamp = datetime.now(timezone.utc).replace(tzinfo=None)
        
        # Create paths for storage
        rel_dir = timestamp.strftime("%Y/%m/%d")
        img_dir = settings.IMAGES_DIR / rel_dir
        img_dir.mkdir(parents=True, exist_ok=True)
        
        # Store original image
        original_name = f"{inspection_id}_original.jpg"
        stored_original = img_dir / original_name
        
        if image_path != str(stored_original):
            img = Image.open(image_path).convert("RGB")
            img.save(stored_original)
        
        # Run pipeline
        try:
            result = self.pipeline.run(image_path)
            
            # Determine decision
            if len(result.objects) == 0:
                decision = Decision.PASS
                confidence = 1.0
            else:
                # Calculate overall confidence
                avg_conf = np.mean([obj.detection.score for obj in result.objects])
                decision = Decision.FAIL if avg_conf > 0.5 else Decision.UNCERTAIN
                confidence = float(avg_conf)
            
            # Generate annotated image
            annotated_path = None
            if config.generate_annotated:
                annotated_name = f"{inspection_id}_annotated.jpg"
                annotated_path = img_dir / annotated_name
                self.pipeline.visualize(result, save_path=annotated_path, show=False)
            
            # VLM description — runs on the full image before cropping
            vlm_description = None
            if settings.VLM_ENABLED and len(result.objects) > 0:
                try:
                    from services.vlm_service import get_vlm_service
                    vlm = get_vlm_service()
                    if vlm:
                        vlm_description = vlm.describe_defect(image_path)
                except Exception as _vlm_err:
                    logger.debug(f"[VLM] Skipped: {_vlm_err}")

            # Build result
            inspection_result = {
                "id": inspection_id,
                "station_id": station_id,
                "part_id": part_id,
                "timestamp": timestamp.isoformat(),
                "decision": decision.value,
                "confidence": confidence,
                "detection_time_ms": result.detection_time_s * 1000,
                "segmentation_time_ms": result.segmentation_time_s * 1000,
                "total_time_ms": result.total_time_s * 1000,
                "objects_found": len(result.objects),
                "original_image": str(stored_original.relative_to(settings.DATA_DIR)),
                "annotated_image": str(annotated_path.relative_to(settings.DATA_DIR)) if annotated_path else None,
                "vlm_description": vlm_description,
                "detections": []
            }
            
            # Process detections
            for idx, obj in enumerate(result.objects):
                det_data = self._process_detection(
                    obj, idx, inspection_id, rel_dir, config
                )
                inspection_result["detections"].append(det_data)
            
            # Save to database if provided
            if db:
                self._save_to_db(db, inspection_result)
                
                # Record metrics
                from services.monitoring import get_metrics_collector
                metrics = get_metrics_collector()
                metrics.record_inspection(inspection_result)
                
                # Check for active learning
                if settings.ACTIVE_LEARNING_ENABLED:
                    from services.active_learning import get_active_learning
                    al_service = get_active_learning()
                    
                    if al_service.should_flag_for_review(inspection_result):
                        uncertainty = al_service.calculate_uncertainty(inspection_result)
                        al_service.add_to_review_queue(db, inspection_result, uncertainty)
                        logger.info("Active learning: flagged %s for review (conf=%.2f)", inspection_result['id'], uncertainty.confidence)
                
                # Publish to MQTT if enabled
                try:
                    from integrations.mqtt_client import get_mqtt_client
                    mqtt = get_mqtt_client()
                    if mqtt:
                        mqtt.publish_inspection(inspection_result)
                except:
                    pass
            
            return inspection_result
            
        except Exception as e:
            logger.exception("Inspection failed for %s", image_path)
            return {
                "id": inspection_id,
                "station_id": station_id,
                "error": str(e),
                "decision": Decision.UNCERTAIN.value,
                "objects_found": 0
            }
    
    def _process_detection(
        self,
        obj: SegmentedObject,
        idx: int,
        inspection_id: str,
        rel_dir: str,
        config: InspectionConfig
    ) -> Dict[str, Any]:
        """Process a single detection and extract measurements."""
        det = obj.detection
        
        # Save mask if present
        mask_path = None
        if obj.mask is not None and config.save_images:
            mask_name = f"{inspection_id}_mask_{idx}.png"
            mask_full_path = settings.MASKS_DIR / rel_dir / mask_name
            mask_full_path.parent.mkdir(parents=True, exist_ok=True)
            cv2.imwrite(str(mask_full_path), obj.mask.astype(np.uint8) * 255)
            mask_path = str(mask_full_path.relative_to(settings.DATA_DIR))
        
        # Calculate measurements
        measurements = []
        if obj.mask is not None:
            area_pixels = int(np.sum(obj.mask))
            
            # Get bounding box dimensions
            y_indices, x_indices = np.where(obj.mask)
            if len(y_indices) > 0 and len(x_indices) > 0:
                width = int(x_indices.max() - x_indices.min())
                height = int(y_indices.max() - y_indices.min())
                
                measurements.append({
                    "name": "area_pixels",
                    "value": float(area_pixels),
                    "unit": "px"
                })
                measurements.append({
                    "name": "width",
                    "value": float(width),
                    "unit": "px"
                })
                measurements.append({
                    "name": "height",
                    "value": float(height),
                    "unit": "px"
                })
        
        return {
            "id": str(uuid.uuid4()),
            "inspection_id": inspection_id,
            "class_name": det.class_name,
            "class_label": int(det.label),
            "confidence": float(det.score),
            "box": {
                "x1": float(det.box[0]),
                "y1": float(det.box[1]),
                "x2": float(det.box[2]),
                "y2": float(det.box[3])
            },
            "mask_path": mask_path,
            "mask_iou": float(obj.iou_score),
            "measurements": measurements
        }
    
    def _save_to_db(self, db: Session, result: Dict[str, Any]):
        """Save inspection result to database."""
        # Create inspection record
        inspection = Inspection(
            id=result["id"],
            station_id=result["station_id"],
            timestamp=datetime.fromisoformat(result["timestamp"]),
            part_id=result.get("part_id"),
            original_image_path=result.get("original_image"),
            annotated_image_path=result.get("annotated_image"),
            status=InspectionStatus.COMPLETED,
            decision=Decision(result["decision"]),
            confidence=result.get("confidence"),
            detection_time_ms=result.get("detection_time_ms", 0),
            segmentation_time_ms=result.get("segmentation_time_ms", 0),
            total_time_ms=result.get("total_time_ms", 0),
            metadata_json={"vlm_description": result.get("vlm_description")} if result.get("vlm_description") else {},
        )
        db.add(inspection)
        
        # Create detection records
        for det_data in result.get("detections", []):
            detection = DBDetection(
                id=det_data["id"],
                inspection_id=result["id"],
                class_name=det_data["class_name"],
                class_label=det_data["class_label"],
                confidence=det_data["confidence"],
                box_x1=det_data["box"]["x1"],
                box_y1=det_data["box"]["y1"],
                box_x2=det_data["box"]["x2"],
                box_y2=det_data["box"]["y2"],
                mask_path=det_data.get("mask_path"),
                mask_iou=det_data.get("mask_iou"),
            )
            db.add(detection)
            
            # Create measurement records
            for meas_data in det_data.get("measurements", []):
                measurement = Measurement(
                    id=str(uuid.uuid4()),
                    detection_id=det_data["id"],
                    name=meas_data["name"],
                    value=meas_data["value"],
                    unit=meas_data["unit"]
                )
                db.add(measurement)
        
        db.commit()
    
    def inspect_from_camera(
        self,
        station_id: str = "default",
        part_id: Optional[str] = None,
        db: Optional[Session] = None
    ) -> Dict[str, Any]:
        """Capture from camera and inspect."""
        from services.camera import CameraService
        
        camera = CameraService()
        image_path = camera.capture()
        
        if image_path:
            return self.inspect_image(image_path, part_id, station_id, db)
        else:
            return {"error": "Failed to capture image from camera"}
    
    def get_statistics(self, db: Session, station_id: Optional[str] = None, hours: int = 24) -> Dict[str, Any]:
        """Get inspection statistics."""
        from sqlalchemy import func
        from datetime import timedelta
        
        since = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(hours=hours)
        
        query = db.query(Inspection).filter(Inspection.timestamp >= since)
        if station_id:
            query = query.filter(Inspection.station_id == station_id)
        
        total = query.count()
        passed = query.filter(Inspection.decision == Decision.PASS).count()
        failed = query.filter(Inspection.decision == Decision.FAIL).count()
        uncertain = query.filter(Inspection.decision == Decision.UNCERTAIN).count()
        
        avg_time = db.query(func.avg(Inspection.total_time_ms)).filter(
            Inspection.timestamp >= since
        ).scalar() or 0
        
        # Top defects
        defect_counts = db.query(
            DBDetection.class_name,
            func.count(DBDetection.id)
        ).join(Inspection).filter(
            Inspection.timestamp >= since
        ).group_by(DBDetection.class_name).all()
        
        return {
            "period_hours": hours,
            "station_id": station_id,
            "total_inspections": total,
            "passed": passed,
            "failed": failed,
            "uncertain": uncertain,
            "pass_rate": passed / total if total > 0 else 0,
            "avg_inspection_time_ms": round(avg_time, 2),
            "defect_breakdown": {name: count for name, count in defect_counts}
        }
