"""
On-Device Model Training Pipeline for Ussop
Fine-tunes Faster R-CNN detector on annotated inspection data.
"""
import uuid
import json
import shutil
import threading
import time
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum

import numpy as np
import torch
import torch.optim as optim
from torch.utils.data import Dataset, DataLoader
from PIL import Image

from config.settings import settings


class TrainingStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class TrainingConfig:
    """Hyperparameters for fine-tuning."""
    epochs: int = 10
    batch_size: int = 2
    learning_rate: float = 1e-4
    momentum: float = 0.9
    weight_decay: float = 5e-4
    validation_split: float = 0.2
    early_stopping_patience: int = 3
    min_improvement: float = 0.01


@dataclass
class TrainingJob:
    """Tracks a single training job."""
    job_id: str
    created_at: str
    image_count: int
    config: TrainingConfig
    status: TrainingStatus = TrainingStatus.QUEUED
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    current_epoch: int = 0
    total_epochs: int = 0
    train_loss: float = 0.0
    val_loss: float = 0.0
    best_map: float = 0.0
    output_model_path: Optional[str] = None
    error_message: Optional[str] = None
    log: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "job_id": self.job_id,
            "created_at": self.created_at,
            "image_count": self.image_count,
            "status": self.status.value,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "progress": {
                "current_epoch": self.current_epoch,
                "total_epochs": self.total_epochs,
                "percent": int(self.current_epoch / self.total_epochs * 100) if self.total_epochs > 0 else 0,
            },
            "metrics": {
                "train_loss": round(self.train_loss, 4),
                "val_loss": round(self.val_loss, 4),
                "best_map": round(self.best_map, 4),
            },
            "output_model_path": self.output_model_path,
            "error_message": self.error_message,
            "log": self.log[-20:],  # last 20 lines
        }


class DefectDataset(Dataset):
    """PyTorch Dataset for annotated inspection images."""

    def __init__(self, images: List[Dict], annotations: List[Dict]):
        self.items = []
        ann_map = {a["image_id"]: a["annotations"] for a in annotations}

        for img in images:
            path = Path(img["path"])
            if not path.exists():
                continue
            anns = ann_map.get(img["id"], [])
            self.items.append({"path": path, "annotations": anns})

    def __len__(self):
        return len(self.items)

    def __getitem__(self, idx):
        item = self.items[idx]
        image = Image.open(item["path"]).convert("RGB")
        img_tensor = torch.as_tensor(
            np.array(image), dtype=torch.float32
        ).permute(2, 0, 1) / 255.0

        boxes, labels = [], []
        for ann in item["annotations"]:
            box = ann.get("box", [])
            if len(box) == 4:
                x1, y1, x2, y2 = box
                if x2 > x1 and y2 > y1:
                    boxes.append([x1, y1, x2, y2])
                    labels.append(ann.get("class_label", 1))

        if boxes:
            target = {
                "boxes": torch.as_tensor(boxes, dtype=torch.float32),
                "labels": torch.as_tensor(labels, dtype=torch.int64),
            }
        else:
            target = {
                "boxes": torch.zeros((0, 4), dtype=torch.float32),
                "labels": torch.zeros(0, dtype=torch.int64),
            }

        return img_tensor, target


def _collate_fn(batch):
    return tuple(zip(*batch))


def _compute_map(predictions, targets, iou_threshold=0.5) -> float:
    """Simple mAP@0.5 estimate for validation."""
    if not predictions:
        return 0.0

    aps = []
    for pred, tgt in zip(predictions, targets):
        pred_boxes = pred["boxes"].cpu().numpy() if len(pred["boxes"]) > 0 else np.zeros((0, 4))
        tgt_boxes = tgt["boxes"].cpu().numpy() if len(tgt["boxes"]) > 0 else np.zeros((0, 4))
        scores = pred["scores"].cpu().numpy() if len(pred["scores"]) > 0 else np.zeros(0)

        if len(tgt_boxes) == 0:
            aps.append(1.0 if len(pred_boxes) == 0 else 0.0)
            continue

        if len(pred_boxes) == 0:
            aps.append(0.0)
            continue

        # Sort by score
        order = np.argsort(-scores)
        pred_boxes = pred_boxes[order]

        matched = np.zeros(len(tgt_boxes), dtype=bool)
        tp = np.zeros(len(pred_boxes))

        for pi, pb in enumerate(pred_boxes):
            best_iou, best_j = 0.0, -1
            for j, tb in enumerate(tgt_boxes):
                if matched[j]:
                    continue
                ix1, iy1 = max(pb[0], tb[0]), max(pb[1], tb[1])
                ix2, iy2 = min(pb[2], tb[2]), min(pb[3], tb[3])
                inter = max(0, ix2 - ix1) * max(0, iy2 - iy1)
                union = ((pb[2] - pb[0]) * (pb[3] - pb[1]) +
                         (tb[2] - tb[0]) * (tb[3] - tb[1]) - inter)
                iou = inter / union if union > 0 else 0.0
                if iou > best_iou:
                    best_iou, best_j = iou, j
            if best_iou >= iou_threshold:
                tp[pi] = 1
                matched[best_j] = True

        cum_tp = np.cumsum(tp)
        precision = cum_tp / (np.arange(len(tp)) + 1)
        recall = cum_tp / len(tgt_boxes)
        # AP via trapezoid
        _trapezoid = getattr(np, 'trapezoid', np.trapz)
        ap = float(_trapezoid(precision, recall)) if len(recall) > 1 else precision[0]
        aps.append(ap)

    return float(np.mean(aps)) if aps else 0.0


class ModelTrainer:
    """
    On-device Faster R-CNN fine-tuning pipeline.

    Workflow:
    1. Load annotated dataset from active learning queue
    2. Fine-tune Faster R-CNN on defect classes
    3. Validate on held-out split
    4. Save checkpoint if metrics improve
    5. Signal ModelDeployer to hot-swap on success
    """

    def __init__(self):
        self._jobs: Dict[str, TrainingJob] = {}
        self._lock = threading.Lock()
        self._jobs_dir = settings.MODELS_DIR / "training_jobs"
        self._jobs_dir.mkdir(parents=True, exist_ok=True)
        self._load_persisted_jobs()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def submit_job(self, dataset: Dict[str, Any], config: Optional[TrainingConfig] = None) -> TrainingJob:
        """Create and queue a training job."""
        if not dataset.get("ready"):
            raise ValueError("Dataset not ready: " + dataset.get("message", ""))

        cfg = config or TrainingConfig()
        job = TrainingJob(
            job_id=str(uuid.uuid4()),
            created_at=datetime.now(timezone.utc).replace(tzinfo=None).isoformat(),
            image_count=dataset["count"],
            config=cfg,
            total_epochs=cfg.epochs,
        )

        with self._lock:
            self._jobs[job.job_id] = job
        self._persist_job(job)

        # Run in background thread
        thread = threading.Thread(
            target=self._run_job,
            args=(job, dataset),
            daemon=True,
            name=f"train-{job.job_id[:8]}",
        )
        thread.start()

        return job

    def get_job(self, job_id: str) -> Optional[TrainingJob]:
        with self._lock:
            return self._jobs.get(job_id)

    def list_jobs(self) -> List[Dict[str, Any]]:
        with self._lock:
            return [j.to_dict() for j in sorted(
                self._jobs.values(),
                key=lambda j: j.created_at,
                reverse=True,
            )]

    def cancel_job(self, job_id: str) -> bool:
        with self._lock:
            job = self._jobs.get(job_id)
            if job and job.status == TrainingStatus.QUEUED:
                job.status = TrainingStatus.CANCELLED
                self._persist_job(job)
                return True
        return False

    # ------------------------------------------------------------------
    # Internal training loop
    # ------------------------------------------------------------------

    def _run_job(self, job: TrainingJob, dataset: Dict[str, Any]):
        """Execute training in a background thread."""
        try:
            self._update_job(job, status=TrainingStatus.RUNNING,
                             started_at=datetime.now(timezone.utc).replace(tzinfo=None).isoformat())

            images = dataset["images"]
            annotations = dataset["annotations"]

            # Split train / val
            n = len(images)
            n_val = max(1, int(n * job.config.validation_split))
            n_train = n - n_val

            idx = list(range(n))
            np.random.shuffle(idx)
            train_idx, val_idx = idx[:n_train], idx[n_train:]

            train_imgs = [images[i] for i in train_idx]
            train_anns = [annotations[i] for i in train_idx]
            val_imgs = [images[i] for i in val_idx]
            val_anns = [annotations[i] for i in val_idx]

            train_ds = DefectDataset(train_imgs, train_anns)
            val_ds = DefectDataset(val_imgs, val_anns)

            if len(train_ds) == 0:
                raise ValueError("No valid training images found")

            train_loader = DataLoader(
                train_ds,
                batch_size=min(job.config.batch_size, len(train_ds)),
                shuffle=True,
                collate_fn=_collate_fn,
                num_workers=0,
            )
            val_loader = DataLoader(
                val_ds,
                batch_size=1,
                shuffle=False,
                collate_fn=_collate_fn,
                num_workers=0,
            )

            # Load base model
            model = self._load_base_model()
            model.train()

            optimizer = optim.SGD(
                [p for p in model.parameters() if p.requires_grad],
                lr=job.config.learning_rate,
                momentum=job.config.momentum,
                weight_decay=job.config.weight_decay,
            )
            scheduler = optim.lr_scheduler.StepLR(optimizer, step_size=3, gamma=0.1)

            best_val_loss = float("inf")
            patience_counter = 0
            best_ckpt_path = None

            for epoch in range(1, job.config.epochs + 1):
                if job.status == TrainingStatus.CANCELLED:
                    break

                # Train epoch
                train_loss = self._train_epoch(model, train_loader, optimizer, job)
                val_loss, val_map = self._val_epoch(model, val_loader)
                scheduler.step()

                self._update_job(
                    job,
                    current_epoch=epoch,
                    train_loss=train_loss,
                    val_loss=val_loss,
                    best_map=max(job.best_map, val_map),
                )
                job.log.append(
                    f"Epoch {epoch}/{job.config.epochs} | "
                    f"train_loss={train_loss:.4f} val_loss={val_loss:.4f} mAP={val_map:.4f}"
                )

                # Checkpoint if improved
                if val_loss < best_val_loss - job.config.min_improvement:
                    best_val_loss = val_loss
                    patience_counter = 0
                    ckpt_dir = self._jobs_dir / job.job_id
                    ckpt_dir.mkdir(exist_ok=True)
                    best_ckpt_path = str(ckpt_dir / "best_model.pt")
                    torch.save(model.state_dict(), best_ckpt_path)
                    job.log.append(f"  -> Checkpoint saved (val_loss={val_loss:.4f})")
                else:
                    patience_counter += 1
                    if patience_counter >= job.config.early_stopping_patience:
                        job.log.append(f"Early stopping at epoch {epoch}")
                        break

            if job.status != TrainingStatus.CANCELLED:
                self._update_job(
                    job,
                    status=TrainingStatus.COMPLETED,
                    completed_at=datetime.now(timezone.utc).replace(tzinfo=None).isoformat(),
                    output_model_path=best_ckpt_path,
                )
                job.log.append("Training completed successfully.")

        except Exception as exc:
            self._update_job(
                job,
                status=TrainingStatus.FAILED,
                completed_at=datetime.now(timezone.utc).replace(tzinfo=None).isoformat(),
                error_message=str(exc),
            )
            job.log.append(f"ERROR: {exc}")

        finally:
            self._persist_job(job)

    def _train_epoch(self, model, loader, optimizer, job: TrainingJob) -> float:
        model.train()
        total_loss = 0.0
        count = 0

        for images, targets in loader:
            if job.status == TrainingStatus.CANCELLED:
                break
            optimizer.zero_grad()
            loss_dict = model(list(images), list(targets))
            loss = sum(loss_dict.values())
            loss.backward()
            optimizer.step()
            total_loss += float(loss)
            count += 1

        return total_loss / count if count > 0 else 0.0

    @torch.no_grad()
    def _val_epoch(self, model, loader) -> Tuple[float, float]:
        model.train()  # keep in train mode to get loss dict
        total_loss = 0.0
        count = 0

        for images, targets in loader:
            loss_dict = model(list(images), list(targets))
            total_loss += float(sum(loss_dict.values()))
            count += 1

        # Switch to eval for mAP
        model.eval()
        all_preds, all_tgts = [], []
        for images, targets in loader:
            preds = model(list(images))
            all_preds.extend(preds)
            all_tgts.extend(targets)

        val_map = _compute_map(all_preds, all_tgts)
        model.train()

        return (total_loss / count if count > 0 else 0.0), val_map

    def _load_base_model(self):
        """Load the pre-trained Faster R-CNN and prepare for fine-tuning."""
        from torchvision.models.detection import (
            fasterrcnn_mobilenet_v3_large_fpn,
            FasterRCNN_MobileNet_V3_Large_FPN_Weights,
        )
        from torchvision.models.detection.faster_rcnn import FastRCNNPredictor

        weights = FasterRCNN_MobileNet_V3_Large_FPN_Weights.DEFAULT
        model = fasterrcnn_mobilenet_v3_large_fpn(weights=weights)

        # Freeze backbone, only train head
        for param in model.backbone.parameters():
            param.requires_grad = False

        # Replace classification head for binary (background + defect)
        in_features = model.roi_heads.box_predictor.cls_score.in_features
        num_classes = 2  # background + defect
        model.roi_heads.box_predictor = FastRCNNPredictor(in_features, num_classes)

        # Load existing fine-tuned weights if present
        deployed = settings.MODELS_DIR / "deployed" / "finetuned.pt"
        if deployed.exists():
            model.load_state_dict(torch.load(str(deployed), map_location="cpu"), strict=False)

        return model

    # ------------------------------------------------------------------
    # Persistence helpers
    # ------------------------------------------------------------------

    def _update_job(self, job: TrainingJob, **kwargs):
        with self._lock:
            for k, v in kwargs.items():
                setattr(job, k, v)
        self._persist_job(job)

    def _persist_job(self, job: TrainingJob):
        path = self._jobs_dir / f"{job.job_id}.json"
        with open(path, "w") as f:
            json.dump(job.to_dict(), f, indent=2)

    def _load_persisted_jobs(self):
        for path in self._jobs_dir.glob("*.json"):
            try:
                with open(path) as f:
                    data = json.load(f)
                cfg = TrainingConfig()
                job = TrainingJob(
                    job_id=data["job_id"],
                    created_at=data["created_at"],
                    image_count=data["image_count"],
                    config=cfg,
                    status=TrainingStatus(data["status"]),
                    started_at=data.get("started_at"),
                    completed_at=data.get("completed_at"),
                    current_epoch=data.get("progress", {}).get("current_epoch", 0),
                    total_epochs=data.get("progress", {}).get("total_epochs", 0),
                    train_loss=data.get("metrics", {}).get("train_loss", 0.0),
                    val_loss=data.get("metrics", {}).get("val_loss", 0.0),
                    best_map=data.get("metrics", {}).get("best_map", 0.0),
                    output_model_path=data.get("output_model_path"),
                    error_message=data.get("error_message"),
                    log=data.get("log", []),
                )
                # Mark any interrupted running jobs as failed
                if job.status == TrainingStatus.RUNNING:
                    job.status = TrainingStatus.FAILED
                    job.error_message = "Interrupted by server restart"
                self._jobs[job.job_id] = job
            except Exception:
                pass  # skip corrupt files


# Singleton
_trainer: Optional[ModelTrainer] = None


def get_model_trainer() -> ModelTrainer:
    global _trainer
    if _trainer is None:
        _trainer = ModelTrainer()
    return _trainer
