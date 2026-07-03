def _detect_clips(
    self,
    region: np.ndarray,
    hoop_contour: Optional[np.ndarray],
) -> List[Tuple[int, int, int, int]]:

    hsv = cv2.cvtColor(region, cv2.COLOR_RGB2HSV)

    # Silver/metallic = low saturation, high brightness
    lower_silver = np.array([0,   0,  180])   # raise brightness threshold
    upper_silver = np.array([180, 40, 255])   # lower saturation threshold
    mask = cv2.inRange(hsv, lower_silver, upper_silver)

    # Remove blue hoop region
    if hoop_contour is not None:
        hoop_mask = np.zeros(region.shape[:2], dtype=np.uint8)
        cv2.drawContours(hoop_mask, [hoop_contour], -1, 255, -1)
        mask = cv2.bitwise_and(mask, cv2.bitwise_not(hoop_mask))

    kernel = np.ones((3, 3), np.uint8)   # smaller kernel — less dilation
    mask   = cv2.morphologyEx(mask, cv2.MORPH_OPEN,  kernel)
    mask   = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)

    contours, _ = cv2.findContours(
        mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
    )

    clips = []
    for c in contours:
        area = cv2.contourArea(c)
        if area < self.min_clip_area:
            continue
        if area > 5000:              # reduce max area — clips are small
            continue

        x, y, w, h = cv2.boundingRect(c)
        aspect = w / (h + 1e-5)

        # Clips are roughly square
        if 0.5 < aspect < 2.0:      # tighter aspect ratio
            clips.append((x, y, w, h))

    # Merge overlapping boxes — nearby detections are the same clip
    clips = self._merge_overlapping_boxes(clips, overlap_thresh=0.3)

    clips.sort(key=lambda b: b[0])              # sort left to right
    clips.sort(key=lambda b: b[2]*b[3], reverse=True)
    return clips[:2]


def _merge_overlapping_boxes(
    self,
    boxes: List[Tuple[int, int, int, int]],
    overlap_thresh: float = 0.3,
) -> List[Tuple[int, int, int, int]]:
    """Merge boxes that overlap significantly into one box."""
    if not boxes:
        return []

    merged = []
    used   = [False] * len(boxes)

    for i, (x1, y1, w1, h1) in enumerate(boxes):
        if used[i]:
            continue
        group = [(x1, y1, w1, h1)]
        for j, (x2, y2, w2, h2) in enumerate(boxes):
            if i == j or used[j]:
                continue
            # Check overlap
            ix = max(x1, x2)
            iy = max(y1, y2)
            iw = min(x1+w1, x2+w2) - ix
            ih = min(y1+h1, y2+h2) - iy
            if iw > 0 and ih > 0:
                overlap = (iw * ih) / min(w1*h1, w2*h2)
                if overlap > overlap_thresh:
                    group.append((x2, y2, w2, h2))
                    used[j] = True
        # Merge group into one bounding box
        gx = min(b[0] for b in group)
        gy = min(b[1] for b in group)
        gw = max(b[0]+b[2] for b in group) - gx
        gh = max(b[1]+b[3] for b in group) - gy
        merged.append((gx, gy, gw, gh))
        used[i] = True

    return merged
