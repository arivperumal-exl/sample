def inspect(
    self,
    image: np.ndarray,
    roi_cfg: dict = None,
) -> InspectionResult:
    """
    Run inspection on full image but restrict detection to ROI region.
    Results are drawn on the full image.
    """
    annotated = image.copy()
    anomalies = []

    # Extract ROI region for detection only
    if roi_cfg and roi_cfg.get("enabled", False):
        x  = roi_cfg["x"]
        y  = roi_cfg["y"]
        rw = roi_cfg["width"]
        rh = roi_cfg["height"]
        region = image[y:y+rh, x:x+rw]   # crop for detection

        # Draw ROI box on full annotated image
        cv2.rectangle(annotated, (x, y), (x+rw, y+rh), (0, 255, 255), 2)
        cv2.putText(annotated, "ROI", (x, y-8),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1)
    else:
        region = image
        x, y = 0, 0   # no offset needed

    # Run all detections on the ROI region
    hoop_contour, hoop_mask = self._detect_blue_hoop(region)
    hoop_found = hoop_contour is not None

    if not hoop_found:
        anomalies.append("Blue hoop not found")
    else:
        # Shift contour coordinates back to full image space
        hoop_contour_full = hoop_contour + np.array([x, y])
        cv2.drawContours(annotated, [hoop_contour_full], -1, (0, 255, 0), 2)
        M = cv2.moments(hoop_contour_full)
        if M["m00"] > 0:
            cx = int(M["m10"] / M["m00"])
            cy = int(M["m01"] / M["m00"])
            cv2.putText(annotated, "Hoop", (cx, cy),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)

    # Fastenings
    fastenings = self._detect_fastenings(region, hoop_contour)
    fastening_count = len(fastenings)

    for fx, fy, fw, fh in fastenings:
        # Shift to full image coordinates
        cv2.rectangle(annotated,
                      (fx+x, fy+y), (fx+x+fw, fy+y+fh),
                      (255, 165, 0), 2)
        cv2.putText(annotated, "Fastening", (fx+x, fy+y-5),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 165, 0), 1)

    if fastening_count < 2:
        anomalies.append(f"Expected 2 fastenings, found {fastening_count}")

    if hoop_found and fastening_count >= 2:
        if not self._hoop_between_fastenings(hoop_contour, fastenings):
            anomalies.append("Blue hoop is not between the fastenings")

    # Wires outside hoop
    wires_outside = 0
    if hoop_found:
        # Create full image sized annotated copy for wire drawing
        region_annotated = region.copy()
        wires_outside = self._count_wires_outside_hoop(
            region, hoop_mask, region_annotated
        )
        if wires_outside > 0:
            anomalies.append(f"{wires_outside} wire(s) detected outside the blue hoop")

        # Copy wire detections back to full image with offset
        # Find red pixels in region_annotated and draw on full image
        red_mask = (
            (region_annotated[:, :, 0] > 200) &
            (region_annotated[:, :, 1] < 50)  &
            (region_annotated[:, :, 2] < 50)
        )
        annotated[y:y+rh, x:x+rw][red_mask] = [255, 0, 0]

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
