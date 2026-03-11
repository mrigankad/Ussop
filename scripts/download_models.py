"""
Download NanoSAM ONNX models for CPU inference.

NanoSAM uses two ONNX models:
  1. resnet18_image_encoder.onnx  - lightweight image encoder (~45 MB)
  2. mobile_sam_mask_decoder.onnx - SAM mask decoder (~17 MB)

Models are sourced from the Hugging Face hub (community upload of NVIDIA NanoSAM).
"""

import os
import sys
import hashlib
import requests
from pathlib import Path
from tqdm import tqdm

MODELS_DIR = Path(__file__).parent / "models"

# Model sources - primary: Hugging Face, fallback: direct links
MODELS = {
    "resnet18_image_encoder.onnx": {
        # Community mirror of the original NVIDIA NanoSAM encoder
        # (official Google Drive link was restricted — see GitHub issue #41)
        "url": "https://github.com/johnnynunez/nanosam/raw/refs/heads/main/data/resnet18_image_encoder.onnx",
        "size_mb": 60,
    },
    "mobile_sam_mask_decoder.onnx": {
        # MobileSAM decoder — also available in the johnnynunez fork
        "url": "https://huggingface.co/dragonSwing/nanosam/resolve/main/mobile_sam_mask_decoder.onnx",
        "size_mb": 17,
    },
}


def download_file(url: str, dest: Path, desc: str = "") -> bool:
    """Download a file with a progress bar. Returns True on success."""
    try:
        response = requests.get(url, stream=True, timeout=30)
        response.raise_for_status()
        total = int(response.headers.get("content-length", 0))
        with open(dest, "wb") as f, tqdm(
            desc=desc,
            total=total,
            unit="B",
            unit_scale=True,
            unit_divisor=1024,
        ) as bar:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
                bar.update(len(chunk))
        return True
    except Exception as e:
        print(f"  Error downloading {url}: {e}")
        if dest.exists():
            dest.unlink()
        return False


def download_models(models_dir: Path = MODELS_DIR, force: bool = False) -> bool:
    """
    Download all required NanoSAM ONNX models.

    Args:
        models_dir: Directory to save models into.
        force:      Re-download even if file already exists.

    Returns:
        True if all models are present after the call.
    """
    models_dir.mkdir(parents=True, exist_ok=True)
    all_ok = True

    for filename, meta in MODELS.items():
        dest = models_dir / filename
        if dest.exists() and not force:
            print(f"[OK] {filename} already present ({dest})")
            continue

        print(f"[>>] Downloading {filename} (~{meta['size_mb']} MB) ...")
        ok = download_file(meta["url"], dest, desc=filename)
        if ok:
            print(f"    Saved to {dest}")
        else:
            print(f"    FAILED - see manual instructions below.")
            all_ok = False

    if not all_ok:
        _print_manual_instructions(models_dir)

    return all_ok


def _print_manual_instructions(models_dir: Path) -> None:
    print(
        f"""
Manual model download instructions
===================================
1. Visit https://huggingface.co/dragonSwing/nanosam/tree/main
2. Download:
     - resnet18_image_encoder.onnx
     - mobile_sam_mask_decoder.onnx
3. Place both files in:
     {models_dir}

Alternative — export from NanoSAM source:
  pip install git+https://github.com/NVIDIA-AI-IOT/nanosam
  python -m nanosam.tools.export_image_encoder --output {models_dir / "resnet18_image_encoder.onnx"}
  python -m nanosam.tools.export_mask_decoder  --output {models_dir / "mobile_sam_mask_decoder.onnx"}
"""
    )


def verify_models(models_dir: Path = MODELS_DIR) -> bool:
    """Return True if all model files exist and are non-empty."""
    ok = True
    for filename in MODELS:
        p = models_dir / filename
        if not p.exists() or p.stat().st_size == 0:
            print(f"[MISSING] {p}")
            ok = False
    return ok


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Download NanoSAM ONNX models")
    parser.add_argument(
        "--models-dir",
        default=str(MODELS_DIR),
        help="Directory to save models (default: ./models)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Re-download even if files already exist",
    )
    args = parser.parse_args()

    success = download_models(Path(args.models_dir), force=args.force)
    sys.exit(0 if success else 1)
