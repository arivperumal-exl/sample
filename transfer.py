def _count_wires_outside_hoop(
    self,
    image: np.ndarray,
    hoop_mask: np.ndarray,
    annotated: np.ndarray,
) -> int:
    """Count wire clusters outside hoop — excludes holes and metal cutouts."""
    gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)

    # Step 1 — Remove circular holes using Hough circles
    circles = cv2.HoughCircles(
        gray,
        cv2.HOUGH_GRADIENT,
        dp=1,
        minDist=20,
        param1=50,
        param2=30,
        minRadius=5,
        maxRadius=50,
    )
    hole_mask = np.zeros_like(gray)
    if circles is not None:
        circles = np.uint16(np.around(circles))
        for cx, cy, r in circles[0]:
            cv2.circle(hole_mask, (cx, cy), r + 5, 255, -1)

    # Step 2 — Detect wires using color (wires have specific colors)
    # Wires are typically NOT pure black — they have slight color
    hsv = cv2.cvtColor(image, cv2.COLOR_RGB2HSV)

    # Detect colored wires (non-grey, non-black regions)
    # High saturation = colored wire
    saturation = hsv[:, :, 1]
    wire_mask  = cv2.inRange(saturation, 30, 255)   # colored pixels only

    # Also include dark wires (low value, low saturation but cylindrical shape)
    value       = hsv[:, :, 2]
    dark_mask   = cv2.inRange(value, 20, 80)        # dark but not pure black holes

    combined_wire = cv2.bitwise_or(wire_mask, dark_mask)

    # Step 3 — Remove holes, blue hoop and metal sheet cutouts
    # Pure black holes have very low value AND low saturation
    pure_black  = cv2.inRange(value, 0, 20)         # pure black = holes
    combined_wire = cv2.bitwise_and(
        combined_wire, cv2.bitwise_not(pure_black)
    )
    combined_wire = cv2.bitwise_and(
        combined_wire, cv2.bitwise_not(hole_mask)
    )
    combined_wire = cv2.bitwise_and(
        combined_wire, cv2.bitwise_not(hoop_mask)
    )

    # Step 4 — Morphological cleanup
    kernel   = np.ones((5, 5), np.uint8)
    cleaned  = cv2.morphologyEx(combined_wire, cv2.MORPH_OPEN,  kernel)
    cleaned  = cv2.morphologyEx(cleaned,       cv2.MORPH_CLOSE, kernel)

    # Step 5 — Filter by shape — wires are elongated not circular
    contours, _ = cv2.findContours(
        cleaned, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
    )

    wire_clusters = []
    for c in contours:
        area = cv2.contourArea(c)
        if area < 100:              # too small — noise
            continue
        if area > 10000:            # too large — metal sheet
            continue

        # Check aspect ratio — wires are elongated
        x, y, w, h = cv2.boundingRect(c)
        aspect = max(w, h) / (min(w, h) + 1e-5)
        if aspect < 1.5:            # too circular — likely a hole
            continue

        # Check if inside hoop
        M = cv2.moments(c)
        if M["m00"] == 0:
            continue
        cx = int(M["m10"] / M["m00"])
        cy = int(M["m01"] / M["m00"])

        if hoop_mask is not None and hoop_mask[cy, cx] > 0:
            continue                # wire is inside hoop — OK

        wire_clusters.append(c)

    # Draw detected wires outside hoop in red
    for c in wire_clusters:
        cv2.drawContours(annotated, [c], -1, (255, 0, 0), 2)

    return len(wire_clusters)
