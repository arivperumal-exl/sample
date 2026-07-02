# select_roi.py
import cv2
import yaml
from pathlib import Path
import argparse

cfg = yaml.safe_load(open("configs/config.yaml"))
categories = cfg["data"]["categories"]

print("Available categories:")
for i, cat in enumerate(categories):
    print(f"  {i+1}. {cat}")

choice = input("\nEnter category number: ")
category = categories[int(choice) - 1]

crop = cfg["data"]["center_crop"]

sample_dir = Path(f"data/{category}/train/good")
images = list(sample_dir.glob("*.*"))

print(f"\nAvailable images in {category}:")
for i, img in enumerate(images[:10]):   # show first 10
    print(f"  {i+1}. {img.name}")

img_choice = input("\nEnter image number: ")
img_path = images[int(img_choice) - 1]

img = cv2.imread(str(img_path))
img = cv2.resize(img, (crop, crop))

print("\nDraw a rectangle with your mouse. Press ENTER to confirm, R to reset.")
roi = cv2.selectROI("Select ROI", img, fromCenter=False, showCrosshair=True)
cv2.destroyAllWindows()

x, y, w, h = int(roi[0]), int(roi[1]), int(roi[2]), int(roi[3])

print(f"\nCopy these to configs/config.yaml:")
print(f"""
roi:
  {category}:
    enabled: true
    x: {x}
    y: {y}
    width: {w}
    height: {h}
    weight: 1.0
    outside_weight: 0.1
""")
