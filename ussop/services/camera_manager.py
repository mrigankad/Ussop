"""
Multi-Camera Manager for Ussop
Supports multiple camera types and concurrent capture
"""
import asyncio
from typing import Dict, List, Optional, Callable
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from config.settings import settings
from services.camera import CameraService


@dataclass
class CameraConfig:
    """Configuration for a single camera."""
    camera_id: str
    camera_type: str  # usb, gige, file, mock
    index: int = 0
    width: int = 1920
    height: int = 1080
    fps: int = 30
    enabled: bool = True
    trigger_mode: str = "software"  # software, hardware, continuous


class MultiCameraManager:
    """
    Manager for multiple cameras.
    
    Features:
    - Simultaneous capture from multiple cameras
    - Hardware trigger support
    - Continuous monitoring mode
    """
    
    def __init__(self):
        self.cameras: Dict[str, CameraService] = {}
        self.configs: Dict[str, CameraConfig] = {}
        self.trigger_callbacks: List[Callable] = []
        self._monitoring = False
        
        # Initialize default camera
        self.add_camera(CameraConfig(
            camera_id="default",
            camera_type=settings.CAMERA_TYPE,
            index=settings.CAMERA_INDEX,
            width=settings.CAMERA_WIDTH,
            height=settings.CAMERA_HEIGHT,
            fps=settings.CAMERA_FPS
        ))
    
    def add_camera(self, config: CameraConfig) -> bool:
        """Add a camera to the manager."""
        try:
            # Create camera service with specific config
            camera = CameraService()
            camera.camera_type = config.camera_type
            camera.camera_index = config.index
            
            self.cameras[config.camera_id] = camera
            self.configs[config.camera_id] = config
            
            print(f"[CameraManager] Added camera: {config.camera_id} ({config.camera_type})")
            return True
            
        except Exception as e:
            print(f"[CameraManager] Failed to add camera {config.camera_id}: {e}")
            return False
    
    def remove_camera(self, camera_id: str):
        """Remove a camera."""
        if camera_id in self.cameras:
            self.cameras[camera_id].release()
            del self.cameras[camera_id]
            del self.configs[camera_id]
            print(f"[CameraManager] Removed camera: {camera_id}")
    
    def capture_single(self, camera_id: str = "default") -> Optional[str]:
        """
        Capture from a single camera.
        
        Returns:
            Path to captured image
        """
        if camera_id not in self.cameras:
            print(f"[CameraManager] Camera not found: {camera_id}")
            return None
        
        camera = self.cameras[camera_id]
        return camera.capture()
    
    async def capture_all(self) -> Dict[str, Optional[str]]:
        """
        Capture from all enabled cameras simultaneously.
        
        Returns:
            Dict mapping camera_id to image path (or None if failed)
        """
        tasks = {}
        
        for camera_id, config in self.configs.items():
            if config.enabled and camera_id in self.cameras:
                # Run capture in thread pool
                loop = asyncio.get_event_loop()
                camera = self.cameras[camera_id]
                task = loop.run_in_executor(None, camera.capture)
                tasks[camera_id] = task
        
        # Wait for all captures
        results = {}
        for camera_id, task in tasks.items():
            try:
                results[camera_id] = await task
            except Exception as e:
                print(f"[CameraManager] Capture failed for {camera_id}: {e}")
                results[camera_id] = None
        
        return results
    
    def start_monitoring(self, callback: Callable[[str, str], None]):
        """
        Start continuous monitoring mode.
        
        Args:
            callback: Function called with (camera_id, image_path) on each capture
        """
        self._monitoring = True
        self.trigger_callbacks.append(callback)
        
        # Start monitoring task
        asyncio.create_task(self._monitoring_loop())
    
    async def _monitoring_loop(self):
        """Background monitoring loop."""
        while self._monitoring:
            try:
                # Capture from all cameras
                results = await self.capture_all()
                
                # Trigger callbacks
                for camera_id, image_path in results.items():
                    if image_path:
                        for callback in self.trigger_callbacks:
                            try:
                                callback(camera_id, image_path)
                            except Exception as e:
                                print(f"[CameraManager] Callback error: {e}")
                
                # Wait before next capture
                await asyncio.sleep(1.0)  # 1 FPS for monitoring
                
            except Exception as e:
                print(f"[CameraManager] Monitoring error: {e}")
                await asyncio.sleep(5)
    
    def stop_monitoring(self):
        """Stop continuous monitoring."""
        self._monitoring = False
        self.trigger_callbacks.clear()
    
    def get_camera_list(self) -> List[Dict]:
        """Get list of configured cameras."""
        return [
            {
                "camera_id": cid,
                "type": config.camera_type,
                "enabled": config.enabled,
                "resolution": f"{config.width}x{config.height}",
                "fps": config.fps,
                "trigger_mode": config.trigger_mode
            }
            for cid, config in self.configs.items()
        ]
    
    def update_camera_config(self, camera_id: str, updates: Dict) -> bool:
        """Update camera configuration."""
        if camera_id not in self.configs:
            return False
        
        config = self.configs[camera_id]
        
        # Update allowed fields
        if "enabled" in updates:
            config.enabled = updates["enabled"]
        if "trigger_mode" in updates:
            config.trigger_mode = updates["trigger_mode"]
        if "fps" in updates:
            config.fps = updates["fps"]
        
        return True
    
    def release_all(self):
        """Release all cameras."""
        for camera in self.cameras.values():
            camera.release()
        self.cameras.clear()
        self.configs.clear()


# Singleton instance
_camera_manager: Optional[MultiCameraManager] = None


def get_camera_manager() -> MultiCameraManager:
    """Get camera manager singleton."""
    global _camera_manager
    if _camera_manager is None:
        _camera_manager = MultiCameraManager()
    return _camera_manager
