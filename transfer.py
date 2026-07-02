"""
Run this script to interactively select ROI on a sample image.
Draw a rectangle on the image — coordinates are printed to terminal.

Usage:
    python select_roi.py --category engine_wiring
"""
import argparse
from pathlib import Path
import streamlit as st
from streamlit_drawable_canvas import st_canvas
from PIL import Image
import yaml

parser = argparse.ArgumentParser()
parser.add_argument("--category", default="engine_wiring")
args, _ = parser.parse_known_args()

cfg = yaml.safe_load(open("configs/config.yaml"))
crop = cfg["data"]["center_crop"]

st.title(f"ROI Selector — {args.category}")
st.write("Draw a rectangle on the region you want to prioritise. Copy the coordinates to config.yaml")

# Load a sample good image
sample_dir = Path(f"data/{args.category}/train/good")
images = list(sample_dir.glob("*.*"))
if not images:
    st.error("No training images found")
    st.stop()

selected = st.selectbox("Select sample image", [p.name for p in images])
img_path = sample_dir / selected
img = Image.open(img_path).convert("RGB").resize((crop, crop))

st.subheader("Draw rectangle on the region to prioritise")
canvas = st_canvas(
    fill_color="rgba(255, 0, 0, 0.1)",
    stroke_width=2,
    stroke_color="#FF0000",
    background_image=img,
    drawing_mode="rect",
    width=crop,
    height=crop,
    key="roi_canvas",
)

if canvas.json_data is not None:
    objects = canvas.json_data.get("objects", [])
    if objects:
        rect = objects[-1]   # use the last drawn rectangle
        x  = int(rect["left"])
        y  = int(rect["top"])
        w  = int(rect["width"])
        h  = int(rect["height"])

        st.success("ROI Coordinates — copy these to configs/config.yaml")
        st.code(f"""
roi:
  {args.category}:
    enabled: true
    x: {x}
    y: {y}
    width: {w}
    height: {h}
    weight: 1.0
    outside_weight: 0.1
        """)
        st.write(f"x={x}, y={y}, width={w}, height={h}")
