"""
Camera Service - Image acquisition
"""
import time
import uuid
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional

import cv2
import numpy as np
from PIL import Image

from config.settings import settings


class CameraService:
    """Handle camera operations."""
    
    def __init__(self):
        self.camera_type = settings.CAMERA_TYPE
        self.cap = None
        
        if self.camera_type == "usb":
            self._init_usb_camera()
    
    def _init_usb_camera(self):
        """Initialize USB camera."""
        self.cap = cv2.VideoCapture(settings.CAMERA_INDEX)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, settings.CAMERA_WIDTH)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, settings.CAMERA_HEIGHT)
        self.cap.set(cv2.CAP_PROP_FPS, settings.CAMERA_FPS)
    
    def capture(self, save_dir: Optional[Path] = None) -> Optional[str]:
        """
        Capture an image from camera.
        
        Returns path to saved image.
        """
        if self.camera_type == "file":
            # For testing - use demo image generation
            return self._generate_test_image(save_dir)
        
        elif self.camera_type == "mock":
            # Return a synthetic test image
            return self._generate_test_image(save_dir)
        
        elif self.camera_type == "usb":
            if self.cap is None:
                self._init_usb_camera()
            
            ret, frame = self.cap.read()
            if not ret:
                print("[Camera] Failed to capture from USB camera")
                return None
            
            # Save frame
            save_dir = save_dir or settings.IMAGES_DIR / "captures"
            save_dir.mkdir(parents=True, exist_ok=True)
            
            timestamp = datetime.now(timezone.utc).replace(tzinfo=None).strftime("%Y%m%d_%H%M%S_%f")
            filename = f"capture_{timestamp}.jpg"
            filepath = save_dir / filename
            
            cv2.imwrite(str(filepath), frame)
            return str(filepath)
        
        else:
            print(f"[Camera] Unknown camera type: {self.camera_type}")
            return None
    
    def _generate_test_image(self, save_dir: Optional[Path] = None) -> str:
        """Generate a synthetic test image."""
        from PIL import Image, ImageDraw
        
        w, h = 800, 600
        img = Image.new("RGB", (w, h), (30, 40, 50))
        draw = ImageDraw.Draw(img)
        
        # Simple gradient sky
        for y in range(h):
            v = int(80 + 100 * y / h)
            draw.line([(0, y), (w, y)], fill=(v, v + 20, v + 60))
        
        # Coloured blocks (simulating objects)
        draw.rectangle([50, 80, 250, 300], fill=(200, 60, 60), outline=(255, 255, 255), width=3)
        draw.rectangle([300, 120, 550, 380], fill=(60, 180, 60), outline=(255, 255, 255), width=3)
        draw.ellipse([580, 60, 760, 280], fill=(60, 80, 210), outline=(255, 255, 255), width=3)
        draw.rectangle([100, 380, 700, 560], fill=(180, 140, 40), outline=(255, 255, 255), width=3)
        
        # Save
        save_dir = save_dir or settings.IMAGES_DIR / "captures"
        save_dir.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now(timezone.utc).replace(tzinfo=None).strftime("%Y%m%d_%H%M%S_%f")
        filename = f"test_{timestamp}.jpg"
        filepath = save_dir / filename
        
        img.save(str(filepath))
        return str(filepath)
    
    def preview(self) -> Optional[np.ndarray]:
        """Get a preview frame without saving."""
        if self.camera_type == "usb" and self.cap:
            ret, frame = self.cap.read()
            if ret:
                return frame
        return None
    
    def release(self):
        """Release camera resources."""
        if self.cap:
            self.cap.release()
            self.cap = None
    
    def __del__(self):
        self.release()
