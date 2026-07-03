if uploaded_struct:
    img_pil = Image.open(uploaded_struct).convert("RGB")
    
    # Resize to same size as anomaly detection so ROI coordinates match
    crop = cfg["data"]["center_crop"]
    img_pil = img_pil.resize((crop, crop), Image.BICUBIC)
    img = np.array(img_pil)

    roi_cfg_cat = cfg.get("roi", {}).get("engine_wiring", {})
    
    inspector = StructuralInspector(
        blue_hue_low=blue_low,
        blue_hue_high=blue_high,
        min_hoop_area=min_hoop,
    )
    result = inspector.inspect(img, roi_cfg=roi_cfg_cat)
