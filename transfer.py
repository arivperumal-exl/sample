from src.inspection.structural_inspector import StructuralInspector

tab1, tab2 = st.tabs(["Anomaly Detection", "Structural Inspection"])

with tab2:
    st.subheader("Engine Wiring Structural Inspection")
    st.caption("Checks: blue hoop presence, fastenings, wire containment")

    uploaded_struct = st.file_uploader(
        "Upload engine wiring image",
        type=["png", "jpg", "jpeg"],
        key="struct_upload"
    )

    # Tuning sliders
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
