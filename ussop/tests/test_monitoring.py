"""
Tests for monitoring service
"""
import pytest
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime, timedelta, timezone

from ussop.services.monitoring import MetricsCollector, AlertManager, AuditLogger


class TestMetricsCollector:
    """Test cases for MetricsCollector."""
    
    @pytest.fixture
    def collector(self):
        """Create metrics collector."""
        with patch('ussop.services.monitoring.settings'):
            return MetricsCollector()
    
    def test_record_inspection(self, collector):
        """Test recording inspection metrics."""
        result = {
            'id': 'test-123',
            'timestamp': datetime.now(timezone.utc).replace(tzinfo=None).isoformat(),
            'station_id': 'default',
            'decision': 'pass',
            'confidence': 0.95,
            'objects_found': 2,
            'detection_time_ms': 300,
            'segmentation_time_ms': 500,
            'total_time_ms': 850
        }
        
        collector.record_inspection(result)
        
        assert len(collector.metrics_buffer) == 1
        assert collector.metrics_buffer[0].inspection_id == 'test-123'
    
    def test_flush_buffer(self, collector, tmp_path):
        """Test that _flush_buffer clears the metrics_buffer after writing."""
        from ussop.services.monitoring import InspectionMetrics
        from datetime import datetime

        # Add real InspectionMetrics items (asdict requires dataclass instances)
        for i in range(5):
            collector.metrics_buffer.append(InspectionMetrics(
                inspection_id=f"test-{i}",
                timestamp=datetime.now(timezone.utc).replace(tzinfo=None).isoformat(),
                station_id="s1",
                decision="pass",
                confidence=0.9,
                objects_found=0,
                detection_time_ms=100,
                segmentation_time_ms=200,
                total_time_ms=300,
            ))

        assert len(collector.metrics_buffer) == 5

        # Patch settings to write to tmp_path
        with patch('ussop.services.monitoring.settings') as mock_settings:
            mock_settings.DATA_DIR = tmp_path
            (tmp_path / 'logs').mkdir(exist_ok=True)
            collector._flush_buffer()

        assert len(collector.metrics_buffer) == 0


class TestAlertManager:
    """Test cases for AlertManager."""
    
    @pytest.fixture
    def alert_mgr(self):
        """Create alert manager."""
        return AlertManager()
    
    def test_get_alerts_empty(self, alert_mgr):
        """Test getting alerts when none exist."""
        alerts = alert_mgr.get_alerts()
        assert alerts == []
    
    def test_acknowledge_alert(self, alert_mgr):
        """Test acknowledging an alert."""
        from ussop.services.monitoring import Alert
        
        alert = Alert(
            id='alert-1',
            severity='warning',
            title='Test Alert',
            message='Test message',
            timestamp=datetime.now(timezone.utc).replace(tzinfo=None)
        )
        alert_mgr.alerts.append(alert)
        
        success = alert_mgr.acknowledge_alert('alert-1')
        
        assert success is True
        assert alert.acknowledged is True
    
    def test_acknowledge_nonexistent_alert(self, alert_mgr):
        """Test acknowledging non-existent alert."""
        success = alert_mgr.acknowledge_alert('nonexistent')
        assert success is False


class TestAuditLogger:
    """Test cases for AuditLogger."""
    
    @pytest.fixture
    def audit_logger(self, tmp_path):
        """Create audit logger with temp directory."""
        with patch('ussop.services.monitoring.settings') as mock_settings:
            mock_settings.DATA_DIR = tmp_path
            return AuditLogger()
    
    def test_log(self, audit_logger):
        """Test logging an audit event."""
        hash_value = audit_logger.log(
            action='inspection_completed',
            user='operator',
            resource_type='inspection',
            resource_id='test-123',
            details={'result': 'pass'}
        )
        
        assert hash_value is not None
        assert len(hash_value) == 64  # SHA-256 hex
    
    def test_verify_integrity_empty(self, audit_logger):
        """Test integrity verification with no logs."""
        result = audit_logger.verify_integrity()
        assert result is True
