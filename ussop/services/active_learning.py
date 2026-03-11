"""
Active Learning Pipeline for Ussop
Identifies uncertain predictions for human review and retraining
"""
import uuid
import json
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime, timezone

import numpy as np
from sqlalchemy.orm import Session

from config.settings import settings
from models.database import TrainingImage, Inspection, Detection


@dataclass
class UncertaintyScore:
    """Uncertainty metrics for a prediction."""
    inspection_id: str
    confidence: float
    entropy: float
    margin: float
    suggested_action: str  # 'review', 'auto_accept', 'auto_reject'


class ActiveLearningService:
    """
    Active learning service for continuous model improvement.
    
    Strategies:
    1. Uncertainty Sampling: Low confidence predictions
    2. Margin Sampling: Close decision boundaries
    3. Entropy-based: High prediction entropy
    """
    
    def __init__(self):
        self.uncertainty_low = settings.UNCERTAINTY_THRESHOLD_LOW
        self.uncertainty_high = settings.UNCERTAINTY_THRESHOLD_HIGH
    
    def calculate_uncertainty(self, inspection_result: Dict[str, Any]) -> UncertaintyScore:
        """
        Calculate uncertainty metrics for an inspection result.
        
        Returns:
            UncertaintyScore with confidence, entropy, and margin
        """
        detections = inspection_result.get('detections', [])
        
        if not detections:
            # No detections = high confidence (background)
            return UncertaintyScore(
                inspection_id=inspection_result['id'],
                confidence=1.0,
                entropy=0.0,
                margin=1.0,
                suggested_action='auto_accept'
            )
        
        # Get confidence scores
        confidences = [d['confidence'] for d in detections]
        avg_confidence = np.mean(confidences)
        
        # Calculate entropy (uncertainty in prediction distribution)
        # Higher entropy = more uncertain
        probs = np.array(confidences)
        probs = probs / probs.sum() if probs.sum() > 0 else probs
        entropy = -np.sum(probs * np.log(probs + 1e-10))
        
        # Calculate margin (difference between top 2 predictions)
        sorted_conf = sorted(confidences, reverse=True)
        margin = sorted_conf[0] - (sorted_conf[1] if len(sorted_conf) > 1 else 0)
        
        # Determine suggested action
        if avg_confidence < self.uncertainty_low:
            suggested_action = 'review'  # Human review needed
        elif avg_confidence > self.uncertainty_high and margin > 0.3:
            suggested_action = 'auto_accept'
        else:
            suggested_action = 'review'
        
        return UncertaintyScore(
            inspection_id=inspection_result['id'],
            confidence=float(avg_confidence),
            entropy=float(entropy),
            margin=float(margin),
            suggested_action=suggested_action
        )
    
    def should_flag_for_review(self, inspection_result: Dict[str, Any]) -> bool:
        """Check if inspection should be flagged for human review."""
        uncertainty = self.calculate_uncertainty(inspection_result)
        return uncertainty.suggested_action == 'review'
    
    def add_to_review_queue(
        self,
        db: Session,
        inspection_result: Dict[str, Any],
        uncertainty: UncertaintyScore
    ) -> str:
        """
        Add an inspection to the review queue for active learning.
        
        Returns:
            training_image_id
        """
        # Ask VLM to pre-label the image before a human reviews it
        vlm_suggestions = None
        if settings.VLM_ENABLED:
            try:
                from services.vlm_service import get_vlm_service
                vlm = get_vlm_service()
                if vlm:
                    image_path = inspection_result.get('original_image', '')
                    if image_path:
                        vlm_suggestions = vlm.suggest_annotations(image_path)
            except Exception:
                pass  # VLM failure must never block the queue

        training_image = TrainingImage(
            id=str(uuid.uuid4()),
            image_path=inspection_result.get('original_image'),
            status='pending',
            confidence_score=uncertainty.confidence,
            annotations=vlm_suggestions  # None or VLM pre-labels
        )

        db.add(training_image)
        db.commit()

        return training_image.id
    
    def get_review_queue(
        self,
        db: Session,
        status: str = 'pending',
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Get images in the review queue."""
        query = db.query(TrainingImage).filter(TrainingImage.status == status)
        
        # Sort by confidence (lowest first = most uncertain)
        images = query.order_by(TrainingImage.confidence_score.asc()).limit(limit).all()
        
        return [
            {
                'id': img.id,
                'image_path': img.image_path,
                'timestamp': img.timestamp.isoformat(),
                'confidence_score': img.confidence_score,
                'status': img.status,
                'annotations': img.annotations
            }
            for img in images
        ]
    
    def submit_annotation(
        self,
        db: Session,
        training_image_id: str,
        annotations: List[Dict[str, Any]],
        reviewed_by: str
    ) -> bool:
        """
        Submit human annotations for a training image.
        
        Args:
            annotations: List of annotation dicts with 'box', 'class_name', 'segmentation'
        """
        image = db.query(TrainingImage).filter(TrainingImage.id == training_image_id).first()
        if not image:
            return False
        
        image.annotations = annotations
        image.status = 'labeled'
        image.reviewed_by = reviewed_by
        image.reviewed_at = datetime.now(timezone.utc).replace(tzinfo=None)
        
        db.commit()
        return True
    
    def get_training_dataset(
        self,
        db: Session,
        min_annotations: int = 10
    ) -> Dict[str, Any]:
        """
        Get dataset for model retraining.
        
        Returns:
            Dict with images, annotations, and statistics
        """
        labeled_images = db.query(TrainingImage).filter(
            TrainingImage.status == 'labeled'
        ).all()
        
        if len(labeled_images) < min_annotations:
            return {
                'ready': False,
                'count': len(labeled_images),
                'min_required': min_annotations,
                'message': f'Need {min_annotations - len(labeled_images)} more annotations'
            }
        
        # Build training dataset
        dataset = {
            'ready': True,
            'count': len(labeled_images),
            'images': [],
            'annotations': []
        }
        
        for img in labeled_images:
            dataset['images'].append({
                'id': img.id,
                'path': str(settings.DATA_DIR / img.image_path),
                'original_path': img.image_path
            })
            dataset['annotations'].append({
                'image_id': img.id,
                'annotations': img.annotations or []
            })
        
        return dataset
    
    def mark_as_trained(self, db: Session, image_ids: List[str]) -> int:
        """Mark images as trained after model update."""
        updated = db.query(TrainingImage).filter(
            TrainingImage.id.in_(image_ids)
        ).update({'status': 'trained'}, synchronize_session=False)
        
        db.commit()
        return updated
    
    def get_statistics(self, db: Session) -> Dict[str, int]:
        """Get active learning queue statistics."""
        from sqlalchemy import func
        
        counts = db.query(
            TrainingImage.status,
            func.count(TrainingImage.id)
        ).group_by(TrainingImage.status).all()
        
        return {
            'pending': sum(c for s, c in counts if s == 'pending'),
            'labeled': sum(c for s, c in counts if s == 'labeled'),
            'trained': sum(c for s, c in counts if s == 'trained'),
            'total': sum(c for _, c in counts)
        }
    
    def export_for_labeling(
        self,
        db: Session,
        output_dir: Path,
        max_images: int = 100
    ) -> Path:
        """
        Export pending images to directory for external labeling.
        
        Returns:
            Path to export directory
        """
        import shutil
        
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        pending = db.query(TrainingImage).filter(
            TrainingImage.status == 'pending'
        ).order_by(TrainingImage.confidence_score.asc()).limit(max_images).all()
        
        manifest = []
        for img in pending:
            src_path = settings.DATA_DIR / img.image_path
            if src_path.exists():
                dst_path = output_dir / f"{img.id}.jpg"
                shutil.copy(src_path, dst_path)
                manifest.append({
                    'id': img.id,
                    'filename': f"{img.id}.jpg",
                    'confidence_score': img.confidence_score
                })
        
        # Save manifest
        with open(output_dir / 'manifest.json', 'w') as f:
            json.dump(manifest, f, indent=2)
        
        return output_dir


class ModelRetrainer:
    """
    Handles model retraining workflow.
    
    Note: This is a placeholder for the actual training implementation.
    In production, this would:
    1. Export training data
    2. Start training job (local or cloud)
    3. Validate new model
    4. Deploy if metrics improve
    """
    
    def __init__(self, active_learning: ActiveLearningService):
        self.active_learning = active_learning
    
    def check_retraining_needed(self, db: Session) -> Tuple[bool, str]:
        """Check if retraining should be triggered."""
        stats = self.active_learning.get_statistics(db)
        
        if stats['labeled'] < 20:
            return False, f"Need {20 - stats['labeled']} more labeled images"
        
        # Check if model performance degraded
        recent_inspections = db.query(Inspection).order_by(
            Inspection.timestamp.desc()
        ).limit(100).all()
        
        if len(recent_inspections) < 50:
            return False, "Not enough recent inspections"
        
        # Check for high uncertainty rate
        uncertain_count = sum(
            1 for i in recent_inspections
            if i.decision and i.decision.value == 'uncertain'
        )
        uncertainty_rate = uncertain_count / len(recent_inspections)
        
        if uncertainty_rate < 0.1:
            return False, f"Uncertainty rate ({uncertainty_rate:.1%}) below threshold"
        
        return True, f"Uncertainty rate: {uncertainty_rate:.1%}, Labeled: {stats['labeled']}"
    
    def prepare_training_job(self, db: Session) -> Dict[str, Any]:
        """Prepare data for training job."""
        dataset = self.active_learning.get_training_dataset(db, min_annotations=1)
        
        if not dataset['ready']:
            return {'error': 'Not enough training data'}
        
        # Export to format suitable for training
        job = {
            'job_id': str(uuid.uuid4()),
            'created_at': datetime.now(timezone.utc).replace(tzinfo=None).isoformat(),
            'image_count': dataset['count'],
            'images': dataset['images'],
            'annotations': dataset['annotations'],
            'base_model': settings.ENCODER_PATH,
            'training_config': {
                'epochs': 10,
                'batch_size': 4,
                'learning_rate': 1e-4,
                'validation_split': 0.2
            }
        }
        
        return job
    
    def submit_training_job(self, job: Dict[str, Any]) -> str:
        """
        Submit training job to training service.
        
        In production, this would:
        - Queue job in Redis/RabbitMQ
        - Or submit to cloud ML service (SageMaker, Vertex AI)
        """
        # Placeholder - would integrate with actual training infrastructure
        print(f"[Training] Job {job['job_id']} submitted with {job['image_count']} images")
        return job['job_id']


# Singleton instance
_active_learning: Optional[ActiveLearningService] = None
_retrainer: Optional[ModelRetrainer] = None


def get_active_learning() -> ActiveLearningService:
    """Get active learning service singleton."""
    global _active_learning
    if _active_learning is None:
        _active_learning = ActiveLearningService()
    return _active_learning


def get_retrainer() -> ModelRetrainer:
    """Get model retrainer singleton."""
    global _retrainer
    if _retrainer is None:
        _retrainer = ModelRetrainer(get_active_learning())
    return _retrainer
