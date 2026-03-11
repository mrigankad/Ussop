"""
Demo script — generates a sample image and runs the full pipeline.

Run:
    python demo.py

Or point it at your own image:
    python demo.py --input path/to/your_image.jpg
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import requests
from PIL import Image, ImageDraw


# ── quick sanity-check before importing heavy modules ─────────────────
def _check_models() -> bool:
    enc = Path("models/resnet18_image_encoder.onnx")
    dec = Path("models/mobile_sam_mask_decoder.onnx")
    if not enc.exists() or not dec.exists():
        print(
            "[Demo] NanoSAM ONNX models not found.\n"
            "       Run first:  python download_models.py\n"
        )
        return False
    return True


def _try_download(url: str, save_path: Path) -> bool:
    """Try to download from url. Returns True on success."""
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        r = requests.get(url, stream=True, timeout=15, headers=headers)
        r.raise_for_status()
        save_path.parent.mkdir(parents=True, exist_ok=True)
        with open(save_path, "wb") as f:
            for chunk in r.iter_content(8192):
                f.write(chunk)
        return True
    except Exception:
        return False


def _make_synthetic_image(save_path: Path) -> None:
    """
    Generate a colourful test image with distinct regions so Faster R-CNN
    has objects to detect (the model is pre-trained on COCO, so simple
    geometric shapes won't be detected — this image is a fallback for
    verifying the pipeline mechanics).
    """
    w, h = 800, 600
    img = Image.new("RGB", (w, h), (30, 40, 50))
    draw = ImageDraw.Draw(img)

    # Simple gradient sky
    for y in range(h):
        v = int(80 + 100 * y / h)
        draw.line([(0, y), (w, y)], fill=(v, v + 20, v + 60))

    # Coloured blocks
    draw.rectangle([50,  80, 250, 300], fill=(200, 60, 60),  outline=(255, 255, 255), width=3)
    draw.rectangle([300, 120, 550, 380], fill=(60, 180, 60), outline=(255, 255, 255), width=3)
    draw.ellipse( [580,  60, 760, 280], fill=(60, 80, 210),  outline=(255, 255, 255), width=3)
    draw.rectangle([100, 380, 700, 560], fill=(180, 140, 40), outline=(255, 255, 255), width=3)

    save_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(str(save_path))
    print(f"[Demo] Generated synthetic test image: {save_path}")


def get_sample_image(save_path: Path) -> Path:
    """Return a sample image: download if possible, otherwise synthesize."""
    if save_path.exists():
        print(f"[Demo] Using existing image: {save_path}")
        return save_path

    # Try COCO val image then Flickr fallbacks
    candidate_urls = [
        "http://images.cocodataset.org/val2017/000000039769.jpg",   # cats on a sofa
        "https://farm1.staticflickr.com/56/188397090_b3ae84f4e2_z.jpg",
        "https://farm4.staticflickr.com/3752/9684880629_de05b7d51a_z.jpg",
    ]
    print("[Demo] Attempting to download a sample image ...")
    for url in candidate_urls:
        if _try_download(url, save_path):
            print(f"[Demo] Saved to {save_path}")
            return save_path

    # Fallback: synthesize
    print("[Demo] Download failed; generating a synthetic test image.")
    _make_synthetic_image(save_path)
    return save_path


def main() -> None:
    parser = argparse.ArgumentParser(description="NanoSAM pipeline demo")
    parser.add_argument("--input",  "-i", default=None, help="Input image (optional)")
    parser.add_argument("--output", "-o", default="output/demo_result.jpg")
    parser.add_argument(
        "--backbone", choices=["resnet50", "mobilenet"], default="mobilenet",
        help="'mobilenet' is faster on CPU; 'resnet50' is more accurate",
    )
    parser.add_argument("--threshold", "-t", type=float, default=0.5)
    parser.add_argument("--show", action="store_true")
    args = parser.parse_args()

    if not _check_models():
        sys.exit(1)

    # Resolve input image
    if args.input:
        img_path = Path(args.input)
        if not img_path.exists():
            print(f"[Demo] File not found: {img_path}")
            sys.exit(1)
    else:
        img_path = get_sample_image(Path("assets/sample.jpg"))

    # Import pipeline only after confirming models exist
    from pipeline import NanoSAMPipeline

    pipeline = NanoSAMPipeline(
        detector_backbone=args.backbone,
        confidence_threshold=args.threshold,
    )

    result = pipeline.run(img_path)
    pipeline.print_summary(result)
    pipeline.visualize(result, save_path=args.output, show=args.show)

    print(
        f"\n[Demo] Done!  Result saved to: {args.output}\n"
        f"       Detected {len(result.objects)} object(s) in "
        f"{result.total_time_s:.2f}s on CPU.\n"
    )


if __name__ == "__main__":
    main()
