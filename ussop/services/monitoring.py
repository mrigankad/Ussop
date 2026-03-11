"""
Monitoring and Observability Service for Ussop
Metrics, logging, and alerting
"""
import time
import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta, timezone
from dataclasses import dataclass, asdict
from functools import wraps

from sqlalchemy import func
from sqlalchemy.orm import Session

from config.settings import settings
from models.database import Inspection, Decision


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(settings.DATA_DIR / 'logs' / 'ussop.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('ussop')


@dataclass
class InspectionMetrics:
    """Metrics for a single inspection."""
    inspection_id: str
    timestamp: datetime
    station_id: str
    decision: str
    confidence: float
    objects_found: int
    detection_time_ms: float
    segmentation_time_ms: float
    total_time_ms: float


@dataclass
class Alert:
    """Alert definition."""
    id: str
    severity: str  # info, warning, critical
    title: str
    message: str
    timestamp: datetime
    acknowledged: bool = False


class MetricsCollector:
    """Collect and aggregate system metrics."""
    
    def __init__(self):
        self.metrics_buffer: List[InspectionMetrics] = []
        self.buffer_size = 100
        self._ensure_log_dir()
    
    def _ensure_log_dir(self):
        """Ensure log directory exists."""
        log_dir = settings.DATA_DIR / 'logs'
        log_dir.mkdir(parents=True, exist_ok=True)
    
    def record_inspection(self, result: Dict[str, Any]):
        """Record metrics from an inspection result."""
        metric = InspectionMetrics(
            inspection_id=result['id'],
            timestamp=datetime.fromisoformat(result['timestamp']),
            station_id=result.get('station_id', 'default'),
            decision=result.get('decision', 'unknown'),
            confidence=result.get('confidence', 0),
            objects_found=result.get('objects_found', 0),
            detection_time_ms=result.get('detection_time_ms', 0),
            segmentation_time_ms=result.get('segmentation_time_ms', 0),
            total_time_ms=result.get('total_time_ms', 0)
        )
        
        self.metrics_buffer.append(metric)
        
        # Flush buffer if full
        if len(self.metrics_buffer) >= self.buffer_size:
            self._flush_buffer()
        
        # Log to structured log
        logger.info(f"Inspection completed: {metric.inspection_id}", extra={
            'metric': asdict(metric)
        })
    
    def _flush_buffer(self):
        """Write buffered metrics to persistent storage."""
        if not self.metrics_buffer:
            return
        
        # Write to JSON Lines file
        log_file = settings.DATA_DIR / 'logs' / f"metrics_{datetime.now().strftime('%Y%m')}.jsonl"
        
        with open(log_file, 'a') as f:
            for metric in self.metrics_buffer:
                f.write(json.dumps(asdict(metric), default=str) + '\n')
        
        self.metrics_buffer = []
    
    def get_system_health(self, db: Session) -> Dict[str, Any]:
        """Get overall system health status."""
        # Check recent error rate
        since = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(hours=1)
        
        recent = db.query(Inspection).filter(Inspection.timestamp >= since).count()
        errors = db.query(Inspection).filter(
            Inspection.timestamp >= since,
            Inspection.decision == None
        ).count()
        
        error_rate = errors / recent if recent > 0 else 0
        
        # Determine health status
        if error_rate > 0.1:
            status = 'critical'
            message = f'High error rate: {error_rate:.1%}'
        elif error_rate > 0.05:
            status = 'warning'
            message = f'Elevated error rate: {error_rate:.1%}'
        else:
            status = 'healthy'
            message = 'System operating normally'
        
        return {
            'status': status,
            'message': message,
            'error_rate': error_rate,
            'inspections_last_hour': recent,
            'timestamp': datetime.now(timezone.utc).replace(tzinfo=None).isoformat()
        }
    
    def get_performance_metrics(self, db: Session, hours: int = 24) -> Dict[str, Any]:
        """Get performance metrics."""
        since = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(hours=hours)
        
        # Timing statistics
        timing_stats = db.query(
            func.avg(Inspection.total_time_ms),
            func.min(Inspection.total_time_ms),
            func.max(Inspection.total_time_ms),
            func.percentile_cont(0.95).within_group(Inspection.total_time_ms)
        ).filter(Inspection.timestamp >= since).first()
        
        # Throughput
        total = db.query(Inspection).filter(Inspection.timestamp >= since).count()
        throughput = total / hours  # inspections per hour
        
        return {
            'period_hours': hours,
            'avg_time_ms': round(timing_stats[0] or 0, 2),
            'min_time_ms': round(timing_stats[1] or 0, 2),
            'max_time_ms': round(timing_stats[2] or 0, 2),
            'p95_time_ms': round(timing_stats[3] or 0, 2),
            'throughput_per_hour': round(throughput, 2),
            'total_inspections': total
        }


class AlertManager:
    """Manage system alerts."""
    
    def __init__(self):
        self.alerts: List[Alert] = []
        self.alert_rules = [
            {
                'name': 'high_defect_rate',
                'condition': lambda stats: stats.get('fail_rate', 0) > 0.2,
                'severity': 'warning',
                'title': 'High Defect Rate',
                'message': 'Defect rate exceeds 20%'
            },
            {
                'name': 'high_latency',
                'condition': lambda stats: stats.get('avg_time_ms', 0) > 2000,
                'severity': 'warning',
                'title': 'High Inspection Latency',
                'message': 'Average inspection time > 2s'
            },
            {
                'name': 'system_error',
                'condition': lambda stats: stats.get('error_rate', 0) > 0.1,
                'severity': 'critical',
                'title': 'System Errors',
                'message': 'Error rate exceeds 10%'
            }
        ]
    
    def check_alerts(self, db: Session) -> List[Alert]:
        """Check for alert conditions and create alerts."""
        from ussop.services.inspector import InspectionService
        
        service = InspectionService()
        stats = service.get_statistics(db, hours=1)
        
        new_alerts = []
        for rule in self.alert_rules:
            if rule['condition'](stats):
                # Check if alert already exists
                exists = any(
                    a.title == rule['title'] and not a.acknowledged
                    for a in self.alerts
                )
                
                if not exists:
                    alert = Alert(
                        id=str(time.time()),
                        severity=rule['severity'],
                        title=rule['title'],
                        message=rule['message'],
                        timestamp=datetime.now(timezone.utc).replace(tzinfo=None)
                    )
                    self.alerts.append(alert)
                    new_alerts.append(alert)
                    
                    logger.warning(f"Alert triggered: {alert.title}")
        
        return new_alerts
    
    def get_alerts(
        self,
        severity: Optional[str] = None,
        acknowledged: Optional[bool] = None
    ) -> List[Alert]:
        """Get alerts with optional filtering."""
        alerts = self.alerts
        
        if severity:
            alerts = [a for a in alerts if a.severity == severity]
        if acknowledged is not None:
            alerts = [a for a in alerts if a.acknowledged == acknowledged]
        
        return sorted(alerts, key=lambda a: a.timestamp, reverse=True)
    
    def acknowledge_alert(self, alert_id: str) -> bool:
        """Acknowledge an alert."""
        for alert in self.alerts:
            if alert.id == alert_id:
                alert.acknowledged = True
                return True
        return False
    
    def clear_old_alerts(self, hours: int = 24):
        """Clear alerts older than specified hours."""
        cutoff = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(hours=hours)
        self.alerts = [
            a for a in self.alerts
            if a.timestamp > cutoff or not a.acknowledged
        ]


class AuditLogger:
    """
    Tamper-proof audit logging for compliance.
    
    Features:
    - Immutable log entries
    - Chain hashing for integrity
    - Export for audits
    """
    
    def __init__(self):
        self.audit_dir = settings.DATA_DIR / 'audit'
        self.audit_dir.mkdir(parents=True, exist_ok=True)
        self.current_log = self.audit_dir / f"audit_{datetime.now().strftime('%Y%m')}.log"
        self.last_hash = self._load_last_hash()
    
    def _load_last_hash(self) -> str:
        """Load last hash from file for chain integrity."""
        if self.current_log.exists():
            try:
                with open(self.current_log, 'r') as f:
                    lines = f.readlines()
                    if lines:
                        last_entry = json.loads(lines[-1])
                        return last_entry.get('hash', '0' * 64)
            except:
                pass
        return '0' * 64
    
    def _compute_hash(self, entry: Dict[str, Any]) -> str:
        """Compute SHA-256 hash of entry."""
        import hashlib
        data = json.dumps(entry, sort_keys=True, default=str)
        return hashlib.sha256(data.encode()).hexdigest()
    
    def log(
        self,
        action: str,
        user: str,
        resource_type: str,
        resource_id: str,
        details: Optional[Dict] = None
    ) -> str:
        """
        Log an audit event.
        
        Returns:
            Hash of the log entry
        """
        entry = {
            'timestamp': datetime.now(timezone.utc).replace(tzinfo=None).isoformat(),
            'action': action,
            'user': user,
            'resource_type': resource_type,
            'resource_id': resource_id,
            'details': details or {},
            'previous_hash': self.last_hash
        }
        
        # Compute hash including previous hash for chain
        entry['hash'] = self._compute_hash(entry)
        self.last_hash = entry['hash']
        
        # Append to log
        with open(self.current_log, 'a') as f:
            f.write(json.dumps(entry, default=str) + '\n')
        
        return entry['hash']
    
    def verify_integrity(self) -> bool:
        """Verify the integrity of the audit log."""
        if not self.current_log.exists():
            return True
        
        previous_hash = '0' * 64
        
        with open(self.current_log, 'r') as f:
            for line in f:
                entry = json.loads(line)
                
                # Check previous hash matches
                if entry.get('previous_hash') != previous_hash:
                    return False
                
                # Recompute and verify hash
                entry_copy = entry.copy()
                stored_hash = entry_copy.pop('hash')
                computed_hash = self._compute_hash(entry_copy)
                
                if stored_hash != computed_hash:
                    return False
                
                previous_hash = stored_hash
        
        return True
    
    def export_audit_log(
        self,
        start_date: datetime,
        end_date: datetime,
        output_path: Path
    ) -> Path:
        """Export audit log for compliance review."""
        entries = []
        
        # Collect all log files in date range
        for log_file in self.audit_dir.glob('audit_*.log'):
            with open(log_file, 'r') as f:
                for line in f:
                    entry = json.loads(line)
                    entry_time = datetime.fromisoformat(entry['timestamp'])
                    
                    if start_date <= entry_time <= end_date:
                        entries.append(entry)
        
        # Sort by timestamp
        entries.sort(key=lambda e: e['timestamp'])
        
        # Export
        with open(output_path, 'w') as f:
            json.dump({
                'export_date': datetime.now(timezone.utc).replace(tzinfo=None).isoformat(),
                'start_date': start_date.isoformat(),
                'end_date': end_date.isoformat(),
                'entry_count': len(entries),
                'entries': entries,
                'integrity_verified': self.verify_integrity()
            }, f, indent=2, default=str)
        
        return output_path


# Decorator for timing function execution
def timed(metric_name: str):
    """Decorator to time function execution."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            start = time.perf_counter()
            try:
                result = func(*args, **kwargs)
                duration = time.perf_counter() - start
                logger.debug(f"{metric_name} completed in {duration:.3f}s")
                return result
            except Exception as e:
                duration = time.perf_counter() - start
                logger.error(f"{metric_name} failed after {duration:.3f}s: {e}")
                raise
        return wrapper
    return decorator


# Singleton instances
_metrics_collector: Optional[MetricsCollector] = None
_alert_manager: Optional[AlertManager] = None
_audit_logger: Optional[AuditLogger] = None


def get_metrics_collector() -> MetricsCollector:
    """Get metrics collector singleton."""
    global _metrics_collector
    if _metrics_collector is None:
        _metrics_collector = MetricsCollector()
    return _metrics_collector


def get_alert_manager() -> AlertManager:
    """Get alert manager singleton."""
    global _alert_manager
    if _alert_manager is None:
        _alert_manager = AlertManager()
    return _alert_manager


def get_audit_logger() -> AuditLogger:
    """Get audit logger singleton."""
    global _audit_logger
    if _audit_logger is None:
        _audit_logger = AuditLogger()
    return _audit_logger
