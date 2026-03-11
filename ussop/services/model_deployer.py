"""
Model Deployment Service for Ussop
Handles hot-swap of fine-tuned models with rollback capability.
"""
import json
import shutil
import threading
from pathlib import Path
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from datetime import datetime, timezone

import torch

from config.settings import settings


@dataclass
class ModelVersion:
    """Metadata for a deployed model version."""
    version_id: str
    created_at: str
    model_path: str
    base_model: str
    map_score: float
    val_loss: float
    training_job_id: str
    is_active: bool = False
    description: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "version_id": self.version_id,
            "created_at": self.created_at,
            "model_path": self.model_path,
            "base_model": self.base_model,
            "map_score": self.map_score,
            "val_loss": self.val_loss,
            "training_job_id": self.training_job_id,
            "is_active": self.is_active,
            "description": self.description,
        }


class ModelDeployer:
    """
    Manages model versions and hot-swapping.

    Directory layout under settings.MODELS_DIR:
        deployed/
            active.pt          <- currently active fine-tuned weights
            registry.json      <- version history
            versions/
                <version_id>.pt
    """

    def __init__(self):
        self._deploy_dir = settings.MODELS_DIR / "deployed"
        self._versions_dir = self._deploy_dir / "versions"
        self._registry_path = self._deploy_dir / "registry.json"
        self._deploy_dir.mkdir(parents=True, exist_ok=True)
        self._versions_dir.mkdir(exist_ok=True)
        self._lock = threading.Lock()
        self._versions: Dict[str, ModelVersion] = {}
        self._inspector_ref = None  # injected after startup
        self._load_registry()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def deploy_from_job(
        self,
        job_id: str,
        model_path: str,
        map_score: float,
        val_loss: float,
        auto_activate: bool = True,
        description: str = "",
    ) -> ModelVersion:
        """
        Register a trained model and optionally activate it.
        Only activates if mAP improves over current active model.
        """
        import uuid
        version_id = str(uuid.uuid4())[:8]

        # Copy weights to versioned location
        src = Path(model_path)
        if not src.exists():
            raise FileNotFoundError(f"Model checkpoint not found: {model_path}")

        dst = self._versions_dir / f"{version_id}.pt"
        shutil.copy(src, dst)

        version = ModelVersion(
            version_id=version_id,
            created_at=datetime.now(timezone.utc).replace(tzinfo=None).isoformat(),
            model_path=str(dst),
            base_model="fasterrcnn_mobilenet_v3_large_fpn",
            map_score=map_score,
            val_loss=val_loss,
            training_job_id=job_id,
            is_active=False,
            description=description,
        )

        with self._lock:
            self._versions[version_id] = version

        if auto_activate:
            active = self._get_active_version()
            if active is None or map_score > active.map_score:
                self.activate_version(version_id)
            else:
                version.description += (
                    f" [Not activated: mAP {map_score:.3f} <= current {active.map_score:.3f}]"
                )

        self._save_registry()
        return version

    def activate_version(self, version_id: str) -> bool:
        """
        Hot-swap the active model to the given version.
        Triggers InspectionService to reload weights.
        """
        with self._lock:
            version = self._versions.get(version_id)
            if not version:
                return False

            # Deactivate current
            for v in self._versions.values():
                v.is_active = False

            # Copy to active slot
            active_path = self._deploy_dir / "active.pt"
            shutil.copy(version.model_path, active_path)
            version.is_active = True

        self._save_registry()

        # Hot-reload the inspector's model
        if self._inspector_ref is not None:
            try:
                self._inspector_ref.reload_finetuned_weights(str(active_path))
            except Exception as e:
                print(f"[Deployer] Hot-swap warning: {e}")

        print(f"[Deployer] Activated model version {version_id} (mAP={version.map_score:.3f})")
        return True

    def rollback(self) -> Optional[str]:
        """
        Activate the previous model version (by created_at order).
        Returns the activated version_id or None.
        """
        with self._lock:
            sorted_v = sorted(
                self._versions.values(), key=lambda v: v.created_at, reverse=True
            )
            active_idx = next(
                (i for i, v in enumerate(sorted_v) if v.is_active), None
            )
            if active_idx is None or active_idx + 1 >= len(sorted_v):
                return None
            prev = sorted_v[active_idx + 1]

        self.activate_version(prev.version_id)
        return prev.version_id

    def list_versions(self) -> List[Dict[str, Any]]:
        with self._lock:
            return [
                v.to_dict()
                for v in sorted(
                    self._versions.values(), key=lambda v: v.created_at, reverse=True
                )
            ]

    def get_active_version(self) -> Optional[Dict[str, Any]]:
        v = self._get_active_version()
        return v.to_dict() if v else None

    def delete_version(self, version_id: str) -> bool:
        """Delete a non-active version to free disk space."""
        with self._lock:
            version = self._versions.get(version_id)
            if not version or version.is_active:
                return False
            path = Path(version.model_path)
            if path.exists():
                path.unlink()
            del self._versions[version_id]

        self._save_registry()
        return True

    def register_inspector(self, inspector):
        """Inject InspectionService reference for hot-swap."""
        self._inspector_ref = inspector

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _get_active_version(self) -> Optional[ModelVersion]:
        return next((v for v in self._versions.values() if v.is_active), None)

    def _save_registry(self):
        with self._lock:
            data = {v_id: v.to_dict() for v_id, v in self._versions.items()}
        with open(self._registry_path, "w") as f:
            json.dump(data, f, indent=2)

    def _load_registry(self):
        if not self._registry_path.exists():
            return
        try:
            with open(self._registry_path) as f:
                data = json.load(f)
            for v_id, v_data in data.items():
                self._versions[v_id] = ModelVersion(**{
                    k: v_data[k] for k in ModelVersion.__dataclass_fields__
                    if k in v_data
                })
        except Exception as e:
            print(f"[Deployer] Registry load error: {e}")


# Singleton
_deployer: Optional[ModelDeployer] = None


def get_model_deployer() -> ModelDeployer:
    global _deployer
    if _deployer is None:
        _deployer = ModelDeployer()
    return _deployer
