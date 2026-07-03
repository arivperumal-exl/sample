def inspect(
    self,
    image: np.ndarray,
    roi_cfg: dict = None,
) -> InspectionResult:
    """
    Run full structural inspection on one image.
    If roi_cfg is provided, inspection is restricted to that region.
    """
    # Crop to ROI before any detection
    if roi_cfg and roi_cfg.get("enabled", False):
        x  = roi_cfg["x"]
        y  = roi_cfg["y"]
        rw = roi_cfg["width"]
        rh = roi_cfg["height"]
        image = image[y:y+rh, x:x+rw]   # crop to ROI only

    annotated = image.copy()
    anomalies = []

    # rest of the method stays exactly the same ...
