"""
Ussop Configuration Settings
"""
import os
from pathlib import Path
from typing import List, Optional
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings with environment variable support."""
    
    # App
    APP_NAME: str = "Ussop"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    
    # Paths
    BASE_DIR: Path = Path(__file__).parent.parent
    DATA_DIR: Path = BASE_DIR / "data"
    MODELS_DIR: Path = DATA_DIR / "models"
    IMAGES_DIR: Path = DATA_DIR / "images"
    MASKS_DIR: Path = DATA_DIR / "masks"
    
    # API
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8080
    API_WORKERS: int = 1
    
    # Database (absolute path resolved in ensure_directories)
    DATABASE_URL: str = ""
    
    # Redis (optional, for caching)
    REDIS_URL: Optional[str] = None
    
    # Security
    SECRET_KEY: str = "your-secret-key-change-in-production"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # Model paths - set via env or resolved at runtime from MODELS_DIR
    ENCODER_PATH: str = ""
    DECODER_PATH: str = ""
    
    # Inference
    DETECTOR_BACKBONE: str = "mobilenet"  # or "resnet50"
    CONFIDENCE_THRESHOLD: float = 0.5
    MAX_DETECTIONS: int = 20
    ONNX_THREADS: int = 0  # 0 = auto
    
    # Camera
    CAMERA_TYPE: str = "file"  # file, usb, gige, mock
    CAMERA_INDEX: int = 0
    CAMERA_WIDTH: int = 1920
    CAMERA_HEIGHT: int = 1080
    CAMERA_FPS: int = 30
    
    # Modbus (optional)
    MODBUS_ENABLED: bool = False
    MODBUS_HOST: str = "0.0.0.0"
    MODBUS_PORT: int = 502
    
    # MQTT (optional)
    MQTT_ENABLED: bool = False
    MQTT_BROKER: str = "localhost"
    MQTT_PORT: int = 1883
    
    # Storage
    IMAGE_RETENTION_DAYS: int = 90
    MAX_STORAGE_GB: float = 100.0
    
    # Active Learning
    ACTIVE_LEARNING_ENABLED: bool = True
    UNCERTAINTY_THRESHOLD_LOW: float = 0.3
    UNCERTAINTY_THRESHOLD_HIGH: float = 0.7

    # ── OPC-UA (optional) ────────────────────────────────────────────────────
    OPCUA_ENABLED: bool = False
    OPCUA_HOST: str = "0.0.0.0"
    OPCUA_PORT: int = 4840       # standard OPC-UA port

    # ── OpenVINO / NPU acceleration (optional) ───────────────────────────────
    # Device: AUTO | CPU | GPU | NPU
    OPENVINO_DEVICE: str = "AUTO"
    OPENVINO_ENABLED: bool = False   # set True to activate at startup

    # ── VLM (Vision Language Model) ───────────────────────────────────────────
    VLM_ENABLED: bool = False
    # Backend: local | anthropic | openai | google | groq | nim
    VLM_BACKEND: str = "local"

    # Local model name: moondream2 | internvl2 | qwen2vl | phi35vision | llava | paligemma
    VLM_LOCAL_MODEL: str = "moondream2"
    # Leave empty to auto-download into MODELS_DIR/vlm/
    VLM_LOCAL_MODEL_PATH: str = ""

    # API keys — set whichever backend you use in .env
    ANTHROPIC_API_KEY: str = ""
    OPENAI_API_KEY: str = ""
    GOOGLE_API_KEY: str = ""
    GROQ_API_KEY: str = ""

    # NVIDIA NIM
    NVIDIA_NIM_API_KEY: str = ""
    NVIDIA_NIM_BASE_URL: str = "https://integrate.api.nvidia.com/v1"
    NVIDIA_NIM_MODEL: str = "microsoft/phi-3-vision-128k-instruct"

    # VLM behaviour
    VLM_MAX_TOKENS: int = 200
    VLM_TIMEOUT_S: float = 10.0
    # If True, inspection continues normally when VLM errors — just no description
    VLM_FALLBACK_ON_ERROR: bool = True

    model_config = {"env_file": ".env", "case_sensitive": True}


# Global settings instance
settings = Settings()

# Resolve absolute paths immediately (before any module uses them)
_db_path = settings.DATA_DIR / "db" / "ussop.db"
_db_path.parent.mkdir(parents=True, exist_ok=True)
if not settings.DATABASE_URL:
    settings.DATABASE_URL = f"sqlite:///{_db_path}"
if not settings.ENCODER_PATH:
    settings.ENCODER_PATH = str(settings.MODELS_DIR / "resnet18_image_encoder.onnx")
if not settings.DECODER_PATH:
    settings.DECODER_PATH = str(settings.MODELS_DIR / "mobile_sam_mask_decoder.onnx")


def ensure_directories():
    """Create necessary directories if they don't exist."""
    dirs = [
        settings.DATA_DIR,
        settings.MODELS_DIR,
        settings.IMAGES_DIR,
        settings.MASKS_DIR,
        settings.DATA_DIR / "db",
    ]
    for d in dirs:
        d.mkdir(parents=True, exist_ok=True)

    # Paths are already resolved at module load time above
