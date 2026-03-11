"""
NanoSAM Object Detection + Segmentation Pipeline (CPU).

This pipeline combines:
  1. FasterRCNNDetector  — detects objects and returns bounding boxes.
  2. NanoSAMPredictor    — segments each detected object using its bounding box
                           as a prompt to SAM.

Usage (programmatic)
--------------------
    pipeline = NanoSAMPipeline()
    results  = pipeline.run("image.jpg")
    pipeline.visualize(results, save_path="output.jpg")

Usage (CLI)
-----------
    python pipeline.py --input image.jpg --output output.jpg
"""

from __future__ import annotations

import argparse
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Tuple

import cv2
import numpy as np
from PIL import Image

from detector import Detection, FasterRCNNDetector
from predictor import NanoSAMPredictor


@dataclass
class SegmentedObject:
    """Combines a detection with its segmentation mask."""
    detection: Detection
    mask: np.ndarray          # (H, W) bool — best mask chosen from SAM heads
    iou_score: float          # SAM IoU confidence for the chosen mask


@dataclass
class PipelineResult:
    """Full result for one image."""
    image: np.ndarray                    # original BGR image (H, W, 3)
    objects: List[SegmentedObject]       # detected + segmented objects
    detection_time_s: float
    segmentation_time_s: float

    @property
    def total_time_s(self) -> float:
        return self.detection_time_s + self.segmentation_time_s


# Pre-defined colour palette (BGR) for visualisation
_PALETTE = [
    (255,  56,  56), (255, 157,  51), ( 78, 200,  99), ( 51, 161, 255),
    (188,  51, 255), (255,  51, 186), ( 51, 255, 255), (255, 255,  51),
    (128,   0, 128), (  0, 128, 128), (128, 128,   0), (  0,   0, 255),
    (255,   0,   0), (  0, 255,   0), (  0, 128,   0), (128,   0,   0),
]


class NanoSAMPipeline:
    """
    End-to-end detection → segmentation pipeline.

    Parameters
    ----------
    encoder_path         : path to resnet18_image_encoder.onnx
    decoder_path         : path to mobile_sam_mask_decoder.onnx
    detector_backbone    : "resnet50" (accurate) | "mobilenet" (fast)
    confidence_threshold : minimum detection score
    allowed_classes      : COCO class names to keep (None = all)
    max_detections       : cap on number of objects segmented per image
    mask_alpha           : transparency of mask overlay (0–1)
    """

    def __init__(
        self,
        encoder_path: str = "models/resnet18_image_encoder.onnx",
        decoder_path: str = "models/mobile_sam_mask_decoder.onnx",
        detector_backbone: str = "resnet50",
        confidence_threshold: float = 0.5,
        allowed_classes: Optional[List[str]] = None,
        max_detections: int = 20,
        mask_alpha: float = 0.45,
    ) -> None:
        self.max_detections = max_detections
        self.mask_alpha = mask_alpha

        self.detector = FasterRCNNDetector(
            backbone=detector_backbone,
            confidence_threshold=confidence_threshold,
            allowed_classes=allowed_classes,
        )
        self.predictor = NanoSAMPredictor(
            encoder_path=encoder_path,
            decoder_path=decoder_path,
        )

    # ------------------------------------------------------------------
    # Core pipeline
    # ------------------------------------------------------------------

    def run(self, image_source: str | Path | Image.Image) -> PipelineResult:
        """
        Run the full pipeline on an image.

        Parameters
        ----------
        image_source : file path string/Path or a PIL Image.

        Returns
        -------
        PipelineResult with detections, masks, and timing info.
        """
        if isinstance(image_source, (str, Path)):
            pil_image = Image.open(image_source).convert("RGB")
        else:
            pil_image = image_source.convert("RGB")

        np_bgr = cv2.cvtColor(np.array(pil_image), cv2.COLOR_RGB2BGR)

        # ── Stage 1: detection ──────────────────────────────────────────
        t0 = time.perf_counter()
        detections = self.detector.detect(pil_image)
        detections = detections[: self.max_detections]
        det_time = time.perf_counter() - t0

        print(
            f"[Pipeline] Detection: {len(detections)} objects found "
            f"in {det_time:.2f}s"
        )

        # ── Stage 2: NanoSAM segmentation ──────────────────────────────
        t1 = time.perf_counter()
        self.predictor.set_image(pil_image)

        segmented_objects: List[SegmentedObject] = []
        for det in detections:
            x1, y1, x2, y2 = det.box
            masks, scores = self.predictor.predict_from_box(x1, y1, x2, y2)

            # Pick the highest-IoU mask head
            best = int(np.argmax(scores))
            segmented_objects.append(
                SegmentedObject(
                    detection=det,
                    mask=masks[best],
                    iou_score=float(scores[best]),
                )
            )

        seg_time = time.perf_counter() - t1
        print(f"[Pipeline] Segmentation: {seg_time:.2f}s")

        return PipelineResult(
            image=np_bgr,
            objects=segmented_objects,
            detection_time_s=det_time,
            segmentation_time_s=seg_time,
        )

    # ------------------------------------------------------------------
    # Visualisation
    # ------------------------------------------------------------------

    def visualize(
        self,
        result: PipelineResult,
        save_path: Optional[str | Path] = None,
        show: bool = False,
        draw_boxes: bool = True,
        draw_masks: bool = True,
        draw_labels: bool = True,
    ) -> np.ndarray:
        """
        Draw detections and masks on the original image.

        Returns
        -------
        Annotated BGR numpy array.
        """
        canvas = result.image.copy().astype(np.float32)
        overlay = canvas.copy()

        for idx, obj in enumerate(result.objects):
            colour = _PALETTE[idx % len(_PALETTE)]

            # Filled mask overlay
            if draw_masks and obj.mask is not None:
                overlay[obj.mask] = colour

        # Alpha-blend mask overlay
        canvas = cv2.addWeighted(overlay, self.mask_alpha, canvas, 1 - self.mask_alpha, 0)
        canvas = canvas.astype(np.uint8)

        for idx, obj in enumerate(result.objects):
            colour = _PALETTE[idx % len(_PALETTE)]
            x1, y1, x2, y2 = [int(v) for v in obj.detection.box]

            # Bounding box
            if draw_boxes:
                cv2.rectangle(canvas, (x1, y1), (x2, y2), colour, 2)

            # Label + scores
            if draw_labels:
                label_txt = (
                    f"{obj.detection.class_name} "
                    f"{obj.detection.score:.2f} "
                    f"(iou {obj.iou_score:.2f})"
                )
                (tw, th), _ = cv2.getTextSize(label_txt, cv2.FONT_HERSHEY_SIMPLEX, 0.55, 1)
                ty = max(y1 - 6, th + 4)
                cv2.rectangle(canvas, (x1, ty - th - 4), (x1 + tw + 4, ty + 2), colour, -1)
                cv2.putText(
                    canvas, label_txt,
                    (x1 + 2, ty),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.55,
                    (255, 255, 255), 1, cv2.LINE_AA,
                )

        # Timing watermark
        timing_txt = (
            f"det: {result.detection_time_s:.2f}s | "
            f"seg: {result.segmentation_time_s:.2f}s | "
            f"total: {result.total_time_s:.2f}s"
        )
        cv2.putText(
            canvas, timing_txt,
            (10, canvas.shape[0] - 10),
            cv2.FONT_HERSHEY_SIMPLEX, 0.5,
            (200, 200, 200), 1, cv2.LINE_AA,
        )

        if save_path:
            save_path = Path(save_path)
            save_path.parent.mkdir(parents=True, exist_ok=True)
            cv2.imwrite(str(save_path), canvas)
            print(f"[Pipeline] Saved output to {save_path}")

        if show:
            cv2.imshow("NanoSAM Detection Pipeline", canvas)
            cv2.waitKey(0)
            cv2.destroyAllWindows()

        return canvas

    def print_summary(self, result: PipelineResult) -> None:
        """Print a human-readable summary of detections."""
        sep = "-" * 55
        print(f"\n{sep}")
        print(f"  Objects detected : {len(result.objects)}")
        print(f"  Detection time   : {result.detection_time_s:.2f}s")
        print(f"  Segmentation time: {result.segmentation_time_s:.2f}s")
        print(f"  Total time       : {result.total_time_s:.2f}s")
        print(sep)
        for i, obj in enumerate(result.objects):
            d = obj.detection
            print(
                f"  [{i+1:2d}] {d.class_name:<18s} "
                f"det={d.score:.3f}  iou={obj.iou_score:.3f}  "
                f"box=[{d.box[0]:.0f},{d.box[1]:.0f},{d.box[2]:.0f},{d.box[3]:.0f}]"
            )
        print(f"{sep}\n")


# ──────────────────────────────────────────────────────────────────────
# CLI entry-point
# ──────────────────────────────────────────────────────────────────────

def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="NanoSAM CPU object detection + segmentation pipeline"
    )
    p.add_argument("--input",  "-i", required=True,        help="Input image path")
    p.add_argument("--output", "-o", default="output.jpg", help="Output image path")
    p.add_argument(
        "--encoder", default="models/resnet18_image_encoder.onnx",
        help="Path to NanoSAM image encoder ONNX model",
    )
    p.add_argument(
        "--decoder", default="models/mobile_sam_mask_decoder.onnx",
        help="Path to NanoSAM mask decoder ONNX model",
    )
    p.add_argument(
        "--backbone", choices=["resnet50", "mobilenet"], default="resnet50",
        help="Detector backbone (resnet50=accurate, mobilenet=faster)",
    )
    p.add_argument(
        "--threshold", "-t", type=float, default=0.5,
        help="Detection confidence threshold (default: 0.5)",
    )
    p.add_argument(
        "--classes", nargs="+", default=None,
        help="Only detect specific COCO classes, e.g. --classes person car dog",
    )
    p.add_argument(
        "--max-detections", type=int, default=20,
        help="Maximum number of objects to segment (default: 20)",
    )
    p.add_argument("--show", action="store_true", help="Display result in a window")
    p.add_argument("--no-boxes",  action="store_true", help="Hide bounding boxes")
    p.add_argument("--no-masks",  action="store_true", help="Hide segmentation masks")
    p.add_argument("--no-labels", action="store_true", help="Hide class labels")
    return p.parse_args()


def main() -> None:
    args = _parse_args()

    pipeline = NanoSAMPipeline(
        encoder_path=args.encoder,
        decoder_path=args.decoder,
        detector_backbone=args.backbone,
        confidence_threshold=args.threshold,
        allowed_classes=args.classes,
        max_detections=args.max_detections,
    )

    result = pipeline.run(args.input)
    pipeline.print_summary(result)
    pipeline.visualize(
        result,
        save_path=args.output,
        show=args.show,
        draw_boxes=not args.no_boxes,
        draw_masks=not args.no_masks,
        draw_labels=not args.no_labels,
    )


if __name__ == "__main__":
    main()
