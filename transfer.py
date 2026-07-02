def apply_roi(
    self,
    anomaly_map: np.ndarray,
    roi_cfg: dict,
    spatial_shape: tuple,
) -> np.ndarray:
    """Apply weighted mask — full weight inside ROI, low weight outside."""
    if not roi_cfg.get("enabled", False):
        return anomaly_map

    h, w = spatial_shape
    orig_size = 224

    scale_x = w / orig_size
    scale_y = h / orig_size

    x  = int(roi_cfg["x"]      * scale_x)
    y  = int(roi_cfg["y"]      * scale_y)
    rw = int(roi_cfg["width"]  * scale_x)
    rh = int(roi_cfg["height"] * scale_y)

    outside_weight = roi_cfg.get("outside_weight", 0.1)
    weight_map = np.full((h, w), outside_weight, dtype=np.float32)
    weight_map[y:y+rh, x:x+rw] = roi_cfg.get("weight", 1.0)

    return anomaly_map * weight_map
