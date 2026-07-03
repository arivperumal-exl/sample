def __init__(
    self,
    blue_hue_low=95,
    blue_hue_high=130,
    min_hoop_area=200,
    min_clip_area=300,
    max_clip_area=5000,
    clip_min_brightness=180,
):
    self.blue_hue_low       = blue_hue_low
    self.blue_hue_high      = blue_hue_high
    self.min_hoop_area      = min_hoop_area
    self.min_clip_area      = min_clip_area
    self.max_clip_area      = max_clip_area
    self.clip_min_brightness = clip_min_brightness
