score, amap, original_np = run_inference(
    image_pil, extractor, patchcore, cfg
)

# Apply ROI weighting to anomaly map in UI as well
import numpy as np
roi_cfg_cat = cfg.get("roi", {}).get(category, {})
if roi_cfg_cat.get("enabled", False):
    h, w = amap.shape
    orig_size = cfg["data"]["center_crop"]
    scale_x = w / orig_size
    scale_y = h / orig_size

    x  = int(roi_cfg_cat["x"]      * scale_x)
    y  = int(roi_cfg_cat["y"]      * scale_y)
    rw = int(roi_cfg_cat["width"]  * scale_x)
    rh = int(roi_cfg_cat["height"] * scale_y)

    outside_weight = roi_cfg_cat.get("outside_weight", 0.0)
    weight_map = np.full((h, w), outside_weight, dtype=np.float32)
    weight_map[y:y+rh, x:x+rw] = roi_cfg_cat.get("weight", 1.0)

    amap  = amap * weight_map          # weighted map
    score = float(amap.max())          # recompute score
