"""
MQTT Client for IoT Integration
Publishes inspection results to MQTT broker for IoT platforms
"""
import json
import asyncio
from typing import Optional, Dict, Any, Callable
from datetime import datetime

try:
    import paho.mqtt.client as mqtt
    MQTT_AVAILABLE = True
except ImportError:
    MQTT_AVAILABLE = False
    print("[MQTT] paho-mqtt not installed. Run: pip install paho-mqtt")

from ussop.config.settings import settings


class UssopMQTTClient:
    """
    MQTT client for publishing inspection data.
    
    Topic Structure:
    - ussop/{station_id}/status       - System status (online/offline)
    - ussop/{station_id}/inspection   - Inspection results
    - ussop/{station_id}/alert        - Alerts and warnings
    - ussop/{station_id}/command      - Incoming commands (subscribe)
    
    Message Format (JSON):
    {
        "timestamp": "2026-03-15T10:30:00Z",
        "station_id": "line1_station2",
        "type": "inspection",
        "data": { ... }
    }
    """
    
    def __init__(self):
        self.client: Optional[mqtt.Client] = None
        self.connected = False
        self.station_id = "default"
        
        if not MQTT_AVAILABLE:
            raise ImportError("paho-mqtt not installed")
        
        if not settings.MQTT_ENABLED:
            print("[MQTT] MQTT disabled in settings")
            return
        
        self._init_client()
    
    def _init_client(self):
        """Initialize MQTT client."""
        self.client = mqtt.Client(client_id=f"ussop_{self.station_id}")
        
        # Set callbacks
        self.client.on_connect = self._on_connect
        self.client.on_disconnect = self._on_disconnect
        self.client.on_message = self._on_message
        
        # Set will (last testament)
        self.client.will_set(
            topic=f"ussop/{self.station_id}/status",
            payload=json.dumps({
                "timestamp": datetime.utcnow().isoformat(),
                "station_id": self.station_id,
                "status": "offline",
                "reason": "unexpected_disconnect"
            }),
            qos=1,
            retain=True
        )
        
        # Connect
        try:
            self.client.connect(
                settings.MQTT_BROKER,
                settings.MQTT_PORT,
                keepalive=60
            )
            self.client.loop_start()
        except Exception as e:
            print(f"[MQTT] Failed to connect: {e}")
    
    def _on_connect(self, client, userdata, flags, rc):
        """Callback when connected to broker."""
        if rc == 0:
            self.connected = True
            print(f"[MQTT] Connected to {settings.MQTT_BROKER}")
            
            # Publish online status
            self.publish_status("online")
            
            # Subscribe to command topic
            self.client.subscribe(f"ussop/{self.station_id}/command")
            print(f"[MQTT] Subscribed to ussop/{self.station_id}/command")
        else:
            print(f"[MQTT] Connection failed with code {rc}")
    
    def _on_disconnect(self, client, userdata, rc):
        """Callback when disconnected."""
        self.connected = False
        if rc != 0:
            print(f"[MQTT] Unexpected disconnection (rc={rc}), will retry")
    
    def _on_message(self, client, userdata, msg):
        """Callback for incoming messages."""
        try:
            topic = msg.topic
            payload = json.loads(msg.payload.decode())
            
            print(f"[MQTT] Received command on {topic}: {payload}")
            
            # Handle commands
            if topic.endswith('/command'):
                self._handle_command(payload)
                
        except Exception as e:
            print(f"[MQTT] Error handling message: {e}")
    
    def _handle_command(self, payload: Dict[str, Any]):
        """Handle incoming command."""
        command = payload.get('command')
        
        if command == 'inspect':
            # Trigger inspection
            print("[MQTT] Triggering inspection from command")
            # Would trigger inspection via callback
        elif command == 'reload_config':
            print("[MQTT] Reloading configuration")
            # Would reload config
        elif command == 'get_status':
            self.publish_status("online")
        else:
            print(f"[MQTT] Unknown command: {command}")
    
    def publish_status(self, status: str, details: Optional[Dict] = None):
        """Publish system status."""
        if not self.connected or not self.client:
            return
        
        message = {
            "timestamp": datetime.utcnow().isoformat(),
            "station_id": self.station_id,
            "type": "status",
            "status": status,
            "details": details or {}
        }
        
        self.client.publish(
            topic=f"ussop/{self.station_id}/status",
            payload=json.dumps(message),
            qos=1,
            retain=True
        )
    
    def publish_inspection(self, result: Dict[str, Any]):
        """Publish inspection result."""
        if not self.connected or not self.client:
            return
        
        station_id = result.get('station_id', self.station_id)
        
        message = {
            "timestamp": result.get('timestamp', datetime.utcnow().isoformat()),
            "station_id": station_id,
            "type": "inspection",
            "data": {
                "inspection_id": result.get('id'),
                "part_id": result.get('part_id'),
                "decision": result.get('decision'),
                "confidence": result.get('confidence'),
                "objects_found": result.get('objects_found'),
                "detection_time_ms": result.get('detection_time_ms'),
                "segmentation_time_ms": result.get('segmentation_time_ms'),
                "total_time_ms": result.get('total_time_ms'),
                "detections": [
                    {
                        "class_name": d.get('class_name'),
                        "confidence": d.get('confidence'),
                        "box": d.get('box')
                    }
                    for d in result.get('detections', [])
                ]
            }
        }
        
        self.client.publish(
            topic=f"ussop/{station_id}/inspection",
            payload=json.dumps(message),
            qos=1
        )
        
        print(f"[MQTT] Published inspection {result.get('id')}")
    
    def publish_alert(self, alert: Dict[str, Any]):
        """Publish alert/warning."""
        if not self.connected or not self.client:
            return
        
        station_id = alert.get('station_id', self.station_id)
        
        message = {
            "timestamp": datetime.utcnow().isoformat(),
            "station_id": station_id,
            "type": "alert",
            "severity": alert.get('severity', 'info'),
            "title": alert.get('title'),
            "message": alert.get('message')
        }
        
        self.client.publish(
            topic=f"ussop/{station_id}/alert",
            payload=json.dumps(message),
            qos=1
        )
    
    def disconnect(self):
        """Disconnect from broker."""
        if self.client:
            # Publish offline status
            self.publish_status("offline", {"reason": "shutdown"})
            
            self.client.loop_stop()
            self.client.disconnect()
            self.connected = False
            print("[MQTT] Disconnected")


# Singleton instance
_mqtt_client: Optional[UssopMQTTClient] = None


def get_mqtt_client() -> Optional[UssopMQTTClient]:
    """Get MQTT client singleton."""
    global _mqtt_client
    if _mqtt_client is None and MQTT_AVAILABLE and settings.MQTT_ENABLED:
        try:
            _mqtt_client = UssopMQTTClient()
        except Exception as e:
            print(f"[MQTT] Failed to initialize: {e}")
    return _mqtt_client
