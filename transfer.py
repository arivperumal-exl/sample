"""
Rule-based structural inspector for engine wiring.

Checks:
1. Blue hoop is present
2. Fastenings exist on both sides of the hoop
3. All wires are contained within the blue hoop
"""
import cv2
import numpy as np
from dataclasses import dataclass
from typing import List, Optional, Tuple


@dataclass
class InspectionResult:
    passed: bool
    anomalies: List[str]          # list of failure reasons
    hoop_found: bool
    fastenings_found: int         # count of fastenings detected
    wires_outside_hoop: int       # count of wire clusters outside hoop
    annotated_image: np.ndarray   # image with detections drawn


class StructuralInspector:
    """
    Args:
        blue_hue_range:   HSV hue range for blue hoop detection.
        min_hoop_area:    Minimum contour area to be considered a hoop.
        min_fastening_area: Minimum area for fastening detection.
    """

    def __init__(
        self,
        blue_hue_low:       int = 90,
        blue_hue_high:      int = 130,
        min_hoop_area:      int = 500,
        min_fastening_area: int = 100,
    ):
        self.blue_hue_low       = blue_hue_low
        self.blue_hue_high      = blue_hue_high
        self.min_hoop_area      = min_hoop_area
        self.min_fastening_area = min_fastening_area

    # ------------------------------------------------------------------
    def inspect(self, image: np.ndarray) -> InspectionResult:
        """
        Run full structural inspection on one image.

        Args:
            image: (H, W, 3) uint8 RGB image.

        Returns:
            InspectionResult with pass/fail and details.
        """
        annotated = image.copy()
        anomalies = []

        # Step 1 — Detect blue hoop
        hoop_contour, hoop_mask = self._detect_blue_hoop(image)
        hoop_found = hoop_contour is not None

        if not hoop_found:
            anomalies.append("Blue hoop not found")
        else:
            cv2.drawContours(annotated, [hoop_contour], -1, (0, 255, 0), 2)
            # Label
            M = cv2.moments(hoop_contour)
            if M["m00"] > 0:
                cx = int(M["m10"] / M["m00"])
                cy = int(M["m01"] / M["m00"])
                cv2.putText(annotated, "Hoop", (cx, cy),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)

        # Step 2 — Detect fastenings
        fastenings = self._detect_fastenings(image, hoop_contour)
        fastening_count = len(fastenings)

        for fx, fy, fw, fh in fastenings:
            cv2.rectangle(annotated, (fx, fy), (fx+fw, fy+fh), (255, 165, 0), 2)
            cv2.putText(annotated, "Fastening", (fx, fy-5),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 165, 0), 1)

        if fastening_count < 2:
            anomalies.append(
                f"Expected 2 fastenings, found {fastening_count}"
            )

        # Check hoop is between fastenings
        if hoop_found and fastening_count >= 2:
            if not self._hoop_between_fastenings(hoop_contour, fastenings):
                anomalies.append("Blue hoop is not between the fastenings")

        # Step 3 — Check wires inside hoop
        wires_outside = 0
        if hoop_found:
            wires_outside = self._count_wires_outside_hoop(
                image, hoop_mask, annotated
            )
            if wires_outside > 0:
                anomalies.append(
                    f"{wires_outside} wire(s) detected outside the blue hoop"
                )

        passed = len(anomalies) == 0

        # Draw result banner
        color  = (0, 200, 0) if passed else (0, 0, 255)
        status = "PASS" if passed else "FAIL"
        cv2.rectangle(annotated, (0, 0), (annotated.shape[1], 30), color, -1)
        cv2.putText(annotated, status, (10, 22),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)

        return InspectionResult(
            passed=passed,
            anomalies=anomalies,
            hoop_found=hoop_found,
            fastenings_found=fastening_count,
            wires_outside_hoop=wires_outside,
            annotated_image=annotated,
        )

    # ------------------------------------------------------------------
    def _detect_blue_hoop(
        self, image: np.ndarray
    ) -> Tuple[Optional[np.ndarray], Optional[np.ndarray]]:
        """Detect blue hoop using HSV color segmentation."""
        hsv   = cv2.cvtColor(image, cv2.COLOR_RGB2HSV)
        lower = np.array([self.blue_hue_low,  80,  50])
        upper = np.array([self.blue_hue_high, 255, 255])
        mask  = cv2.inRange(hsv, lower, upper)

        # Clean up mask
        kernel = np.ones((5, 5), np.uint8)
        mask   = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
        mask   = cv2.morphologyEx(mask, cv2.MORPH_OPEN,  kernel)

        contours, _ = cv2.findContours(
            mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
        )
        if not contours:
            return None, None

        # Pick largest blue contour above minimum area
        valid = [c for c in contours
                 if cv2.contourArea(c) > self.min_hoop_area]
        if not valid:
            return None, None

        largest = max(valid, key=cv2.contourArea)
        return largest, mask

    # ------------------------------------------------------------------
    def _detect_fastenings(
        self,
        image: np.ndarray,
        hoop_contour: Optional[np.ndarray],
    ) -> List[Tuple[int, int, int, int]]:
        """
        Detect fastenings using edge detection + contour analysis.
        Returns list of (x, y, w, h) bounding boxes.
        """
        gray    = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)
        edges   = cv2.Canny(blurred, 50, 150)

        kernel    = np.ones((3, 3), np.uint8)
        edges_closed = cv2.morphologyEx(edges, cv2.MORPH_CLOSE, kernel)

        contours, _ = cv2.findContours(
            edges_closed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
        )

        fastenings = []
        for c in contours:
            area = cv2.contourArea(c)
            if area < self.min_fastening_area:
                continue

            x, y, w, h = cv2.boundingRect(c)
            aspect = w / (h + 1e-5)

            # Fastenings are roughly square/circular
            if 0.5 < aspect < 2.0 and area < 5000:
                # Exclude hoop region
                if hoop_contour is not None:
                    cx, cy = x + w // 2, y + h // 2
                    if cv2.pointPolygonTest(
                        hoop_contour, (cx, cy), False
                    ) > 0:
                        continue
                fastenings.append((x, y, w, h))

        # Keep the two largest — most likely the fastenings
        fastenings.sort(key=lambda b: b[2] * b[3], reverse=True)
        return fastenings[:2]

    # ------------------------------------------------------------------
    def _hoop_between_fastenings(
        self,
        hoop_contour: np.ndarray,
        fastenings: List[Tuple[int, int, int, int]],
    ) -> bool:
        """Check if hoop centre x is between the two fastening centres."""
        if len(fastenings) < 2:
            return False

        M   = cv2.moments(hoop_contour)
        if M["m00"] == 0:
            return False
        hoop_cx = int(M["m10"] / M["m00"])

        f_centers = sorted([f[0] + f[2] // 2 for f in fastenings])
        return f_centers[0] < hoop_cx < f_centers[1]

    # ------------------------------------------------------------------
    def _count_wires_outside_hoop(
        self,
        image: np.ndarray,
        hoop_mask: np.ndarray,
        annotated: np.ndarray,
    ) -> int:
        """Count wire clusters that fall outside the hoop boundary."""
        # Wires are typically dark — threshold on grayscale
        gray      = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
        _, wire_mask = cv2.threshold(gray, 60, 255, cv2.THRESH_BINARY_INV)

        # Remove blue hoop pixels from wire mask
        wire_mask = cv2.bitwise_and(
            wire_mask, cv2.bitwise_not(hoop_mask)
        )

        # Outside hoop = wire pixels NOT inside hoop mask
        outside_mask = cv2.bitwise_and(
            wire_mask, cv2.bitwise_not(hoop_mask)
        )

        kernel  = np.ones((3, 3), np.uint8)
        outside = cv2.morphologyEx(outside_mask, cv2.MORPH_OPEN, kernel)

        contours, _ = cv2.findContours(
            outside, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
        )

        wire_clusters = [c for c in contours if cv2.contourArea(c) > 50]

        # Draw wires outside hoop in red
        for c in wire_clusters:
            cv2.drawContours(annotated, [c], -1, (255, 0, 0), 2)

        return len(wire_clusters)
