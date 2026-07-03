with st.expander("Tuning"):
    blue_low   = st.slider("Blue hue low",       80,  120,  95)
    blue_high  = st.slider("Blue hue high",      120, 140, 130)
    min_hoop   = st.slider("Min hoop area",      100, 1000, 200)
    min_clip   = st.slider("Min clip area",      100, 1000, 300)
    max_clip   = st.slider("Max clip area",     1000, 10000, 5000)
    brightness = st.slider("Clip min brightness", 150, 240, 180)
