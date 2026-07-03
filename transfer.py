def _is_hoop_between_clips(
    self,
    hoop_contour: np.ndarray,
    clips: List[Tuple[int, int, int, int]],
) -> bool:
    """
    Check if hoop centre x lies strictly between 
    the right edge of left clip and left edge of right clip.
    """
    if len(clips) < 2:
        return False

    M = cv2.moments(hoop_contour)
    if M["m00"] == 0:
        return False
    hoop_cx = int(M["m10"] / M["m00"])
    hoop_cy = int(M["m01"] / M["m00"])

    # Sort clips left to right by their centre x
    clips_sorted = sorted(clips, key=lambda c: c[0] + c[2] // 2)

    left_clip  = clips_sorted[0]
    right_clip = clips_sorted[1]

    left_clip_right_edge  = left_clip[0]  + left_clip[2]
    right_clip_left_edge  = right_clip[0]

    print(f"  Hoop centre x: {hoop_cx}")
    print(f"  Left clip right edge: {left_clip_right_edge}")
    print(f"  Right clip left edge: {right_clip_left_edge}")

    return left_clip_right_edge < hoop_cx < right_clip_left_edge
