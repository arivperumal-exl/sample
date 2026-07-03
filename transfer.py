"""
Verifies ROI weighting is applied correctly.
Run: python debug_roi.py --category engine_wiring
"""
import argparse
import yaml
import numpy as np
import cv2
from pathlib import Path
from PIL import Image
import torch

from src.features.extractor import FeatureExtractor
from src.models.patchcore import PatchCore
from src.data.transforms import get_transforms
from scipy.ndimage import gaussian_filter

parser = argparse.ArgumentParser()
parser.add_argument("--category", default="engine_wiring")
args = parser.parse_args()

cfg      = yaml.safe_load(open("configs/config.yaml"))
category = args.category
roi_cfg  = cfg.get("roi", {}).get(category, {})

print(f"\nROI config for {category}:")
print(roi_cfg)

if not roi_cfg.get("enabled", False):
    print("ROI is DISABLED in config.yaml — enable it first")
    exit()

# Load model
device = torch.device("cpu")
extractor = FeatureExtractor(
    cfg["model"]["backbone"], cfg["model"]["layers"], device
)
patchcore = PatchCore.load(f"outputs/{category}/patchcore.pkl")

# Load a test anomaly image
test_dir = Path(f"data/{category}/test")
bad_dirs  = [d for d in test_dir.iterdir() if d.is_dir() and d.name != "good"]
if not bad_dirs:
    print("No anomaly images found")
    exit()

img_path = next(bad_dirs[0].glob("*.*"))
print(f"\nTesting on: {img_path}")

_, transform, _ = get_transforms(
    cfg["data"]["image_size"], cfg["data"]["center_crop"]
)
img_pil  = Image.open(img_path).convert("RGB")
tensor   = transform(img_pil).unsqueeze(0)

with torch.no_grad():
    fmap = extractor(tensor)
    _, C, h, w = fmap.shape
    patches = fmap.permute(0, 2, 3, 1).reshape(-1, C).numpy()

score_raw, amap_raw = patchcore.predict(patches, (h, w))
amap_raw = gaussian_filter(amap_raw.astype(np.float32), sigma=4)
print(f"\nBefore ROI — max score: {amap_raw.max():.4f}  location: {np.unravel_index(amap_raw.argmax(), amap_raw.shape)}")

# Apply ROI
orig_size   = cfg["data"]["center_crop"]
scale_x     = w / orig_size
scale_y     = h / orig_size
x           = int(roi_cfg["x"]     * scale_x)
y           = int(roi_cfg["y"]     * scale_y)
rw          = int(roi_cfg["width"] * scale_x)
rh          = int(roi_cfg["height"]* scale_y)
outside_w   = roi_cfg.get("outside_weight", 0.0)

weight_map  = np.full((h, w), outside_w, dtype=np.float32)
weight_map[y:y+rh, x:x+rw] = roi_cfg.get("weight", 1.0)

amap_weighted = amap_raw * weight_map
print(f"After  ROI — max score: {amap_weighted.max():.4f}  location: {np.unravel_index(amap_weighted.argmax(), amap_weighted.shape)}")
print(f"ROI region in feature map: x={x}, y={y}, w={rw}, h={rh}")
print(f"Outside weight applied: {outside_w}")

# Visualise side by side
crop = cfg["data"]["center_crop"]
img_np = np.array(img_pil.resize((crop, crop)))

def to_heatmap(amap, size):
    norm = cv2.resize(amap, (size, size))
    mn, mx = norm.min(), norm.max()
    if mx > mn:
        norm = ((norm - mn) / (mx - mn) * 255).astype(np.uint8)
    return cv2.applyColorMap(norm, cv2.COLORMAP_JET)

heatmap_raw      = to_heatmap(amap_raw,      crop)
heatmap_weighted = to_heatmap(amap_weighted, crop)

# Draw ROI box
roi_box = img_np.copy()
cv2.rectangle(roi_box, (roi_cfg["x"], roi_cfg["y"]),
              (roi_cfg["x"]+roi_cfg["width"], roi_cfg["y"]+roi_cfg["height"]),
              (0, 255, 0), 2)
roi_box_bgr = cv2.cvtColor(roi_box, cv2.COLOR_RGB2BGR)

combined = np.concatenate([
    roi_box_bgr,
    heatmap_raw,
    heatmap_weighted,
], axis=1)

# Add labels
cv2.putText(combined, "Original + ROI", (10, 20),
            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255,255,255), 1)
cv2.putText(combined, "Raw Anomaly Map", (crop+10, 20),
            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255,255,255), 1)
cv2.putText(combined, "Weighted Anomaly Map", (crop*2+10, 20),
            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255,255,255), 1)

cv2.imshow("ROI Debug", combined)
cv2.waitKey(0)
cv2.destroyAllWindows()
