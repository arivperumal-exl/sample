st.title(f"🔍 Anomaly Detection — {category}")

tab1, tab2 = st.tabs(["Anomaly Detection", "Structural Inspection"])

with tab1:
    # ── Upload ─────────────────────────────────────────────────────────
    uploaded = st.file_uploader(
        "Upload an image", type=["png", "jpg", "jpeg", "bmp"]
    )

    if uploaded is None:
        st.info("Upload an image to start inspection.")
    else:
        image_pil = Image.open(uploaded).convert("RGB")

        with st.spinner("Running inference …"):
            score, amap, original_np = run_inference(
                image_pil, extractor, patchcore, cfg
            )

        # Apply ROI weighting
        roi_cfg_cat = cfg.get("roi", {}).get(category, {})
        if roi_cfg_cat.get("enabled", False):
            h, w = amap.shape
            orig_size   = cfg["data"]["center_crop"]
            scale_x     = w / orig_size
            scale_y     = h / orig_size
            x           = int(roi_cfg_cat["x"]      * scale_x)
            y           = int(roi_cfg_cat["y"]      * scale_y)
            rw          = int(roi_cfg_cat["width"]  * scale_x)
            rh          = int(roi_cfg_cat["height"] * scale_y)
            outside_weight = roi_cfg_cat.get("outside_weight", 0.0)
            weight_map  = np.full((h, w), outside_weight, dtype=np.float32)
            weight_map[y:y+rh, x:x+rw] = roi_cfg_cat.get("weight", 1.0)
            amap        = amap * weight_map
            score       = float(amap.max())

        metrics_path = Path("outputs") / category / "metrics.json"
        if metrics_path.exists():
            with open(metrics_path) as f:
                m = json.load(f)
            learned_threshold = m.get("img_threshold", threshold)
        else:
            learned_threshold = threshold

        label = "anomaly" if score > learned_threshold else "normal"

        visualizer = Visualizer(alpha=alpha, contour_thresh=threshold)
        original, heatmap, overlay, bbox = visualizer.make_overlay(
            original_np, amap, score,
            threshold=score * threshold if label == "anomaly" else None,
        )

        if label == "anomaly":
            st.error(f"⚠️  **ANOMALY DETECTED** — Score: `{score:.4f}`")
            col1, col2, col3 = st.columns(3)
            with col1:
                st.subheader("Original")
                st.image(original, use_column_width=True)
            with col2:
                st.subheader("Anomaly Map")
                st.image(heatmap, use_column_width=True)
            with col3:
                st.subheader("Defect Location")
                st.image(overlay, use_column_width=True)
            if bbox is not None:
                x, y, w, h = bbox
                st.info(
                    f"📦 **Defect Region** — "
                    f"Top-left: `({x}, {y})` | "
                    f"Width: `{w}px` | Height: `{h}px`"
                )
        else:
            st.success(f"✅  **NORMAL** — Score: `{score:.4f}`")
            st.image(original, width=300)

with tab2:
    st.subheader("Engine Wiring Structural Inspection")
    st.caption("Checks: blue hoop presence, fastenings, wire containment")

    uploaded_struct = st.file_uploader(
        "Upload engine wiring image",
        type=["png", "jpg", "jpeg"],
        key="struct_upload"
    )

    with st.expander("Tuning"):
        blue_low  = st.slider("Blue hue low",  80, 110, 90)
        blue_high = st.slider("Blue hue high", 120, 140, 130)
        min_hoop  = st.slider("Min hoop area", 100, 2000, 500)

    if uploaded_struct:
        img = np.array(Image.open(uploaded_struct).convert("RGB"))
        inspector = StructuralInspector(
            blue_hue_low=blue_low,
            blue_hue_high=blue_high,
            min_hoop_area=min_hoop,
        )
        result = inspector.inspect(img)

        if result.passed:
            st.success("✅ PASS — All checks passed")
        else:
            st.error("⚠️ FAIL — Anomalies detected")
            for a in result.anomalies:
                st.write(f"• {a}")

        st.image(result.annotated_image, use_column_width=True)

        with st.expander("Details"):
            st.write(f"**Hoop found:** {result.hoop_found}")
            st.write(f"**Fastenings found:** {result.fastenings_found}")
            st.write(f"**Wires outside hoop:** {result.wires_outside_hoop}")
