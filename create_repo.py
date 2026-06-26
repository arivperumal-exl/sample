"""
Run this script once to scaffold the full autoVI-anomaly-detection repo.
Usage:
    python create_repo.py            # creates ./autoVI-anomaly-detection/
    python create_repo.py --dest /path/to/dir
"""
import argparse, os, textwrap
from pathlib import Path

# ---------------------------------------------------------------------------
# File contents
# ---------------------------------------------------------------------------

FILES = {}

# ── configs/config.yaml ────────────────────────────────────────────────────
FILES["configs/config.yaml"] = """\
data:
  root: ./data
  categories:
    - engine_wiring
    - pipe_clips
    - pipe_staples
  image_size: 256          # resize shorter edge to this
  center_crop: 224         # center crop after resize
  batch_size: 32
  num_workers: 4

model:
  backbone: wide_resnet50_2   # torchvision pretrained backbone
  layers:
    - layer2                  # mid-level features  (spatial ~28x28)
    - layer3                  # high-level features (spatial ~14x14)
  coreset_sampling_ratio: 0.1 # fraction of patches to keep in memory bank
  num_neighbors: 9            # k for kNN anomaly scoring

training:
  device: auto                # auto | cpu | cuda | mps

evaluation:
  threshold_method: roc       # roc (optimal F1 point) | percentile
  threshold_percentile: 95    # used only when threshold_method=percentile
  output_dir: ./outputs
  save_anomaly_maps: true
"""

# ── src/__init__.py ─────────────────────────────────────────────────────────
FILES["src/__init__.py"] = ""

# ── src/data/__init__.py ────────────────────────────────────────────────────
FILES["src/data/__init__.py"] = """\
from .dataset import AutoVIDataset, get_dataloaders
from .transforms import get_transforms
"""

# ── src/data/dataset.py ─────────────────────────────────────────────────────
FILES["src/data/dataset.py"] = '''\
"""
AutoVI dataset loader.

Expected folder structure (per category):
    data/<category>/
        train/
            good/           <- only normal images
        test/
            good/           <- normal test images
            <defect_1>/     <- anomaly images
            <defect_2>/
            ...
        ground_truth/
            <defect_1>/     <- binary masks matching test/<defect_1>
            <defect_2>/
            ...
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Callable, List, Optional, Tuple

import numpy as np
from PIL import Image
from torch.utils.data import DataLoader, Dataset


class AutoVIDataset(Dataset):
    """
    Loads images (and optionally GT masks) for one AutoVI category.

    Args:
        root:       Path to the category folder (e.g. ./data/engine_wiring).
        split:      \'train\' or \'test\'.
        transform:  Transform applied to the PIL image.
        mask_transform: Transform applied to the GT mask (test split only).
    """

    def __init__(
        self,
        root: str | Path,
        split: str,
        transform: Optional[Callable] = None,
        mask_transform: Optional[Callable] = None,
    ):
        assert split in ("train", "test"), "split must be \'train\' or \'test\'"
        self.root = Path(root)
        self.split = split
        self.transform = transform
        self.mask_transform = mask_transform

        self.samples: List[Tuple[Path, Optional[Path], int]] = []
        # Each entry: (image_path, mask_path_or_None, label)
        # label: 0 = normal, 1 = anomaly

        self._load_samples()

    # ------------------------------------------------------------------
    def _load_samples(self) -> None:
        split_dir = self.root / self.split

        if self.split == "train":
            good_dir = split_dir / "good"
            for img_path in sorted(good_dir.glob("*.*")):
                if self._is_image(img_path):
                    self.samples.append((img_path, None, 0))

        else:  # test
            gt_root = self.root / "ground_truth"
            for defect_dir in sorted(split_dir.iterdir()):
                if not defect_dir.is_dir():
                    continue
                label = 0 if defect_dir.name == "good" else 1
                for img_path in sorted(defect_dir.glob("*.*")):
                    if not self._is_image(img_path):
                        continue
                    mask_path: Optional[Path] = None
                    if label == 1:
                        candidate = gt_root / defect_dir.name / img_path.name
                        # Ground-truth masks may have _mask suffix or same name
                        if candidate.exists():
                            mask_path = candidate
                        else:
                            # Try with _mask suffix
                            stem = img_path.stem + "_mask"
                            for ext in (".png", ".jpg", ".bmp"):
                                alt = gt_root / defect_dir.name / (stem + ext)
                                if alt.exists():
                                    mask_path = alt
                                    break
                    self.samples.append((img_path, mask_path, label))

    # ------------------------------------------------------------------
    @staticmethod
    def _is_image(path: Path) -> bool:
        return path.suffix.lower() in {".png", ".jpg", ".jpeg", ".bmp", ".tiff"}

    # ------------------------------------------------------------------
    def __len__(self) -> int:
        return len(self.samples)

    def __getitem__(self, idx: int):
        img_path, mask_path, label = self.samples[idx]

        image = Image.open(img_path).convert("RGB")
        if self.transform is not None:
            image = self.transform(image)

        mask = None
        if mask_path is not None:
            mask = Image.open(mask_path).convert("L")
            if self.mask_transform is not None:
                mask = self.mask_transform(mask)
            else:
                mask = np.array(mask) > 0  # bool ndarray

        return {
            "image": image,
            "mask": mask,          # None for normal images
            "label": label,        # 0 = normal, 1 = anomaly
            "image_path": str(img_path),
        }


# ---------------------------------------------------------------------------
def get_dataloaders(
    root: str | Path,
    transform_train,
    transform_test,
    mask_transform=None,
    batch_size: int = 32,
    num_workers: int = 4,
) -> Tuple[DataLoader, DataLoader]:
    """Return (train_loader, test_loader) for a single category root."""
    train_ds = AutoVIDataset(root, "train", transform=transform_train)
    test_ds  = AutoVIDataset(root, "test",  transform=transform_test,
                             mask_transform=mask_transform)

    train_loader = DataLoader(
        train_ds, batch_size=batch_size, shuffle=False,
        num_workers=num_workers, pin_memory=True, drop_last=False,
    )
    test_loader = DataLoader(
        test_ds, batch_size=1, shuffle=False,
        num_workers=num_workers, pin_memory=True,
    )
    return train_loader, test_loader
'''

# ── src/data/transforms.py ──────────────────────────────────────────────────
FILES["src/data/transforms.py"] = '''\
"""Image and mask transforms for AutoVI."""
from torchvision import transforms


def get_transforms(image_size: int = 256, center_crop: int = 224):
    """
    Returns (train_transform, test_transform, mask_transform).
    Train and test use identical deterministic transforms — no augmentation
    is applied because PatchCore is fit on clean features.
    """
    img_mean = [0.485, 0.456, 0.406]   # ImageNet stats
    img_std  = [0.229, 0.224, 0.225]

    base = transforms.Compose([
        transforms.Resize(image_size, interpolation=transforms.InterpolationMode.BICUBIC),
        transforms.CenterCrop(center_crop),
        transforms.ToTensor(),
        transforms.Normalize(mean=img_mean, std=img_std),
    ])

    mask_tf = transforms.Compose([
        transforms.Resize(image_size, interpolation=transforms.InterpolationMode.NEAREST),
        transforms.CenterCrop(center_crop),
        transforms.ToTensor(),   # [0,1] float tensor, 1 channel
    ])

    return base, base, mask_tf
'''

# ── src/features/__init__.py ────────────────────────────────────────────────
FILES["src/features/__init__.py"] = """\
from .extractor import FeatureExtractor
"""

# ── src/features/extractor.py ───────────────────────────────────────────────
FILES["src/features/extractor.py"] = '''\
"""
Hook-based feature extractor using a pretrained torchvision backbone.

Extracts intermediate layer activations, applies adaptive average pooling
to align spatial sizes, then concatenates into patch-level feature vectors.
"""
from __future__ import annotations

from typing import Dict, List

import torch
import torch.nn as nn
import torch.nn.functional as F
import torchvision.models as tvm


class FeatureExtractor(nn.Module):
    """
    Wraps a pretrained backbone and returns spatially-aligned patch features
    from the requested intermediate layers.

    Args:
        backbone_name: Name of a torchvision model (e.g. \'wide_resnet50_2\').
        layers:        Layer names to tap (e.g. [\'layer2\', \'layer3\']).
        device:        Torch device.
    """

    def __init__(
        self,
        backbone_name: str = "wide_resnet50_2",
        layers: List[str] = ("layer2", "layer3"),
        device: torch.device = torch.device("cpu"),
    ):
        super().__init__()
        self.layers = list(layers)
        self.device = device
        self._features: Dict[str, torch.Tensor] = {}

        # Load pretrained backbone
        weights_enum = tvm.get_model_weights(backbone_name).DEFAULT
        self.backbone = tvm.get_model(backbone_name, weights=weights_enum)
        self.backbone.eval().to(device)

        # Freeze all parameters
        for p in self.backbone.parameters():
            p.requires_grad_(False)

        self._register_hooks()

    # ------------------------------------------------------------------
    def _register_hooks(self) -> None:
        for name, module in self.backbone.named_modules():
            if name in self.layers:
                module.register_forward_hook(self._make_hook(name))

    def _make_hook(self, name: str):
        def hook(module, input, output):   # noqa: ARG001
            self._features[name] = output.detach()
        return hook

    # ------------------------------------------------------------------
    @torch.no_grad()
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """
        Args:
            x: (B, 3, H, W) normalised image tensor.

        Returns:
            patch_features: (B, C_total, h, w) where h, w come from the
                            smallest (deepest) tapped layer and C_total is
                            the sum of channels across tapped layers.
        """
        self._features.clear()
        _ = self.backbone(x.to(self.device))

        feature_maps = [self._features[l] for l in self.layers]

        # Align all maps to the spatial size of the deepest (smallest) layer
        target_h, target_w = feature_maps[-1].shape[2:]
        aligned = []
        for fm in feature_maps:
            if fm.shape[2:] != (target_h, target_w):
                fm = F.adaptive_avg_pool2d(fm, (target_h, target_w))
            aligned.append(fm)

        # (B, C_total, h, w)
        return torch.cat(aligned, dim=1)

    # ------------------------------------------------------------------
    @torch.no_grad()
    def extract_patches(self, x: torch.Tensor) -> torch.Tensor:
        """
        Convenience method: flatten spatial dims to get per-patch vectors.

        Returns:
            (B * h * w, C_total) — each row is one patch feature vector.
        """
        fmap = self.forward(x)           # (B, C, h, w)
        B, C, h, w = fmap.shape
        # (B, C, h*w) -> (B, h*w, C) -> (B*h*w, C)
        return fmap.permute(0, 2, 3, 1).reshape(B * h * w, C)
'''

# ── src/models/__init__.py ──────────────────────────────────────────────────
FILES["src/models/__init__.py"] = """\
from .patchcore import PatchCore
"""

# ── src/models/patchcore.py ─────────────────────────────────────────────────
FILES["src/models/patchcore.py"] = '''\
"""
PatchCore anomaly detection model.

References:
    Roth et al. (2022) "Towards Total Recall in Industrial Anomaly Detection"
    https://arxiv.org/abs/2106.08265

Steps:
    1. fit()  : build a memory bank from normal training patch features;
                apply greedy coreset subsampling to reduce its size.
    2. predict(): for each test image, compute the k-NN distance from every
                  patch to the memory bank; the image score is the max patch
                  distance; the anomaly map is the spatial distance grid.
"""
from __future__ import annotations

import pickle
from pathlib import Path
from typing import Tuple

import numpy as np
import torch
import torch.nn.functional as F
from sklearn.neighbors import NearestNeighbors
from tqdm import tqdm


class PatchCore:
    """
    Args:
        coreset_ratio:  Fraction of training patches to retain (0 < r <= 1).
        num_neighbors:  k for kNN scoring.
    """

    def __init__(self, coreset_ratio: float = 0.1, num_neighbors: int = 9):
        self.coreset_ratio = coreset_ratio
        self.num_neighbors = num_neighbors
        self.memory_bank: np.ndarray | None = None   # (M, C)
        self._knn: NearestNeighbors | None = None

    # ------------------------------------------------------------------
    def fit(self, patch_features: np.ndarray) -> None:
        """
        Build and subsample the memory bank.

        Args:
            patch_features: (N, C) array of all training patch features.
        """
        print(f"  Building memory bank from {len(patch_features):,} patches …")
        subsampled = self._greedy_coreset(patch_features, self.coreset_ratio)
        self.memory_bank = subsampled
        print(f"  Memory bank size after coreset: {len(self.memory_bank):,} patches")

        self._knn = NearestNeighbors(
            n_neighbors=self.num_neighbors,
            algorithm="ball_tree",
            metric="euclidean",
            n_jobs=-1,
        )
        self._knn.fit(self.memory_bank)

    # ------------------------------------------------------------------
    def predict(
        self, patch_features: np.ndarray, spatial_shape: Tuple[int, int]
    ) -> Tuple[float, np.ndarray]:
        """
        Compute image-level anomaly score and pixel-level anomaly map.

        Args:
            patch_features: (h*w, C) patch features for ONE image.
            spatial_shape:  (h, w) spatial grid size.

        Returns:
            score:       Scalar image-level anomaly score.
            anomaly_map: (h, w) float array with per-patch distances.
        """
        assert self._knn is not None, "Call fit() before predict()."
        h, w = spatial_shape

        distances, _ = self._knn.kneighbors(patch_features)  # (h*w, k)
        # Aggregate k neighbours: use mean of top-1 neighbour (PatchCore paper)
        patch_scores = distances[:, 0]                       # (h*w,)
        anomaly_map  = patch_scores.reshape(h, w)
        score        = float(anomaly_map.max())
        return score, anomaly_map

    # ------------------------------------------------------------------
    def save(self, path: str | Path) -> None:
        """Persist memory bank and kNN index to disk."""
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "wb") as f:
            pickle.dump({"memory_bank": self.memory_bank,
                         "coreset_ratio": self.coreset_ratio,
                         "num_neighbors": self.num_neighbors}, f)
        print(f"  Saved model → {path}")

    @classmethod
    def load(cls, path: str | Path) -> "PatchCore":
        """Load a previously saved PatchCore model."""
        with open(path, "rb") as f:
            data = pickle.load(f)
        model = cls(coreset_ratio=data["coreset_ratio"],
                    num_neighbors=data["num_neighbors"])
        model.memory_bank = data["memory_bank"]
        model._knn = NearestNeighbors(
            n_neighbors=model.num_neighbors,
            algorithm="ball_tree",
            metric="euclidean",
            n_jobs=-1,
        )
        model._knn.fit(model.memory_bank)
        return model

    # ------------------------------------------------------------------
    @staticmethod
    def _greedy_coreset(features: np.ndarray, ratio: float) -> np.ndarray:
        """
        Greedy k-center coreset approximation.

        Selects `ceil(ratio * N)` points that maximally cover the feature
        space by iteratively picking the point farthest from the current set.
        Uses random projections to reduce cost from O(N²) to O(N·d_proj).
        """
        n = len(features)
        target = max(1, int(np.ceil(ratio * n)))
        if target >= n:
            return features

        # Random projection to 128 dims for distance approximation
        rng = np.random.default_rng(42)
        proj_dim = min(128, features.shape[1])
        proj = rng.standard_normal((features.shape[1], proj_dim)).astype(np.float32)
        proj /= np.linalg.norm(proj, axis=0, keepdims=True)
        projected = features @ proj                     # (N, proj_dim)

        selected = [rng.integers(0, n)]
        min_dists = np.full(n, np.inf, dtype=np.float32)

        for _ in tqdm(range(target - 1), desc="  Coreset sampling", leave=False):
            last = projected[selected[-1]]
            d = np.linalg.norm(projected - last, axis=1)
            np.minimum(min_dists, d, out=min_dists)
            selected.append(int(np.argmax(min_dists)))

        return features[selected]
'''

# ── src/training/__init__.py ────────────────────────────────────────────────
FILES["src/training/__init__.py"] = """\
from .trainer import Trainer
"""

# ── src/training/trainer.py ─────────────────────────────────────────────────
FILES["src/training/trainer.py"] = '''\
"""
Trainer: extracts patch features from all training images (good only)
and fits a PatchCore memory bank.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import torch
from torch.utils.data import DataLoader
from tqdm import tqdm

from src.features.extractor import FeatureExtractor
from src.models.patchcore import PatchCore


class Trainer:
    """
    Args:
        extractor:  Initialised FeatureExtractor.
        model:      Initialised PatchCore model.
        device:     Torch device.
    """

    def __init__(
        self,
        extractor: FeatureExtractor,
        model: PatchCore,
        device: torch.device,
    ):
        self.extractor = extractor
        self.model = model
        self.device = device

    # ------------------------------------------------------------------
    def fit(self, train_loader: DataLoader) -> None:
        """
        Extract features from all training images and fit PatchCore.

        Args:
            train_loader: DataLoader yielding batches of normal images.
        """
        all_patches = []

        self.extractor.eval()
        with torch.no_grad():
            for batch in tqdm(train_loader, desc="  Extracting train features"):
                images = batch["image"].to(self.device)        # (B, 3, H, W)
                fmap   = self.extractor(images)                # (B, C, h, w)

                B, C, h, w = fmap.shape
                # (B, C, h, w) → (B*h*w, C)
                patches = fmap.permute(0, 2, 3, 1).reshape(-1, C)
                all_patches.append(patches.cpu().numpy())

        all_patches_np = np.concatenate(all_patches, axis=0)  # (N, C)
        self.model.fit(all_patches_np)

    # ------------------------------------------------------------------
    def save(self, save_dir: str | Path, category: str) -> Path:
        """Save the fitted model to <save_dir>/<category>/patchcore.pkl"""
        save_dir = Path(save_dir) / category
        save_dir.mkdir(parents=True, exist_ok=True)
        model_path = save_dir / "patchcore.pkl"
        self.model.save(model_path)
        return model_path
'''

# ── src/evaluation/__init__.py ──────────────────────────────────────────────
FILES["src/evaluation/__init__.py"] = """\
from .evaluator import Evaluator
"""

# ── src/evaluation/evaluator.py ─────────────────────────────────────────────
FILES["src/evaluation/evaluator.py"] = '''\
"""
Evaluator: runs inference on the test set and computes metrics.

Metrics computed:
  Image-level: AUROC, Average Precision, F1 (at optimal threshold)
  Pixel-level: AUROC, Average Precision  (requires ground-truth masks)
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import cv2
import numpy as np
import torch
from scipy.ndimage import gaussian_filter
from sklearn.metrics import (
    average_precision_score,
    f1_score,
    roc_auc_score,
    roc_curve,
)
from torch.utils.data import DataLoader
from tqdm import tqdm

from src.features.extractor import FeatureExtractor
from src.models.patchcore import PatchCore


class Evaluator:
    """
    Args:
        extractor:        Fitted FeatureExtractor.
        model:            Fitted PatchCore model.
        device:           Torch device.
        output_dir:       Directory to write results & visualisations.
        save_anomaly_maps: Whether to save anomaly map PNGs.
    """

    def __init__(
        self,
        extractor: FeatureExtractor,
        model: PatchCore,
        device: torch.device,
        output_dir: str | Path = "./outputs",
        save_anomaly_maps: bool = True,
    ):
        self.extractor = extractor
        self.model = model
        self.device = device
        self.output_dir = Path(output_dir)
        self.save_anomaly_maps = save_anomaly_maps

    # ------------------------------------------------------------------
    def evaluate(
        self, test_loader: DataLoader, category: str
    ) -> Dict[str, float]:
        """
        Run inference and compute all metrics for one category.

        Returns dict with keys: img_auroc, img_ap, img_f1,
                                pix_auroc, pix_ap  (if masks available).
        """
        cat_dir = self.output_dir / category
        cat_dir.mkdir(parents=True, exist_ok=True)

        image_scores: List[float] = []
        image_labels: List[int]   = []
        pixel_scores: List[np.ndarray] = []
        pixel_labels: List[np.ndarray] = []
        spatial_shape: Optional[Tuple[int, int]] = None

        self.extractor.eval()
        with torch.no_grad():
            for batch in tqdm(test_loader, desc=f"  Testing [{category}]"):
                image  = batch["image"].to(self.device)      # (1, 3, H, W)
                label  = int(batch["label"][0])
                mask   = batch["mask"]                       # may be None / tensor

                fmap = self.extractor(image)                 # (1, C, h, w)
                _, C, h, w = fmap.shape
                if spatial_shape is None:
                    spatial_shape = (h, w)

                patches = fmap.permute(0, 2, 3, 1).reshape(-1, C).cpu().numpy()
                score, amap = self.model.predict(patches, (h, w))

                # Smooth anomaly map
                amap = gaussian_filter(amap, sigma=4)

                image_scores.append(score)
                image_labels.append(label)

                if mask is not None and not isinstance(mask, type(None)):
                    m = mask[0].squeeze().numpy() if torch.is_tensor(mask) else mask
                    if m is not None:
                        pixel_scores.append(amap.ravel())
                        pixel_labels.append((m > 0).ravel().astype(int))

                if self.save_anomaly_maps:
                    img_name = Path(batch["image_path"][0]).stem
                    self._save_map(amap, cat_dir / f"{img_name}_amap.png")

        metrics = self._compute_metrics(
            image_scores, image_labels, pixel_scores, pixel_labels
        )

        # Save metrics JSON
        with open(cat_dir / "metrics.json", "w") as f:
            json.dump(metrics, f, indent=2)
        self._print_metrics(category, metrics)
        return metrics

    # ------------------------------------------------------------------
    @staticmethod
    def _compute_metrics(
        img_scores, img_labels, pix_scores, pix_labels
    ) -> Dict[str, float]:
        metrics: Dict[str, float] = {}

        arr_s = np.array(img_scores)
        arr_l = np.array(img_labels)

        if len(np.unique(arr_l)) > 1:
            metrics["img_auroc"] = float(roc_auc_score(arr_l, arr_s))
            metrics["img_ap"]    = float(average_precision_score(arr_l, arr_s))

            # Optimal F1 threshold via ROC curve
            fpr, tpr, thresholds = roc_curve(arr_l, arr_s)
            f1s = [
                f1_score(arr_l, (arr_s >= t).astype(int), zero_division=0)
                for t in thresholds
            ]
            best_t = float(thresholds[int(np.argmax(f1s))])
            metrics["img_f1"]        = float(max(f1s))
            metrics["img_threshold"] = best_t
        else:
            metrics["img_auroc"] = metrics["img_ap"] = metrics["img_f1"] = float("nan")

        if pix_scores:
            all_ps = np.concatenate(pix_scores)
            all_pl = np.concatenate(pix_labels)
            if len(np.unique(all_pl)) > 1:
                metrics["pix_auroc"] = float(roc_auc_score(all_pl, all_ps))
                metrics["pix_ap"]    = float(average_precision_score(all_pl, all_ps))

        return metrics

    # ------------------------------------------------------------------
    @staticmethod
    def _save_map(amap: np.ndarray, path: Path) -> None:
        """Normalise and save anomaly map as a heatmap PNG."""
        a_min, a_max = amap.min(), amap.max()
        if a_max > a_min:
            norm = ((amap - a_min) / (a_max - a_min) * 255).astype(np.uint8)
        else:
            norm = np.zeros_like(amap, dtype=np.uint8)
        heatmap = cv2.applyColorMap(norm, cv2.COLORMAP_JET)
        cv2.imwrite(str(path), heatmap)

    # ------------------------------------------------------------------
    @staticmethod
    def _print_metrics(category: str, metrics: Dict[str, float]) -> None:
        print(f"\n{'─'*50}")
        print(f"  Results — {category}")
        print(f"  Image AUROC : {metrics.get('img_auroc', float('nan')):.4f}")
        print(f"  Image AP    : {metrics.get('img_ap',    float('nan')):.4f}")
        print(f"  Image F1    : {metrics.get('img_f1',    float('nan')):.4f}")
        if "pix_auroc" in metrics:
            print(f"  Pixel AUROC : {metrics.get('pix_auroc', float('nan')):.4f}")
            print(f"  Pixel AP    : {metrics.get('pix_ap',    float('nan')):.4f}")
        print(f"{'─'*50}\n")
'''

# ── src/utils/__init__.py ───────────────────────────────────────────────────
FILES["src/utils/__init__.py"] = """\
from .helpers import get_device, load_config, seed_everything, summarize_results
"""

# ── src/utils/helpers.py ────────────────────────────────────────────────────
FILES["src/utils/helpers.py"] = '''\
"""Utility helpers shared across the pipeline."""
from __future__ import annotations

import json
import random
from pathlib import Path
from typing import Any, Dict

import numpy as np
import torch
import yaml


# ---------------------------------------------------------------------------
def load_config(path: str | Path) -> Dict[str, Any]:
    """Load a YAML config file and return as a nested dict."""
    with open(path) as f:
        return yaml.safe_load(f)


# ---------------------------------------------------------------------------
def get_device(preference: str = "auto") -> torch.device:
    """
    Resolve a torch device.

    Args:
        preference: \'auto\' | \'cpu\' | \'cuda\' | \'mps\'
    """
    if preference == "auto":
        if torch.cuda.is_available():
            return torch.device("cuda")
        if torch.backends.mps.is_available():
            return torch.device("mps")
        return torch.device("cpu")
    return torch.device(preference)


# ---------------------------------------------------------------------------
def seed_everything(seed: int = 42) -> None:
    """Fix random seeds for reproducibility."""
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


# ---------------------------------------------------------------------------
def summarize_results(
    all_metrics: Dict[str, Dict[str, float]],
    output_dir: str | Path,
) -> None:
    """
    Print a summary table and save combined results JSON.

    Args:
        all_metrics: {category: metrics_dict}
        output_dir:  Directory to write summary.json
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    print("\n" + "=" * 60)
    print("  SUMMARY")
    print(f"  {'Category':<20} {'Img AUROC':>10} {'Img F1':>8} {'Pix AUROC':>10}")
    print("=" * 60)

    for cat, m in all_metrics.items():
        print(
            f"  {cat:<20} "
            f"{m.get('img_auroc', float('nan')):>10.4f} "
            f"{m.get('img_f1',    float('nan')):>8.4f} "
            f"{m.get('pix_auroc', float('nan')):>10.4f}"
        )

    print("=" * 60)

    with open(output_dir / "summary.json", "w") as f:
        json.dump(all_metrics, f, indent=2)
    print(f"\n  Saved summary → {output_dir / \'summary.json\'}\n")
'''

# ── main.py ─────────────────────────────────────────────────────────────────
FILES["main.py"] = '''\
"""
AutoVI Anomaly Detection — pipeline entry point.

Usage:
    python main.py                                  # uses configs/config.yaml
    python main.py --config configs/config.yaml
    python main.py --categories engine_wiring       # single category
    python main.py --mode train                     # train only
    python main.py --mode test                      # test only (needs saved model)
"""
from __future__ import annotations

import argparse
from pathlib import Path

import torch

from src.data.dataset import get_dataloaders
from src.data.transforms import get_transforms
from src.evaluation.evaluator import Evaluator
from src.features.extractor import FeatureExtractor
from src.models.patchcore import PatchCore
from src.training.trainer import Trainer
from src.utils.helpers import get_device, load_config, seed_everything, summarize_results


# ---------------------------------------------------------------------------
def parse_args():
    p = argparse.ArgumentParser(description="AutoVI Anomaly Detection")
    p.add_argument("--config",     default="configs/config.yaml")
    p.add_argument("--categories", nargs="+", default=None,
                   help="Override categories from config")
    p.add_argument("--mode",       choices=["train", "test", "all"], default="all")
    return p.parse_args()


# ---------------------------------------------------------------------------
def run_category(
    category: str,
    cfg: dict,
    device: torch.device,
    mode: str,
) -> dict | None:
    """Full train + evaluate loop for one category."""
    data_cfg  = cfg["data"]
    model_cfg = cfg["model"]
    eval_cfg  = cfg["evaluation"]

    root = Path(data_cfg["root"]) / category

    transform_train, transform_test, mask_transform = get_transforms(
        image_size=data_cfg["image_size"],
        center_crop=data_cfg["center_crop"],
    )
    train_loader, test_loader = get_dataloaders(
        root=root,
        transform_train=transform_train,
        transform_test=transform_test,
        mask_transform=mask_transform,
        batch_size=data_cfg["batch_size"],
        num_workers=data_cfg["num_workers"],
    )

    extractor = FeatureExtractor(
        backbone_name=model_cfg["backbone"],
        layers=model_cfg["layers"],
        device=device,
    )
    patchcore = PatchCore(
        coreset_ratio=model_cfg["coreset_sampling_ratio"],
        num_neighbors=model_cfg["num_neighbors"],
    )

    model_path = Path(eval_cfg["output_dir"]) / category / "patchcore.pkl"

    # ── TRAIN ──────────────────────────────────────────────────────────
    if mode in ("train", "all"):
        print(f"\n[TRAIN] {category}")
        trainer = Trainer(extractor=extractor, model=patchcore, device=device)
        trainer.fit(train_loader)
        trainer.save(eval_cfg["output_dir"], category)

    # ── TEST ───────────────────────────────────────────────────────────
    if mode in ("test", "all"):
        if mode == "test":
            print(f"\n[LOAD] {model_path}")
            patchcore = PatchCore.load(model_path)

        print(f"\n[TEST]  {category}")
        evaluator = Evaluator(
            extractor=extractor,
            model=patchcore,
            device=device,
            output_dir=eval_cfg["output_dir"],
            save_anomaly_maps=eval_cfg["save_anomaly_maps"],
        )
        metrics = evaluator.evaluate(test_loader, category)
        return metrics

    return None


# ---------------------------------------------------------------------------
def main():
    args   = parse_args()
    cfg    = load_config(args.config)
    seed_everything(42)

    device = get_device(cfg["training"]["device"])
    print(f"Using device: {device}")

    categories = args.categories or cfg["data"]["categories"]
    all_metrics: dict = {}

    for category in categories:
        metrics = run_category(category, cfg, device, args.mode)
        if metrics:
            all_metrics[category] = metrics

    if all_metrics:
        summarize_results(all_metrics, cfg["evaluation"]["output_dir"])


if __name__ == "__main__":
    main()
'''

# ── requirements.txt ────────────────────────────────────────────────────────
FILES["requirements.txt"] = """\
torch>=2.0.0
torchvision>=0.15.0
numpy>=1.24.0
scikit-learn>=1.3.0
scipy>=1.11.0
opencv-python>=4.8.0
Pillow>=9.5.0
PyYAML>=6.0
tqdm>=4.65.0
"""

# ── .gitignore ──────────────────────────────────────────────────────────────
FILES[".gitignore"] = """\
__pycache__/
*.py[cod]
*.pth
*.pkl
*.egg-info/
.venv/
venv/
outputs/
*.DS_Store
.idea/
.vscode/
"""

# ---------------------------------------------------------------------------
# Scaffold
# ---------------------------------------------------------------------------

def scaffold(dest: Path) -> None:
    for rel_path, content in FILES.items():
        target = dest / rel_path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(textwrap.dedent(content), encoding="utf-8")
        print(f"  created  {rel_path}")

    # Empty __init__ files for sub-packages that may not have one yet
    for pkg in ["src/data", "src/features", "src/models", "src/training",
                "src/evaluation", "src/utils"]:
        init = dest / pkg / "__init__.py"
        if not init.exists():
            init.write_text("", encoding="utf-8")

    print(f"\n✓ Repo created at: {dest.resolve()}\n")
    print("Next steps:")
    print("  1. pip install -r requirements.txt")
    print("  2. Place your data under ./data/ following the expected structure")
    print("  3. python main.py")


# ---------------------------------------------------------------------------
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--dest", default="./autoVI-anomaly-detection",
        help="Where to create the repo (default: ./autoVI-anomaly-detection)",
    )
    args = parser.parse_args()
    scaffold(Path(args.dest))
