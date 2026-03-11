"""
Setup script for Ussop
Run: python setup.py
"""
import os
import sys
import subprocess
from pathlib import Path

def check_python_version():
    """Check Python version."""
    print("Checking Python version...")
    version = sys.version_info
    if version.major < 3 or (version.major == 3 and version.minor < 11):
        print("❌ Python 3.11+ required")
        return False
    print(f"✅ Python {version.major}.{version.minor}.{version.micro}")
    return True

def check_models():
    """Check if models are downloaded."""
    print("\nChecking for NanoSAM models...")
    
    # Check both locations
    model_paths = [
        Path("../models"),
        Path("models"),
    ]
    
    encoder = "resnet18_image_encoder.onnx"
    decoder = "mobile_sam_mask_decoder.onnx"
    
    for models_dir in model_paths:
        enc_path = models_dir / encoder
        dec_path = models_dir / decoder
        
        if enc_path.exists() and dec_path.exists():
            print(f"✅ Models found in {models_dir}")
            return True
    
    print("❌ Models not found!")
    print("   Run from project root: python download_models.py")
    return False

def install_dependencies():
    """Install Python dependencies."""
    print("\nInstalling dependencies...")
    try:
        subprocess.run([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"], 
                      check=True, capture_output=True)
        print("✅ Dependencies installed")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to install dependencies: {e}")
        return False

def create_directories():
    """Create required directories."""
    print("\nCreating directories...")
    
    dirs = [
        "data/images",
        "data/masks",
        "data/db",
        "data/logs",
        "data/audit",
    ]
    
    for d in dirs:
        Path(d).mkdir(parents=True, exist_ok=True)
    
    print("✅ Directories created")

def init_database():
    """Initialize database."""
    print("\nInitializing database...")
    try:
        from config.settings import ensure_directories
        from models.database import init_database
        
        ensure_directories()
        init_database()
        print("✅ Database initialized")
        return True
    except Exception as e:
        print(f"❌ Failed to initialize database: {e}")
        return False

def main():
    """Run setup."""
    print("""
╔═══════════════════════════════════════════════════════════╗
║                                                           ║
║   🎯 USSOP - Setup Wizard                                ║
║                                                           ║
╚═══════════════════════════════════════════════════════════╝
""")
    
    # Check Python version
    if not check_python_version():
        sys.exit(1)
    
    # Check models
    if not check_models():
        response = input("\nDownload models now? (y/n): ")
        if response.lower() == 'y':
            subprocess.run([sys.executable, "../download_models.py"])
        else:
            print("Please download models before running Ussop")
            sys.exit(1)
    
    # Install dependencies
    response = input("\nInstall dependencies? (y/n): ")
    if response.lower() == 'y':
        if not install_dependencies():
            sys.exit(1)
    
    # Create directories
    create_directories()
    
    # Init database
    if not init_database():
        sys.exit(1)
    
    print("""
╔═══════════════════════════════════════════════════════════╗
║                                                           ║
║   ✅ Setup Complete!                                     ║
║                                                           ║
║   Run: python run.py                                     ║
║   Then: http://localhost:8080                            ║
║                                                           ║
╚═══════════════════════════════════════════════════════════╝
""")

if __name__ == "__main__":
    main()
