# debug_hsv.py
import cv2
import numpy as np
from pathlib import Path

img_path = next(Path("data/engine_wiring/train/good").glob("*.*"))
img = cv2.imread(str(img_path))
hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)

# Print HSV values at mouse click
def mouse_callback(event, x, y, flags, param):
    if event == cv2.EVENT_LBUTTONDOWN:
        h, s, v = hsv[y, x]
        print(f"Clicked at ({x},{y}) → HSV: ({h}, {s}, {v})")

cv2.imshow("Click on the blue hoop", img)
cv2.setMouseCallback("Click on the blue hoop", mouse_callback)
cv2.waitKey(0)
cv2.destroyAllWindows()
