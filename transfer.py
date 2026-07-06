def _detect_clips(
    self,
    region: np.ndarray,
    hoop_contour: Optional[np.ndarray],
) -> List[Tuple[int, int, int, int]]:
    """
    Detect metal clips using edge detection + shape filtering.
    Clips are small rectangular metallic clamps over the wires.
    """
    gray    = cv2.cvtColor(region, cv2.COLOR_RGB2GRAY)
    hsv     = cv2.cvtColor(region, cv2.COLOR_RGB2HSV)

    # ── Step 1: Find bright metallic regions ──────────────────────────
    lower_silver = np.array([0,   0,  self.clip_min_brightness])
    upper_silver = np.array([180, 50, 255])
    silver_mask  = cv2.inRange(hsv, lower_silver, upper_silver)

    # ── Step 2: Remove blue hoop ───────────────────────────────────────
    if hoop_contour is not None:
        hoop_mask = np.zeros(region.shape[:2], dtype=np.uint8)
        cv2.drawContours(hoop_mask, [hoop_contour], -1, 255, -1)
        # Also remove area around hoop
        kernel    = np.ones((10, 10), np.uint8)
        hoop_mask = cv2.dilate(hoop_mask, kernel, iterations=1)
        silver_mask = cv2.bitwise_and(
            silver_mask, cv2.bitwise_not(hoop_mask)
        )

    # ── Step 3: Remove large background metal regions ─────────────────
    # Background metal sheet forms very large contours — filter by size
    kernel      = np.ones((3, 3), np.uint8)
    silver_mask = cv2.morphologyEx(silver_mask, cv2.MORPH_OPEN,  kernel)
    silver_mask = cv2.morphologyEx(silver_mask, cv2.MORPH_CLOSE, kernel)

    contours, _ = cv2.findContours(
        silver_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
    )

    # ── Step 4: Filter by size AND rectangularity ─────────────────────
    clips = []
    for c in contours:
        area = cv2.contourArea(c)
        if area < self.min_clip_area:
            continue
        if area > self.max_clip_area:
            continue

        cx, cy, cw, ch = cv2.boundingRect(c)

        # Aspect ratio — clips are wider than tall or roughly square
        aspect = cw / (ch + 1e-5)
        if not (0.4 < aspect < 3.0):
            continue

        # Rectangularity — clip fills most of its bounding box
        # (background metal has irregular shapes, clips are compact)
        rect_area    = cw * ch
        fill_ratio   = area / (rect_area + 1e-5)
        if fill_ratio < 0.4:       # less than 40% fill = irregular shape
            continue

        # Solidity — clip contour is solid, not irregular
        hull          = cv2.convexHull(c)
        hull_area     = cv2.contourArea(hull)
        solidity      = area / (hull_area + 1e-5)
        if solidity < 0.6:         # too irregular
            continue

        clips.append((cx, cy, cw, ch))

    # ── Step 5: Merge overlapping boxes ───────────────────────────────
    clips = self._merge_overlapping_boxes(clips, overlap_thresh=0.3)

    # ── Step 6: Pick the two most central clips ────────────────────────
    # Clips are in the centre of the image over the wires
    # Background metal tends to be at the edges
    img_cx = region.shape[1] // 2
    img_cy = region.shape[0] // 2

    def distance_to_centre(box):
        bx, by, bw, bh = box
        return abs((bx + bw // 2) - img_cx) + abs((by + bh // 2) - img_cy)

    clips.sort(key=distance_to_centre)   # closest to centre first
    return clips[:2]
