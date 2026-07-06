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
            ix = max(x1, x2)
            iy = max(y1, y2)
            iw = min(x1+w1, x2+w2) - ix
            ih = min(y1+h1, y2+h2) - iy
            if iw > 0 and ih > 0:
                overlap = (iw * ih) / min(w1*h1, w2*h2)
                if overlap > overlap_thresh:
                    group.append((x2, y2, w2, h2))
                    used[j] = True

        gx = min(b[0] for b in group)
        gy = min(b[1] for b in group)
        gw = max(b[0]+b[2] for b in group) - gx
        gh = max(b[1]+b[3] for b in group) - gy
        merged.append((gx, gy, gw, gh))
        used[i] = True

    return merged
