"""
NanoSAM predictor — pure ONNX Runtime (CPU-only).

Architecture
------------
NanoSAM is a two-stage model:
  1. Image encoder  : ResNet-18 backbone → (1, 256, 64, 64) image embedding
  2. Mask decoder   : MobileSAM decoder  → binary segmentation mask

This module reimplements the NanoSAM Predictor without TensorRT so it runs
entirely on CPU via onnxruntime.

Usage
-----
    predictor = NanoSAMPredictor(
        encoder_path="models/resnet18_image_encoder.onnx",
        decoder_path="models/mobile_sam_mask_decoder.onnx",
    )
    predictor.set_image(pil_image)
    masks, scores = predictor.predict_from_box(x1, y1, x2, y2)
    masks, scores = predictor.predict_from_points([(cx, cy)], labels=[1])
"""

from __future__ import annotations

import warnings
from pathlib import Path
from typing import List, Optional, Tuple

import numpy as np
import onnxruntime as ort
from PIL import Image

# Input resolution expected by the NanoSAM image encoder
ENCODER_INPUT_SIZE = 1024  # square


class _OnnxSession:
    """Thin wrapper around an onnxruntime InferenceSession for CPU inference."""

    def __init__(self, model_path: str | Path) -> None:
        opts = ort.SessionOptions()
        opts.inter_op_num_threads = 0   # let ORT decide
        opts.intra_op_num_threads = 0
        opts.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
        self.session = ort.InferenceSession(
            str(model_path),
            sess_options=opts,
            providers=["CPUExecutionProvider"],
        )
        self.input_names  = [i.name for i in self.session.get_inputs()]
        self.output_names = [o.name for o in self.session.get_outputs()]

    def run(self, **kwargs) -> List[np.ndarray]:
        return self.session.run(self.output_names, kwargs)


class NanoSAMPredictor:
    """
    CPU NanoSAM predictor.

    Parameters
    ----------
    encoder_path : path to resnet18_image_encoder.onnx
    decoder_path : path to mobile_sam_mask_decoder.onnx
    """

    def __init__(
        self,
        encoder_path: str | Path = "models/resnet18_image_encoder.onnx",
        decoder_path: str | Path = "models/mobile_sam_mask_decoder.onnx",
    ) -> None:
        encoder_path = Path(encoder_path)
        decoder_path = Path(decoder_path)
        if not encoder_path.exists():
            raise FileNotFoundError(
                f"Encoder model not found: {encoder_path}\n"
                "Run `python download_models.py` to download the ONNX models."
            )
        if not decoder_path.exists():
            raise FileNotFoundError(
                f"Decoder model not found: {decoder_path}\n"
                "Run `python download_models.py` to download the ONNX models."
            )

        print("[NanoSAM] Loading image encoder ...")
        self._encoder = _OnnxSession(encoder_path)
        print("[NanoSAM] Loading mask decoder ...")
        self._decoder = _OnnxSession(decoder_path)
        print("[NanoSAM] Models loaded (CPU / ONNX Runtime)")

        # State set by set_image()
        self._image_embedding: Optional[np.ndarray] = None
        self._orig_size: Optional[Tuple[int, int]] = None   # (H, W)

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def set_image(self, image: Image.Image) -> None:
        """
        Pre-compute the image embedding for the given PIL image.
        Must be called before predict_from_box / predict_from_points.
        """
        self._orig_size = (image.height, image.width)
        inp = self._preprocess(image)
        outputs = self._encoder.run(**{self._encoder.input_names[0]: inp})
        self._image_embedding = outputs[0]   # (1, 256, 64, 64)

    def predict_from_box(
        self,
        x1: float,
        y1: float,
        x2: float,
        y2: float,
        orig_size: Optional[Tuple[int, int]] = None,
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Predict mask for a bounding-box prompt.

        Parameters
        ----------
        x1, y1, x2, y2 : bounding-box corners in *original-image* pixel coords.
        orig_size       : (H, W) of the original image; uses stored value if None.

        Returns
        -------
        masks  : (N, H, W) bool array (one mask per output head, N=3 by default)
        scores : (N,) float32 IoU confidence scores
        """
        self._check_image_set()
        h, w = orig_size if orig_size else self._orig_size

        # Box prompt: two corners with labels 2 (top-left) and 3 (bottom-right)
        coords = np.array([[x1, y1], [x2, y2]], dtype=np.float32)[None]  # (1,2,2)
        labels = np.array([2, 3], dtype=np.float32)[None]                # (1,2)

        return self._decode(coords, labels, h, w)

    def predict_from_points(
        self,
        points: List[Tuple[float, float]],
        labels: List[int],
        orig_size: Optional[Tuple[int, int]] = None,
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Predict mask from point prompts.

        Parameters
        ----------
        points : list of (x, y) in original-image pixel coords.
        labels : 1 = foreground, 0 = background.
        orig_size : (H, W); uses stored value if None.

        Returns
        -------
        masks  : (N, H, W) bool
        scores : (N,) float32
        """
        self._check_image_set()
        h, w = orig_size if orig_size else self._orig_size

        coords = np.array(points, dtype=np.float32)[None]           # (1,P,2)
        lbls   = np.array(labels, dtype=np.float32)[None]           # (1,P)

        return self._decode(coords, lbls, h, w)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _check_image_set(self) -> None:
        if self._image_embedding is None:
            raise RuntimeError("Call set_image() before predict_from_box/points.")

    def _preprocess(self, image: Image.Image) -> np.ndarray:
        """Resize, normalise and convert PIL image to (1, 3, 1024, 1024) float32."""
        image = image.convert("RGB").resize(
            (ENCODER_INPUT_SIZE, ENCODER_INPUT_SIZE), Image.BILINEAR
        )
        img = np.array(image, dtype=np.float32) / 255.0
        # ImageNet normalisation (SAM uses these exact values)
        mean = np.array([0.485, 0.456, 0.406], dtype=np.float32)
        std  = np.array([0.229, 0.224, 0.225], dtype=np.float32)
        img = (img - mean) / std
        img = img.transpose(2, 0, 1)[None]   # (1, 3, H, W)
        return img

    def _scale_coords(
        self,
        coords: np.ndarray,
        orig_h: int,
        orig_w: int,
    ) -> np.ndarray:
        """Scale prompt coordinates from original image space to 1024x1024."""
        coords = coords.copy()
        coords[..., 0] *= ENCODER_INPUT_SIZE / orig_w
        coords[..., 1] *= ENCODER_INPUT_SIZE / orig_h
        return coords

    def _decode(
        self,
        coords: np.ndarray,
        labels: np.ndarray,
        orig_h: int,
        orig_w: int,
    ) -> Tuple[np.ndarray, np.ndarray]:
        """Run the mask decoder and return upscaled masks + scores."""
        scaled_coords = self._scale_coords(coords, orig_h, orig_w)

        # Dummy mask input (no prior mask)
        mask_input    = np.zeros((1, 1, 256, 256), dtype=np.float32)
        has_mask_input = np.zeros(1, dtype=np.float32)

        dec_inputs = {
            "image_embeddings": self._image_embedding,
            "point_coords":     scaled_coords,
            "point_labels":     labels,
            "mask_input":       mask_input,
            "has_mask_input":   has_mask_input,
        }

        # Build named dict from decoder input names (order may vary per export)
        named = {}
        for name in self._decoder.input_names:
            if name in dec_inputs:
                named[name] = dec_inputs[name]
            # Some exports include image_pe; skip if not needed

        outputs = self._decoder.run(**named)

        # Decoder outputs (by name order): iou_predictions (B,4), low_res_masks (B,4,H,W)
        output_map = dict(zip(self._decoder.output_names, outputs))

        iou_preds     = output_map.get("iou_predictions")    # (B, 4)
        low_res_masks = output_map.get("low_res_masks")      # (B, 4, H, W)

        if low_res_masks is None:
            raise RuntimeError("Unexpected decoder outputs — check model format.")

        # Squeeze batch dim: (4, H, W) and (4,)
        if low_res_masks.ndim == 4:
            low_res_masks = low_res_masks[0]
        if iou_preds is not None and iou_preds.ndim == 2:
            iou_preds = iou_preds[0]

        # Up-sample low-res masks (256×256) → original image size
        masks = self._upsample_masks(low_res_masks, orig_h, orig_w)
        binary_masks = masks > 0.0                   # logits → bool

        if iou_preds is None:
            iou_preds = np.ones(binary_masks.shape[0], dtype=np.float32)

        return binary_masks, iou_preds

    @staticmethod
    def _upsample_masks(
        masks: np.ndarray, target_h: int, target_w: int
    ) -> np.ndarray:
        """
        Bilinear upsample (N, H_lr, W_lr) → (N, target_h, target_w) using numpy.
        """
        import cv2

        upsampled = []
        for mask in masks:
            up = cv2.resize(
                mask.astype(np.float32),
                (target_w, target_h),
                interpolation=cv2.INTER_LINEAR,
            )
            upsampled.append(up)
        return np.stack(upsampled)
