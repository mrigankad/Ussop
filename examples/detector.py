"""
Lightweight CPU object detector using torchvision Faster R-CNN.

The default backbone is ResNet-50 + FPN pre-trained on MS-COCO (80 classes).
For faster CPU inference, a MobileNet-v3 backbone is available via
`backbone="mobilenet"`.

Usage
-----
    detector = FasterRCNNDetector(confidence_threshold=0.5)
    detections = detector.detect(pil_image)
    # detections: list of Detection(box, label, score, class_name)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

import numpy as np
import torch
import torchvision.transforms.functional as TF
from PIL import Image
from torchvision.models.detection import (
    fasterrcnn_mobilenet_v3_large_fpn,
    fasterrcnn_resnet50_fpn_v2,
    FasterRCNN_MobileNet_V3_Large_FPN_Weights,
    FasterRCNN_ResNet50_FPN_V2_Weights,
)

# MS-COCO 80-class labels (index 0 = background)
COCO_CLASSES = [
    "__background__",
    "person", "bicycle", "car", "motorcycle", "airplane", "bus",
    "train", "truck", "boat", "traffic light", "fire hydrant",
    "stop sign", "parking meter", "bench", "bird", "cat", "dog",
    "horse", "sheep", "cow", "elephant", "bear", "zebra", "giraffe",
    "backpack", "umbrella", "handbag", "tie", "suitcase", "frisbee",
    "skis", "snowboard", "sports ball", "kite", "baseball bat",
    "baseball glove", "skateboard", "surfboard", "tennis racket",
    "bottle", "wine glass", "cup", "fork", "knife", "spoon", "bowl",
    "banana", "apple", "sandwich", "orange", "broccoli", "carrot",
    "hot dog", "pizza", "donut", "cake", "chair", "couch",
    "potted plant", "bed", "dining table", "toilet", "tv", "laptop",
    "mouse", "remote", "keyboard", "cell phone", "microwave", "oven",
    "toaster", "sink", "refrigerator", "book", "clock", "vase",
    "scissors", "teddy bear", "hair drier", "toothbrush",
]


@dataclass
class Detection:
    """Single object detection result."""
    box: np.ndarray          # [x1, y1, x2, y2] in pixel coords
    label: int               # COCO class index
    score: float             # confidence in [0, 1]
    class_name: str = field(default="")

    def __post_init__(self):
        if not self.class_name:
            self.class_name = (
                COCO_CLASSES[self.label]
                if 0 <= self.label < len(COCO_CLASSES)
                else str(self.label)
            )


class FasterRCNNDetector:
    """
    Torchvision Faster R-CNN detector (CPU).

    Parameters
    ----------
    backbone            : "resnet50" (default, more accurate) or "mobilenet" (faster)
    confidence_threshold: discard detections below this score
    nms_iou_threshold   : NMS IoU threshold (model default if None)
    allowed_classes     : if set, only return detections for these COCO class names
    """

    def __init__(
        self,
        backbone: str = "resnet50",
        confidence_threshold: float = 0.5,
        nms_iou_threshold: Optional[float] = None,
        allowed_classes: Optional[List[str]] = None,
    ) -> None:
        self.confidence_threshold = confidence_threshold
        self.allowed_classes = set(allowed_classes) if allowed_classes else None

        print(f"[Detector] Loading Faster R-CNN ({backbone}) on CPU ...")
        if backbone == "mobilenet":
            weights = FasterRCNN_MobileNet_V3_Large_FPN_Weights.DEFAULT
            self.model = fasterrcnn_mobilenet_v3_large_fpn(weights=weights)
        else:
            weights = FasterRCNN_ResNet50_FPN_V2_Weights.DEFAULT
            self.model = fasterrcnn_resnet50_fpn_v2(weights=weights)

        self.model.eval()
        self.transforms = weights.transforms()
        print("[Detector] Model loaded.")

    @torch.no_grad()
    def detect(self, image: Image.Image) -> List[Detection]:
        """
        Run detection on a PIL image.

        Returns
        -------
        List of Detection objects sorted by descending confidence.
        """
        img_tensor = self.transforms(image.convert("RGB"))
        outputs = self.model([img_tensor])[0]

        boxes  = outputs["boxes"].cpu().numpy()    # (N, 4)
        labels = outputs["labels"].cpu().numpy()   # (N,)
        scores = outputs["scores"].cpu().numpy()   # (N,)

        detections = []
        for box, label, score in zip(boxes, labels, scores):
            if score < self.confidence_threshold:
                continue
            class_name = (
                COCO_CLASSES[label] if 0 <= label < len(COCO_CLASSES) else str(label)
            )
            if self.allowed_classes and class_name not in self.allowed_classes:
                continue
            detections.append(
                Detection(box=box, label=int(label), score=float(score), class_name=class_name)
            )

        detections.sort(key=lambda d: d.score, reverse=True)
        return detections
