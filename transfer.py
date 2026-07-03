if uploaded_struct:
    img_pil = Image.open(uploaded_struct).convert("RGB")
    img = np.array(img_pil)                          # full resolution image
    H, W = img.shape[:2]

    crop = cfg["data"]["center_crop"]                # 224

    # Scale ROI coordinates from 224x224 space to full image size
    roi_cfg_cat = cfg.get("roi", {}).get("engine_wiring", {})
    scaled_roi  = {}
    if roi_cfg_cat.get("enabled", False):
        scale_x = W / crop
        scale_y = H / crop
        scaled_roi = {
            "enabled":        True,
            "x":              int(roi_cfg_cat["x"]      * scale_x),
            "y":              int(roi_cfg_cat["y"]      * scale_y),
            "width":          int(roi_cfg_cat["width"]  * scale_x),
            "height":         int(roi_cfg_cat["height"] * scale_y),
            "weight":         roi_cfg_cat.get("weight", 1.0),
            "outside_weight": roi_cfg_cat.get("outside_weight", 0.0),
        }

    inspector = StructuralInspector(
        blue_hue_low=blue_low,
        blue_hue_high=blue_high,
        min_hoop_area=min_hoop,
    )
    result = inspector.inspect(img, roi_cfg=scaled_roi)
