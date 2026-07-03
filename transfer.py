"""
Engine wiring structural inspector.

Checks:
1. Two metal clips are present
2. Blue hoop is present
3. Blue hoop is positioned between the two clips
"""
import cv2
import numpy as np
from dataclasses import dataclass, field
from typing import List, Optional, Tuple


@dataclass
class InspectionResult:
    passed: bool
    anomalies: List[str]
    hoop_found: bool
    clips_found: int
    hoop_between_clips: bool
    annotated_image: np.ndarray


class StructuralInspector:

    def __init__(
        self,
        blue_hue_low:  int = 95,
        blue_hue_high: int = 130,
        min_hoop_area: int = 200,
        min_clip_area: int = 300,
    ):
        self.blue_hue_low  = blue_hue_low
        self.blue_hue_high = blue_hue_high
        self.min_hoop_area = min_hoop_area
        self.min_clip_area = min_clip_area

    # ------------------------------------------------------------------
    def inspect(
        self,
        image: np.ndarray,
        roi_cfg: dict = None,
    ) -> InspectionResult:

        annotated = image.copy()
        anomalies = []

        # Extract ROI region for detection
        if roi_cfg and roi_cfg.get("enabled", False):
            x  = roi_cfg["x"]
            y  = roi_cfg["y"]
            rw = roi_cfg["width"]
            rh = roi_cfg["height"]
            region = image[y:y+rh, x:x+rw]

            # Draw yellow ROI box on full image
            cv2.rectangle(annotated, (x, y), (x+rw, y+rh), (0, 255, 255), 2)
            cv2.putText(annotated, "ROI", (x, y-8),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1)
        else:
            region = image
            x, y = 0, 0

        # ── Step 1: Detect blue hoop ───────────────────────────────────
        hoop_contour = self._detect_blue_hoop(region)
        hoop_found   = hoop_contour is not None

        if not hoop_found:
            anomalies.append("Blue hoop not found")
        else:
            shifted = hoop_contour + np.array([x, y])
            cv2.drawContours(annotated, [shifted], -1, (255, 0, 0), 2)
            M = cv2.moments(shifted)
            if M["m00"] > 0:
                cx = int(M["m10"] / M["m00"])
                cy = int(M["m01"] / M["m00"])
                cv2.putText(annotated, "Blue Hoop", (cx - 30, cy - 10),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 0), 2)

        # ── Step 2: Detect metal clips ─────────────────────────────────
        clips = self._detect_clips(region, hoop_contour)
        clips_found = len(clips)

        if clips_found < 2:
            anomalies.append(f"Expected 2 clips, found {clips_found}")

        for i, (cx2, cy2, cw, ch) in enumerate(clips):
            cv2.rectangle(annotated,
                          (cx2+x, cy2+y), (cx2+x+cw, cy2+y+ch),
                          (0, 165, 255), 2)
            cv2.putText(annotated, f"Clip {i+1}", (cx2+x, cy2+y-5),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 165, 255), 2)

        # ── Step 3: Check hoop is between clips ────────────────────────
        hoop_between = False
        if hoop_found and clips_found >= 2:
            hoop_between = self._is_hoop_between_clips(
                hoop_contour, clips
            )
            if not hoop_between:
                anomalies.append("Blue hoop is not between the two clips")

        passed = len(anomalies) == 0

        # Result banner
        color  = (0, 200, 0) if passed else (0, 0, 255)
        status = "PASS" if passed else "FAIL"
        cv2.rectangle(annotated, (0, 0), (annotated.shape[1], 35), color, -1)
        cv2.putText(annotated, status, (10, 25),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)

        return InspectionResult(
            passed=passed,
            anomalies=anomalies,
            hoop_found=hoop_found,
            clips_found=clips_found,
            hoop_between_clips=hoop_between,
            annotated_image=annotated,
        )

    # ------------------------------------------------------------------
    def _detect_blue_hoop(
        self, region: np.ndarray
    ) -> Optional[np.ndarray]:
        """Detect blue hoop using HSV color segmentation."""
        hsv   = cv2.cvtColor(region, cv2.COLOR_RGB2HSV)
        lower = np.array([self.blue_hue_low,  80,  50])
        upper = np.array([self.blue_hue_high, 255, 255])
        mask  = cv2.inRange(hsv, lower, upper)

        kernel = np.ones((5, 5), np.uint8)
        mask   = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
        mask   = cv2.morphologyEx(mask, cv2.MORPH_OPEN,  kernel)

        contours, _ = cv2.findContours(
            mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
        )
        valid = [c for c in contours
                 if cv2.contourArea(c) > self.min_hoop_area]
        if not valid:
            return None

        return max(valid, key=cv2.contourArea)

    # ------------------------------------------------------------------
    def _detect_clips(
        self,
        region: np.ndarray,
        hoop_contour: Optional[np.ndarray],
    ) -> List[Tuple[int, int, int, int]]:
        """
        Detect metal clips using silver/grey color segmentation.
        Clips are metallic rectangular clamps.
        """
        hsv = cv2.cvtColor(region, cv2.COLOR_RGB2HSV)

        # Silver/metallic = low saturation, high brightness
        lower_silver = np.array([0,   0,  150])
        upper_silver = np.array([180, 50, 255])
        mask = cv2.inRange(hsv, lower_silver, upper_silver)

        # Remove blue hoop region from clip detection
        if hoop_contour is not None:
            hoop_mask = np.zeros(region.shape[:2], dtype=np.uint8)
            cv2.drawContours(hoop_mask, [hoop_contour], -1, 255, -1)
            mask = cv2.bitwise_and(mask, cv2.bitwise_not(hoop_mask))

        kernel = np.ones((5, 5), np.uint8)
        mask   = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
        mask   = cv2.morphologyEx(mask, cv2.MORPH_OPEN,  kernel)

        contours, _ = cv2.findContours(
            mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
        )

        clips = []
        for c in contours:
            area = cv2.contourArea(c)
            if area < self.min_clip_area:
                continue
            if area > 20000:         # too large — background metal
                continue

            x, y, w, h = cv2.boundingRect(c)
            aspect = w / (h + 1e-5)

            # Clips are roughly square or slightly wide
            if 0.3 < aspect < 3.0:
                clips.append((x, y, w, h))

        # Sort left to right — return the two most prominent
        clips.sort(key=lambda b: b[0])
        clips.sort(key=lambda b: b[2]*b[3], reverse=True)
        return clips[:2]

    # ------------------------------------------------------------------
    def _is_hoop_between_clips(
        self,
        hoop_contour: np.ndarray,
        clips: List[Tuple[int, int, int, int]],
    ) -> bool:
        """Check if hoop centre x lies between the two clip centres."""
        M = cv2.moments(hoop_contour)
        if M["m00"] == 0:
            return False
        hoop_cx = int(M["m10"] / M["m00"])

        clip_centers_x = sorted([c[0] + c[2] // 2 for c in clips])
        return clip_centers_x[0] < hoop_cx < clip_centers_x[1]
