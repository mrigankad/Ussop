"""
PPE Safety Compliance Checker  (v2 — goggles vs spectacles aware)
==================================================================
Detects persons in an image and checks whether each person is wearing:
  - Safety goggles  (required PPE — wrap-around eye protection)
  - Lab coat        (required PPE — white protective coat)

Eyewear classification
----------------------
The checker distinguishes three states:

  GOGGLES      Full eye protection — wrap-around, large lenses, contiguous
               frame that seals around the eye area.
  SPECTACLES   Regular glasses — two separated smaller lenses, thin frames,
               no side/peripheral protection. NOT compliant for lab safety.
  NONE         No eyewear detected.

Key visual differences used
---------------------------
  Feature               Goggles         Spectacles      None
  ─────────────────────────────────────────────────────────
  Non-skin area ratio   > 35 %          8 – 35 %        < 8 %
  Eye-band width cover  > 60 %          30 – 60 %       < 30 %
  Height ratio          > 55 %          < 45 %          —
  # connected comps     1 (contiguous)  2 (separated)   —
  Component gap         < 8 px          > 12 px         —
  Aspect ratio (W/H)    > 1.7           1.2 – 1.65      —

Usage (CLI)
-----------
    python safety_checker.py --input ref/image.jpg
    python safety_checker.py --input ref/image.jpg --output output/safety.jpg --show
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Dict, Optional, Tuple

import cv2
import numpy as np
from PIL import Image, ImageOps

from detector import Detection, FasterRCNNDetector
from predictor import NanoSAMPredictor


# ── tunable thresholds ─────────────────────────────────────────────────
LAB_COAT_WHITE_RATIO = 0.22   # white pixel ratio inside NanoSAM mask

# Eyewear classifier — face geometry fractions
FACE_ZONE_FRAC  = 0.32   # top fraction of person box = "face zone"
EYE_BAND_TOP    = 0.28   # start of eye band inside face zone
EYE_BAND_BOT    = 0.68   # end   of eye band inside face zone

# Scoring thresholds (based on published goggle/spec dimensions)
_GOGGLE_AREA_THRESH  = 0.32   # non-skin area ratio
_GOGGLE_WIDTH_THRESH = 0.58   # eye-band width coverage
_GOGGLE_H_THRESH     = 0.52   # height of largest component / eye-band height
_GOGGLE_AR_THRESH    = 1.65   # aspect ratio (W/H) of combined eyewear bbox
_GOGGLE_GAP_THRESH   = 10     # max pixel gap between components for goggles
_SPEC_AREA_THRESH    = 0.07   # min non-skin area ratio for any eyewear
_SPEC_WIDTH_THRESH   = 0.28   # min width coverage for any eyewear


# ══════════════════════════════════════════════════════════════════════
# Eyewear type
# ══════════════════════════════════════════════════════════════════════

class EyewearType(str, Enum):
    GOGGLES     = "SAFETY GOGGLES"
    SPECTACLES  = "SPECTACLES"
    NONE        = "NONE"


# ══════════════════════════════════════════════════════════════════════
# Colour helpers
# ══════════════════════════════════════════════════════════════════════

def _skin_mask(rgb: np.ndarray) -> np.ndarray:
    """
    YCrCb skin detector — robust across all skin tones including very dark skin.
    (HSV hue-based detectors fail on dark skin; YCrCb Cr/Cb ranges work universally.)
    """
    ycrcb = cv2.cvtColor(rgb.astype(np.uint8), cv2.COLOR_RGB2YCrCb)
    cr, cb = ycrcb[..., 1], ycrcb[..., 2]
    # Standard skin locus in YCrCb (validated across diverse skin tones)
    return (cr >= 133) & (cr <= 177) & (cb >= 77) & (cb <= 127)


def _is_white(rgb: np.ndarray) -> np.ndarray:
    """Near-white pixel detector for lab-coat check."""
    brightness = rgb.astype(np.int32).sum(axis=-1) / 3
    saturation = rgb.max(axis=-1).astype(np.int32) - rgb.min(axis=-1)
    return (brightness > 168) & (saturation < 58)


# ══════════════════════════════════════════════════════════════════════
# Lab-coat check
# ══════════════════════════════════════════════════════════════════════

def check_lab_coat(
    image_rgb: np.ndarray,
    person_mask: np.ndarray,
) -> Tuple[bool, float]:
    """White-pixel ratio inside the NanoSAM person mask."""
    if person_mask.sum() == 0:
        return False, 0.0
    white = _is_white(image_rgb)
    ratio = float((white & person_mask).sum()) / float(person_mask.sum())
    return ratio >= LAB_COAT_WHITE_RATIO, ratio


# ══════════════════════════════════════════════════════════════════════
# Eyewear classifier  (goggles / spectacles / none)
# ══════════════════════════════════════════════════════════════════════

@dataclass
class EyewearFeatures:
    """Raw measurements used by the classifier (kept for debugging)."""
    area_ratio:    float = 0.0   # non-skin / eye-band area
    width_ratio:   float = 0.0   # span of eyewear / face width
    height_ratio:  float = 0.0   # tallest component / eye-band height
    aspect_ratio:  float = 0.0   # W/H of combined eyewear bbox
    n_components:  int   = 0     # significant non-skin components
    component_gap: float = 0.0   # pixel gap between two main comps
    goggle_score:  int   = 0     # accumulated score
    spec_score:    int   = 0


def _get_eye_band(
    image_rgb: np.ndarray,
    person_box: np.ndarray,
) -> Tuple[Optional[np.ndarray], int, int]:
    """
    Crop the eye-band region from the image.

    Strategy
    --------
    1. Take the top FACE_ZONE_FRAC of the person bounding box.
    2. Run YCrCb skin detection in the UPPER 60% of that zone (above hands/body).
    3. Find the largest skin connected region = the face.
    4. Compute a tight bounding box around that skin region.
    5. Extract the eye-band (EYE_BAND_TOP … EYE_BAND_BOT) inside that tight box,
       plus a horizontal margin so goggles that extend beyond the face are included.

    This eliminates background contamination for small/distant persons and
    handles any skin tone correctly via YCrCb.

    Returns (eye_band_rgb, effective_face_width, eye_band_height) or (None, 0, 0).
    """
    h_img, w_img = image_rgb.shape[:2]
    x1, y1, x2, y2 = (
        max(0, int(person_box[0])),
        max(0, int(person_box[1])),
        min(w_img, int(person_box[2])),
        min(h_img, int(person_box[3])),
    )
    ph, pw = y2 - y1, x2 - x1
    if ph < 20 or pw < 10:
        return None, 0, 0

    # ── Step 1: face zone ─────────────────────────────────────────────
    face_y2  = y1 + int(ph * FACE_ZONE_FRAC)
    face_rgb = image_rgb[y1:face_y2, x1:x2]
    fh, fw   = face_rgb.shape[:2]
    if fh < 12:
        return None, pw, 0

    # ── Step 2: skin in full face zone ───────────────────────────────
    skin = _skin_mask(face_rgb)

    # ── Step 3: pick the best skin region (= face) ───────────────────
    n_lbl, labels, stats, centroids = cv2.connectedComponentsWithStats(
        skin.astype(np.uint8), connectivity=8
    )

    # ── Step 3: pick the best skin region (= face) ───────────────────
    # Strategy: among significant skin blobs, ignore those that touch
    # the left/right image edges (those are background elements, not face).
    # Then take the TOPMOST remaining blob (highest in image = head).
    edge_px   = max(4, int(fw * 0.07))     # 7% of face-zone width
    min_area  = max(20, int(fh * fw * 0.003))  # at least 0.3% of zone

    # Collect candidates: (y_centroid, label_index)
    candidates = []
    for i in range(1, n_lbl):
        a  = int(stats[i, cv2.CC_STAT_AREA])
        if a < min_area:
            continue
        sx_i = int(stats[i, cv2.CC_STAT_LEFT])
        sw_i = int(stats[i, cv2.CC_STAT_WIDTH])
        # Skip blobs that hug the left or right edge (they're background)
        if sx_i <= edge_px or (sx_i + sw_i) >= (fw - edge_px):
            continue
        candidates.append((float(centroids[i][1]), i))

    # If nothing passed the edge filter, fall back to all significant blobs
    if not candidates:
        for i in range(1, n_lbl):
            if int(stats[i, cv2.CC_STAT_AREA]) >= min_area:
                candidates.append((float(centroids[i][1]), i))

    if not candidates:
        return None, pw, 0

    # Take the topmost (smallest y_centroid) — that's the head
    candidates.sort(key=lambda x: x[0])
    best = candidates[0][1]

    sx = int(stats[best, cv2.CC_STAT_LEFT])
    sy = int(stats[best, cv2.CC_STAT_TOP])
    sw = int(stats[best, cv2.CC_STAT_WIDTH])
    sh = int(stats[best, cv2.CC_STAT_HEIGHT])

    # Minimum face size: if blob is tiny the person is too far to classify
    if sw < 12 or sh < 8:
        return None, pw, 0

    # ── Step 4: eye-band inside the tight face bbox ───────────────────
    # The face bounding box goes from sy to sy+sh (in face-zone coords).
    # Eyes are at EYE_BAND_TOP … EYE_BAND_BOT of the face height.
    face_h = sh
    ey1 = sy + int(face_h * EYE_BAND_TOP)
    ey2 = sy + int(face_h * EYE_BAND_BOT)

    # Horizontal: face extent + margin for goggles that stick out sideways
    margin = int(sw * 0.22)
    ex1 = max(0,  sx - margin)
    ex2 = min(fw, sx + sw + margin)

    if ey2 <= ey1 or ex2 <= ex1:
        return None, sw, 0

    eye_band = face_rgb[ey1:ey2, ex1:ex2]
    if eye_band.size == 0:
        return None, sw, 0

    effective_face_w = ex2 - ex1
    return eye_band, effective_face_w, (ey2 - ey1)


def _connected_component_stats(binary: np.ndarray) -> list[dict]:
    """
    Return stats for each significant connected component.
    Each dict has: area, x, y, w, h, cx, cy.
    """
    n_labels, labels, stats, centroids = cv2.connectedComponentsWithStats(
        binary.astype(np.uint8), connectivity=8
    )
    total_pixels = binary.shape[0] * binary.shape[1]
    min_area = max(4, int(total_pixels * 0.015))   # drop < 1.5 % of eye band
    result = []
    for i in range(1, n_labels):                   # skip background (label 0)
        a = int(stats[i, cv2.CC_STAT_AREA])
        if a < min_area:
            continue
        result.append({
            "area": a,
            "x":    int(stats[i, cv2.CC_STAT_LEFT]),
            "y":    int(stats[i, cv2.CC_STAT_TOP]),
            "w":    int(stats[i, cv2.CC_STAT_WIDTH]),
            "h":    int(stats[i, cv2.CC_STAT_HEIGHT]),
            "cx":   float(centroids[i][0]),
            "cy":   float(centroids[i][1]),
        })
    return sorted(result, key=lambda c: c["area"], reverse=True)


def classify_eyewear(
    image_rgb: np.ndarray,
    person_box: np.ndarray,
) -> Tuple[EyewearType, EyewearFeatures]:
    """
    Classify the eyewear worn by a person using multi-feature scoring.

    Scoring system
    ──────────────
    Each feature adds/subtracts points to GOGGLE or SPEC score.
    Final decision: argmax(goggle_score, spec_score) if any score > 0,
    otherwise NONE.

    Returns
    -------
    eyewear_type : EyewearType enum
    features     : EyewearFeatures (diagnostic measurements)
    """
    feat = EyewearFeatures()

    eye_band, face_w, eye_band_h = _get_eye_band(image_rgb, person_box)
    if eye_band is None or face_w == 0:
        return EyewearType.NONE, feat

    # ── non-skin mask with morphological cleanup ──────────────────────
    skin      = _skin_mask(eye_band)
    non_skin  = (~skin).astype(np.uint8)

    # Open (remove noise), then close (fill small holes in goggles/lenses)
    k3  = np.ones((3, 3), np.uint8)
    k5  = np.ones((5, 5), np.uint8)
    non_skin = cv2.morphologyEx(non_skin, cv2.MORPH_OPEN,  k3)
    non_skin = cv2.morphologyEx(non_skin, cv2.MORPH_CLOSE, k5)

    # ── basic area ratio ──────────────────────────────────────────────
    n_total       = eye_band.shape[0] * eye_band.shape[1]
    feat.area_ratio = float(non_skin.sum()) / max(n_total, 1)

    if feat.area_ratio < _SPEC_AREA_THRESH:
        # Too little non-skin: almost certainly bare eyes
        return EyewearType.NONE, feat

    # ── connected components ──────────────────────────────────────────
    comps = _connected_component_stats(non_skin)
    feat.n_components = len(comps)

    if not comps:
        return EyewearType.NONE, feat

    # Combined bounding box of all significant components
    all_x1 = min(c["x"]          for c in comps)
    all_x2 = max(c["x"] + c["w"] for c in comps)
    all_y1 = min(c["y"]          for c in comps)
    all_y2 = max(c["y"] + c["h"] for c in comps)

    combined_w = all_x2 - all_x1
    combined_h = max(all_y2 - all_y1, 1)

    feat.width_ratio  = combined_w / max(face_w, 1)
    feat.height_ratio = max(c["h"] for c in comps) / max(eye_band_h, 1)
    feat.aspect_ratio = combined_w / combined_h

    # Gap between the two largest components (if exactly 2)
    if len(comps) >= 2:
        c1, c2     = comps[0], comps[1]
        left_c     = c1 if c1["x"] < c2["x"] else c2
        right_c    = c2 if c1["x"] < c2["x"] else c1
        gap        = (right_c["x"]) - (left_c["x"] + left_c["w"])
        feat.component_gap = max(0.0, float(gap))
    else:
        feat.component_gap = 0.0

    # ── effective width: use per-component avg when lenses are separated ─
    #    (combined span is misleading for spectacles — two lenses far apart)
    two_sep = (feat.n_components == 2 and feat.component_gap > _GOGGLE_GAP_THRESH)
    if two_sep and len(comps) >= 2:
        avg_comp_w = (comps[0]["w"] + comps[1]["w"]) / 2.0
        effective_width = avg_comp_w / max(face_w, 1)
    else:
        effective_width = feat.width_ratio

    # ══ SCORING ═══════════════════════════════════════════════════════
    gs = 0   # goggle score
    ss = 0   # spectacles score

    # 1. Area coverage  (non-skin area / eye-band area)
    if   feat.area_ratio > _GOGGLE_AREA_THRESH:  gs += 3   # large solid band
    elif feat.area_ratio > 0.18:                 gs += 1
    else:                                        ss += 2   # small thin lenses

    # 2. Effective width (per-component for separated pairs)
    if   effective_width > _GOGGLE_WIDTH_THRESH:  gs += 3  # wide band → goggles
    elif effective_width > _SPEC_WIDTH_THRESH:
        gs += 1 if feat.aspect_ratio < 4.0 else 0          # neutral-to-mild
    else:
        ss += 2                                             # narrow → each lens is small

    # 3. Vertical extent (height of tallest component / eye-band height)
    if   feat.height_ratio > _GOGGLE_H_THRESH:   gs += 3   # tall wrap-around
    elif feat.height_ratio > 0.40:               gs += 1
    elif feat.height_ratio < 0.35:               ss += 3   # thin frames → specs

    # 4. Connected components + gap  (most discriminative feature)
    if feat.n_components == 1:
        gs += 4                                  # single contiguous piece → goggles
    elif feat.n_components == 2:
        if feat.component_gap <= _GOGGLE_GAP_THRESH:
            gs += 2                              # very close pair → goggles (bridged)
        else:
            ss += 5                              # clearly separated → spectacles
            if len(comps) >= 2:
                # Both lenses similar size? Strong spectacle signal
                size_ratio = comps[1]["area"] / max(comps[0]["area"], 1)
                if size_ratio > 0.45:
                    ss += 2
    else:
        ss += 1                                  # fragmented → mild spec signal

    # 5. Aspect ratio of combined eyewear bounding box
    #    Spectacles: very high AR (wide gap inflates span vs. thin height)
    #    Goggles:    moderate AR (1.7 – 3.5)
    if   feat.aspect_ratio > 4.5:                ss += 3   # gap-inflated → specs
    elif feat.aspect_ratio > _GOGGLE_AR_THRESH:  gs += 2   # wide solid → goggles
    else:                                        ss += 2   # squarish → specs

    feat.goggle_score = gs
    feat.spec_score   = ss

    # ── decision ──────────────────────────────────────────────────────
    if gs == 0 and ss == 0:
        return EyewearType.NONE, feat
    if gs > ss:
        return EyewearType.GOGGLES, feat
    if ss > gs:
        return EyewearType.SPECTACLES, feat
    # Tie: if large area or single component → lean goggles
    if feat.n_components == 1 or feat.area_ratio > 0.30:
        return EyewearType.GOGGLES, feat
    return EyewearType.SPECTACLES, feat


# ══════════════════════════════════════════════════════════════════════
# Compliance dataclass
# ══════════════════════════════════════════════════════════════════════

@dataclass
class PersonCompliance:
    person_id:     int
    box:           np.ndarray
    mask:          np.ndarray
    has_lab_coat:  bool
    eyewear:       EyewearType
    lab_coat_ratio: float
    ew_features:   EyewearFeatures

    @property
    def has_safety_eyewear(self) -> bool:
        return self.eyewear == EyewearType.GOGGLES

    @property
    def is_compliant(self) -> bool:
        return self.has_lab_coat and self.has_safety_eyewear

    @property
    def status(self) -> str:
        if self.is_compliant:
            return "COMPLIANT"
        missing = []
        if not self.has_lab_coat:
            missing.append("lab coat")
        if self.eyewear == EyewearType.SPECTACLES:
            missing.append("safety goggles (has spectacles)")
        elif self.eyewear == EyewearType.NONE:
            missing.append("safety goggles")
        return "NON-COMPLIANT: " + ", ".join(missing)


# ══════════════════════════════════════════════════════════════════════
# Main checker class
# ══════════════════════════════════════════════════════════════════════

class PPESafetyChecker:
    """
    End-to-end PPE compliance checker.

    Parameters
    ----------
    encoder_path  : NanoSAM image encoder ONNX model
    decoder_path  : NanoSAM mask decoder ONNX model
    det_backbone  : "mobilenet" (fast) | "resnet50" (accurate)
    det_threshold : minimum person detection confidence
    """

    def __init__(
        self,
        encoder_path:  str   = "models/resnet18_image_encoder.onnx",
        decoder_path:  str   = "models/mobile_sam_mask_decoder.onnx",
        det_backbone:  str   = "mobilenet",
        det_threshold: float = 0.35,
    ) -> None:
        self.detector  = FasterRCNNDetector(
            backbone=det_backbone,
            confidence_threshold=det_threshold,
            allowed_classes=["person"],
        )
        self.predictor = NanoSAMPredictor(encoder_path, decoder_path)

    def check(
        self, image_path: str | Path
    ) -> Tuple[np.ndarray, list[PersonCompliance]]:
        """
        Run the full PPE check.

        Returns
        -------
        image_rgb   : EXIF-corrected RGB array
        compliances : one PersonCompliance per detected person
        """
        pil       = Image.open(image_path).convert("RGB")
        pil       = ImageOps.exif_transpose(pil)
        image_rgb = np.array(pil)

        detections: list[Detection] = self.detector.detect(pil)
        if not detections:
            print("[SafetyChecker] No persons detected.")
            return image_rgb, []

        print(f"[SafetyChecker] {len(detections)} person(s) detected.")
        self.predictor.set_image(pil)

        compliances = []
        for i, det in enumerate(detections):
            x1, y1, x2, y2 = det.box

            masks, scores = self.predictor.predict_from_box(x1, y1, x2, y2)
            person_mask   = masks[int(np.argmax(scores))]

            has_coat, coat_ratio = check_lab_coat(image_rgb, person_mask)
            eyewear_type, ew_feat = classify_eyewear(image_rgb, det.box)

            compliances.append(PersonCompliance(
                person_id     = i + 1,
                box           = det.box,
                mask          = person_mask,
                has_lab_coat  = has_coat,
                eyewear       = eyewear_type,
                lab_coat_ratio= coat_ratio,
                ew_features   = ew_feat,
            ))

        return image_rgb, compliances

    # ── visualisation ────────────────────────────────────────────────

    @staticmethod
    def visualize(
        image_rgb: np.ndarray,
        compliances: list[PersonCompliance],
        save_path: Optional[str | Path] = None,
        show: bool = False,
    ) -> np.ndarray:

        # Colour scheme (BGR)
        CLR_COMPLIANT    = ( 30, 200,  30)   # green
        CLR_SPECTACLES   = (  0, 165, 255)   # orange  (has specs not goggles)
        CLR_NONCOMPLIANT = ( 30,  30, 220)   # red

        def _person_colour(pc: PersonCompliance):
            if pc.is_compliant:
                return CLR_COMPLIANT
            if pc.eyewear == EyewearType.SPECTACLES:
                return CLR_SPECTACLES
            return CLR_NONCOMPLIANT

        canvas  = cv2.cvtColor(image_rgb, cv2.COLOR_RGB2BGR).astype(np.float32)
        overlay = canvas.copy()
        for pc in compliances:
            overlay[pc.mask] = _person_colour(pc)
        canvas = cv2.addWeighted(overlay, 0.40, canvas, 0.60, 0).astype(np.uint8)

        for pc in compliances:
            colour = _person_colour(pc)
            x1, y1, x2, y2 = [int(v) for v in pc.box]
            cv2.rectangle(canvas, (x1, y1), (x2, y2), colour, 4)

            ef = pc.ew_features
            badge_lines = [
                f"Person {pc.person_id}",
                f"  Lab coat : {'YES' if pc.has_lab_coat else 'NO'}"
                f"  (white {pc.lab_coat_ratio*100:.0f}%)",
                f"  Eyewear  : {pc.eyewear.value}",
                f"    area={ef.area_ratio*100:.0f}%  "
                f"width={ef.width_ratio*100:.0f}%  "
                f"h={ef.height_ratio*100:.0f}%",
                f"    comps={ef.n_components}  "
                f"gap={ef.component_gap:.0f}px  "
                f"AR={ef.aspect_ratio:.1f}",
                f"    score  goggles={ef.goggle_score}  specs={ef.spec_score}",
                f"  >> {pc.status}",
            ]

            font   = cv2.FONT_HERSHEY_SIMPLEX
            fscale = max(0.45, min(0.75, (x2 - x1) / 700))
            thick  = 1
            line_h = int(20 * fscale) + 5
            bw = max(cv2.getTextSize(l, font, fscale, thick)[0][0]
                     for l in badge_lines) + 14
            bx1 = x1
            by1 = max(0, y1 - len(badge_lines) * line_h - 8)
            cv2.rectangle(canvas, (bx1, by1),
                          (bx1 + bw, by1 + len(badge_lines) * line_h + 8),
                          colour, -1)
            for j, line in enumerate(badge_lines):
                ty = by1 + (j + 1) * line_h
                cv2.putText(canvas, line, (bx1 + 5, ty),
                            font, fscale, (255, 255, 255), thick, cv2.LINE_AA)

        # Bottom summary bar
        total = len(compliances)
        n_ok  = sum(1 for p in compliances if p.is_compliant)
        bar   = f"SAFETY CHECK  |  {n_ok}/{total} compliant"
        bclr  = (0, 180, 0) if n_ok == total else (0, 0, 200)
        ih, iw = canvas.shape[:2]
        (bw, bh), _ = cv2.getTextSize(bar, cv2.FONT_HERSHEY_SIMPLEX, 1.1, 2)
        cv2.rectangle(canvas, (0, ih - bh - 22), (iw, ih), (20, 20, 20), -1)
        cv2.putText(canvas, bar, ((iw - bw) // 2, ih - 8),
                    cv2.FONT_HERSHEY_SIMPLEX, 1.1, bclr, 2, cv2.LINE_AA)

        if save_path:
            Path(save_path).parent.mkdir(parents=True, exist_ok=True)
            cv2.imwrite(str(save_path), canvas)
            print(f"[SafetyChecker] Saved: {save_path}")
        if show:
            cv2.imshow("PPE Safety Checker", canvas)
            cv2.waitKey(0)
            cv2.destroyAllWindows()
        return canvas

    # ── text report ──────────────────────────────────────────────────

    @staticmethod
    def print_report(compliances: list[PersonCompliance]) -> None:
        sep = "=" * 62
        print(f"\n{sep}")
        print("  PPE SAFETY COMPLIANCE REPORT  (goggles vs spectacles aware)")
        print(sep)
        if not compliances:
            print("  No persons detected.")
            print(sep)
            return

        for pc in compliances:
            ef = pc.ew_features
            coat_icon = "[OK]" if pc.has_lab_coat else "[!!]"
            ew_icon   = "[OK]" if pc.has_safety_eyewear else (
                        "[~~]" if pc.eyewear == EyewearType.SPECTACLES else "[!!]")

            print(f"\n  Person {pc.person_id}")
            print(f"    {coat_icon} Lab coat : "
                  f"{'PRESENT' if pc.has_lab_coat else 'NOT DETECTED'}"
                  f"  (white ratio = {pc.lab_coat_ratio*100:.1f}%)")
            print(f"    {ew_icon} Eyewear  : {pc.eyewear.value}")
            print(f"         area={ef.area_ratio*100:.1f}%  "
                  f"width={ef.width_ratio*100:.1f}%  "
                  f"height={ef.height_ratio*100:.1f}%")
            print(f"         components={ef.n_components}  "
                  f"gap={ef.component_gap:.0f}px  "
                  f"aspect_ratio={ef.aspect_ratio:.2f}")
            print(f"         score: goggles={ef.goggle_score}  "
                  f"spectacles={ef.spec_score}")
            print(f"    --> {pc.status}")

        print(f"\n{sep}")
        n_ok  = sum(1 for p in compliances if p.is_compliant)
        total = len(compliances)
        print(f"  OVERALL: {n_ok}/{total} person(s) fully compliant")
        if n_ok == total:
            print("  Result : PASS")
        else:
            print("  Result : FAIL")
            # Explain spectacles warning
            has_specs = any(
                p.eyewear == EyewearType.SPECTACLES and not p.has_safety_eyewear
                for p in compliances
            )
            if has_specs:
                print("  NOTE   : Spectacles detected are NOT safety goggles.")
                print("           Lab safety requires wrap-around protective eyewear.")
        print(f"{sep}\n")


# ══════════════════════════════════════════════════════════════════════
# CLI
# ══════════════════════════════════════════════════════════════════════

def main() -> None:
    p = argparse.ArgumentParser(description="PPE safety checker (goggles vs specs)")
    p.add_argument("--input",    "-i", required=True)
    p.add_argument("--output",   "-o", default="output/safety_result.jpg")
    p.add_argument("--encoder",  default="models/resnet18_image_encoder.onnx")
    p.add_argument("--decoder",  default="models/mobile_sam_mask_decoder.onnx")
    p.add_argument("--backbone", choices=["mobilenet", "resnet50"], default="mobilenet")
    p.add_argument("--threshold","-t", type=float, default=0.35)
    p.add_argument("--show",     action="store_true")
    args = p.parse_args()

    checker = PPESafetyChecker(
        encoder_path  = args.encoder,
        decoder_path  = args.decoder,
        det_backbone  = args.backbone,
        det_threshold = args.threshold,
    )
    image_rgb, compliances = checker.check(args.input)
    checker.print_report(compliances)
    checker.visualize(image_rgb, compliances,
                      save_path=args.output, show=args.show)


if __name__ == "__main__":
    main()
