"""
Adds the Streamlit UI to an existing autoVI-anomaly-detection repo.
Run from the same folder as create_repo.py:

    python add_ui.py                                     # targets ./autoVI-anomaly-detection
    python add_ui.py --dest C:/path/to/autoVI-anomaly-detection
"""
import argparse
import textwrap
from pathlib import Path

FILES = {}

# ── src/visualization/__init__.py ──────────────────────────────────────────
FILES["src/visualization/__init__.py"] = """\
from .visualizer import Visualizer
"""

# ── src/visualization/visualizer.py ────────────────────────────────────────
FILES["src/visualization/visualizer.py"] = '''\
"""
Visualizer: overlays anomaly heatmap on the original image and draws
contours around detected defect regions.
"""
from __future__ import annotations

from typing import Tuple

import cv2
import numpy as np
from PIL import Image
from scipy.ndimage import gaussian_filter


class Visualizer:
    """
    Converts a raw anomaly map into a human-readable overlay image.

    Args:
        alpha:          Heatmap blend strength (0=original only, 1=heatmap only).
        contour_thresh: Fraction of max score above which a region is marked
                        as defective (used for contour drawing).
    """

    def __init__(self, alpha: float = 0.5, contour_thresh: float = 0.5):
        self.alpha = alpha
        self.contour_thresh = contour_thresh

    # ------------------------------------------------------------------
    def make_overlay(
        self,
        original_image: np.ndarray,
        anomaly_map: np.ndarray,
        score: float,
        threshold: float | None = None,
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """
        Build three visualisation panels.

        Args:
            original_image: (H, W, 3) uint8 RGB image.
            anomaly_map:    (h, w) float array of patch-level anomaly scores.
            score:          Image-level anomaly score (scalar).
            threshold:      If provided, draws contours where map > threshold.

        Returns:
            original:   Original image unchanged.
            heatmap:    Colourised anomaly map resized to original resolution.
            overlay:    Heatmap blended onto original + contours if threshold given.
        """
        H, W = original_image.shape[:2]

        # Smooth and normalise anomaly map
        amap = gaussian_filter(anomaly_map.astype(np.float32), sigma=4)
        amap_norm = self._normalise(amap)                        # [0, 1]

        # Resize anomaly map to original image size
        amap_resized = cv2.resize(amap_norm, (W, H),
                                  interpolation=cv2.INTER_LINEAR)

        # Colourised heatmap (BGR → RGB for display)
        heatmap_bgr = cv2.applyColorMap(
            (amap_resized * 255).astype(np.uint8), cv2.COLORMAP_JET
        )
        heatmap_rgb = cv2.cvtColor(heatmap_bgr, cv2.COLOR_BGR2RGB)

        # Blend onto original
        overlay = cv2.addWeighted(
            original_image, 1 - self.alpha,
            heatmap_rgb,    self.alpha,
            0,
        )

        # Draw contours where anomaly exceeds threshold
        if threshold is not None:
            norm_thresh = self._normalise_value(threshold, amap)
            binary = (amap_resized > norm_thresh).astype(np.uint8) * 255
            contours, _ = cv2.findContours(
                binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
            )
            overlay = cv2.drawContours(overlay.copy(), contours, -1,
                                       (255, 0, 0), 2)   # red contours

        return original_image, heatmap_rgb, overlay

    # ------------------------------------------------------------------
    def make_side_by_side(
        self,
        original: np.ndarray,
        heatmap: np.ndarray,
        overlay: np.ndarray,
        score: float,
        label: str = "",
    ) -> np.ndarray:
        """
        Concatenate original | heatmap | overlay horizontally with labels.

        Returns:
            (H, 3*W, 3) uint8 RGB image.
        """
        H, W = original.shape[:2]

        def add_label(img: np.ndarray, text: str) -> np.ndarray:
            out = img.copy()
            cv2.putText(out, text, (10, 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2,
                        cv2.LINE_AA)
            return out

        status = f"ANOMALY ({score:.3f})" if label == "anomaly" else f"NORMAL ({score:.3f})"
        panels = [
            add_label(original, "Original"),
            add_label(heatmap,  "Anomaly Map"),
            add_label(overlay,  status),
        ]
        return np.concatenate(panels, axis=1)

    # ------------------------------------------------------------------
    @staticmethod
    def _normalise(arr: np.ndarray) -> np.ndarray:
        mn, mx = arr.min(), arr.max()
        if mx > mn:
            return (arr - mn) / (mx - mn)
        return np.zeros_like(arr)

    @staticmethod
    def _normalise_value(value: float, ref_arr: np.ndarray) -> float:
        mn, mx = ref_arr.min(), ref_arr.max()
        if mx > mn:
            return (value - mn) / (mx - mn)
        return 0.0
'''

# ── app.py ──────────────────────────────────────────────────────────────────
FILES["app.py"] = '''\
"""
Streamlit UI for AutoVI anomaly detection.

Run:
    streamlit run app.py

Requires trained models in outputs/<category>/patchcore.pkl
"""
from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np
import streamlit as st
import torch
import yaml
from PIL import Image

from src.data.transforms import get_transforms
from src.features.extractor import FeatureExtractor
from src.models.patchcore import PatchCore
from src.visualization.visualizer import Visualizer

# ---------------------------------------------------------------------------
# Config & constants
# ---------------------------------------------------------------------------
CONFIG_PATH = "configs/config.yaml"

def load_config():
    with open(CONFIG_PATH) as f:
        return yaml.safe_load(f)

@st.cache_resource
def load_model(category: str, model_cfg: dict, device: torch.device):
    """Load extractor + PatchCore for a category (cached across reruns)."""
    model_path = Path("outputs") / category / "patchcore.pkl"
    if not model_path.exists():
        return None, None

    extractor = FeatureExtractor(
        backbone_name=model_cfg["backbone"],
        layers=model_cfg["layers"],
        device=device,
    )
    patchcore = PatchCore.load(model_path)
    return extractor, patchcore

def get_device() -> torch.device:
    if torch.cuda.is_available():
        return torch.device("cuda")
    if torch.backends.mps.is_available():
        return torch.device("mps")
    return torch.device("cpu")

# ---------------------------------------------------------------------------
# Inference
# ---------------------------------------------------------------------------
def run_inference(image_pil: Image.Image, extractor, patchcore, cfg):
    """Return (score, anomaly_map, original_np)."""
    data_cfg = cfg["data"]
    _, transform_test, _ = get_transforms(
        image_size=data_cfg["image_size"],
        center_crop=data_cfg["center_crop"],
    )

    device = extractor.device
    tensor = transform_test(image_pil).unsqueeze(0).to(device)  # (1,3,H,W)

    with torch.no_grad():
        fmap = extractor(tensor)                                 # (1,C,h,w)
        _, C, h, w = fmap.shape
        patches = fmap.permute(0, 2, 3, 1).reshape(-1, C).cpu().numpy()

    score, amap = patchcore.predict(patches, (h, w))

    # Original image as numpy RGB (cropped to match transform)
    crop = data_cfg["center_crop"]
    original_np = np.array(
        image_pil.resize((data_cfg["image_size"], data_cfg["image_size"]),
                         Image.BICUBIC).crop(
            (
                (data_cfg["image_size"] - crop) // 2,
                (data_cfg["image_size"] - crop) // 2,
                (data_cfg["image_size"] + crop) // 2,
                (data_cfg["image_size"] + crop) // 2,
            )
        )
    )
    return score, amap, original_np

# ---------------------------------------------------------------------------
# UI
# ---------------------------------------------------------------------------
def main():
    st.set_page_config(
        page_title="AutoVI Anomaly Detection",
        page_icon="🔍",
        layout="wide",
    )

    st.title("🔍 AutoVI Anomaly Detection")
    st.caption("Upload an image to detect and localise defects.")

    cfg    = load_config()
    device = get_device()

    # ── Sidebar ────────────────────────────────────────────────────────
    st.sidebar.header("Settings")

    category = st.sidebar.selectbox(
        "Component category",
        cfg["data"]["categories"],
    )

    threshold = st.sidebar.slider(
        "Anomaly threshold (for contour drawing)",
        min_value=0.0, max_value=1.0, value=0.5, step=0.01,
    )

    alpha = st.sidebar.slider(
        "Heatmap opacity",
        min_value=0.1, max_value=0.9, value=0.5, step=0.05,
    )

    st.sidebar.markdown("---")
    st.sidebar.markdown(
        "**Model path:** `outputs/<category>/patchcore.pkl`  \n"
        "Run `python main.py` to train models first."
    )

    # ── Load model ─────────────────────────────────────────────────────
    extractor, patchcore = load_model(category, cfg["model"], device)

    if extractor is None:
        st.error(
            f"No trained model found for **{category}**.  \n"
            f"Run `python main.py --categories {category}` to train it first."
        )
        return

    # ── Upload ─────────────────────────────────────────────────────────
    uploaded = st.file_uploader(
        "Upload an image", type=["png", "jpg", "jpeg", "bmp"]
    )

    if uploaded is None:
        st.info("Upload an image to start inspection.")
        return

    image_pil = Image.open(uploaded).convert("RGB")

    # ── Inference ──────────────────────────────────────────────────────
    with st.spinner("Running inference …"):
        score, amap, original_np = run_inference(
            image_pil, extractor, patchcore, cfg
        )

    visualizer = Visualizer(alpha=alpha, contour_thresh=threshold)

    # Determine label using threshold on normalised score
    # (normalise score relative to a rough range — adjust per dataset)
    label = "anomaly" if score > threshold else "normal"

    original, heatmap, overlay = visualizer.make_overlay(
        original_np, amap, score,
        threshold=score * threshold if label == "anomaly" else None,
    )

    # ── Display ────────────────────────────────────────────────────────
    # Score banner
    if label == "anomaly":
        st.error(f"⚠️  **ANOMALY DETECTED** — Score: `{score:.4f}`")
    else:
        st.success(f"✅  **NORMAL** — Score: `{score:.4f}`")

    # Three-panel view
    col1, col2, col3 = st.columns(3)
    with col1:
        st.subheader("Original")
        st.image(original, use_container_width=True)
    with col2:
        st.subheader("Anomaly Map")
        st.image(heatmap, use_container_width=True)
    with col3:
        st.subheader("Defect Location")
        st.image(overlay, use_container_width=True)

    # Anomaly map details
    with st.expander("Details"):
        st.write(f"**Image-level score:** {score:.6f}")
        st.write(f"**Anomaly map shape:** {amap.shape}")
        st.write(f"**Max patch score:** {amap.max():.6f}")
        st.write(f"**Mean patch score:** {amap.mean():.6f}")
        st.write(f"**Device:** {device}")


if __name__ == "__main__":
    main()
'''

# ── requirements.txt (updated) ──────────────────────────────────────────────
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
streamlit>=1.32.0
"""

# ---------------------------------------------------------------------------
def scaffold(dest: Path) -> None:
    for rel_path, content in FILES.items():
        target = dest / rel_path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(textwrap.dedent(content), encoding="utf-8")
        print(f"  created  {rel_path}")
    print(f"\n✓ UI files added to: {dest.resolve()}")
    print("\nNext steps:")
    print("  1. pip install streamlit")
    print("  2. streamlit run app.py")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--dest", default="./autoVI-anomaly-detection",
        help="Path to your existing repo (default: ./autoVI-anomaly-detection)",
    )
    args = parser.parse_args()
    scaffold(Path(args.dest))
