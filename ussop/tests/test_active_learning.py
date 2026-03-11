"""
Tests for active learning service
"""
import pytest
from unittest.mock import Mock, MagicMock
import numpy as np

from ussop.services.active_learning import ActiveLearningService, UncertaintyScore


class TestActiveLearningService:
    """Test cases for ActiveLearningService."""
    
    @pytest.fixture
    def service(self):
        """Create active learning service."""
        return ActiveLearningService()
    
    def test_calculate_uncertainty_no_detections(self, service):
        """Test uncertainty calculation with no detections."""
        result = {
            'id': 'test-123',
            'detections': [],
            'decision': 'pass'
        }
        
        uncertainty = service.calculate_uncertainty(result)
        
        assert uncertainty.confidence == 1.0
        assert uncertainty.entropy == 0.0
        assert uncertainty.suggested_action == 'auto_accept'
    
    def test_calculate_uncertainty_high_confidence(self, service):
        """Test uncertainty with high confidence detections where margin is large."""
        result = {
            'id': 'test-123',
            'detections': [
                {'confidence': 0.95},
                {'confidence': 0.50}  # large margin ensures auto_accept
            ]
        }

        uncertainty = service.calculate_uncertainty(result)

        assert uncertainty.confidence > 0.7
        assert uncertainty.suggested_action == 'auto_accept'
    
    def test_calculate_uncertainty_low_confidence(self, service):
        """Test uncertainty with low confidence detections."""
        result = {
            'id': 'test-123',
            'detections': [
                {'confidence': 0.4},
                {'confidence': 0.35}
            ]
        }
        
        uncertainty = service.calculate_uncertainty(result)
        
        assert uncertainty.confidence < 0.5
        assert uncertainty.suggested_action == 'review'
    
    def test_should_flag_for_review(self, service):
        """Test flagging logic."""
        # Should flag - low confidence
        low_conf = {'id': 'low', 'detections': [{'confidence': 0.4}]}
        assert service.should_flag_for_review(low_conf) is True

        # Should not flag - high confidence with large margin (single detection = margin=confidence)
        high_conf = {'id': 'high', 'detections': [{'confidence': 0.9}]}
        assert service.should_flag_for_review(high_conf) is False
    
    def test_submit_annotation(self, service):
        """Test annotation submission."""
        # Mock database session
        db = MagicMock()
        mock_image = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = mock_image
        
        annotations = [
            {'class': 'scratch', 'box': [10, 20, 100, 200]}
        ]
        
        success = service.submit_annotation(db, 'img-123', annotations, 'operator')
        
        assert success is True
        assert mock_image.status == 'labeled'
        assert mock_image.annotations == annotations


class TestUncertaintyScore:
    """Test UncertaintyScore dataclass."""
    
    def test_creation(self):
        """Test creating uncertainty score."""
        score = UncertaintyScore(
            inspection_id='test',
            confidence=0.5,
            entropy=0.3,
            margin=0.2,
            suggested_action='review'
        )
        
        assert score.inspection_id == 'test'
        assert score.confidence == 0.5
