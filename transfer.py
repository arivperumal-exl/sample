roi_cfg_cat = cfg.get("roi", {}).get("engine_wiring", {})

result = inspector.inspect(
    img,
    roi_cfg=roi_cfg_cat,    # ← add this
)
